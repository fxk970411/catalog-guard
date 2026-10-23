"""Deterministic validation. No network access; input records are never changed."""
import csv
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit


class InputError(ValueError):
    """Invalid document or configuration."""


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def read_json(path):
    def reject(value):
        raise InputError("Non-finite JSON number: " + value)
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      object_pairs_hook=_object, parse_constant=reject)


def load_rows(path):
    path = Path(path)
    if path.suffix.lower() == ".json":
        rows = read_json(path)
    elif path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            names = reader.fieldnames
            if not names or any(not n.strip() for n in names) or len(set(names)) != len(names):
                raise InputError("CSV requires nonempty, unique headers")
            rows = list(reader)
            if any(None in row or any(v is None for v in row.values()) for row in rows):
                raise InputError("CSV row width does not match header")
    else:
        raise InputError("Input must be .json or .csv")
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise InputError("Input must contain an array of objects")
    for row in rows:
        if any(isinstance(v, (dict, list)) for v in row.values()):
            raise InputError("Only flat records are supported")
    return rows


def config_checked(config):
    allowed = {"id", "required", "enums", "urls", "freshness", "verification", "max_removed_fraction"}
    if not isinstance(config, dict) or set(config) - allowed:
        raise InputError("Config must be an object with documented keys only")
    def field(value):
        return isinstance(value, str) and bool(value.strip())
    if not field(config.get("id")):
        raise InputError("Config requires an id field name")
    for key in ("required", "urls"):
        value = config.get(key, [])
        if not isinstance(value, list) or not all(field(x) for x in value):
            raise InputError(key + " must be a list of field names")
    enums = config.get("enums", {})
    if not isinstance(enums, dict) or any(not field(k) or not isinstance(v, list) or not v or
                                         not all(isinstance(x, str) for x in v) for k, v in enums.items()):
        raise InputError("enums must map field names to nonempty lists of strings")
    freshness = config.get("freshness")
    if freshness is not None:
        if (not isinstance(freshness, dict) or set(freshness) != {"field", "max_age_days"}
                or not field(freshness["field"]) or type(freshness["max_age_days"]) is not int
                or freshness["max_age_days"] < 0):
            raise InputError("freshness requires field and nonnegative integer max_age_days")
    verification = config.get("verification")
    keys = {"status_field", "verified_value", "evidence_field", "error_field"}
    if verification is not None and (not isinstance(verification, dict) or set(verification) != keys
                                    or not all(field(v) for v in verification.values())):
        raise InputError("verification requires status_field, verified_value, evidence_field, error_field")
    limit = config.get("max_removed_fraction", 0.1)
    if type(limit) not in (int, float) or not 0 <= limit <= 1:
        raise InputError("max_removed_fraction must be between 0 and 1")
    return config


def missing(value):
    return value is None or (isinstance(value, str) and not value.strip())


def url_ok(value):
    if not isinstance(value, str) or any(c.isspace() or ord(c) < 32 for c in value):
        return False
    try:
        parsed = urlsplit(value)
        return (parsed.scheme in ("http", "https") and bool(parsed.hostname)
                and parsed.username is None and parsed.password is None and parsed.port != 0)
    except ValueError:
        return False


def analyze(rows, config, baseline=None, today=None):
    """Return a JSON-serializable report; row numbers are 1-based record positions."""
    config_checked(config)
    today = today or date.today()
    findings = []
    def issue(code, message, row=None, field=None, severity="error"):
        findings.append(dict(code=code, severity=severity, row=row, field=field, message=message))
    id_field = config["id"]
    def index(records, label):
        result = {}
        valid = True
        for number, record in enumerate(records, 1):
            key = record.get(id_field)
            if not isinstance(key, str) or not key.strip():
                issue(label + "invalid_id", "ID must be a nonempty string", number, id_field)
                valid = False
            elif key != key.strip():
                issue(label + "invalid_id", "ID must not have surrounding whitespace", number, id_field)
                valid = False
            elif key in result:
                issue(label + "duplicate_id", "ID duplicates an earlier record", number, id_field)
                valid = False
            else:
                result[key] = record
        return result, valid
    current, valid = index(rows, "")
    if not rows:
        issue("empty_catalog", "Catalog has no records")
    for number, row in enumerate(rows, 1):
        for field in config.get("required", []):
            if missing(row.get(field)):
                issue("required", "Required value is missing", number, field)
        for field, values in config.get("enums", {}).items():
            if row.get(field) not in values:
                issue("enum", "Value is not in the allowed list", number, field)
        for field in config.get("urls", []):
            if not missing(row.get(field)) and not url_ok(row[field]):
                issue("url", "Expected an HTTP(S) URL without credentials", number, field)
        fresh = config.get("freshness")
        if fresh:
            field = fresh["field"]
            value = row.get(field)
            try:
                if not isinstance(value, str) or len(value) != 10:
                    raise ValueError()
                stamp = date.fromisoformat(value)
                if stamp.isoformat() != value:
                    raise ValueError()
            except ValueError:
                issue("date", "Expected YYYY-MM-DD", number, field)
            else:
                age = (today - stamp).days
                if age < 0:
                    issue("future_date", "Date is in the future", number, field)
                elif age > fresh["max_age_days"]:
                    issue("stale", "Record exceeds freshness window", number, field, "warning")
        check = config.get("verification")
        if check and row.get(check["status_field"]) == check["verified_value"]:
            if missing(row.get(check["evidence_field"])):
                issue("missing_evidence", "Verified status requires evidence", number, check["evidence_field"])
            if not missing(row.get(check["error_field"])):
                issue("verification_conflict", "Verified status conflicts with an error", number, check["error_field"])
    diff = None
    if baseline is not None:
        previous, previous_valid = index(baseline, "baseline_")
        if valid and previous_valid:
            added = sorted(current.keys() - previous.keys())
            removed = sorted(previous.keys() - current.keys())
            changed = []
            for key in sorted(current.keys() & previous.keys()):
                left, right = current[key], previous[key]
                fields = sorted(k for k in left.keys() | right.keys()
                                if (k in left) != (k in right)
                                or type(left.get(k)) is not type(right.get(k))
                                or left.get(k) != right.get(k))
                if fields:
                    changed.append({"id": key, "fields": fields})
            fraction = len(removed) / len(previous) if previous else 0
            diff = dict(added=added, removed=removed, changed=changed, removed_fraction=fraction)
            if fraction > config.get("max_removed_fraction", 0.1):
                issue("mass_removal", "Removed fraction exceeds configured limit")
        else:
            issue("diff_unavailable", "Fix missing or duplicate IDs before comparing snapshots")
    errors = sum(f["severity"] == "error" for f in findings)
    warnings = len(findings) - errors
    return dict(schema_version=1, as_of=today.isoformat(), records=len(rows),
                errors=errors, warnings=warnings, findings=findings, diff=diff)
