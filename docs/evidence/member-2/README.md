# 第二位成员脱敏截图目录

PR 合并前需提供以下六张截图。可将图片上传为 PR 附件；若提交到仓库，则使用下列文件名。

1. `01-cognito-confirmed-redacted.png`：只显示用户为 enabled/confirmed；遮住邮箱、用户名和 sub；
2. `02-api-401-and-200-redacted.png`：同一业务接口无 token 为 401、登录后为 200；遮住 token；
3. `03-s3-object-redacted.png`：显示 `originals/` 中对象、大小和时间；遮住不必要的账号信息；
4. `04-sqs-message-or-metric-redacted.png`：显示 jobs queue 收到消息或 CloudWatch
   `NumberOfMessagesSent`；不要展示消息正文中的预签名 URL；
5. `05-cloud-run-private-403-redacted.png`：匿名请求 inference 返回 403；
6. `06-wif-worker-infer-200-redacted.png`：AWS Worker 成功结束和相邻的 GCP `/infer 200` 日志；
   遮住 RequestId 等不需要提交的标识。

已有真实文字证据及 UTC 时间记录在 [../../member-2-delivery.md](../../member-2-delivery.md)。截图
只能用于呈现同一事实，不能修改响应码、时间或结果。不得提交：

- 密码、MFA、邮箱验证码；
- Authorization header、JWT、OAuth token、AWS 临时凭据；
- 带查询参数的预签名 URL；
- 完整测试用户邮箱；
- Terraform state、tfvars 或模型权重。
