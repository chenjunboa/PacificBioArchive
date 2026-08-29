# 生成式 AI 使用记录

这是作业报告需要引用的记录，不能删除。生成式 AI 用于辅助架构拆分、原型搭建、边界情况、
测试建议和文档整理。小组成员仍需亲自阅读、理解、修改和验证自己提交的所有代码与报告。

每个人完成工作后按下面格式追加：

```text
日期：
成员：
使用的 AI 工具：
用途：
涉及的文件或功能：
本人如何检查和修改：
最终测试证据：
```

## 2026年8月23日——第一位成员本地原型

- 用途：系统架构拆分、本地原型脚手架、边界情况清单、自动测试建议、仓库说明和四人交接安排。
- 涉及内容：API、本地认证与存储、React 原型、推理服务、Terraform 框架、测试和中文执行手册。
- 人工责任：第一位成员需要阅读接口和执行手册，运行 README 中的检查并亲自确认 GitHub commit。
- 已完成验证：后端/推理测试、Ruff、TypeScript/Vite 构建、Terraform 验证、真实模型样例和浏览器流程。
- 限制：AI 辅助和本地测试不能证明云端正确。第二至第四位成员必须独立实现和验证自己的部分。

## 2026年8月24日——第二位成员真实云端部署

- 使用的 AI 工具：OpenAI Codex。
- 用途：审计本地原型与作业要求的差距、实现云端运行边界、生成测试和部署操作清单。
- 涉及内容：DynamoDB/S3 适配器、SQS Lambda Worker、AWS→GCP WIF、Cognito 注册与邮箱确认、
  模型 GCS 下载、Lambda 容器入口、Terraform 和云端上传前端。
- 人工责任：第二位成员必须用本人账号确认每次云资源操作、邮箱验证码、Billing、镜像 digest、
  云端日志和 PR，并在演示前能解释实际部署结果。
- 本人检查和修改：使用个人 AWS/GCP 账号逐次审核 Terraform plan，处理 AWS 临时凭据、ECR
  登录、Lambda 内存配额、API Gateway CORS 和 DynamoDB 事务序列化问题；本人完成 Cognito
  邮箱验证、真实图片上传和页面结果确认。
- 最终测试证据：13 项 Python 测试、Ruff、React 构建、Terraform 验证和 GitHub Actions 三项
  检查通过；四个镜像已推送并由 registry digest 复核；真实 AWS/GCP apply 完成；匿名 inference
  返回 403，Worker 通过 WIF 调用私有 Cloud Run `/infer` 返回 200，页面最终显示识别完成。
- 限制：AI 没有接触或保存账号密码、MFA、邮箱验证码、云 token 或模型权重；第三位成员范围内
  的完整索引、查询、并发租约、订阅、删除一致性和故障注入测试仍需按独立 Issue 完成。

## 2026年8月28日——第四位成员 UI、E2E 和最终演示准备

- 使用的 AI 工具：OpenAI Codex。
- 用途：审计第三位成员交接代码与第四位成员清单的差距，补齐云端查询/索引稳定性、本地和云端
  UI 工作流、Playwright 本地端到端测试、演示脚本和验收状态记录。
- 涉及内容：DynamoDB 标签索引、缩略图映射、临时查询文件、删除清理、AWS 到 GCP WIF 调用配置、
  React 登录/上传/四类查询/媒体管理/通知页面、Playwright E2E、`docs/demo-script.md` 和
  `docs/member-4-acceptance.md`。
- 人工责任：第四位成员需要亲自阅读这些提交和文档，用自己的 GitHub 账号确认 commit/merge，
  并在真实 AWS/GCP 部署中完成两轮云端冒烟测试、邮箱确认、截图/视频和报告文字复核。
- 本人检查和修改：本地配置 Git author 为 `pb-monash <bpan0043@student.monash.edu>`；逐步运行
  单元测试、Ruff、前端构建、Terraform validate、浏览器页面检查和 Playwright E2E；在获得
  AWS/Cognito 访问后，更新 API/Worker Lambda 镜像，禁用抢占任务的 `member3-worker` fallback
  触发器，并用临时 Cognito 用户运行真实云端图片和短视频冒烟测试；只把实际验证内容写为完成。
- 最终测试证据：`npm run test:e2e` 通过 1 项完整本地流程；`npm run build` 通过；
  `.venv/bin/python -m pytest -q` 通过 17 项测试；Ruff 通过；`terraform -chdir=infra validate`
  通过；真实云端两轮图片 smoke 分别通过 26.0 秒和 24.2 秒；真实云端 3 秒 MP4 smoke 通过
  1.7 分钟；DynamoDB 对这些 smoke media ID 的清理检查为 0，媒体 DLQ 为 0。
- 限制：AI 没有接触或保存 AWS/GCP 凭据、Cognito 测试用户密码、邮箱验证码、JWT、预签名 URL
  查询参数或 Terraform state。SNS 邮箱确认、脱敏截图/日志导出、最终 release tag 和正式报告
  PDF 仍需小组在提交前完成。
