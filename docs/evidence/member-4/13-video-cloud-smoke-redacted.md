# Member 4 short video cloud smoke evidence

Date: 2026-08-29

Purpose: verify that the deployed multi-cloud application can accept a short MP4 media upload,
process it through the main AWS Lambda worker and GCP inference path, return a SpeciesNet tag, query
the uploaded video by tag, delete it, and clean up metadata/index records.

## Test input

The smoke input was a 3 second H.264 MP4 generated locally from the assignment-provided
`Alectura_lathami_1.JPG` image. The resulting file was about 78 KB and below the 60 second video
limit.

```text
codec: h264
container: mp4
duration: 3.000000 seconds
frames: 75
content type observed by the deployed API: video/mp4
```

## Cloud smoke result

```text
npm run test:e2e:cloud -- --timeout=600000
PBA_CLOUD_EXPECT_THUMBNAIL=false
cloud-smoke-media-id=b4c56c61-e229-4aa3-8539-8ff6e1e8f372
cloud-smoke-content-type=video/mp4
1 passed
elapsed: 1.7m
```

The Playwright cloud smoke signed in through the deployed frontend, uploaded the MP4, waited for
the deployed API to return `READY` with tag `alectura_lathami`, verified the tag query through the
protected API using the same Cognito token, deleted the uploaded video by URL, verified the media
endpoint returned 404, and signed out.

## AWS evidence summary

```text
Worker Lambda log window:
START RequestId: a6bd5709-bbf7-58b5-a266-340549271fc7
END RequestId: a6bd5709-bbf7-58b5-a266-340549271fc7
REPORT Duration: 78714.30 ms, Memory Size: 3008 MB, Max Memory Used: 125 MB

DynamoDB cleanup check for b4c56c61-e229-4aa3-8539-8ff6e1e8f372:
Count: 0

SQS media DLQ after the run:
ApproximateNumberOfMessages: 0
ApproximateNumberOfMessagesDelayed: 0
ApproximateNumberOfMessagesNotVisible: 0
```

Secrets, temporary Cognito credentials, JWTs, presigned URL query strings, and full cloud account
identifiers were not recorded in this evidence file.
