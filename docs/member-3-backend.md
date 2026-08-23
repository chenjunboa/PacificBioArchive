# 第三位成员执行手册：云端数据、媒体处理、ML 和查询

## 你的目标

接手第二位成员已经能登录和上传的云端基础版本，把后端所有评分功能做正确、可重试、可验证。

开始标签：`handoff-2-cloud`  
工作分支：`member-3/core-hardening`  
完成标签：`handoff-3-core-complete`

如果第二位成员没有完成 Cognito、S3 上传、SQS 消息和私有 inference 调用，不要默认接手其
未完成工作。先建立 `Handoff blocker` Issue 并记录责任。

## 第一步：复现云端基线

```powershell
git fetch --tags origin
git switch -c member-3/core-hardening handoff-2-cloud
uv sync --extra dev
uv run pytest -q
```

使用自己的账号完成：注册登录、调用 `/species`、上传一张图片、确认 S3 和 SQS。成功后在
第二位成员 PR 写明接受时间和 commit。

## 第二步：完成 DynamoDB 单表适配器

云端不能使用 SQLite。所有稳定链接保存为 `s3://` URI，返回浏览器前才生成短期预签名 URL。

固定数据结构：

| PK | SK | 内容 |
|---|---|---|
| `MEDIA#{mediaId}` | `META` | owner、S3 URI、类型、大小、checksum、标签、状态、模型版本、错误和时间 |
| `CHECKSUM#{sha256}` | `LOCK` | 全局去重锁和 mediaId |
| `TAG#{normalizedTag}` | `COUNT#{paddedCount}#MEDIA#{mediaId}` | 标签数量索引 |
| `THUMB#{urlHash}` | `MAP` | 缩略图与原图映射 |
| `USER#{sub}` | `SUB#{normalizedTag}` | 标签邮件订阅 |

媒体记录还要写：

- `GSI1PK = OWNER#{sub}`；
- `GSI1SK = {createdAt}#MEDIA#{mediaId}`。

标签数量使用固定宽度补零，保证字符串排序与数字排序一致。标签、媒体记录和映射的相关变更
尽量放入同一个 `TransactWriteItems`。

## 第三步：实现上传和并发去重

`POST /uploads/init` 必须：

1. 验证扩展名、MIME、大小和 64 位十六进制 SHA-256。
2. 允许 JPG/JPEG/PNG 不超过 20 MB；MP4/MOV 不超过 100 MB 且视频不超过 60 秒。
3. 用 DynamoDB 条件写创建 `CHECKSUM` 锁和 `MEDIA` 记录。
4. 重复内容即使文件名不同也返回 409 和已有 `mediaId`。
5. 返回受 content type、size 和 checksum metadata 约束的 S3 预签名地址。
6. 对未完成上传设置可恢复策略，不能留下永远占用的假锁。

写并发集成测试：四个线程同时上传相同内容，最终只能有一个媒体记录、一个锁和一个原文件。

## 第四步：完成 SQS worker

处理顺序：

1. 收到 S3 事件，读取 `mediaId` 和对象。
2. 条件更新状态为 `PROCESSING`，重复消息不会重复处理已完成媒体。
3. 图片生成缩略图；视频严格抽帧。
4. 使用短期 S3 下载地址和 WIF 调用私有 inference Cloud Run。
5. 写模型版本、标签、索引和缩略图映射。
6. 状态改为 `READY`，新增标签触发 SNS。
7. 可重试错误抛回 SQS；超过次数进入 DLQ，并把媒体标为 `FAILED`。

错误信息只能说明可操作原因，不能把 token、预签名 URL 或内部凭证返回给用户。

## 第五步：图片、视频和模型规则

### 图片

- 支持横图、竖图和透明 PNG。
- 先转换为 RGB，再生成最长边不超过 480 的 JPEG。
- 保持原比例，不能拉伸；质量明显低于原图但仍可辨认。

### 视频

- 严格在 `t=0,1,2...` 每秒取一帧；2.4 秒视频应取 3 帧。
- 解码失败进入 `FAILED`。
- 同一物种的最终数量是所有帧中“最大同时检测数量”，不能把每帧数量相加。
- 查询返回原视频 URL，视频不要求生成图片缩略图，除非团队另行决定。

### 模型

- MegaDetector 先找到动物框，再把每个 crop 送入 SpeciesNet。
- `labels.txt` 是类别顺序唯一来源。
- 服务启动时确认分类输出维度恰好为 46。
- 定期检查 GCS `manifest.json` generation；发现新 generation 后先下载到临时位置、校验
  SHA-256，全部通过后原子切换模型。
- 每条媒体记录保存实际使用的模型版本。

## 第六步：完成四类查询

### 标签数量查询

输入 `{"tags":{"wombat":2,"magpie":1}}` 表示必须同时满足：wombat 至少 2、magpie
至少 1。先分别查询标签索引，再取 mediaId 交集，不能扫描全表。

### 物种查询

`{"species":"dingo"}` 等价于 `dingo >= 1`，使用相同索引和标签标准化。

### 缩略图反查

对输入缩略图 URL 计算稳定 hash，读取 `THUMB` 映射，返回当前短期原图 URL。数据库不能保存
已经过期的 HTTPS 预签名地址。

### 上传文件查询

1. `/queries/file/init` 返回 `temporary-queries/{queryId}/...` 上传地址。
2. execute 识别临时文件。
3. 使用识别出的全部正数量标签执行 AND 查询。
4. 不创建 `MEDIA` 或 checksum 记录。
5. 成功、识别失败和查询失败都立即删除临时对象。
6. S3 生命周期 1 天只是兜底，不是主要清理方式。

## 第七步：标签、订阅和删除

- `POST /tags/bulk`：operation 1 添加，0 删除；删除不存在标签不报错。
- 添加和删除都同步维护标签索引；只有实际新增或数量更新的匹配标签触发通知。
- 只有 owner 可以改标签或删除；所有认证用户可以查询。
- SNS 邮箱订阅只有用户确认后才视为有效。
- 删除先标记 `DELETING`，再删除原文件和缩略图，然后清理索引、映射、checksum 锁和媒体记录。
- 重复删除保持成功且无副作用。

## 必须完成的自动测试和证据

- 相同内容换名去重；四个并发上传只成功一个。
- 横图、竖图、透明 PNG 缩略图比例正确。
- 2.4 秒视频三帧；坏视频 `FAILED`；视频数量取最大值。
- 多标签 AND/最低数量、物种、缩略图、文件查询。
- 临时文件成功和失败都删除。
- 标签增删后无旧索引；删除后所有相关项目消失。
- 非 owner 修改和删除返回 403。
- GCP 超时、S3/DynamoDB 短暂失败会重试，最终进入 DLQ 并显示明确状态。

PR 中提供脱敏 CloudWatch 日志、DynamoDB 操作前后证据、一张图片和一个短视频结果、模型版本
和 46 类验证结果。任何没有在真实云端运行的项目不能写“通过”。

## 如何交给第四位成员

1. PR 合并后创建 `handoff-3-core-complete`。
2. 让第四位成员从标签创建 `member-4/ui-e2e`。
3. 提供测试用户创建方法和非敏感服务 URL，不发送账号密码。
4. 让对方通过 API 独立完成上传、四类查询、标签和删除。
5. 对方成功后在 PR 记录接受时间和 commit；否则该问题仍由你负责。
