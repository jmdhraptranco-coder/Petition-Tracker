# OWASP Top 10 Traceability (2021)

Scope: Flask app (`app.py`, `models.py`, templates, config).

Status legend:
- `Implemented`: control exists in code now.
- `Partial`: some controls exist; additional audit controls still needed.
- `Gap`: material control missing.

## A01: Broken Access Control - `Partial`

Implemented:
- Session/role gate decorators on protected routes (`login_required`, `role_required`) in `app.py:1130`, `app.py:1139`.
- Petition-level object authorization guard (`_can_access_petition`) in `app.py:834`.
- Petition view/action now check access in `app.py:2492`, `app.py:2532`.
- File access check tied to petition ownership/scope in `app.py:3269`, `app.py:3281`.
- Profile photo owner check in `app.py:3293`.

Remaining gaps:
- `/api/inspectors/<cvo_id>` only requires login; it can enumerate other CVO inspector names (`app.py:4019`).

Audit action:
- Add role/scope validation in `api_inspectors` so non-authorized users cannot query arbitrary `cvo_id`.

## A02: Cryptographic Failures - `Partial`

Implemented:
- Password hashing via Werkzeug (`generate_password_hash`, `check_password_hash`) in `models.py:4`, `models.py:204`, `models.py:324`.
- Secure session cookie flags in `app.py:30`, `app.py:31`, `app.py:32`.
- HSTS in production in `app.py:884`.
- Password complexity enforcement in `app.py:738`.

Remaining gaps:
- Database SSL mode defaults to `prefer` (downgrade possible) in `config.py:138`.
- No explicit encryption-at-rest control documented for uploaded files/database.

Audit action:
- Set `DB_SSLMODE=require` (or stronger, verify-ca/full) for production.
- Document and enforce storage encryption controls operationally.

## A03: Injection - `Partial`

Implemented:
- SQL calls are predominantly parameterized (`cur.execute(..., params)`) across `models.py` (e.g., `models.py:322`, `models.py:950`).
- User file names sanitized with `secure_filename` in `app.py:396`, `app.py:671`, `app.py:717`, `app.py:3265`.
- PDF and image upload validation in `app.py:667`, `app.py:713`.

Remaining gaps:
- Dynamic SQL construction exists (`f"...{...}..."`) in a few functions (`models.py:495`, `models.py:520`, `models.py:1163`, `models.py:2100`, `models.py:2263`). Current use is controlled but should be explicitly constrained and reviewed in audit.

Audit action:
- Keep only allowlisted dynamic fragments and document that constraint in code comments/tests.

## A04: Insecure Design - `Partial`

Implemented:
- Workflow state validation before transitions (e.g., detailed-enquiry routing checks) in `app.py:3013`, `app.py:3018`.
- Additional guards on petition action flow and role checks in `app.py:2530+`.

Remaining gaps:
- No formal threat model/abuse-case documentation in repo.
- No explicit business-rule security test matrix artifact for all role/state transitions.

Audit action:
- Add a short threat model + role/state transition matrix as security evidence.

## A05: Security Misconfiguration - `Partial`

Implemented:
- Security headers centralized in `@app.after_request` (`app.py:875`).
- CSRF validation on unsafe methods in `app.py:858`.
- Global request size limit in `app.py:33`.
- Production-only debug disabled by config guard in `config.py:57`.
- `.env` ignored by git (`.gitignore:1`).

Remaining gaps:
- Many user-facing flashes include raw exception strings (examples: `app.py:2236`, `app.py:3258`, `app.py:3637`), which may leak internals.
- CSP currently allows `'unsafe-inline'` scripts/styles (`app.py:887`).

Audit action:
- Replace `str(e)` messages with generic user message + server-side logging.
- Migrate toward nonce/hash-based CSP to remove `'unsafe-inline'`.

## A06: Vulnerable and Outdated Components - `Gap`

Implemented:
- Minimal dependency list is maintained in `requirements.txt`.

Remaining gaps:
- Version ranges are broad (`>=`), no lockfile/pinned production set (`requirements.txt`).
- No automated SCA evidence (e.g., `pip-audit`) in repo/CI.

Audit action:
- Introduce pinned dependencies and regular vulnerability scans in CI.

## A07: Identification and Authentication Failures - `Partial`

Implemented:
- Password complexity checks now enforced (`app.py:738`).
- Brute-force login throttling/temporary block (`app.py:809`, `app.py:1415`).
- Session rotation on login (`session.clear()`) in `app.py:1091`.

Remaining gaps:
- Login throttling is in-memory and per-process (not durable across restarts or multi-instance deployment).
- No password history / compromised-password check.

Audit action:
- Move rate-limit state to shared store (Redis/DB) for production scale.

## A08: Software and Data Integrity Failures - `Partial`

Implemented:
- Startup schema updates are gated (`SKIP_SCHEMA_UPDATES`) in `app.py:36`.

Remaining gaps:
- No signed dependency verification / trusted artifact pipeline evidence.
- No CI policy artifact showing integrity gates before deployment.

Audit action:
- Add CI integrity controls: pinned hashes, artifact provenance, branch protection.

## A09: Security Logging and Monitoring Failures - `Gap`

Implemented:
- Functional workflow tracking exists (`petition_tracking` table updates across `models.py`), useful for business audit trail.

Remaining gaps:
- No dedicated security-event logging (failed login, lockout triggers, authorization denials) with alerting.
- No documented retention/monitoring policy in repo.

Audit action:
- Add structured security logs and alert hooks for auth/access anomalies.

## A10: Server-Side Request Forgery (SSRF) - `Partial`

Implemented:

Remaining gaps:

Audit action:

## Quick Audit Readiness Checklist

- [x] CSRF protection enabled for authenticated state-changing requests.
- [x] Security headers added globally.
- [x] Session hardening and rotation implemented.
- [x] File upload validation and path safety checks in place.
- [x] Petition-level object authorization added.
- [x] Password complexity policy enforced.
- [ ] Replace raw exception flashes with sanitized messaging.
- [ ] Add scoped authorization for `/api/inspectors/<cvo_id>`.
- [ ] Add dependency SCA evidence + pinned lock strategy.
- [ ] Add security-event logging + monitoring evidence.
