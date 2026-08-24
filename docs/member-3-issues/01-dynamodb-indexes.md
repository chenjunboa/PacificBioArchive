# [MEMBER 3] 完成 DynamoDB TAG/THUMB 索引与一致性写入

## 当前缺口

第二阶段只提供基础单表、owner-created GSI 和最小媒体状态链路。TAG 数量索引、THUMB 反向映射
及其与媒体记录的一致性尚未完成。

## 要求

- 实现 `TAG#{normalizedTag}` / `COUNT#{paddedCount}#MEDIA#{mediaId}`；
- 实现 `THUMB#{urlHash}` / `MAP`；
- 标签数量固定宽度补零，标签使用仓库统一标准化规则；
- 媒体、TAG 与 THUMB 的相关变更尽量放入同一 `TransactWriteItems`；
- 禁止为标签和缩略图查询扫描全表。

## 验收

- 自动测试覆盖标签增加、数量更新、删除以及无旧索引；
- 缩略图反查返回当前短期原图 URL，数据库不保存过期 HTTPS URL；
- PR 提供脱敏 DynamoDB 写入前后证据。
