# Audit Readiness Gap Closure

## Objective
Close remaining audit-readiness gaps through evidence, governance, and operations hardening without changing existing application behavior.

## Scope
- Documentation and operational closure plan only.
- No removal or modification of current features/workflows.
- No runtime behavior change is required by this document.

## Existing Baseline Artifacts
- `SECURITY_AUDIT_READY.md`
- `OWASP_TOP10_TRACEABILITY.md`
- `SECURITY_MONITORING_POLICY.md`
- `.github/workflows/security-ci.yml`
- `requirements-lock.txt`

## Gap Register and Closure Plan
| ID | Gap | Current State | Closure Action | Owner | Required Evidence | Severity | Status |
|---|---|---|---|---|---|---|---|
| G1 | CI/SCA execution evidence not attached to release trail | CI workflow exists but execution evidence may be missing in audit packet | Run `security-ci.yml` on release branch; archive run URLs, logs, artifacts, and approver sign-off | DevOps | CI run link, artifact bundle, release ticket reference | High | Open |
| G2 | Dependency lock governance not formalized | `requirements-lock.txt` exists; SOP now documented in repo | Publish lock refresh SOP (monthly + emergency CVE path) and enforce PR check for lock drift | Engineering Lead | SOP doc, 2 approved change tickets, PR check screenshot | High | In Progress |
| G3 | Structured security logging not operationalized enterprise-wide | Policy doc exists | Route security events to central logging/SIEM and validate parsing for `auth`, `access`, `csrf`, `workflow` events | SecOps/Infra | Log pipeline config, indexed sample events, parser validation output | High | Open |
| G4 | Alerting coverage for security events not evidenced | Baseline controls exist | Configure alerts for brute-force spikes, CSRF failures, repeated forbidden access, suspicious upload attempts | SecOps | Alert rules export + triggered test alert screenshots | High | Open |
| G5 | Retention and immutability controls not evidenced | Not yet mapped in audit bundle | Enforce retention (minimum per policy), access controls, and immutable/archive storage where required | Compliance/SecOps | Retention policy export, RBAC matrix, storage immutability proof | High | Open |
| G7 | Secrets management evidence for production not attached | Env-based config present | Move production secrets to vault/secret manager, enforce rotation and break-glass process | DevOps/SecOps | Secret manager policy screenshots, last rotation ticket, access audit log | High | Open |
| G8 | Threat model traceability missing from final audit pack | OWASP traceability exists; threat model now added in repo | Add lightweight threat model for auth, uploads, petition workflow transitions, and admin actions | AppSec | Threat model document, review sign-off, mitigation mapping | Medium | Closed (Repo Evidence) |
| G9 | IR playbook linkage to app-specific events not evidenced | Security monitoring policy exists; app event mapping now added in repo | Map each key event type to incident severity, responder role, and SLA | SecOps | IR runbook extract, escalation matrix, tabletop drill evidence | Medium | In Progress |
| G10 | Auditor-ready evidence index not centralized | Evidence index now added in repo | Create single audit evidence index with source path, owner, and last-verified date | Compliance | Evidence index sheet, owner attestations, QA checklist | Medium | Closed (Repo Evidence) |

## Closure Sequence (Recommended)
1. Operational evidence first: `G1`, `G3`, `G4`, `G5`.
2. Infrastructure risk closure: `G6`, `G7`.
3. Governance and defensibility: `G2`, `G8`, `G9`, `G10`.

## Exit Criteria for Audit-Ready Sign-Off
- All High severity gaps are `Closed`.
- Every control has current evidence (dated, owner-attributed, reproducible).
- Evidence index is complete and cross-referenced to source artifacts.
- Exception items (if any) have approved risk acceptance with review date.

## Auditor Submission Pack (Minimum)
- Latest successful `security-ci` run evidence.
- Dependency lock governance SOP and recent execution proof.
- Centralized security logging evidence and alerting test proof.
- Retention and access-control evidence for security logs.
- OWASP traceability + threat model + IR mapping.

## Change Control Statement
This document is a gap-closure plan only. It does not remove, disable, or alter any existing application function.
