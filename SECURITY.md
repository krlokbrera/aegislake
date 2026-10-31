# Security and data handling

## Report a vulnerability

Use GitHub private vulnerability reporting when enabled. If it is unavailable, open an issue requesting a private reporting channel without including exploit payloads, telemetry, personal identifiers or secrets.

## Project controls

- Source control contains original code, synthetic configuration, tests and documentation.
- Runtime data and local environment files are excluded by .gitignore.
- Real-export adaptation uses keyed HMAC, not reversible encoding or an unkeyed identifier hash.
- HTML values are escaped; no external scripts or analytics are loaded.
- No pickle or joblib model artifact is deserialized.
- SQL runs against registered local frames with fixed queries.
- Human review inserts use parameterized SQLite queries.
- Azure Blob containers are private; shared-key access and anonymous Blob access are disabled.
- The compute identity is scoped to the reports container.
- CI has read-only repository permissions and does not receive cloud credentials.
- GitHub Actions are pinned to reviewed commit identifiers and monitored by Dependabot.

## Threat model

| Threat | Mitigation | Residual limit |
| --- | --- | --- |
| Secrets committed by mistake | Ignore rules, documentation, scoped Azure identities | Ignore rules are not a secret scanner; enable repository secret scanning |
| Malicious source strings | Strict contract, escaped HTML, fixed SQL | Inputs are still bounded trusted exports; add file/line limits for hostile ingestion |
| Target leakage | Explicit feature allowlist and temporal tests | Simulator artifacts and reference design still affect conclusions |
| Untrusted model code | Model reconstruction, no pickle loading | Dependency integrity and training data integrity remain essential |
| Raw telemetry disclosure | Private local data, synthetic-only publication allowlist | A synthetic flag is user-controlled metadata, not a data loss prevention classifier |
| Analyst overreach | Evidence queue and no remediation permissions | Human actions outside this app remain outside project control |
| Feedback tampering | Application only appends ledger rows | SQLite owner can modify the file; not a forensic audit system |
| Artifact tampering | Per-file hashes and version checks | Unsigned manifests do not prove authenticity |
| Azure cost growth | Manual finite job, timeout, no retry by default | Storage and repeated concurrent manual starts can still incur charges |
| Infrastructure access | Container-scoped Blob RBAC | Contributor role includes delete; narrower custom write-only role is future work |

## Azure networking

Storage-only mode denies access except an explicit operator public IPv4 address. Optional compute mode permits the authenticated public storage endpoint because this minimal consumption setup lacks stable egress. Containers remain non-public and require Entra authorization.

This is a documented demo tradeoff. A production design should evaluate private connectivity, trusted egress, per-environment identities and signed build provenance.

## Operational review

Before a real-data pilot, review source authorization, identity mapping, cloud policy and blast radius. Keep production data out of GitHub Actions and public reports. The software does not certify compliance with a regulation, framework or organizational policy.
