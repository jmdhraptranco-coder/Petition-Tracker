# Audit Evidence Index

## Purpose

This index centralizes the main code, test, and document artifacts that support audit-readiness review for the Nigaa application.

## Evidence Register

| ID | Evidence Item | Purpose | Source | Owner | Last Verified |
|---|---|---|---|---|---|
| E1 | VAPT remediation plan | Original remediation mapping for `NIG001` to `NIG007` | [PLAN.md](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/PLAN.md) | Engineering | 31-03-2026 |
| E2 | VAPT resolution summary | Auditor-facing summary of implemented changes | [RESOLUTION.md](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/RESOLUTION.md) | Engineering | 31-03-2026 |
| E3 | Security readiness statement | Current high-level security posture | [SECURITY_AUDIT_READY.md](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/SECURITY_AUDIT_READY.md) | Engineering | 31-03-2026 |
| E4 | Threat model | Auth, upload, workflow, and admin threat coverage | [THREAT_MODEL.md](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/THREAT_MODEL.md) | AppSec / Engineering | 31-03-2026 |
| E5 | Incident response mapping | Event-to-severity and responder mapping | [INCIDENT_RESPONSE_MAPPING.md](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/INCIDENT_RESPONSE_MAPPING.md) | SecOps / Engineering | 31-03-2026 |
| E6 | Security monitoring policy | Logging/monitoring policy for security events | [SECURITY_MONITORING_POLICY.md](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/SECURITY_MONITORING_POLICY.md) | SecOps | 31-03-2026 |
| E7 | OWASP traceability | Control mapping to OWASP categories | [OWASP_TOP10_TRACEABILITY.md](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/OWASP_TOP10_TRACEABILITY.md) | AppSec | 31-03-2026 |
| E8 | Dependency governance SOP | Lock refresh and emergency CVE handling | [DEPENDENCY_LOCK_GOVERNANCE.md](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/DEPENDENCY_LOCK_GOVERNANCE.md) | Engineering Lead | 31-03-2026 |
| E9 | Auditor deployment checklist | Live deployment and retest handoff checklist | [AUDITOR_HANDOFF_CHECKLIST.md](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/AUDITOR_HANDOFF_CHECKLIST.md) | Engineering / DevOps | 31-03-2026 |
| E10 | Application security implementation | Primary application logic implementing session/auth/rate-limit/CAPTCHA changes | [app.py](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/app.py) | Engineering | 31-03-2026 |
| E11 | Persistent security state models | Session, settings, and rate-limit persistence | [models.py](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/models.py) | Engineering | 31-03-2026 |
| E12 | Security configuration | Session, proxy, and rate-limit config values | [config.py](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/config.py) | Engineering | 31-03-2026 |
| E13 | Authentication regression tests | Session, CAPTCHA, redirect, auth, and throttle validation | [tests/test_app_routes_branches.py](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/tests/test_app_routes_branches.py) | QA / Engineering | 31-03-2026 |
| E14 | Password/session regression tests | Password reset and forced re-login validation | [tests/test_password_reset.py](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/tests/test_password_reset.py) | QA / Engineering | 31-03-2026 |
| E15 | Quality route regression tests | Broader route integrity validation | [tests/test_quality_routes.py](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/tests/test_quality_routes.py) | QA / Engineering | 31-03-2026 |
| E16 | Local readiness precheck | Local verification and remaining live-environment items | [AUDIT_PRECHECK.md](c:/Users/AP%20TRANSCO/OneDrive%20-%20APTRANSCO/Pictures/Petition%20Tracker%20with%20chatbot/AUDIT_PRECHECK.md) | Engineering | 31-03-2026 |

## Notes

- This index covers repository artifacts only.
- Operational evidence such as CI execution proof, SIEM screenshots, alert tests, and production deployment approvals must be attached separately where required.
