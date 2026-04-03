# Audit Runtime Checklist

Use this checklist before claiming the deployment is ready for security audit closure.

## Pass/Fail Items

- `PASS` only if `APP_ENV=production` is set in the live environment so secure-cookie and HSTS behavior are enabled.
- `PASS` only if `SESSION_LIFETIME_MINUTES` is set to `60` or lower for inactivity timeout unless a documented exception is approved.
- `PASS` only if `.env` is not committed, not bundled into deployment artifacts, and access to secrets is restricted to authorized operators.
- `PASS` only if the current `SECRET_KEY` and database password have been rotated after any sharing through chat, screenshots, or source history.
- `PASS` only if TLS terminates safely in front of the app and authenticated requests are served over HTTPS only.
- `PASS` only if the live browser session cookie is observed with `HttpOnly`, `Secure`, and `SameSite=Lax`.
- `PASS` only if CSRF protection is active on authenticated unsafe methods in the deployed environment.
- `PASS` only if login throttling and single-use CAPTCHA behavior are verified in the deployed environment.
- `PASS` only if database access is restricted to the application host/network path and the chosen `DB_SSLMODE` matches DBA-approved transport requirements.
- `PASS` only if uploads are stored outside publicly writable web roots and are not directly browsable.


## Evidence To Capture

- screenshot or header capture showing `Strict-Transport-Security`
- screenshot or browser-devtools capture showing secure session cookie flags
- login timeout evidence showing logout after inactivity window
- CAPTCHA single-use and expiry evidence
- secret-rotation or credential custody evidence from operations team
