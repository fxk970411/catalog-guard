# Catalog Guard

**Catch broken catalog updates before you publish them.**

[中文使用说明](docs/README.zh-CN.md) · [Rules](docs/RULES.md) · [Release guide](docs/RELEASE.md)

Catalog Guard is a small, offline command-line quality gate for CSV and JSON directories: libraries, community resources, store lists, and other public catalogs. It checks required values, duplicate IDs, allowed statuses, URL syntax, freshness, and contradictory verification metadata. Compare with a previous snapshot to flag accidental mass removals.

**Status: initial 0.1.0 implementation.** No adoption claims, external audits, or production deployment are implied. Python 3.10+; no runtime dependencies, accounts, API keys, telemetry, or network requests. MIT licensed.

## Try it in one minute

From this project folder, run:

```sh
python3 -m catalog_guard examples/good.csv --config examples/rules.json --today 2026-10-23
```

Expected: `Catalog Guard: 2 records, 0 errors, 0 warnings`.

Try a deliberately broken fixture (expected exit status **1**):

```sh
python3 -m catalog_guard examples/broken.json --config examples/rules.json --today 2026-10-23
```

It finds duplicate IDs, a missing name, an unsafe URL scheme, missing verification evidence, an API-error/status conflict, and a stale record. All fixtures are fictional; `example.org` links are not evidence of real services.

## Compare updates

```sh
python3 -m catalog_guard examples/good.csv --config examples/rules.json --baseline examples/baseline.json --today 2026-10-23
```

Expected: one changed record and one removal. Removing 1 of 3 records exceeds the configured 25% limit and fails the gate. Records compare exactly, including data types and missing versus null fields. Use the same export format for both snapshots to avoid type-only changes.

## Share a report

```sh
python3 -m catalog_guard examples/good.csv --config examples/rules.json --today 2026-10-23 --format html --output report.html
python3 -m catalog_guard examples/good.csv --config examples/rules.json --today 2026-10-23 --format json --output report.json
```

Open `report.html` in a browser. Reports are standalone and contain no scripts or remote resources. Output paths must be new; existing files are never overwritten. Diff reports contain record IDs and field names, so review them before publishing.

## Install locally (optional)

Direct execution above needs no installation. To get the `catalog-guard` command:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
catalog-guard --version
```

On Windows use `py` for Python and `.venv\Scripts\activate` to activate. Build installation may download setuptools; the checker itself runs offline. The distribution name `catalog-guard-local` is provisional and has not been registered on PyPI.

## Use it as a release gate

Exit statuses: **0** checks passed; **1** findings block publication; **2** input/configuration/output error. Stale data is a warning unless `--strict` is set. Without `--today`, the local system date is used. A passing result validates configured structure and consistency, **not truth, address deliverability, source authenticity, or URL availability**.

Add this command before your publish step, using your own paths:

```sh
python3 -m catalog_guard data/current.json --config rules.json --baseline data/previous.json --strict
```

Do not use `continue-on-error` for a publication gate. See [GitHub example](docs/RELEASE.md). There is no scraping, enrichment, automatic data correction, or automatic promotion from pending to verified.

## Development

```sh
python3 -m unittest discover -s tests -v
```

The GitHub workflow is configured for Python 3.10–3.13 on Linux and Python 3.12 on Windows/macOS. These remote jobs run after upload; their configuration is not evidence that they have run. See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [roadmap](docs/ROADMAP.md).

The project intentionally stays narrower than a general schema-validation framework: one small config plus snapshot protection and verification-state checks. Use a full schema tool when you need nested structures, coercion, or complex validation expressions.
