# API contract

All application routes use `/api/v1` and require `Authorization: Bearer <token>`, except
the local-only development token endpoint. OpenAPI documentation is available at `/docs`.

| Method | Route | Purpose |
|---|---|---|
| POST | `/auth/dev-token` | Local-only JWT; absent in cloud mode |
| POST | `/uploads/init` | Validate metadata, reserve checksum and return upload URL |
| PUT | `/uploads/{id}/content` | Local upload target |
| GET | `/media/{id}` | Processing status and media metadata |
| GET | `/media/{id}/content` | Authenticated original media |
| GET | `/media/{id}/thumbnail` | Authenticated image thumbnail |
| POST | `/queries/tags` | Logical AND query with minimum tag counts |
| POST | `/queries/species` | Single species query with minimum count one |
| POST | `/queries/thumbnail` | Map a thumbnail URL to the original |
| POST | `/queries/file/init` | Reserve an ephemeral query file |
| PUT | `/queries/file/{id}/content` | Local ephemeral upload target |
| POST | `/queries/file/{id}/execute` | Detect tags, query and delete the temporary file |
| POST | `/tags/bulk` | Add (`operation=1`) or remove (`operation=0`) tags |
| DELETE | `/media` | Idempotently remove owned media and derivatives |
| POST | `/subscriptions` | Subscribe an email to a normalized tag |
| DELETE | `/subscriptions/{tag}` | Remove the current user's subscription |
| GET | `/species` | Return the 46 model labels and common names |

Tags are NFC-normalized, lower-case, and use underscores in place of spaces or hyphens.
Queries are global to authenticated researchers. Mutation and deletion are owner-only.
