## 阶段和负责人

- 阶段：<!-- 第二位云部署 / 第三位后端 / 第四位 UI与发布 -->
- 负责人：
- 开始标签和 commit：
- 当前 commit：

## 已完成范围

<!-- 只列出执行手册中已经真正完成的内容。 -->

## 检查结果

```text
uv run pytest -q：
uv run ruff check services/api services/inference：
npm run build：
terraform validate：
真实云端测试：
```

## 证据

<!-- 添加脱敏截图、测试报告、日志或视频链接。 -->

## 云账号和安全

- [ ] 没有凭证、token、`.env`、Terraform state、预签名 URL 或模型权重。
- [ ] 部署前核对了 AWS account/region 和 GCP project/region。
- [ ] 记录了新增资源、可能费用和清理负责人。
- [ ] 没有创建长期 GCP Service Account JSON key。

## 已知限制和阻塞

<!-- 必须写清楚具体行为和 Issue；确认后才能写“无”。 -->

## 下一位成员复现

- 接受人：
- 复现的流程：
- 结果：
- 记录：`<姓名> 于 <UTC时间> 接受 commit <sha>`
