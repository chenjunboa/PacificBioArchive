# Pacific BioArchive demo script

This script is for the final team rehearsal and video demo. It assumes the deployed API, web
frontend, Cognito user pool, S3 buckets, DynamoDB table, SQS worker, and private GCP Cloud Run
inference service are already deployed from Terraform.

## Demo accounts

- Primary presenter: Member 4, using a pre-verified Cognito test user.
- Second user: another pre-verified Cognito test user for the non-owner 403 check.
- Do not write the password, MFA code, email confirmation code, JWT, presigned URL, or AWS/GCP
  credential into this repository, screenshots, or report.

## Demo files

Use the provided `test_images.zip` from the assignment material folder.

| Purpose | Zip entry | SHA-256 |
|---|---|---|
| Main image upload | `test_images/Alectura_lathami_1.JPG` | `a55dc44ee044c09230929b247b78992e7e9b833bc755f083e093db8b681f6854` |
| Backup image upload | `test_images/Casuarius_casuarius_2.JPG` | `ee57b3ee5ac1194529137b6a72a7827cd96b536d7b770200a0d32b4abbd2216b` |
| Query/duplicate backup | `test_images/Bos_taurus_2.JPG` | `ee3693c36f1d8c48e385c47f62df59a001d6a010e4349224d689f2f6231c6e24` |

Short video evidence is still required if the deployed worker has a known-good MP4 or MOV sample.
Record the filename, checksum, duration, and cleanup media ID before the final submission rehearsal.

## Minute-by-minute flow

| Time | Presenter action | Expected evidence |
|---|---|---|
| 00:00 | Open the deployed frontend URL. | Login screen shows Cognito mode, not the local development login shortcut. |
| 00:30 | Sign in with the primary pre-verified Cognito test user. | Sidebar shows the user email and business tabs. |
| 01:00 | Upload `Alectura_lathami_1.JPG`. | UI shows checksum calculation, upload reservation, upload, and worker status polling. |
| 02:00 | Wait until the media card reaches `READY`. | Card shows media ID, content type, status, model version, created time, tags, original URL, and thumbnail. |
| 02:45 | Upload the same file again. | UI shows a 409 duplicate message and the existing media ID/detail from the API. |
| 03:15 | Search by tag count with `alectura_lathami` and count `1`. Add a second row if testing AND/count. | Results use the same media card component and include the uploaded image. |
| 04:00 | Search by species using the dropdown. | Dropdown comes from `/species`; there are 46 model-supported options. |
| 04:45 | Copy the thumbnail URL from the media card/API response and run thumbnail reverse query. | Result resolves back to the correct media ID and original file link. |
| 05:30 | Upload a temporary query file through File query. | The UI says it is temporary and does not add it as archive media. Results are shown as normal media cards. |
| 06:30 | Use Manage to add tag `demo_reviewed`, then remove it. | Success messages show add/remove as human-readable operations. |
| 07:15 | Subscribe to `alectura_lathami`. | Response says `PENDING_CONFIRMATION` in cloud and reminds the user to confirm the SNS email. |
| 07:45 | Unsubscribe from the same tag. | Success message confirms removal. |
| 08:15 | Sign in as the second Cognito user and attempt a manual API tag/delete request against the first user's media. | API returns 403; save the redacted request/response evidence. |
| 09:00 | Sign back in as the owner and delete the demo media after the confirmation prompt. | UI removes the media and API no longer returns it. |
| 09:45 | Sign out and retry a business API request without a token. | API returns 401; UI asks the user to sign in again. |

## Cold-start fallback

If Cloud Run or Lambda is cold, keep the UI visible on the loading state and wait up to two minutes.
If the worker still does not complete, show the CloudWatch log group, SQS DLQ count, and Cloud Run
revision status instead of editing DynamoDB by hand.

## Evidence checklist

- Two consecutive successful runs of login, upload, READY polling, at least two query modes, and delete.
- Screenshot or Playwright video for each of the four query modes.
- Redacted 409 duplicate response with existing media detail.
- Redacted 403 non-owner request and response.
- Redacted 401 signed-out request and response.
- SNS confirmation email screenshot with recipient and token-like links hidden.
- Terraform outputs and deployment URLs with account IDs or sensitive IDs redacted where required.
- Final cleanup list of media IDs, query IDs, and subscriptions removed after the demo.

## Cleanup after demo

Delete all uploaded demo media through the owner account. Confirm the S3 original object, thumbnail
object, DynamoDB media row, tag index rows, thumbnail mapping row, checksum reservation, temporary query
object, and temporary query reservation are gone. Remove the SNS subscription created for rehearsal if
it is not needed for marking.
