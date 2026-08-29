# Member 4 Individual Report

Name: Bo Pang
Student ID: 36969842
Repository: https://github.com/chenjunboa/PacificBioArchive

## Role and Contribution

My role was to complete the final user-facing integration, stabilize the handed-off backend paths
needed by the interface, and prepare the project for demonstration and final acceptance. I completed
the Cognito-aware React workflow for sign-up, sign-in, session restoration, token refresh, and
sign-out, while keeping a local development login path for automated testing. I implemented the
upload, query, media management, and notification UI flows, including file type and size feedback,
video duration validation, checksum progress, polling, duplicate upload messaging, four query modes,
bulk tag add/remove, owner-only delete, and SNS subscription messaging.

During handoff review I found that several cloud-mode backend paths were not ready for the final UI
to demonstrate truthfully. I helped stabilize DynamoDB tag-count indexes, thumbnail reverse
mappings, temporary query reservations, delete cleanup, and worker index writes. I also added and
ran Playwright end-to-end tests, prepared the demo script and evidence checklist, deployed the latest
API/Worker Lambda images, disabled the fallback worker that was consuming messages, and validated
the live cloud path with two image smoke runs and one short MP4 smoke run.

## Reflection

This project showed me how quickly a group cloud assignment can become an integration problem rather
than four isolated coding tasks. Earlier members established important foundations, especially the
local prototype and AWS/GCP deployment, but the later handoff exposed gaps around query indexes,
cleanup consistency, real worker routing, and evidence boundaries. I learned that it is not enough
for code to exist in the repository; we had to prove that the deployed system was using the expected
version, that the correct worker consumed SQS messages, and that records were cleaned up after
testing.

The team workflow improved when we treated unresolved items as explicit handoff risks instead of
quiet assumptions. My biggest challenge was balancing urgency with honesty: I wanted the report to
sound complete, but only after real validation. The final image and video smoke tests gave us a much
stronger basis for the report and demo. If I repeated the project, I would ask the team to define
shared evidence requirements earlier, including who owns cloud screenshots, email confirmations,
and final release approval.

## Generative AI Use

I used OpenAI Codex selectively to inspect the repository, compare the implementation with the
assignment brief, generate focused code changes, run tests, debug AWS/GCP integration issues, and
draft documentation. I reviewed the generated changes through builds, Playwright tests, AWS CLI
checks, CloudWatch logs, DynamoDB cleanup checks, and Git history before accepting them. No cloud
secrets, Cognito passwords, verification codes, JWTs, presigned URL query strings, Terraform state,
or model weights were committed.
