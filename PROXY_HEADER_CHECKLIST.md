# Proxy And Load Balancer Header Checklist

## Required Headers

- `X-Forwarded-Proto` should be `https` for externally secure requests.
- `X-Forwarded-For` should contain the client IP chain.
- `X-Forwarded-Host` should match the public host name.
- `X-Forwarded-Port` should be `443` when TLS is terminated upstream.

## Application Expectations

- `TRUST_PROXY_HEADERS=1`
- `PROXY_FIX_X_FOR=1`
- `PROXY_FIX_X_PROTO=1`
- `PROXY_FIX_X_HOST=1`
- `PROXY_FIX_X_PORT=1`

## Cookie Expectations

- `SESSION_COOKIE_SECURE=1` in production.
- `SESSION_COOKIE_SAMESITE=Lax` unless a true cross-site use case requires otherwise.
- `SESSION_COOKIE_PATH=/`
- Use `SESSION_COOKIE_DOMAIN=` empty when using a `__Host-` cookie name.
- If `SESSION_COOKIE_NAME` starts with `__Host-`, do not set a cookie domain.

## Reverse Proxy Checks

- Nginx should forward `X-Forwarded-Proto $scheme`.
- Cloudflare / CDN should preserve the original host header or forward the public host correctly.
- The app should not see inbound requests as plain HTTP when the browser is using HTTPS.
- Confirm only trusted proxies can inject forwarded headers.

## Verification Steps

- Check the browser network tab for `Set-Cookie` on login and on a normal authenticated click.
- Confirm the cookie remains scoped to the same host and path across sub-routes.
- Confirm the session cookie is not downgraded from `Secure` in production.
- Confirm the server-side `server_sessions.expires_at` advances when the browser receives a refreshed session cookie.
- If Safari still drops the session, compare the first authenticated response headers between Safari and Chrome.
