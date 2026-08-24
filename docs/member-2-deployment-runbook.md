# 第二阶段真实云部署操作清单

这份清单用于部署 `member-2/cloud-deployment` 分支。代码、测试和 Terraform 可以由协作工具
准备，但 AWS Academy 登录、GCP 登录、MFA、邮箱验证码、Billing 确认和实际费用授权必须由
账号本人操作。任何命令都不要把凭证、token、Terraform state 或模型权重提交到 Git。

## 0. 当前本地验证状态

- Python：12 项测试通过；
- Ruff：通过；
- React：`npm ci` 和生产构建通过，0 个已知 npm 漏洞；
- Terraform：`fmt -check` 和 `validate` 通过；
- Docker：API、worker、inference、web 四个镜像已在本机完成构建；API/Web/inference
  健康检查、worker 导入、MegaDetector/YOLO 导入和视频抽帧均通过；
- 真实云端：AWS/GCP foundation 已创建 33 个资源，模型 bundle 的 4 个对象已上传到私有
  GCS bucket；compute 镜像和云端端到端测试尚未完成。

## 1. 账号和工具准备（账号本人操作）

1. 选择 AWS 账号并把区域设为 `us-east-1`。本次部署使用个人 AWS 账号；如果改用
   AWS Academy，则启动 Learner Lab。
2. 个人账号使用 `aws login --profile fit5225` 的短期凭据；Academy 则把 Learner Lab
   提供的临时环境变量放入当前 PowerShell。不要把任何凭据贴到聊天或文件。
3. 执行 `aws sts get-caller-identity`，记录 Account ID，并确认身份是预期的 IAM user 或
   `LabRole`。
4. 安装 Google Cloud CLI，执行 `gcloud auth login` 和
   `gcloud auth application-default login`。
5. 执行 `gcloud config set project <PROJECT_ID>`，确认该项目已经关联 Billing。
6. 启动 Docker Desktop，执行 `docker info`，必须能显示 Server Version。

本机当前已有 AWS CLI、Google Cloud CLI、Terraform、Node 和可用的 Docker Desktop。

## 2. 填写不会提交的 Terraform 参数

```powershell
Copy-Item infra/terraform.tfvars.example infra/terraform.tfvars
```

编辑 `infra/terraform.tfvars`：

```hcl
gcp_project_id = "实际-project-id"
aws_account_id = "12位AWS账号ID"
deploy_compute = false
```

个人 AWS 账号不填写 `lab_role_arn`，Terraform 会创建专用最小权限角色。仅在 Academy
禁止创建角色时才填写课程提供的 `LabRole` ARN。

## 3. 部署 foundation

```powershell
Set-Location infra
terraform init -backend=false
terraform fmt -check
terraform validate
terraform plan -out=foundation.tfplan
terraform apply foundation.tfplan
terraform output
Set-Location ..
```

计划中应包含私有 S3、DynamoDB、SQS/DLQ、SNS、Cognito、ECR、GCS、Artifact Registry、
两个 Cloud Run service account 和 AWS Workload Identity Provider。此时 compute 尚未部署。

## 4. 准备模型文件

在仓库根目录准备以下三个不会提交 Git 的文件：

- `mdv5a.pt`；
- `model.pt`；
- `labels.txt`（仓库已包含）。

使用脚本生成一个不会提交的、换行和 SHA-256 都一致的 bundle：

```powershell
$bundle = .\scripts\prepare-model-bundle.ps1 -DetectorPath .\mdv5a.pt -ClassifierPath .\model.pt
```

脚本会打印目录；把该目录赋给 `$bundle`（例如
`.model-bundles/20260824-120000`），然后上传：

```powershell
$modelBucket = terraform -chdir=infra output -raw gcp_model_bucket
gcloud storage cp "$bundle/model-manifest.json" "gs://$modelBucket/model-manifest.json"
gcloud storage cp "$bundle/mdv5a.pt" "gs://$modelBucket/mdv5a.pt"
gcloud storage cp "$bundle/model.pt" "gs://$modelBucket/model.pt"
gcloud storage cp "$bundle/labels.txt" "gs://$modelBucket/labels.txt"
```

如果没有两个模型权重，必须先从第一位成员提供的校内安全渠道取得，不能从陌生链接下载，也
不能先部署 stub 后在报告中声称真实模型已完成。

## 5. 用完整 commit SHA 构建并推送四个镜像

先让第二位成员用自己的 GitHub 账号提交当前分支，再取得 SHA：

```powershell
$commitSha = git rev-parse HEAD
$awsAccount = aws sts get-caller-identity --query Account --output text
$awsRegion = "us-east-1"
$apiRepository = terraform -chdir=infra output -raw api_ecr
$workerRepository = terraform -chdir=infra output -raw worker_ecr
$gcpRegistry = terraform -chdir=infra output -raw gcp_artifact_registry_url
$apiEndpoint = terraform -chdir=infra output -raw api_endpoint
$userPoolId = terraform -chdir=infra output -raw cognito_user_pool_id
$clientId = terraform -chdir=infra output -raw cognito_client_id
```

登录两个 registry：

```powershell
$ecrPassword = aws ecr get-login-password --region $awsRegion
$ecrPassword | docker login --username AWS --password-stdin "$awsAccount.dkr.ecr.$awsRegion.amazonaws.com"
gcloud auth configure-docker "us-central1-docker.pkg.dev"
```

构建与推送：

```powershell
docker build --provenance=false -f services/api/Dockerfile -t "${apiRepository}:$commitSha" .
docker build --provenance=false -f services/worker/Dockerfile -t "${workerRepository}:$commitSha" .
docker build -f services/inference/Dockerfile -t "${gcpRegistry}/inference:$commitSha" .
docker build -f web/Dockerfile `
  --build-arg "VITE_API_BASE_URL=${apiEndpoint}/api/v1" `
  --build-arg "VITE_COGNITO_USER_POOL_ID=$userPoolId" `
  --build-arg "VITE_COGNITO_CLIENT_ID=$clientId" `
  -t "${gcpRegistry}/web:$commitSha" .

docker push "${apiRepository}:$commitSha"
docker push "${workerRepository}:$commitSha"
docker push "${gcpRegistry}/inference:$commitSha"
docker push "${gcpRegistry}/web:$commitSha"
```

把四个 `docker push` 输出中的 digest 保存到 PR，不要只记录 tag。

## 6. 部署 compute

在未提交的 `infra/terraform.tfvars` 追加：

```hcl
deploy_compute  = true
api_image_uri   = "上一步API镜像完整URI"
worker_image_uri = "上一步Worker镜像完整URI"
inference_image = "上一步Inference镜像完整URI"
web_image       = "上一步Web镜像完整URI"
```

然后执行：

```powershell
Set-Location infra
terraform fmt -check
terraform validate
terraform plan -out=compute.tfplan
terraform apply compute.tfplan
terraform output
Set-Location ..
```

第二次 apply 会把真实 Cloud Run Web URL 加入 Cognito callback/logout、API CORS 和 S3 CORS。

## 7. 必须由账号本人配合的冒烟测试

1. 打开 `web_url`，注册真实可收信邮箱，填写 first name、last name 和密码。
2. 输入 Cognito 邮件验证码，然后登录。
3. 无 token 请求 `/api/v1/species` 应为 401；登录后的请求应返回 46 项。
4. 上传小 JPG：浏览器先向 API 预约，再直接 POST 到私有 S3。
5. 查看 SQS、Lambda 和 CloudWatch，状态应进入 `PROCESSING`，随后为 `READY` 或明确
   `FAILED`。
6. 匿名请求 `inference_url` 应拒绝；Worker 日志应证明 WIF 调用成功。
7. 保存脱敏截图，不显示 URL 查询参数、token、AWS 临时凭据或用户密码。

## 8. 已知交接边界

第二阶段提供生产运行边界、原子 checksum 预约、直接 S3 上传、最小 Worker、Cognito 和 WIF。
第三阶段仍需完成 TAG/THUMB 索引、所有 DynamoDB 事务、临时文件查询、完整 SNS 订阅、并发
Worker 租约、模型 generation 定期热更新和全面故障注入测试。不得把这些未完成项写成通过。
