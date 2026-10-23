# Configuration and data contract

Configuration is a JSON object; unknown keys fail to catch typos. See `examples/rules.json` for a complete example.

| Key | Meaning | Default |
| --- | --- | --- |
| `id` | Required field name; values must be unique nonempty strings without edge whitespace | required |
| `required` | Fields whose values cannot be absent, null, empty or whitespace-only | `[]` |
| `enums` | Map field names to nonempty lists of permitted strings; absence is an error | `{}` |
| `urls` | Fields checked for HTTP(S) syntax without embedded credentials when nonempty | `[]` |
| `freshness` | Object with `field` and nonnegative integer `max_age_days`; requires canonical YYYY-MM-DD | omitted |
| `verification` | Object with `status_field`, `verified_value`, `evidence_field`, `error_field` | omitted |
| `max_removed_fraction` | Allowed number removed / baseline count; only strictly greater fails | `0.1` |

For the configured verified status, evidence must be nonempty and the error field empty/absent. This checks consistency only. To check evidence URL syntax, also put that field in `urls`. To require a URL even for pending records, also include it in `required`. Boolean false and number zero are present values, not missing values; an error field containing either is therefore nonempty.

JSON must be a top-level array of flat objects; CSV must have unique nonblank headers and consistent row width. UTF-8 and UTF-8 BOM are supported. CSV values stay strings; JSON scalar types are preserved. Duplicate JSON keys, nonstandard non-finite numbers, nested values and unknown extensions are rejected. CSV blank physical lines are skipped by the standard CSV reader. Fully empty catalogs fail. ID matching is exact and case sensitive; there is no hidden normalization.

Freshness: future dates and invalid/missing dates are errors. Age greater than the limit is a warning, upgraded to failing exit status by `--strict`. The timezone is the local machine's date unless `--today` is supplied.

Baseline records are used for ID integrity and comparison only, not revalidated against current required-field/freshness rules. Ambiguous IDs on either side disable comparison and fail the gate. An empty baseline permits an initial import. No baseline means no removal check.

JSON output schema version is `1`: `as_of`, `records`, `errors`, `warnings`, `findings`, `diff`. Findings have `code`, `severity`, `row`, `field`, `message`. Rows are 1-based record positions, not physical CSV line numbers. Diff contains sorted `added` and `removed` IDs, `changed` objects with ID and changed field names, and `removed_fraction`. No values are automatically redacted from IDs/field names.

Limits: entire files and reports are held in memory; intended for small trusted local datasets. No streaming or hard resource cap. URL checks do not contact servers or enforce public IP destinations. A passing check never proves that a verified claim is true.
