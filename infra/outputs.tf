output "media_bucket" { value = aws_s3_bucket.media.id }
output "table_name" { value = aws_dynamodb_table.archive.name }
output "api_endpoint" { value = aws_apigatewayv2_api.http.api_endpoint }
output "cognito_user_pool_id" { value = aws_cognito_user_pool.users.id }
output "cognito_client_id" { value = aws_cognito_user_pool_client.web.id }
output "api_ecr" { value = aws_ecr_repository.api.repository_url }
output "worker_ecr" { value = aws_ecr_repository.worker.repository_url }
output "member3_worker_name" { value = try(aws_lambda_function.worker_zip[0].function_name, null) }
output "gcp_model_bucket" { value = google_storage_bucket.models.name }
output "gcp_artifact_registry" { value = google_artifact_registry_repository.containers.name }
output "gcp_artifact_registry_url" {
  value = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.containers.repository_id}"
}
output "gcp_wif_audience" {
  value = "//iam.googleapis.com/projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.aws.workload_identity_pool_id}/providers/${google_iam_workload_identity_pool_provider.aws.workload_identity_pool_provider_id}"
}
output "gcp_wif_service_account" { value = google_service_account.aws_caller.email }
output "inference_url" { value = var.deploy_compute ? google_cloud_run_v2_service.inference[0].uri : null }
output "web_url" { value = var.deploy_compute ? google_cloud_run_v2_service.web[0].uri : null }
