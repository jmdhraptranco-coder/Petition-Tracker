# Audit Precheck

## Verified Locally

- App imports and Flask route map build successfully in `app.py`.
- Python files compile cleanly:
  - `app.py`
  - `models.py`
  - `config.py`
  - `create_admin.py`
  - `serve.py`
  - `wsgi.py`
  - `setup_field_inspectors.py`
- Functional tests pass with cache disabled and no coverage gate:
  - `python -m pytest -q --no-cov -p no:cacheprovider`
- Template `url_for(...)` references resolve; no missing endpoint names.
- Static asset references resolve; no missing referenced files under `static/`.
- Translation JSON files parse correctly:
  - `static/i18n/en.json`
  - `static/i18n/te.json`
- Referenced i18n keys are covered in the English catalog.
- Upload/download code paths are guarded by petition/file resolution checks in `app.py`.
- Overdue workflow remains distinguishable with persistent overdue tagging in:
  - `models.py`
  - `templates/petitions_list.html`
  - `templates/petition_view.html`

## Needs Live-Environment Validation

- Real database connectivity and migrations against staging/production PostgreSQL.
- Real browser validation for:
  - mobile layout
  - dark/light theme rendering
  - chart rendering
  - modal interactions
  - upload UX
- End-to-end upload/download validation for:
  - e-receipts
  - enquiry report PDFs
  - permission copy PDFs
  - profile photos
- Role-based workflow validation with actual users:
  - DEO
  - CVO/DSP
  - Inspector
  - PO
  - CMD/CGM
- Telugu visual validation for long labels and wrapping.
- Production security headers and cookie behavior under deployed config.
- Reverse proxy / WSGI behavior in deployed environment.

## Known Non-Product Issue

- Default `pytest` can still fail in this workspace because:
  - `pyproject.toml` enforces `--cov-fail-under=90`
  - local `.pytest_cache` is corrupted/inaccessible

This is a tooling/workspace issue, not an application runtime failure.

## Recommended Auditor Handoff Note

- Static code validation passed.
- Functional test suite passed locally with cache disabled.
- Route, template, asset, and translation integrity checks passed.
- Live environment validation is still required for deployment-specific security, DB, uploads, and browser behavior.
