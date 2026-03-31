# Auditor Handoff Checklist

## Before Deployment

- confirm latest code is deployed from the remediated branch/workspace
- confirm latest templates are deployed with the same code version
- verify `.env` / production settings are correct
- confirm strong `SECRET_KEY` and production mode
- confirm intended `TRUST_PROXY_HEADERS` setting

## After Deployment

- restart or reload the application service
- verify schema update path created required tables
- verify `/login`, `/`, and protected routes open correctly
- verify static assets load

## Live Retest Checklist

### NIG001
- stale or invalid session is rejected
- session tamper attempt does not grant access

### NIG002
- browser cookie does not expose role/profile/auth state
- anonymous landing/login views do not create persistent sessions

### NIG003
- profile password change fails without current password
- profile password change fails with wrong current password

### NIG004
- password change forces re-login
- older sessions no longer work after credential change

### NIG005
- external redirect payload is rejected
- valid internal navigation still works

### NIG006
- rapid petition burst triggers throttling
- normal DEO usage remains functional
- admin can review/update rate-limit settings if needed

### NIG007
- CAPTCHA answer is not visible in page source/cookie
- used or expired CAPTCHA token fails

## Evidence to Attach

- screenshots or recordings of live retest results
- deployment ticket/change reference
- regression test output
- any required CI/logging/ops evidence

## Final Auditor Packet

- [RESOLUTION.md](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/RESOLUTION.md)
- [AUDIT_EVIDENCE_INDEX.md](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/AUDIT_EVIDENCE_INDEX.md)
- [THREAT_MODEL.md](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/THREAT_MODEL.md)
- [INCIDENT_RESPONSE_MAPPING.md](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/INCIDENT_RESPONSE_MAPPING.md)
- [SECURITY_MONITORING_POLICY.md](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/SECURITY_MONITORING_POLICY.md)
