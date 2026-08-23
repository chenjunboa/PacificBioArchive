# 第二位成员执行手册：AWS/GCP 部署、认证和跨云调用

## 你的目标

把第一位成员的本地原型变成一个真实可访问的多云基础版本。你负责“部署和身份链路能工作”；
第三位成员负责把所有云端数据、ML、查询和异常处理做完整。

开始标签：`handoff-1-local`  
工作分支：`member-2/cloud-deployment`  
完成标签：`handoff-2-cloud`

## 开始前先做账号检查

### AWS Academy

1. 从 FIT5225 课程入口打开 Learner Lab。
2. 点击 **Start Lab**，等状态变绿后进入 AWS Console。
3. 右上角区域选择 **N. Virginia / us-east-1**。
4. 记录当前 AWS Account ID 的最后四位和剩余实验时间。
5. 在 IAM 中确认是否存在课程提供的 `LabRole`。
6. 逐项确认可以创建或使用：S3、DynamoDB、SQS、SNS、Lambda、API Gateway、Cognito、ECR。

AWS Academy 凭证会过期。只把临时凭证放在当前终端，不要发到群聊、Issue、截图或代码中。

### GCP

1. 登录 GCP Console，选择一个现有项目。
2. 记录项目名称和不可变的 Project ID。
3. 打开 **Billing**，确认该项目已关联有效 Billing Account。
4. 确认你有权限启用 API、创建 Cloud Run、Cloud Storage、Artifact Registry、Service
   Account 和 Workload Identity Pool。

如果没有已经启用 Billing 的项目，立即停止并告知组长。禁止自行绑卡、开免费试用或接受付费条款。

## 第一步：取得代码并复现原型

```powershell
git clone https://github.com/chenjunboa/PacificBioArchive.git
Set-Location PacificBioArchive
git fetch --tags
git switch -c member-2/cloud-deployment handoff-1-local
uv sync --extra dev
uv run pytest -q
Push-Location web
npm ci
npm run build
Pop-Location
```

基线失败时先建立 `Handoff blocker` Issue，让第一位成员复现。不要一边修原型一边部署，避免责任混淆。

## 第二步：准备 Terraform 参数

复制 `infra/terraform.tfvars.example` 为不会上传的 `infra/terraform.tfvars`，填写：

- `gcp_project_id`：GCP Project ID；
- `aws_account_id`：Learner Lab Account ID；
- `deploy_compute = false`；
- 如果不能创建 IAM Role，填写课程 `lab_role_arn`，并在报告写明限制；
- `notification_email` 只有在收件人准备点击 SNS 确认时才填写。

先执行 foundation plan：

```powershell
Set-Location infra
terraform init
terraform fmt -check
terraform validate
terraform plan -out=foundation.tfplan
```

核对计划只使用 AWS `us-east-1`、GCP `us-central1`，资源名称都有
`pacific-bioarchive-prototype` 前缀。确认后再 apply。`tfplan` 和 state 已被 Git 忽略。

## 第三步：建立生产运行边界

当前 API 只能使用 SQLite 和本地文件。你必须先把代码分为：

- local 模式：SQLite、本地目录、本地 JWT；
- cloud API 模式：DynamoDB、S3 预签名 URL、Cognito JWT；
- cloud worker：接收 SQS 事件，从 S3 读取文件，调用推理后写回 DynamoDB/SNS；
- API Lambda 和 worker Lambda 使用不同的入口或镜像命令。

你负责让这些入口可以部署和启动。复杂索引、事务、所有异常场景由第三位成员继续完善。

云端 `POST /auth/dev-token` 必须返回 404；本地模式仍需保留，方便测试。

## 第四步：构建并发布镜像

按当前完整 Git commit SHA 标记镜像，不能只使用 `latest`：

- API 和 worker 推送到 AWS ECR；
- inference 和 web 推送到 GCP Artifact Registry。

在 PR 中记录四个镜像的 digest，不能记录登录 token。

将 `labels.txt`、模型和 `manifest.json` 上传到私有 GCS 模型桶。上传前后都计算 SHA-256。
manifest 必须记录 detector、classifier、labels 的 GCS URI、版本和 SHA-256。

当前推理容器引用本地 manifest 路径，你需要增加启动时从 GCS 下载或挂载 manifest 和模型的
逻辑。不能让云端服务依赖你电脑上的 `D:` 路径。

## 第五步：配置 Cognito 和 API Gateway

1. Cognito 使用邮箱作为用户名，自动验证邮箱。
2. 注册必须包含 `given_name` 和 `family_name`。
3. App client 不能生成 client secret，前端使用 Amplify。
4. Cloud Run Web URL 加入 Cognito callback 和 logout URL。
5. API Gateway 除健康检查外全部使用 Cognito JWT authorizer。
6. CORS 只允许本地开发地址和准确的 Cloud Run Web 域名，不能保持 `*`。
7. 测试无 token 返回 401、正确 token 返回 200、退出后旧浏览器会话不可继续调用。

邮箱验证码必须由真实收件人操作；遇到 MFA 时暂停让账号本人完成。

## 第六步：配置 AWS 到 GCP 的 WIF

目标是 Lambda 使用 AWS 临时身份换取 Google 短期 token，再调用私有 inference Cloud Run。

必须满足：

- inference Cloud Run 不允许 `allUsers`；
- 只有 federated caller Service Account 有 `roles/run.invoker`；
- Lambda、GitHub 和仓库都没有 GCP JSON key；
- 匿名请求 Cloud Run 返回拒绝；
- Lambda worker 使用 WIF 后调用成功。

禁止为了省事下载 Service Account JSON key。

## 第七步：部署 compute 并做冒烟测试

把四个 digest URI 填入本地 tfvars，设置 `deploy_compute=true`，再次 plan 和 apply。

必须依次测试：

1. Cloud Run Web 可以公开打开。
2. 新用户注册、收到验证码、确认、登录和退出。
3. 未登录调用 `/species` 返回 401。
4. 登录后 `/species` 返回 46 项。
5. `/uploads/init` 返回 S3 预签名上传地址。
6. 文件出现在 `originals/{mediaId}/...`。
7. S3 事件只进入 SQS 一次。
8. 匿名调用 inference 被拒绝，worker 使用 WIF 成功。
9. 媒体状态真实显示 `UPLOADED`、`PROCESSING`、`READY` 或明确的 `FAILED`，不能伪造成功。

## 你需要提交的内容

- 代码和 Terraform PR；
- 四个镜像 digest；
- 脱敏截图：Cognito 已验证用户、401/200、S3 文件、SQS 消息、Cloud Run 私有拒绝和 WIF 成功；
- 实际资源列表、可能费用、最小实例数和作业结束后的清理负责人；
- 仍需第三位成员完成的问题，每一项建立 Issue，不能只写“待完善”。

## 如何交给第三位成员

1. PR 合并后创建 `handoff-2-cloud` 标签。
2. 让第三位成员从该标签建立 `member-3/core-hardening`。
3. 不发送凭证；让对方用自己的 AWS Academy/GCP 登录。
4. 当面让对方完成登录、`/species` 和一次上传。
5. 在 PR 记录对方姓名、UTC 时间和接受的 commit。

第三位成员无法独立完成以上三步时，第二阶段仍由你负责，不能算交接完成。
