variable "project_name" {
  type    = string
  default = "pacific-bioarchive"
}
variable "environment" {
  type    = string
  default = "prototype"
}
variable "aws_region" {
  type    = string
  default = "us-east-1"
}
variable "gcp_region" {
  type    = string
  default = "us-central1"
}
variable "gcp_project_id" {
  type = string
}
variable "notification_email" {
  type    = string
  default = ""
}
variable "lab_role_arn" {
  type        = string
  default     = ""
  description = "AWS Academy LabRole ARN. Leave empty to create a least-privilege Lambda role."
}
variable "aws_account_id" {
  type = string
}
variable "aws_role_name" {
  type    = string
  default = "PacificBioArchiveLambdaRole"
}
variable "deploy_compute" {
  type    = bool
  default = false
}
variable "api_image_uri" {
  type    = string
  default = ""
}
variable "worker_image_uri" {
  type    = string
  default = ""
}
variable "inference_image" {
  type    = string
  default = ""
}
variable "web_image" {
  type    = string
  default = ""
}
