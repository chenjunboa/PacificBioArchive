# Verification matrix

Replace `PENDING-CLOUD` only after execution against the deployed system. Evidence is a test
name, CI link, redacted screenshot filename or log reference.

| ID | Requirement | Owner | Local baseline | Cloud evidence |
|---|---|---|---|---|
| AUTH-01 | Registration fields, verification, login and logout | Member 2 | Local token only | PENDING-CLOUD |
| AUTH-02 | Business API rejects missing/invalid JWT | Member 2 | `test_authentication_required` | PENDING-CLOUD |
| AUTH-03 | Dev-token endpoint absent in cloud | Member 2 | Code path present | PENDING-CLOUD |
| UP-01 | SHA-256 and renamed-file de-duplication | Members 1/3 | duplicate workflow test | PENDING-CLOUD |
| UP-02 | Four concurrent duplicates create one record/object | Member 3 | concurrency test | PENDING-CLOUD |
| UP-03 | Allowed type, size and video-duration limits | Members 3/4 | Partial | PENDING-CLOUD |
| IMG-01 | Landscape/portrait/transparent thumbnails preserve ratio | Member 3 | Landscape covered | PENDING-CLOUD |
| VID-01 | Exactly one frame for every started second | Member 3 | video sampling test | PENDING-CLOUD |
| VID-02 | Invalid video becomes `FAILED` and reaches retry/DLQ | Member 3 | decoder test | PENDING-CLOUD |
| ML-01 | Detector -> crop -> classifier returns counts | Members 1/3 | manual real-model check | PENDING-CLOUD |
| ML-02 | Manifest hashes/version, label order and dimension 46 | Member 3 | startup path | PENDING-CLOUD |
| ML-03 | Video uses max simultaneous count, not frame sum | Member 3 | PENDING | PENDING-CLOUD |
| QRY-01 | Multi-tag AND and `>=` count | Member 3 | tag query test | PENDING-CLOUD |
| QRY-02 | Species query means minimum one | Member 3 | tag/species test | PENDING-CLOUD |
| QRY-03 | Thumbnail maps to correct original | Member 3 | reverse test | PENDING-CLOUD |
| QRY-04 | Query file creates no media and is deleted on success/error | Member 3 | Success covered | PENDING-CLOUD |
| TAG-01 | Bulk add/remove normalises and updates indexes | Member 3 | Add covered | PENDING-CLOUD |
| TAG-02 | Removing missing tag is harmless | Member 3 | PENDING | PENDING-CLOUD |
| DEL-01 | Delete cleans objects/indexes/lock/record idempotently | Member 3 | Local core covered | PENDING-CLOUD |
| ACL-01 | Only uploader mutates/deletes; queries are shared | Members 3/4 | owner test | PENDING-CLOUD |
| SNS-01 | Matching newly added tags notify confirmed subscribers | Member 3 | local notification test | PENDING-CLOUD |
| FAIL-01 | GCP/AWS transient failure exposes retry, status and DLQ | Member 3 | PENDING | PENDING-CLOUD |
| UI-01 | Demo is continuous, with no DB edit/console error | Member 4 | manual local smoke | PENDING-CLOUD |
| SEC-01 | Private inference uses WIF and no long-lived GCP key | Member 2 | Architecture only | PENDING-CLOUD |
| SEC-02 | Git has no secret, state or model weight | Everyone | file-list check | PENDING-CLOUD |

## Status and evidence rules

- `PASS`: repeated in the named environment with inspectable evidence.
- `PARTIAL`: list the exact assertions passed and remaining.
- `FAIL`: reproducible wrong result; open a `release-blocker` issue.
- `BLOCKED`: external permission/dependency; attach the exact redacted blocker.
- `PENDING`: not executed. “Implemented” or “expected” is not `PASS`.

Name evidence `<ID>-<date>-<description>`, for example
`QRY-01-2026-08-25-and-count.png`. Redact tokens, email, all but four account-ID digits and
presigned URL query strings.
