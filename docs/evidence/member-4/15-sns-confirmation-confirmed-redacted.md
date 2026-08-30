# Member 4 SNS confirmation status

Date: 2026-08-30

Purpose: record the current state of tag-based email notification evidence.

## Current state

An AWS SNS email subscription request was sent for the Pacific BioArchive tag notification topic to
the Member 4 Monash email address. The request was re-sent on 2026-08-30 after refreshing the AWS
CLI session. The mailbox owner then opened the AWS SNS confirmation page and confirmed the
subscription on 2026-08-30.

```text
Endpoint: bpan0043@student.monash.edu
Protocol: email
SubscriptionArn/status: Confirmed
SubscriptionArn suffix: ed7585db-f663-4546-82f4-0185307345a5
```

This is final SNS subscription confirmation evidence for the Member 4 mailbox. The post-confirmation
AWS CLI check returned a concrete subscription ARN instead of `PendingConfirmation`.

Do not include the full confirmation link in the report or repository because it contains a
token-like value.
