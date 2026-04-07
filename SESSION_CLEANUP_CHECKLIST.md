# Session And Auth Cleanup Checklist

## Request Lifecycle

- Consolidate all session validation into one path. Keep `_load_current_authenticated_user()` as the single source of truth.
- Avoid ad hoc `session.clear()` calls outside login/logout/password-change/session-expiry flows.
- Prefer `_destroy_current_session()` when ending a live authenticated session so the server-side record is removed too.
- Keep CSRF validation in one middleware path only.

## Dead Code Review

- Search for routes no longer linked from templates or navigation.
- Search for helper functions that are never referenced with `rg -n "function_name\("`.
- Remove legacy auth flows that are disabled but still leave template, test, or route artifacts behind.
- Remove stale fallback branches tied to deprecated login methods.
- Review [app.py](/d:/Nigaa/app.py) legacy routes that only redirect with warning messages:
  `request_signup`, `forgot_password_request`, and `forgot_password_set`.
- Review first-login temporary session fields:
  `force_change_user_id`, `force_change_username`, and `force_change_role`.
  Keep them only if the forced-password-change flow remains required.
- Review in-memory fallback stores:
  `LOGIN_ATTEMPTS`, `PETITION_SUBMISSION_ATTEMPTS`, `LOGIN_CAPTCHA_USED_TOKENS`, and `LOGIN_CAPTCHA_CHALLENGES`.
  They are acceptable for single-node operation but should be moved to a shared store for horizontally scaled deployments.

## Duplicate Logic

- Route guards should use `@login_required` and `@role_required(...)` instead of inline session checks.
- Session activation should always go through `_activate_login_session()`.
- Session invalidation should always go through `_destroy_current_session()` or server-side revoke helpers.
- Session invalidation during auth validation should always go through `_invalidate_current_session()`.
- Cookie/security headers should be configured once at app startup, not repeated in route handlers.

## Sensitive Logging

- Remove debug prints or temporary request dumps that include headers, cookies, CSRF tokens, or session IDs.
- Avoid logging raw `session` objects.
- Keep security logs high-level: event type, user id, reason, and source IP.

## Store Stability

- Do not use in-memory stores for production session state.
- Periodically prune expired `server_sessions` rows.
- Review other volatile stores such as login-attempt counters and captcha caches if multi-instance deployment is planned.

## Safari And Proxy Checks

- Confirm production is HTTPS end-to-end or correctly terminated at the reverse proxy.
- Confirm forwarded headers are trusted only from known proxies.
- Confirm cookie name, `Secure`, and `SameSite` settings match the deployment topology.
- If cross-site embedding or third-party login is introduced later, revisit `SameSite=Lax` and move to `None` only with `Secure`.
