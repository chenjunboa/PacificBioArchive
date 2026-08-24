# [MEMBER 3] 实现模型 manifest generation 热更新和原子切换

## 当前缺口

第二阶段能从私有 GCS 下载并启动真实模型，但运行中的服务尚未定期检测新 generation 并安全
切换。

## 要求

- 定期读取 GCS `model-manifest.json` generation；
- 发现新 generation 后下载到临时目录；
- 校验 detector、classifier 和 labels 的 SHA-256；
- 验证分类输出维度恰好为 46 后原子切换；
- 校验或加载失败时继续服务旧模型；
- 每条媒体记录保存实际模型版本。

## 验收

- 测试 generation 未变化、有效升级、hash 错误和加载失败；
- 并发请求期间不能观察到半更新模型；
- PR 提供模型版本切换的脱敏日志。
