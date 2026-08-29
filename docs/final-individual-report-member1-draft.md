# Member 1 Individual Report

Name: Junbo Chen
Student ID: 36970271
Repository: https://github.com/chenjunboa/PacificBioArchive

## Role and Contribution

My role was to turn the assignment brief into the first complete local prototype and establish a
stable foundation that the other three members could extend in sequence. I designed the initial
multi-cloud architecture, repository layout, API contracts and ownership boundaries. I implemented
the baseline FastAPI service, local JWT authentication, upload checksum validation and duplicate
handling, local media storage, query and tag flows, deletion behaviour, and the initial React user
interface. I also created the inference service scaffold, Terraform structure, Docker Compose local
environment, automated tests, and the Chinese handoff documents used by later members.

My main objective was to make the project runnable before cloud deployment rather than leave each
member with disconnected pieces. I verified the local API and interface, added representative image
and video processing paths, and documented exact responsibilities for AWS/GCP deployment, backend
completion and final UI integration. At the end of the project I returned as the release reviewer,
checked the latest cloud evidence and CI results, fixed a Windows-specific Playwright startup issue,
added the official-icon architecture diagram, and approved the tested commit for the
`release-candidate-1` tag.

## Reflection

The project demonstrated that sequential ownership can work for a cloud assignment only when each
handoff contains an executable baseline, clear acceptance criteria and evidence. Building the first
prototype gave the team a shared vocabulary for media states, checksums, tags, ownership and query
behaviour. It also reduced uncertainty for the deployment stage because later members could compare
cloud behaviour with a known local workflow.

The main weakness of the sequential approach was that integration risks appeared late. Some cloud
paths, indexes and worker routing decisions could not be proven until the final interface exercised
them together. I learned to separate “implemented in the repository” from “verified in the deployed
system”, and to record unresolved items instead of assuming that a handoff had completed them. The
final review reinforced the value of cross-platform E2E tests: the workflow passed in Linux CI but
its local startup command initially failed on Windows. In a future project I would define the cloud
evidence checklist and final-report ownership at the beginning, and schedule a shared integration
review before the final day.

## Generative AI Use

I used OpenAI Codex to help analyse the assignment requirements, structure the prototype, generate
focused implementation suggestions, identify edge cases, run and interpret tests, prepare handoff
documentation, and review the release candidate. I inspected and tested the resulting work rather
than accepting generated output directly. Verification included Python tests, Ruff, Terraform
validation, the React production build, Playwright E2E, GitHub Actions and the team's redacted live
AWS/GCP smoke evidence. Credentials, verification codes, tokens, presigned URL parameters,
Terraform state and model weights were not committed.
