# Nigaa VAPT Resolution Summary

## Purpose

This document is the implementation companion to [PLAN.md](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/PLAN.md).

It records:

- what was changed for each audit finding
- how the new control works
- what user-visible behavior changed, if any
- what still remains for final closure

This summary is limited to the findings from the `Nigaa Web Application VAPT First Audit Report`.

## Resolution Status

- `NIG001` Code remediation completed
- `NIG002` Code remediation completed
- `NIG003` Code remediation completed
- `NIG004` Code remediation completed
- `NIG005` Code remediation completed
- `NIG006` Code remediation completed
- `NIG007` Code remediation completed

Final audit closure still requires:

- deployment to the real environment
- restart/reload of the application
- live retest evidence

## NIG001: Improper Session Validation

### Changes made

- Replaced the old client-side Flask session storage model with a server-side session backend.
- Added persistent `server_sessions` storage in the database.
- Added stricter authenticated session validation using:
  - session id
  - user id
  - session version
  - issued time
  - last activity time
  - auth method
- Updated `login_required` to validate trusted user state on each request.
- Updated `role_required` to use refreshed database-backed user role instead of relying only on cached session role data.
- Added inactivity/session-expiry handling.
- Added session id rotation during authentication-state changes.

### How it works now

- The browser stores only an opaque session id cookie.
- On each authenticated request, the app loads the current session from the server.
- The app validates that:
  - the session exists
  - the linked user still exists
  - the user is active
  - the session version still matches the user record
  - the session metadata is present and not stale
- If validation fails, the session is cleared and the user is sent back to login.
- Authorization now follows the trusted current user loaded from the database.

### Behavior impact

- Valid users should see no workflow change.
- Stale, inactive, revoked, or out-of-date sessions are rejected more strictly.
- If an admin changes a user role or password, old session trust is reduced immediately.

## NIG002: Sensitive Data Stored in Client-Side Cookies

### Changes made

- Moved session storage from client-side signed cookies to server-side storage.
- Added persistent session storage in the database.
- Stopped exposing role/profile/auth state in browser cookie contents.
- Added an opaque-cookie regression test.
- Fixed anonymous public pages so they no longer create unnecessary persistent sessions.

### How it works now

- The session cookie is now only a lookup key.
- User information such as:
  - role
  - username
  - phone
  - email
  - profile information
  - reset workflow state
  stays on the server side.
- Public anonymous pages do not create session records unless state is actually needed.

### Behavior impact

- No expected UI change for normal users.
- Browser cookie contents are now safer and much smaller.

## NIG003: Insecure Password Policy

### Changes made

- Added `current_password` requirement for self-service password change in the profile page.
- Added server-side current-password verification before applying the new password.
- Left first-login, forgot-password, and admin reset flows as scoped exceptions.

### How it works now

- A logged-in user cannot change the password from `My Profile` unless the current password is correct.
- Wrong or missing current password causes the change to be rejected.
- Recovery and first-login flows continue to work through their dedicated paths.

### Behavior impact

- Profile password change now requires one additional field: current password.

## NIG004: Improper Session Handling

### Changes made

- Added `session_version` enforcement.
- Password changes and reset flows now invalidate outdated sessions.
- Profile password changes now force re-login.
- Session revocation after credential changes is enforced centrally.

### How it works now

- When password-related events occur, the user record session version increases.
- Old sessions fail the version check and are rejected.
- The user must log in again with fresh credentials/session state.

### Behavior impact

- After a password change or reset, existing sessions will not continue working.

## NIG005: Open Redirection Vulnerability

### Changes made

- Added a shared safe redirect helper.
- Replaced unsafe referrer-based redirect fallbacks with validated internal-only redirect handling.

### How it works now

- Redirect targets are accepted only if they are safe internal relative paths.
- External URLs, malformed targets, protocol-relative targets, and backslash tricks are rejected.
- Unsafe redirect attempts fall back to known internal routes.

### Behavior impact

- Normal internal navigation is unaffected.
- Malicious or tampered redirect attempts no longer send users to external destinations.

## NIG006: Lack of Rate Limiting

### Changes made

- Added petition submission throttling for `/petitions/new`.
- Split throttling into:
  - per-user limits
  - per-IP limits
- Moved limiter persistence into the database for restart/multi-worker safety.
- Added `super_admin` settings UI for admin-controlled tuning.
- Added safer client-IP handling so spoofed proxy headers are not trusted by default.
- Added protection for inactive help-resource access found during the broader review.

### How it works now

- Petition creation checks both the user and IP submission rate.
- Excessive burst submissions are blocked with throttling behavior.
- Limits persist across restarts and workers because counters are stored in the database.
- Admins can tune thresholds from the application UI instead of editing `.env` every time.
- By default, the app uses `REMOTE_ADDR` for IP-based controls.
- `X-Forwarded-For` is used only if `TRUST_PROXY_HEADERS=1` is explicitly enabled.

### Behavior impact

- Normal users should not notice changes during ordinary work.
- Users who submit petitions too quickly will see throttling/block behavior.
- Multiple DEOs on the same office network are handled more safely because IP and user thresholds are separate.

## NIG007: Improper CAPTCHA Implementation

### Changes made

- Removed the old arithmetic/plain-text CAPTCHA approach.
- Replaced it with a server-served image challenge.
- Stopped exposing the answer in HTML or browser cookie/session payloads.
- Added expiry and single-use enforcement for CAPTCHA tokens.
- Fixed the earlier intermediate design issue where SVG data could still reveal the answer.

### How it works now

- The login page receives a CAPTCHA token and fetches the image from a server route.
- The expected answer stays on the server side.
- Used or expired tokens are rejected.
- Replaying the same challenge no longer works.

### Behavior impact

- Users still see a CAPTCHA on login.
- The visible challenge format is different, but the login flow remains familiar.

## Additional Hardening Done During Review

While validating the audit fixes, a few extra hardening changes were also made:

- anonymous public pages no longer create unnecessary persistent sessions
- role checks now follow refreshed trusted user state
- inactive help-resource files are hidden from non-admin access even if the file path is known
- spoofed `X-Forwarded-For` values no longer affect IP-based controls by default

These changes support the audit remediations and reduce the chance of secondary issues.

## Testing Performed

The implemented changes were checked with:

- focused route/auth/session tests
- password-reset and forced-login tests
- petition workflow and management route tests
- broader regression runs across:
  - `tests/test_app_routes_branches.py`
  - `tests/test_password_reset.py`
  - `tests/test_quality_routes.py`

## Final Note

From the codebase side, the audit findings above have been remediated to a strong level.  
From the audit-closure side, the work is not fully finished until the updated application is deployed and retested in the real environment used by the auditors.
