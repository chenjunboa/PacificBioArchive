locals {
  prefix          = "${var.project_name}-${var.environment}"
  lambda_role_arn = var.lab_role_arn != "" ? var.lab_role_arn : aws_iam_role.lambda[0].arn
  lambda_role_name = var.lab_role_arn != "" ? element(
    reverse(split("/", var.lab_role_arn)), 0
  ) : var.aws_role_name
}

resource "aws_s3_bucket" "media" {
  bucket_prefix = "${local.prefix}-media-"
  force_destroy = false
}
resource "aws_s3_bucket_public_access_block" "media" {
  bucket                  = aws_s3_bucket.media.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
resource "aws_s3_bucket_lifecycle_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  rule {
    id     = "expire-temporary-queries"
    status = "Enabled"
    filter {
      prefix = "temporary-queries/"
    }
    expiration {
      days = 1
    }
  }
}
resource "aws_s3_bucket_cors_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD", "POST"]
    allowed_origins = concat(
      ["http://localhost:5173", "http://127.0.0.1:5173"],
      var.deploy_compute ? [google_cloud_run_v2_service.web[0].uri] : []
    )
    expose_headers  = ["ETag"]
    max_age_seconds = 3600
  }
}

resource "aws_sqs_queue" "dlq" {
  name                      = "${local.prefix}-media-dlq"
  message_retention_seconds = 1209600
}
resource "aws_sqs_queue" "jobs" {
  name                       = "${local.prefix}-media-jobs"
  visibility_timeout_seconds = 5400
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}
resource "aws_sqs_queue_policy" "s3" {
  queue_url = aws_sqs_queue.jobs.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "s3.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.jobs.arn
      Condition = { ArnEquals = { "aws:SourceArn" = aws_s3_bucket.media.arn } }
    }]
  })
}
resource "aws_s3_bucket_notification" "jobs" {
  bucket = aws_s3_bucket.media.id
  queue {
    queue_arn     = aws_sqs_queue.jobs.arn
    events        = ["s3:ObjectCreated:*"]
    filter_prefix = "originals/"
  }
  depends_on = [aws_sqs_queue_policy.s3]
}

resource "aws_dynamodb_table" "archive" {
  name         = local.prefix
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"
  attribute {
    name = "PK"
    type = "S"
  }
  attribute {
    name = "SK"
    type = "S"
  }
  attribute {
    name = "GSI1PK"
    type = "S"
  }
  attribute {
    name = "GSI1SK"
    type = "S"
  }
  global_secondary_index {
    name            = "owner-created"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }
  point_in_time_recovery { enabled = true }
  server_side_encryption { enabled = true }
}

resource "aws_sns_topic" "notifications" {
  name = "${local.prefix}-tag-notifications"
}
resource "aws_sns_topic_subscription" "demo_email" {
  count     = var.notification_email == "" ? 0 : 1
  topic_arn = aws_sns_topic.notifications.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

resource "aws_cognito_user_pool" "users" {
  name                     = "${local.prefix}-users"
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  password_policy {
    minimum_length    = 10
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }
  schema {
    name                = "given_name"
    attribute_data_type = "String"
    mutable             = true
    required            = true
    string_attribute_constraints {
      min_length = 1
      max_length = 128
    }
  }
  schema {
    name                = "family_name"
    attribute_data_type = "String"
    mutable             = true
    required            = true
    string_attribute_constraints {
      min_length = 1
      max_length = 128
    }
  }
}
resource "aws_cognito_user_pool_client" "web" {
  name                                 = "${local.prefix}-web"
  user_pool_id                         = aws_cognito_user_pool.users.id
  generate_secret                      = false
  explicit_auth_flows                  = ["ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
  prevent_user_existence_errors        = "ENABLED"
  supported_identity_providers         = ["COGNITO"]
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["email", "openid", "profile"]
  callback_urls = concat(
    ["http://localhost:5173/"],
    var.deploy_compute ? ["${google_cloud_run_v2_service.web[0].uri}/"] : []
  )
  logout_urls = concat(
    ["http://localhost:5173/"],
    var.deploy_compute ? ["${google_cloud_run_v2_service.web[0].uri}/"] : []
  )
}

resource "aws_ecr_repository" "api" {
  name = "${local.prefix}-api"
  image_scanning_configuration { scan_on_push = true }
}
resource "aws_ecr_repository" "worker" {
  name = "${local.prefix}-worker"
  image_scanning_configuration { scan_on_push = true }
}

resource "aws_iam_role" "lambda" {
  count = var.lab_role_arn == "" ? 1 : 0
  name  = var.aws_role_name
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}
resource "aws_iam_role_policy" "lambda" {
  count = var.lab_role_arn == "" ? 1 : 0
  role  = aws_iam_role.lambda[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], Resource = "arn:aws:logs:*:*:*" },
      { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], Resource = "${aws_s3_bucket.media.arn}/*" },
      { Effect = "Allow", Action = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan", "dynamodb:BatchGetItem", "dynamodb:BatchWriteItem", "dynamodb:TransactWriteItems"], Resource = [aws_dynamodb_table.archive.arn, "${aws_dynamodb_table.archive.arn}/index/*"] },
      { Effect = "Allow", Action = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"], Resource = aws_sqs_queue.jobs.arn },
      { Effect = "Allow", Action = "sns:Publish", Resource = aws_sns_topic.notifications.arn }
    ]
  })
}

resource "aws_lambda_function" "api" {
  count         = var.deploy_compute ? 1 : 0
  function_name = "${local.prefix}-api"
  role          = local.lambda_role_arn
  package_type  = "Image"
  image_uri     = var.api_image_uri
  timeout       = 30
  memory_size   = 1024
  environment {
    variables = {
      APP_ENV           = "cloud"
      TABLE_NAME        = aws_dynamodb_table.archive.name
      MEDIA_BUCKET      = aws_s3_bucket.media.id
      COGNITO_CLIENT_ID = aws_cognito_user_pool_client.web.id
      COGNITO_ISSUER    = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.users.id}"
      CORS_ORIGINS = join(",", concat(
        ["http://localhost:5173", "http://127.0.0.1:5173"],
        var.deploy_compute ? [google_cloud_run_v2_service.web[0].uri] : []
      ))
      NOTIFICATION_TOPIC_ARN  = aws_sns_topic.notifications.arn
      INFERENCE_MODE          = "http"
      INFERENCE_URL           = var.deploy_compute ? google_cloud_run_v2_service.inference[0].uri : ""
      GCP_WIF_AUDIENCE        = "//iam.googleapis.com/projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.aws.workload_identity_pool_id}/providers/${google_iam_workload_identity_pool_provider.aws.workload_identity_pool_provider_id}"
      GCP_WIF_SERVICE_ACCOUNT = google_service_account.aws_caller.email
    }
  }
}
resource "aws_lambda_function" "worker" {
  count         = var.deploy_compute ? 1 : 0
  function_name = "${local.prefix}-worker"
  role          = local.lambda_role_arn
  package_type  = "Image"
  image_uri     = var.worker_image_uri
  timeout       = 900
  memory_size   = 3008
  ephemeral_storage {
    size = 4096
  }
  environment {
    variables = {
      TABLE_NAME              = aws_dynamodb_table.archive.name
      MEDIA_BUCKET            = aws_s3_bucket.media.id
      NOTIFICATION_TOPIC_ARN  = aws_sns_topic.notifications.arn
      GCP_PROJECT_ID          = var.gcp_project_id
      GCP_REGION              = var.gcp_region
      INFERENCE_URL           = var.deploy_compute ? google_cloud_run_v2_service.inference[0].uri : ""
      GCP_WIF_AUDIENCE        = "//iam.googleapis.com/projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.aws.workload_identity_pool_id}/providers/${google_iam_workload_identity_pool_provider.aws.workload_identity_pool_provider_id}"
      GCP_WIF_SERVICE_ACCOUNT = google_service_account.aws_caller.email
    }
  }
}
resource "aws_lambda_event_source_mapping" "worker" {
  count                   = var.deploy_compute ? 1 : 0
  event_source_arn        = aws_sqs_queue.jobs.arn
  function_name           = aws_lambda_function.worker[0].arn
  batch_size              = 1
  function_response_types = ["ReportBatchItemFailures"]
}

# Docker-free deployment path for Member 3's S3 -> SQS -> DynamoDB workflow.
# Run infra/build-member3-worker.ps1 before Terraform apply to generate the ZIP.
resource "aws_lambda_function" "worker_zip" {
  count            = var.deploy_zip_worker ? 1 : 0
  function_name    = "${local.prefix}-member3-worker"
  role             = local.lambda_role_arn
  filename         = "${path.module}/build/member3-worker.zip"
  source_code_hash = var.deploy_zip_worker ? filebase64sha256("${path.module}/build/member3-worker.zip") : null
  handler          = "member3_lambda.handler"
  runtime          = "python3.12"
  timeout          = 120
  memory_size      = 1024
  environment {
    variables = {
      TABLE_NAME        = aws_dynamodb_table.archive.name
      MEDIA_BUCKET      = aws_s3_bucket.media.id
      ENABLE_THUMBNAILS = "false"
    }
  }
}
resource "aws_lambda_event_source_mapping" "worker_zip" {
  count                   = var.deploy_zip_worker ? 1 : 0
  event_source_arn        = aws_sqs_queue.jobs.arn
  function_name           = aws_lambda_function.worker_zip[0].arn
  batch_size              = 1
  function_response_types = ["ReportBatchItemFailures"]
}

resource "aws_apigatewayv2_api" "http" {
  name          = "${local.prefix}-api"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = concat(
      ["http://localhost:5173", "http://127.0.0.1:5173"],
      var.deploy_compute ? [google_cloud_run_v2_service.web[0].uri] : []
    )
    allow_headers = ["authorization", "content-type"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
  }
}
resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.http.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "cognito"
  jwt_configuration {
    audience = [aws_cognito_user_pool_client.web.id]
    issuer   = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.users.id}"
  }
}
resource "aws_apigatewayv2_integration" "api" {
  count                  = var.deploy_compute ? 1 : 0
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api[0].invoke_arn
  payload_format_version = "2.0"
}
resource "aws_apigatewayv2_route" "default" {
  count              = var.deploy_compute ? 1 : 0
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "$default"
  target             = "integrations/${aws_apigatewayv2_integration.api[0].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}
resource "aws_apigatewayv2_route" "cors_preflight" {
  count              = var.deploy_compute ? 1 : 0
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "OPTIONS /{proxy+}"
  target             = "integrations/${aws_apigatewayv2_integration.api[0].id}"
  authorization_type = "NONE"
}
resource "aws_apigatewayv2_route" "health" {
  count              = var.deploy_compute ? 1 : 0
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /health"
  target             = "integrations/${aws_apigatewayv2_integration.api[0].id}"
  authorization_type = "NONE"
}
resource "aws_apigatewayv2_route" "dev_token_disabled" {
  count              = var.deploy_compute ? 1 : 0
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "POST /api/v1/auth/dev-token"
  target             = "integrations/${aws_apigatewayv2_integration.api[0].id}"
  authorization_type = "NONE"
}
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true
}
resource "aws_lambda_permission" "api_gateway" {
  count         = var.deploy_compute ? 1 : 0
  statement_id  = "AllowApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api[0].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}
