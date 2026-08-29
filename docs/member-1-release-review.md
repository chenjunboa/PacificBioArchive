# Member 1 release candidate review

Review date: 29 August 2026  
Reviewer role: Member 1 / original prototype owner  
Scope reviewed: latest `main`, Member 4 cloud evidence, final UI workflow, reports and release assets

## Review decision

Accepted for the `release-candidate-1` tag after the reviewed commit passes GitHub Actions. This is
not approval for `v1.0.0`; the final tag still requires all four members to accept the report,
contribution table and submission state.

## Evidence checked

- The latest GitHub Actions workflow on the inherited Member 4 commit passed backend, web, E2E and
  container checks.
- Local verification passed 17 Python tests, Ruff, Terraform formatting/initialisation/validation,
  the React production build and the complete Playwright archive workflow.
- Member 4 evidence records two live image smoke runs and one live three-second MP4 run through the
  deployed AWS/GCP path, including cleanup and an empty DLQ.
- The architecture diagram uses official AWS and Google Cloud icon packages. Source links and
  retrieval dates are recorded beside the editable source.
- A repository scan found no committed `.env`, Terraform state, model weights, cloud credentials,
  JWTs or presigned URLs. Documentation uses placeholders only.

## Issue found and resolved during review

The Playwright local API command used POSIX-only inline environment syntax and `.venv/bin/python`,
so `npm run test:e2e` could not run on the Member 1 Windows workstation. The API startup was moved
to `web/e2e/start-local-api.mjs`, which chooses the platform-specific virtual-environment Python and
passes environment variables explicitly. The full Playwright flow then passed on Windows.

## Remaining human gates

1. The owner of `bpan0043@student.monash.edu` must click the AWS SNS confirmation link.
2. The team must provide and verify every formal student name and numeric student ID.
3. All four members must review the final PDFs and contribution declarations.
4. Create `v1.0.0` only after those checks and explicit team acceptance.
