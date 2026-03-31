# Nigaa VAPT Remediation Plan

## Scope

This plan is limited to the findings listed in `Nigaa Web Application VAPT First Audit Report` dated `30-03-2026`:

- `NIG001` Improper Session Validation
- `NIG002` Sensitive Data Stored in Client-Side Cookies
- `NIG003` Insecure Password Policy
- `NIG004` Improper Session Handling
- `NIG005` Open Redirection Vulnerability
- `NIG006` Lack of Rate Limiting
- `NIG007` Improper CAPTCHA Implementation

This document is based on:

- Thorough review of the audit report PDF
- Review of current application code in `app.py`, `models.py`, `config.py`, templates, and existing audit notes
- Comparison of audit observations against the present codebase, not assumptions about earlier builds

## Executive Assessment

The current codebase already contains some security hardening not reflected in the report, including CSRF checks, login-session reset on successful authentication, baseline security headers, password-strength validation, and login brute-force lockout. However, the report findings still map to real or partially real weaknesses in the application as it exists today.

Most important conclusion:

- `NIG002`, `NIG003`, `NIG004`, `NIG006`, and `NIG007` still appear materially valid in the current codebase.
- `NIG001` appears partially mitigated in the login flow, but the root trust model is still weak because authenticated state and role-bearing session data are stored in Flask client-side session cookies.
- `NIG005` needs cleanup even if the exact proof of concept used by the auditor was against an older redirect path, because the current code still performs redirects using request-controlled referrer values.

## Finding-by-Finding Plan

### NIG001: Improper Session Validation

Severity: `High`

Status: `Code remediation completed on 31-03-2026; deployment retest pending`

Current code observations:

- Successful login resets the session with `session.clear()` before authenticated state is re-established in `app.py`.
- Authenticated identity and authorization context are then written into Flask session cookies:
  - `user_id`
  - `username`
  - `full_name`
  - `user_role`
  - `cvo_office`
  - `phone`
  - `email`
  - `profile_photo`
- These values are later trusted throughout the app for access-control decisions.

Assessment:

- The login flow is better than the audit implies because session fixation mitigation is already present.
- The larger issue still remains: session state is client-side and the app depends heavily on cookie-carried role and identity data.
- Even when signed, this is the wrong trust boundary for a multi-role internal application.

Remediation plan:

1. Move from Flask client-side sessions to server-side session storage.
2. Store only an opaque session identifier in the browser cookie.
3. Resolve the current user and role from server-side state on each request.
4. Add explicit session metadata server-side:
   - session id
   - user id
   - issued at
   - last activity
   - auth method
   - optional client fingerprint fields for anomaly detection
5. Regenerate the session identifier after each successful authentication and after privilege-changing events.
6. Add server-side invalidation support so sessions can be revoked immediately.
7. Reduce direct reliance on raw `session['user_role']` and similar fields in route logic; prefer a refreshed server-side user context.

Implementation notes:

- Introduce a server-side session backend before changing auth behavior in multiple routes.
- Refactor shared auth helpers first, then update route guards and current-user refresh logic.

Validation evidence:

- Attempted reuse or tampering of stale session cookies must fail.
- Session identifier changes after login.
- Access-control checks continue to work after browser cookie modification attempts.
- New regression tests for login, role checks, and invalid session replay.

### NIG002: Sensitive Data Stored in Client-Side Cookies

Severity: `Medium`

Status: `Code remediation completed on 31-03-2026; deployment retest pending`

Current code observations:

- The app uses Flask signed cookie sessions.
- Sensitive and authorization-relevant fields are stored in the cookie-backed session.
- The login CAPTCHA answer is also stored in session, which means it is client-side too.

Assessment:

- This finding is valid in the current codebase.
- Signed cookies protect integrity only if the secret stays safe; they do not remove exposure of readable values to the client.
- Role-bearing and workflow-bearing data should not live in browser-managed session content.

Remediation plan:

1. Eliminate storage of user role, profile attributes, and security workflow state in client-side cookies.
2. Move the following state server-side:
   - authenticated user context
   - OTP pending state
   - forced first-login password-change state
   - password reset workflow state
   - CAPTCHA answer/challenge state
3. Keep the browser cookie minimal:
   - opaque session id
   - secure attributes only
4. Review and minimize every `session[...]` assignment in auth and profile flows.
5. Add a cookie-content review step to ensure no sensitive business or auth state is exposed.

Validation evidence:

- Browser cookie contents no longer reveal user role, user id, phone, email, or CAPTCHA answer.
- Cookie tampering does not affect server-side authorization.
- Security review checklist completed for all session keys.
- Anonymous public pages no longer create persistent session records or emit session cookies.

### NIG003: Insecure Password Policy

Severity: `Medium`

Status: `Code remediation completed on 31-03-2026; deployment retest pending`

Current code observations:

- Password strength checks exist.
- In `/profile`, a logged-in user can change password by entering only:
  - `new_password`
  - `confirm_password`
- No current password verification is required before `models.set_user_password(...)` is called.

Assessment:

- This finding is valid in the current codebase for the profile password-change flow.
- Password complexity is enforced, but current-password verification is missing.

Remediation plan:

1. Update the profile password-change form to require `current_password`.
2. Verify the submitted current password against the authenticated user before allowing password update.
3. Reject the change on mismatch with audit logging.
4. Preserve exceptions only for dedicated recovery flows:
   - first-login forced reset
   - forgot-password OTP reset
   - admin-issued reset to default
5. Add user notification hooks for password changes if the deployment supports SMS or email alerts.

Validation evidence:

- Password change without the correct current password must fail.
- Password change with the correct current password must succeed.
- Recovery and first-login flows must continue to work without regression.
- Tests added for success, wrong-current-password, and blank-current-password cases.

### NIG004: Improper Session Handling

Severity: `Medium`

Status: `Code remediation completed on 31-03-2026; deployment retest pending`

Current code observations:

- In `/profile`, after password change the code calls `refresh_session_user()` and keeps the session active.
- No logout-all-sessions capability exists.
- Password reset flows do not currently invalidate other sessions for the same user.

Assessment:

- This finding is valid in the current codebase.
- The app changes credentials but does not force re-authentication after a sensitive credential event.

Remediation plan:

1. Invalidate the active session immediately after any self-service password change.
2. Invalidate all active sessions for that user after:
   - profile password change
   - forgot-password completion
   - admin reset to default password
3. Redirect the user to login with a success message after password updates.
4. If server-side sessions are introduced for `NIG001/NIG002`, implement per-user session revocation there.
5. Add a security event for session revocation after credential changes.

Validation evidence:

- Existing session cannot be used after password change.
- Other active sessions for the same user are rejected after password reset.
- Tests added for forced re-login and post-reset session invalidation.

### NIG005: Open Redirection Vulnerability

Severity: `Low`

Status: `Code remediation completed on 31-03-2026; deployment retest pending`

Current code observations:

- The code redirects to request-controlled referrer values in at least these places:
  - upload-size handler fallback
  - CSRF failure handler fallback
- Petition import redirect behavior is currently allowlisted and appears safe.

Assessment:

- The exact auditor proof may have targeted an earlier redirect parameter, but the present code still contains unsafe redirect patterns.
- Referrer-based redirects should be treated as untrusted unless validated.

Remediation plan:

1. Replace direct redirects to `request.referrer` or `Referer` with safe internal fallbacks.
2. Introduce a shared helper such as `safe_redirect_target(...)` that:
   - accepts only relative internal paths, or
   - validates against the application origin/allowlist
3. Refactor all redirect flows to use that helper.
4. Search the codebase for any future `next`, `return_to`, `referrer`, or raw redirect-target usage and standardize it.

Validation evidence:

- External redirect targets are rejected.
- Internal expected navigation still works.
- Tests added for malicious external values and valid internal values.

### NIG006: Lack of Rate Limiting

Severity: `Low`

Status: `Code remediation completed on 31-03-2026; deployment retest pending`

Current code observations:

- Login brute-force protection exists through in-memory IP-based tracking.
- No equivalent throttling exists for new petition creation in `/petitions/new`.
- The audit's described abuse pattern maps directly to the petition submission workflow.

Assessment:

- This finding is valid in the current codebase.
- The current protection is limited to authentication and does not cover business-action abuse.
- The implementation has been additionally hardened with database-backed counters and a `super_admin` settings screen for production-safe threshold tuning.

Remediation plan:

1. Add rate limiting to petition creation based on:
   - user id
   - client IP
   - optionally role
2. Define a practical throttle window for the data-entry workflow without harming legitimate staff usage.
3. Add cooldown handling and user-facing messaging for `429` responses.
4. Log repeated high-frequency petition creation attempts as security events.
5. Prefer a backend-backed limiter over in-memory structures so behavior is consistent across workers/restarts.

Validation evidence:

- Rapid repeated petition submissions trigger throttling.
- Normal operator usage remains unaffected under expected volume.
- Tests added for allowed requests, blocked bursts, and reset after cooldown.

### NIG007: Improper CAPTCHA Implementation

Severity: `Low`

Status: `Code remediation completed on 31-03-2026; deployment retest pending`

Current code observations:

- The login page renders a simple arithmetic CAPTCHA in plain text.
- The expected answer is stored in the Flask session.
- Because session data is client-side in the current design, CAPTCHA state is exposed to the browser.

Assessment:

- This finding is valid in the current codebase.
- The issue is broader than "copying" the CAPTCHA; the current challenge is predictable, machine-readable, and tied to client-side state.

Remediation plan:

1. Replace the arithmetic text CAPTCHA with a stronger server-validated challenge.
2. Store CAPTCHA state only server-side.
3. Ensure the challenge is not trivially extractable from page markup or cookie contents.
4. Refresh the challenge after failed attempts and after successful authentication transitions.
5. Consider whether CAPTCHA is still needed once stronger login throttling and OTP controls are in place; if retained, use it as a secondary friction layer, not the primary defense.

Validation evidence:

- CAPTCHA answer is no longer present in browser cookie data.
- Automated replay of a stale challenge fails.
- Login flow still works for normal users and refresh behavior remains stable.

## Recommended Delivery Order

1. Complete `NIG001` and `NIG002` together because both require session architecture changes.
2. Complete `NIG004` in the same stream because session invalidation depends on the new session model.
3. Fix `NIG003` in parallel or immediately after, since it is isolated to the profile password-change flow.
4. Fix `NIG005` and `NIG006` next because they are localized and lower-risk refactors.
5. Replace the CAPTCHA design in `NIG007` after the session changes, so it is not built on the old cookie model.

## Testing and Evidence Plan

For closure of this audit report, each finding should end with:

- code change completed
- automated test coverage added
- manual proof-of-fix recorded
- deployment verification completed on the actual hosted environment
- retest evidence prepared for the auditor

Minimum retest checklist:

1. Session replay/tamper attempt fails.
2. Browser cookie no longer contains sensitive identity/role state.
3. Profile password change requires current password.
4. Password change forces re-login and revokes existing sessions.
5. External redirect payloads are blocked.
6. Petition burst submission returns throttling.
7. CAPTCHA challenge is no longer readable or solvable from cookie/page state alone.

## Important Note About Current State

The audit report appears to have been conducted against the deployed application available at the time of testing between `26-03-2026` and `30-03-2026`. The current repository already contains some hardening that may not have been present in that exact deployed build. Even so, this plan intentionally treats only the issues that still matter after code review, so remediation work stays aligned with both the audit report and the present application.
