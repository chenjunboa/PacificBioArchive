# 第二位成员云端部署交付证据

这份文件是 `member-2/cloud-deployment` 的 PR 与第三位成员交接依据。它只记录可公开的资源名、
不可变镜像摘要和脱敏结果，不包含密码、MFA、访问 token、预签名 URL、Terraform state 或模型
权重。

## 1. 交付范围

- AWS `us-east-1`：Cognito、API Gateway、Lambda API/Worker、DynamoDB、S3、SQS/DLQ、SNS、
  ECR、IAM 和 CloudWatch 日志；
- GCP `us-central1`：Cloud Run Web/Inference、私有模型 GCS bucket、Artifact Registry、两个
  Service Account 和 AWS Workload Identity Federation；
- Web：Cognito 注册、邮箱确认、登录、S3 直传和识别状态轮询；
- 推理：真实 MegaDetector/SpeciesNet 模型 bundle，AWS Worker 无 JSON key 调用私有 GCP
  inference。

## 2. 四个不可变镜像摘要

以下值于 2026-08-24 直接从 AWS ECR 和 GCP Artifact Registry 重新查询，不是从本地标签推断：

| 镜像 | Commit tag | Registry digest |
|---|---|---|
| API | `9d8d7b802e4a36dbac1a9c4a979e583d2d906b00` | `sha256:66aa3d0e4f0586f144d28623d78728878028b7f28e9581b6e767c8623fde5cc7` |
| Worker | `53720237c47d410d8b58b39769f8a6b5c8e20de8` | `sha256:f68c237c0521214fb9f15579cedc62040f88e818f8be5335667d209514083a68` |
| Inference | `53720237c47d410d8b58b39769f8a6b5c8e20de8` | `sha256:4465568a655ef2a48020a0c45f976fea01b5c3161b207cc8db05f7d11e82f81d` |
| Web | `53720237c47d410d8b58b39769f8a6b5c8e20de8` | `sha256:63f8d1e95fd9d9d68d554e203553b01c9fb307842429fa276764ab43831f4a28` |

## 3. 实际资源列表

2026-08-24 的本地 Terraform state 包含 46 个受管资源地址，另有 1 个只读 GCP project data
source。按平台和用途汇总如下。

### AWS（29 个 Terraform 资源地址）

- API Gateway：1 个 HTTP API、1 个 stage、1 个 Cognito JWT authorizer、1 个 Lambda
  integration、4 条 route；
- Lambda：API 和 Worker 各 1 个、1 个 SQS event source mapping、1 个 API invoke permission；
- S3：1 个私有媒体 bucket，以及 public-access block、AES-256 encryption、CORS、1 天临时对象
  lifecycle 和 SQS notification；
- DynamoDB：1 个按需计费、启用加密和 PITR 的单表；
- SQS：1 个 jobs queue、1 个 DLQ 和 1 个 S3 send policy；
- Cognito：1 个 user pool 和 1 个无 client secret 的 web app client；
- ECR：API 和 Worker 两个私有 repository；
- SNS：1 个通知 topic；
- IAM：1 个 Lambda role 和 1 个最小运行 policy。

### GCP（17 个 Terraform 资源地址）

- Cloud Run：公开 Web 和私有 Inference 两个 service，以及两个 invoker IAM binding；
- Artifact Registry：1 个 Docker repository；
- Cloud Storage：1 个启用版本控制和 public-access prevention 的模型 bucket，以及 1 个只读
  IAM binding；
- IAM：2 个 Service Account、1 个 federated binding、1 个 Workload Identity Pool 和 1 个
  AWS provider；
- 项目 API：Artifact Registry、IAM Credentials、Cloud Run、Cloud Storage 和 STS 共 5 个。

## 4. 实际伸缩、可能费用和清理责任

| 运行项 | 配置 | 费用风险 |
|---|---|---|
| Cloud Run Web | 最小 0、最大 2；1 vCPU、512 MiB | 请求、CPU、内存、网络和镜像存储 |
| Cloud Run Inference | 最小 0、最大 3；4 vCPU、8 GiB；900 秒超时 | 冷启动模型下载、CPU/内存执行和跨云网络 |
| Lambda API | 1024 MB；30 秒超时 | 调用次数和 GB-s |
| Lambda Worker | 3008 MB；900 秒超时；4 GiB 临时空间 | 长时间模型处理的 GB-s 和额外临时存储 |
| 持久资源 | S3、GCS、ECR、Artifact Registry、DynamoDB PITR、日志 | 即使 compute 缩到 0 仍可能产生存储或日志费用 |

当前两个 Cloud Run service 的最小实例数均为 0，不存在常驻实例费用，但首次推理会冷启动。
AWS 和 GCP budget 都只是告警，不是自动停机或硬性消费上限。主要风险是 inference 的 4 vCPU/
8 GiB 执行时间、约 470 MiB 模型与容器存储，以及 AWS/GCP 之间的数据传输。

费用依据以官方定价为准：

- [AWS Lambda Pricing](https://aws.amazon.com/lambda/pricing/)
- [AWS API Gateway Pricing](https://aws.amazon.com/api-gateway/pricing/)
- [Google Cloud Run Pricing](https://cloud.google.com/run/pricing)
- [Google Cloud Storage Pricing](https://cloud.google.com/storage/pricing)

清理负责人：**Bingyi Wang（第二位成员、当前 AWS/GCP 账号持有人）**。清理时间为作业评分和
团队演示全部结束、组长书面确认之后。清理前保存脱敏证据；随后先清空 S3/GCS 的对象与版本、
两个 container registry 的镜像，再审核 `terraform plan -destroy`，最后由账号本人执行 destroy。
不得在评分前提前销毁。

## 5. 真实云端验收结果

以下是 2026-08-24 再次只读核验的脱敏结果：

| 验收项 | 结果 |
|---|---|
| Cognito | 1 个用户：`Enabled=true`、`UserStatus=CONFIRMED`；未记录邮箱或用户名 |
| 未登录业务 API | `GET /api/v1/species` 返回 401 |
| 登录后的 API | 浏览器实测成功加载 46 类并完成一次上传；不保存测试密码或 token |
| Web | 公开入口返回 200 |
| S3 | `originals/` 下存在 1 个真实对象，170,490 bytes，时间 `2026-08-24T13:19:16Z`；对象名已省略 |
| SQS | 当天 `NumberOfMessagesSent=2`；当前 visible/in-flight 均为 0；DLQ maxReceiveCount=3 |
| Worker | `13:19:18Z` 开始、`13:20:20Z` 结束；61.8079 秒；3008 MB 配额，最大使用 141 MB |
| 私有 inference | 匿名 `/health` 返回 403 |
| WIF 成功 | GCP `13:20:15Z` 完成真实模型加载，`13:20:20Z` 的 `POST /infer` 返回 200 |
| 最终页面 | `Ready — detected 1 species tag(s).` |

Worker 结束时间与 GCP `/infer 200` 时间一致，且 inference 匿名访问被拒绝，因此证据同时覆盖
AWS Worker、WIF 身份交换和私有 Cloud Run 调用链，而不是公开 inference 的伪成功。

## 6. 脱敏截图清单

截图存放约定见 [evidence/member-2/README.md](evidence/member-2/README.md)。在 PR 合并前必须把
六张脱敏截图作为 PR 附件或放入该目录；不得上传带 token、密码、邮箱验证码、完整用户邮箱、
预签名查询参数或临时 AWS 凭据的原图。

## 7. 第三位成员范围

每个未完成项均有独立 Issue 草稿，见 [member-3-issues/README.md](member-3-issues/README.md)。
实际 GitHub Issue 创建后，把 Issue 编号和 URL 回填到该索引及 PR。不得用一个“待完善”Issue
代替全部工作。

## 8. PR 与现场交接

- PR：`member-2/cloud-deployment` → `main`；
- PR 合并后才能把 `handoff-2-cloud` 移到合并提交；当前旧标签不能作为最终交接依据；
- 第三位成员必须从最终标签创建 `member-3/core-hardening`；
- 不共享第二位成员的云密码、MFA 或凭据；第三位成员使用自己的 AWS Academy/GCP 身份；
- 第三位成员当面完成登录、`/species` 和一次上传后，在 PR 填写姓名、UTC 时间和接受的 commit。

现场接受记录在第三位成员实际操作前保持未完成，不能由第二位成员代签。
