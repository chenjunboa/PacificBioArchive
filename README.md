# Pacific BioArchive 小组作业仓库

这是 FIT5225 Assignment 2 的四人接力式开发仓库。当前 `main` 分支和
`handoff-1-local` 标签保存的是第一位成员完成并验证过的本地完整原型。

## 当前状态

已经完成并验证：React 本地页面和登录、图片上传与 SHA-256 去重、缩略图、四类查询、
批量标签、删除、订阅、所有者权限、视频每秒一帧函数、真实模型样例、Terraform 框架、
9 项自动测试、前端构建、Terraform 验证和 GitHub Actions。

尚未完成：真实 AWS/GCP 部署、DynamoDB/S3 生产适配器、SQS 云端 worker、Cognito
真实登录、WIF 和云端端到端测试。这些工作已明确分配给第二至第四位成员。

## 四个人只看各自的文档

| 成员 | 工作内容 | 执行文档 |
|---|---|---|
| 第一位 | 本地原型、接口基线、仓库和第一次交接 | [member-1-prototype.md](docs/member-1-prototype.md) |
| 第二位 | AWS/GCP 部署、Cognito、API Gateway、WIF | [member-2-cloud.md](docs/member-2-cloud.md) |
| 第三位 | DynamoDB、S3/SQS worker、ML、查询、标签和删除 | [member-3-backend.md](docs/member-3-backend.md) |
| 第四位 | React 完善、云端集成、E2E、演示和最终验收 | [member-4-release.md](docs/member-4-release.md) |

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
