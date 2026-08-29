# Member 4 SNS confirmation status

Date: 2026-08-29

Purpose: record the current state of tag-based email notification evidence.

## Current state

An AWS SNS email subscription request was sent for the Pacific BioArchive tag notification topic to
the Member 4 Monash email address.

```text
Endpoint: bpan0043@student.monash.edu
Protocol: email
SubscriptionArn/status: PendingConfirmation
```

This is not yet final SNS evidence. The mailbox owner must open the AWS SNS confirmation email and
click the confirmation link. After that, re-run `aws sns list-subscriptions-by-topic` and capture a
redacted screenshot or CLI output showing a concrete subscription ARN instead of
`PendingConfirmation`.

Do not include the full confirmation link in the report or repository because it contains a
token-like value.
