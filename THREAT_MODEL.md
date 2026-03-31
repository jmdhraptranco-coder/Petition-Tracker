# Lightweight Threat Model

## Scope

This model covers the main security-sensitive surfaces in the Nigaa application:

- authentication and sessions
- password recovery and reset
- petition submission and workflow transitions
- file upload and file download paths
- admin-only configuration and user-management actions

## Trust Boundaries

1. Browser to web application
- Untrusted client input.
- Browser cookie should not carry trusted role/profile state.

2. Web application to database
- Trusted persistence boundary for users, petitions, sessions, settings, and counters.

3. Web application to file storage
- Uploaded content must be validated and access-controlled.

4. Web application to external OTP integration
- Outbound dependency requiring URL and transport controls.

## Primary Assets

- authenticated session state
- user accounts and roles
- petition records and attached files
- password reset / OTP state
- admin settings and workflow privileges
- security logs and audit trails

## Main Threats and Current Mitigations

### 1. Session misuse or stale-session reuse

Threat:
- attacker reuses stale session state, tampers with cookie-held auth data, or keeps using session after password change

Mitigations:
- server-side sessions
- opaque session cookie
- session version checks
- issued/last-activity metadata
- inactivity expiry
- session invalidation after credential events

### 2. Password change without sufficient proof

Threat:
- attacker with temporary session access changes victim password without knowing the old one

Mitigations:
- current password required for self-service profile password change
- wrong current password rejected
- re-login forced after password change

### 3. CAPTCHA bypass or replay

Threat:
- attacker reads answer from page state or reuses same challenge repeatedly

Mitigations:
- server-served CAPTCHA image
- answer retained server-side
- single-use token
- expiry enforcement

### 4. Open redirect abuse

Threat:
- attacker sends user through crafted redirect to external phishing destination

Mitigations:
- validated internal-only redirect helper
- external/protocol-relative/malformed targets rejected
- safe fallbacks used

### 5. Petition abuse / automated burst creation

Threat:
- attacker floods petition creation endpoint to degrade operations or create junk records

Mitigations:
- per-user throttling
- per-IP throttling
- persistent counters
- admin-controlled tuning
- `429` behavior for excessive bursts

### 6. Unauthorized file access

Threat:
- user downloads petition/help-resource files outside allowed scope

Mitigations:
- file access tied to petition/resource checks
- inactive help-resource files blocked from non-admins
- path handling remains server-controlled

### 7. Role escalation / stale authorization

Threat:
- stale role values remain trusted after admin role change

Mitigations:
- protected requests resolve current trusted user from DB
- role checks follow refreshed state
- invalid session state is cleared

## Residual Risks Requiring Operational Controls

- production secret storage and rotation
- centralized log retention and alerting
- reverse-proxy correctness for TLS and client IP trust
- CI/SCA execution evidence
- production database encryption and backup controls

## Recommended Auditor Message

The major application-level abuse cases from the VAPT findings are now addressed in code. Remaining assurance items are primarily deployment, logging, infrastructure, and governance evidence rather than missing application controls.
