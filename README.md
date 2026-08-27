# Pacific BioArchive 小组作业仓库

这是 FIT5225 Assignment 2 的四人接力式开发仓库。`main` 当前保存第一位成员完成并验证过的
本地原型；第二位成员的已部署云端版本位于 `member-2/cloud-deployment`，合并与正式交接完成后
再更新 `handoff-2-cloud` 标签。

## 当前状态

已经完成并验证：React 页面、Cognito 注册登录、DynamoDB/S3 云端边界、SQS Lambda Worker、
AWS API Gateway、AWS→GCP WIF、私有 Cloud Run inference、真实模型、四个容器镜像、Terraform
基础与 compute 资源、13 项自动测试、前端构建和 GitHub Actions 三项检查。

第二位成员已在真实 AWS/GCP 环境完成图片上传与推理端到端验证。镜像 digest、资源清单、费用
风险、清理责任和脱敏验收结果见
[member-2-delivery.md](docs/member-2-delivery.md)。第三、第四位成员负责的完整业务适配、并发与
故障注入测试和最终验收尚未完成。

## 四个人只看各自的文档

| 成员 | 工作内容 | 执行文档 |
|---|---|---|
| 第一位 | 本地原型、接口基线、仓库和第一次交接 | [member-1-prototype.md](docs/member-1-prototype.md) |
| 第二位 | AWS/GCP 部署、Cognito、API Gateway、WIF | [member-2-cloud.md](docs/member-2-cloud.md) |
| 第三位 | DynamoDB、S3/SQS worker、ML、查询、标签和删除 | [member-3-backend.md](docs/member-3-backend.md) |
| 第四位 | React 完善、云端集成、E2E、演示和最终验收 | [member-4-release.md](docs/member-4-release.md) |

第二位成员进行真实部署时同时使用
[member-2-deployment-runbook.md](docs/member-2-deployment-runbook.md)，其中列出账号本人必须
完成的步骤、镜像命令、验证证据和第三阶段交接边界。

`docs/ai-usage-zh.md` 是作业要求的生成式 AI 使用记录，每个人工作完成后补一条，不能删除。

## 所有人必须遵守的 Git 规则

1. 从上一位成员的交付标签新建自己的分支，不能直接在 `main` 开发。
2. 使用自己的 GitHub 账号提交，禁止共用账号或代替别人提交。
3. 完成后发起 Pull Request，让下一位成员实际运行后再接受交接。
4. 不得提交 `.env`、云凭证、MFA、Terraform state、上传文件、预签名 URL 或模型权重。
5. 遇到阻塞，用仓库的 `Handoff blocker` 模板建立 Issue，不能口头跳过。
6. 修改接口、数据结构或安全规则必须写进 PR，不能静默修改。

## 固定接口，不要随意改名

所有业务接口使用 `/api/v1`，云端除健康检查外都必须验证 Cognito JWT。

| 方法 | 地址 | 作用 |
|---|---|---|
| POST | `/uploads/init` | 去重并取得上传地址 |
| GET | `/media/{mediaId}` | 查询处理状态和媒体信息 |
| POST | `/queries/tags` | 多标签 AND 和最低数量查询 |
| POST | `/queries/species` | 单一物种查询 |
| POST | `/queries/thumbnail` | 缩略图反查原文件 |
| POST | `/queries/file/init` | 取得临时查询文件上传地址 |
| POST | `/queries/file/{queryId}/execute` | 识别临时文件并查询 |
| POST | `/tags/bulk` | 批量增加或删除标签 |
| DELETE | `/media` | 删除当前用户拥有的媒体 |
| POST | `/subscriptions` | 订阅标签通知 |
| DELETE | `/subscriptions/{tag}` | 取消订阅 |
| GET | `/species` | 返回模型支持的 46 个物种 |

标签统一规则：去掉两端空格、Unicode NFC、小写、空格和连字符替换为下划线；拒绝空标签
和超过 64 个字符的标签。认证用户可查询共享档案，但只能修改和删除自己上传的媒体。

## 时间安排

- 8月23日：第一位成员交付 `handoff-1-local`。
- 8月24日：第二位成员交付 `handoff-2-cloud`。
- 8月25日：第三位成员交付 `handoff-3-core-complete`。
- 8月26日：第四位成员交付 `release-candidate-1`。
- 8月27日至29日：全员修复、撰写各自报告章节、演练两次。
- 8月30日：最终检查后标记 `v1.0.0` 并提交。
