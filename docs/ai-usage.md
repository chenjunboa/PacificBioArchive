# Generative AI usage record

Generative AI was used selectively to help design the system architecture, scaffold the
prototype, identify edge cases, and propose automated tests. The team remains responsible
for reviewing, understanding, modifying and validating every submitted line of code and all
report content. Model-generated suggestions are not accepted without local tests or direct
inspection.

Before submission, each member must add dated notes describing which AI-assisted portions
they personally reviewed or changed. The team and individual reports must explicitly mention
AI use even if a member did not use AI directly.

## Dated activity log

### 23 August 2026 — Member 1 prototype

- AI assistance: architecture decomposition, local prototype scaffolding, edge-case checklist,
  automated test suggestions, repository documentation and four-person handoff structure.
- Human review required: Member 1 must read the API/architecture/handoff documents, run the
  commands in `README.md`, inspect the local demo and approve the GitHub commit before treating
  the output as team work.
- Verification performed: backend/inference tests, Ruff checks, TypeScript/Vite production
  build, Terraform formatting/validation, real-model sample inference and browser smoke test.
- Limitation: AI assistance does not establish cloud correctness. Members 2–4 must independently
  implement, understand and verify their owned cloud, data/ML and UI stages.
