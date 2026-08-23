# Four-person handoff

| Workstream | Ownership | Required evidence |
|---|---|---|
| A - security and upload | Cognito, IAM, API Gateway, checksum reservation, upload UI | Auth tests, IAM explanation, commits and demo script |
| B - media and ML | Thumbnail, video sampling, Cloud Run inference, model manifest | Model validation, sample results, failure tests and commits |
| C - queries | DynamoDB indexes, four query modes, query UI | AND/count tests, temporary-file proof and commits |
| D - management and integration | Bulk tags, deletion, SNS, UI integration, E2E tests | Owner tests, notification proof, demo rehearsal and commits |

Create one GitHub issue per acceptance criterion. Every workstream must be merged through a
pull request reviewed by the paired reviewer: A with C, B with D. Start contribution reporting
at 25% per member and adjust only using issue, commit and review evidence.
