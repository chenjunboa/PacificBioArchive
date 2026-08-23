# Architecture

```mermaid
flowchart LR
  UI[React UI on Cloud Run] -->|Cognito JWT| APIGW[AWS API Gateway]
  APIGW --> API[API Lambda]
  API --> S3[(S3 media)]
  API --> DDB[(DynamoDB single table)]
  S3 --> SQS[SQS + DLQ]
  SQS --> Worker[Processing Lambda]
  Worker -->|Workload Identity Federation| Infer[Private GCP Cloud Run inference]
  Infer --> GCS[(GCS model manifest + models)]
  Worker --> DDB
  Worker --> SNS[SNS tag notifications]
  Cognito[AWS Cognito] --> UI
```

The user-facing trust boundary ends at API Gateway, which validates Cognito JWTs. The
processing Lambda uses a separate short-lived Google identity obtained through Workload
Identity Federation. No browser token or long-lived GCP service-account key crosses clouds.

Original objects use `originals/{mediaId}/{safeFilename}`; thumbnails use
`thumbnails/{mediaId}.jpg`; query uploads use `temporary-queries/{queryId}/{safeFilename}`
and have both immediate deletion and a one-day lifecycle fallback.
