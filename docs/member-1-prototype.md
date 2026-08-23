# 第一位成员执行手册：本地原型与第一次交接

## 你的目标

完成一个能在本地连续演示的系统原型，固定目录、接口和基本行为，让第二位成员可以在此
基础上部署云端。你的交付不是“真实云端完成”，不要把 SQLite、本地文件或模拟识别描述成
AWS/GCP 生产实现。

当前工作已完成，交付提交是 `4402ba8`，标签是 `handoff-1-local`。

## 你负责的内容

- 建立单体仓库、README、四人执行手册和 GitHub Actions。
- FastAPI 路由、Pydantic 输入验证和本地 JWT。
- SQLite、本地文件存储和模拟识别适配器。
- React 原型：登录、上传、查询、标签、删除和订阅。
- 图片缩略图；视频每秒一帧的采样函数。
- MegaDetector + SpeciesNet 的本地真实样例验证。
- AWS/GCP Terraform 资源框架。
- 第一次交接和后续职责划分。

## 项目目录

- `services/api`：API、认证、本地数据库、文件处理和测试。
- `services/inference`：识别服务、模型加载和视频采样。
- `web`：React + TypeScript + Vite 页面。
- `infra`：AWS/GCP Terraform。
- `.github/workflows/ci.yml`：GitHub 自动测试和镜像构建。
- `labels.txt`：唯一的 46 类标签顺序来源。

模型文件 `mdv5a.pt` 和 `model.pt` 只保留在本地，不上传 GitHub。

## 如何启动本地原型

要求：Python 3.12、uv、Node.js 22、npm。

第一个 PowerShell 窗口，在仓库根目录执行：

```powershell
uv sync --extra dev
uv run uvicorn app.main:app --app-dir services/api --reload
```

第二个 PowerShell 窗口执行：

```powershell
Set-Location web
npm ci
npm run dev
```

打开 `http://localhost:5173`。本地模式可以输入任意格式正确的邮箱，系统会签发仅限本地的
开发 JWT。接口文档位于 `http://localhost:8000/docs`。

本地默认根据测试文件名生成标签。例如 `Felis_catus_1.JPG` 会得到
`felis_catus: 1`，这样不用每次加载大型模型也能测试完整流程。

## 交付前怎样检查

在仓库根目录执行：

```powershell
uv run pytest -q
uv run ruff check services/api services/inference
Push-Location web
npm ci
npm run build
npm audit --audit-level=high
Pop-Location
Push-Location infra
terraform fmt -check
terraform init -backend=false
terraform validate
Pop-Location
git status --short
git ls-files "*.pt" "*.onnx" ".env" "*.tfstate" "terraform.tfvars"
```

正确结果：9 项测试通过、Ruff 通过、前端构建通过、0 个高危依赖、Terraform valid、
Git 状态为空，最后一个文件检查不返回任何内容。

## 必须亲自演示的流程

1. 本地登录。
2. 上传一张符合命名规则的 JPG，等待 `READY`。
3. 再用不同文件名上传相同内容，确认返回 409 和已有 `mediaId`。
4. 用物种和标签数量查询找到刚才的图片。
5. 用缩略图地址反查原图。
6. 上传临时查询图片，确认能查到媒体且临时文件被删除。
7. 增加和删除手动标签。
8. 订阅一个标签，再上传匹配图片并查看本地通知记录。
9. 用另一个用户尝试修改，确认返回 403。
10. 删除自己的图片，再次删除也不报错。

## 已确认的限制

- 本地数据库是 SQLite，云端必须替换为 DynamoDB。
- 本地文件必须替换为 S3 和短期预签名 URL。
- 本地后台任务不是 SQS Lambda worker。
- 本地登录不是 Cognito 注册和邮箱验证。
- Terraform 只通过格式和静态验证，尚未证明 AWS Academy 权限。
- Cloud Run 模型 manifest 仍需第二、第三位成员接入 GCS。

这些不是第一阶段缺陷，但第二位成员必须明确接手，不能把本地适配器直接部署后宣称完成。

## 交给第二位成员的具体内容

1. 邀请对方进入私有 GitHub 仓库。
2. 发送仓库地址、提交 `4402ba8` 和标签 `handoff-1-local`。
3. 让对方执行：

```powershell
git clone https://github.com/chenjunboa/PacificBioArchive.git
Set-Location PacificBioArchive
git fetch --tags
git switch -c member-2/cloud-deployment handoff-1-local
```

4. 当面运行测试并演示一次上传、查询和删除。
5. 说明模型权重不会从 GitHub 下载，需要使用安全的校内共享方式传递。
6. 说明 AWS 固定 `us-east-1`，GCP 固定 `us-central1`。
7. 让第二位成员亲自启动本地系统。对方未成功运行前，第一次交接不算完成。
8. 在 GitHub PR/Issue 中记录：`第二位成员已在 <时间> 从 4402ba8 成功运行本地原型`。

## 你后续仍需参与

- 审查第四位成员的最终 PR。
- 撰写报告中的架构、接口、本地原型和协作章节。
- 参加两次最终演练。
- 核对所有成员贡献来自个人账号，最后共同确认 `v1.0.0`。
