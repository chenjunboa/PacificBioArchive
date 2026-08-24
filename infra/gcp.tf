locals {
  gcp_services = toset([
    "artifactregistry.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "storage.googleapis.com",
    "sts.googleapis.com"
  ])
}
data "google_project" "current" {
  project_id = var.gcp_project_id
}
resource "google_project_service" "services" {
  for_each           = local.gcp_services
  service            = each.value
  disable_on_destroy = false
}
resource "google_storage_bucket" "models" {
  name                        = "${var.gcp_project_id}-${local.prefix}-models"
  location                    = var.gcp_region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  versioning {
    enabled = true
  }
  depends_on = [google_project_service.services]
}
resource "google_artifact_registry_repository" "containers" {
  location      = var.gcp_region
  repository_id = local.prefix
  format        = "DOCKER"
  depends_on    = [google_project_service.services]
}
resource "google_service_account" "inference" {
  account_id   = "pba-inference"
  display_name = "Pacific BioArchive inference"
}
resource "google_service_account" "aws_caller" {
  account_id   = "pba-aws-caller"
  display_name = "AWS processing Lambda caller"
}
resource "google_storage_bucket_iam_member" "inference_models" {
  bucket = google_storage_bucket.models.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.inference.email}"
}
resource "google_iam_workload_identity_pool" "aws" {
  workload_identity_pool_id = "pba-aws-pool"
  display_name              = "PBA AWS identities"
}
resource "google_iam_workload_identity_pool_provider" "aws" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.aws.workload_identity_pool_id
  workload_identity_pool_provider_id = "aws-provider"
  display_name                       = "AWS provider"
  aws {
    account_id = var.aws_account_id
  }
  attribute_mapping = {
    "google.subject"     = "assertion.arn"
    "attribute.aws_role" = "assertion.arn.extract('assumed-role/{role}/')"
  }
}
resource "google_service_account_iam_member" "federated" {
  service_account_id = google_service_account.aws_caller.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.aws.name}/attribute.aws_role/${local.lambda_role_name}"
}

resource "google_cloud_run_v2_service" "inference" {
  count    = var.deploy_compute ? 1 : 0
  name     = "${local.prefix}-inference"
  location = var.gcp_region
  template {
    service_account = google_service_account.inference.email
    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }
    containers {
      image = var.inference_image
      resources {
        limits = {
          cpu    = "4"
          memory = "8Gi"
        }
      }
      env {
        name  = "MODEL_MODE"
        value = "real"
      }
      env {
        name  = "MODEL_MANIFEST"
        value = "gs://${google_storage_bucket.models.name}/model-manifest.json"
      }
      env {
        name  = "MODEL_CACHE_DIR"
        value = "/tmp/models"
      }
    }
    timeout = "900s"
  }
  depends_on = [google_project_service.services]
}
resource "google_cloud_run_v2_service_iam_member" "aws_invoker" {
  count    = var.deploy_compute ? 1 : 0
  project  = google_cloud_run_v2_service.inference[0].project
  location = google_cloud_run_v2_service.inference[0].location
  name     = google_cloud_run_v2_service.inference[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.aws_caller.email}"
}
resource "google_cloud_run_v2_service" "web" {
  count    = var.deploy_compute ? 1 : 0
  name     = "${local.prefix}-web"
  location = var.gcp_region
  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
    containers {
      image = var.web_image
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
  }
  depends_on = [google_project_service.services]
}
resource "google_cloud_run_v2_service_iam_member" "web_public" {
  count    = var.deploy_compute ? 1 : 0
  project  = google_cloud_run_v2_service.web[0].project
  location = google_cloud_run_v2_service.web[0].location
  name     = google_cloud_run_v2_service.web[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
