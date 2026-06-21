# 错误码参考文档

> 本文档由 `self_evolving_agent.core.error_response.generate_error_docs()` 生成。
> 阶段180: 生成静态文档，解决 README 中引用 `docs/error_codes.md` 但文件不存在的问题。

## 概述

系统定义了 8 个错误分类、6 个严重级别、25+ 个错误码。
所有 API 错误响应和 CLI 错误消息均使用统一的错误码体系，确保错误信息的一致性和可诊断性。

## 错误响应格式

API 错误响应（JSON）:

```json
{
  "error": "错误详情",
  "error_code": "VAL_002",
  "category": "VAL",
  "severity": "error",
  "recoverable": true,
  "suggested_action": "补充缺失的字段后重试"
}
```

CLI 错误消息（文本）:

```
[ERROR] 错误详情
  错误码: VAL_002
  分类: VAL (数据验证)
  严重级别: error
  可恢复: 是
  建议操作: 补充缺失的字段后重试
```



| 错误码 | 分类 | 严重级别 | 可恢复 | 描述 | 建议操作 |
|--------|------|----------|--------|------|----------|
| CFG_001 | CFG | error | 否 | 配置项不存在 | 检查配置键名，或设置默认值 |
| CFG_002 | CFG | error | 是 | 配置值非法 | 根据配置文档修正配置值 |
| CFG_003 | CFG | error | 是 | 配置值类型不匹配 | 将配置值转换为正确类型 |
| IFC_001 | IFC | error | 否 | 接口版本不兼容 | 升级或降级接口版本，查看兼容性矩阵 |
| IFC_002 | IFC | error | 否 | 请求的接口未注册 | 检查接口名称，确认模块已加载 |
| IFC_003 | IFC | error | 是 | 消息格式不符合协议 | 检查消息结构是否符合序列化协议 |
| IFC_004 | IFC | error | 是 | 序列化/反序列化失败 | 检查数据是否包含不可序列化对象 |
| LOG_001 | LOG | error | 是 | 非法状态转换 | 检查状态机定义，确保转换合法 |
| LOG_002 | LOG | error | 是 | 预测过程失败 | 检查输入数据和模型状态 |
| LOG_003 | LOG | warning | 是 | 优化过程发散 | 降低学习率，或检查梯度计算 |
| LOG_004 | LOG | error | 否 | 检测到循环依赖 | 重构模块依赖关系，消除循环 |
| RES_001 | RES | critical | 是 | 内存使用超过限制 | 释放不必要的缓存，或增加内存限制 |
| RES_002 | RES | warning | 是 | CPU使用率超过阈值 | 降低任务并发度，或优化算法 |
| RES_003 | RES | warning | 是 | 磁盘空间不足 | 清理旧快照和日志，释放磁盘空间 |
| RES_004 | RES | error | 否 | 检测到资源泄漏 | 检查资源释放逻辑，重启可能泄漏的模块 |
| SEC_001 | SEC | error | 否 | 未授权访问 | 检查访问权限配置 |
| SEC_002 | SEC | error | 是 | 安全验证失败 | 检查输入是否符合安全规范 |
| SYS_001 | SYS | error | 否 | 未预期的系统错误 | 查看系统日志，联系系统管理员 |
| SYS_002 | SYS | fatal | 否 | 系统组件初始化失败 | 检查组件配置和依赖，重启系统 |
| SYS_003 | SYS | error | 否 | 请求的模块不存在或未加载 | 检查模块名称，确认模块已注册 |
| SYS_004 | SYS | critical | 否 | 内部状态损坏 | 尝试重置组件状态，如无效则重启系统 |
| SYS_005 | SYS | error | 是 | 线程池资源耗尽 | 等待任务完成或增加线程池大小 |
| VAL_001 | VAL | error | 是 | 字段类型不匹配 | 检查输入数据类型，进行类型转换 |
| VAL_002 | VAL | error | 是 | 缺少必填字段 | 补充缺失的字段后重试 |
| VAL_003 | VAL | error | 是 | 数值超出允许范围 | 调整数值到有效范围内 |
| VAL_004 | VAL | error | 是 | 字符串格式不匹配 | 检查字段格式是否符合要求 |
| VAL_005 | VAL | error | 是 | 字段值不在允许列表中 | 使用允许的值之一 |
| VAL_006 | VAL | error | 是 | 数据不符合Schema定义 | 对照Schema定义修正数据 |
| VAL_007 | VAL | error | 是 | 自定义验证规则未通过 | 根据验证规则修正数据 |
## 错误场景映射

API 和 CLI 错误响应构建器 (`api_error_response` / `cli_error_message`) 支持以下场景：

| 场景标识 | 说明 | 错误码 | HTTP状态码 |
|----------|------|--------|-----------|
| `missing_field` | 缺少必填字段 | VAL_002 | 400 |
| `invalid_value` | 值非法 | VAL_005 | 400 |
| `invalid_type` | 类型不匹配 | VAL_001 | 400 |
| `not_found` | 资源不存在 | CFG_001 | 404 |
| `config_invalid` | 配置错误 | CFG_002 | 400 |
| `module_not_found` | 模块未找到 | SYS_003 | 404 |
| `interface_not_found` | 接口未找到 | IFC_002 | 404 |
| `unauthorized` | 未授权 | SEC_001 | 401 |
| `resource_conflict` | 资源冲突 | RES_004 | 409 |
| `unknown` | 未知错误 | SYS_001 | 500 |

## 错误分类

| 分类 | 说明 |
|------|------|
| SYS | 系统级错误（初始化、模块、状态） |
| NET | 网络错误（连接、超时） |
| VAL | 数据验证错误（类型、范围、格式） |
| RES | 资源错误（内存、CPU、磁盘） |
| LOG | 逻辑错误（状态转换、预测、优化） |
| CFG | 配置错误（键不存在、值非法） |
| IFC | 接口错误（版本、协议、序列化） |
| SEC | 安全错误（授权、验证） |

## 严重级别

| 级别 | 说明 |
|------|------|
| debug | 调试信息 |
| info | 一般信息 |
| warning | 警告 |
| error | 错误 |
| critical | 严重错误 |
| fatal | 致命错误 |
