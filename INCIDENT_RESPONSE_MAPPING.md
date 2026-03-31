# Incident Response Mapping

## Purpose

Map application security events to severity, responder ownership, and expected response timing for audit and operational review.

## Event Mapping

| Event Type | Typical Trigger | Severity | Primary Responder | Target Response |
|---|---|---|---|---|
| `auth.login_failed` | Bad password / failed login | Low to Medium | Service Desk / SecOps | Review trend within same business day |
| `auth.login_lockout_triggered` | Repeated failures causing lockout | Medium | SecOps | Investigate within 4 hours |
| `auth.login_blocked` | Login blocked during active throttling | Medium | SecOps | Investigate within 4 hours |
| `auth.login_success` | Successful login | Informational | Monitoring only | No immediate action unless correlated |
| `web.csrf_validation_failed` | Bad/missing CSRF token | Medium | App Support / SecOps | Review within 4 hours; urgent if spiking |
| `access.unauthenticated_request` | Protected route hit without valid session | Low | Monitoring only | Trend review |
| `access.role_forbidden` | User lacks role for route | Medium | App Support / SecOps | Review same day; urgent if repeated |
| `access.petition_forbidden` | User denied petition visibility | Medium | App Support / SecOps | Review same day |
| `access.petition_action_forbidden` | Unauthorized workflow action attempted | High | SecOps + Application Owner | Investigate within 2 hours |
| `access.file_forbidden` | Unauthorized file access attempt | High | SecOps + Application Owner | Investigate within 2 hours |
| `access.profile_photo_forbidden` | Unauthorized profile-photo access | Low to Medium | App Support | Review same day |
| `access.api_inspectors_forbidden` | Unauthorized inspector lookup | Medium | App Support / SecOps | Review same day |

## Escalation Guidance

Escalate to High priority immediately when any of the following are observed:

- repeated forbidden access against many objects or users
- repeated login lockouts across multiple accounts
- evidence of automation against petition creation or login endpoints
- any sign of account takeover, privilege misuse, or workflow manipulation

## Minimum Response Actions

For authentication or session issues:

- capture user id, IP, timestamp, and user agent
- confirm whether password reset or session revocation is needed
- preserve relevant logs

For authorization or file-access issues:

- identify target object ids
- confirm whether access was expected for that role
- preserve event trail and affected account details

For burst or abuse issues:

- capture user id, IP, request counts, and target path
- confirm whether throttling engaged successfully
- block or contain at infra layer if needed

## Evidence Expected for Audit

- sample alert or ticket for each major event category
- responder ownership list
- escalation matrix or runbook reference
- retention of security-event investigation records
