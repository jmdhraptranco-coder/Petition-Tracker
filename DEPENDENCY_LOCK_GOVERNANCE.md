# Dependency Lock Governance

## Purpose

Define how dependency versions and vulnerability-response actions are governed for this application.

## Baseline

- Runtime dependencies are listed in `requirements.txt`.
- A pinned snapshot is maintained in `requirements-lock.txt`.

## Standard Refresh Cycle

1. Review dependencies monthly.
2. Refresh `requirements-lock.txt` in a controlled branch.
3. Run application regression and security checks.
4. Capture approval in the change/release ticket.
5. Deploy only after successful validation.

## Emergency CVE Response

Use the emergency path when:

- a critical or high CVE affects a direct or transitive dependency
- the dependency is reachable in production usage
- there is a vendor advisory or internal security instruction to patch urgently

Required steps:

1. Identify affected package and current deployed version.
2. Update to the minimum safe version.
3. Refresh lock file.
4. Run regression and targeted validation.
5. Record approver, ticket id, and deployment date.

## Change-Control Expectations

- Do not update dependencies directly on production hosts.
- Treat lock-file changes as review-required code changes.
- Keep release notes or ticket references with each lock-file refresh.

## Audit Evidence

Auditors should be shown:

- `requirements-lock.txt`
- latest approved lock refresh ticket
- latest successful validation run after dependency refresh
- emergency update record if a CVE-driven patch was required
