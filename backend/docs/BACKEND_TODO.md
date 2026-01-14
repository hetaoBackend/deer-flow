# DeerFlow Backend TODO List

## 📋 项目概述

DeerFlow Backend 是一个基于 LangGraph 的 AI Agent 框架，采用配置驱动架构，支持多种 Sandbox 实现和工具扩展。

## 🚨 高优先级问题 (P0)

### 1. LocalSandboxProvider 返回类型不一致
**文件**: `src/sandbox/local/local_sandbox_provider.py`
**问题**: 
- `acquire()` 声明返回 `Sandbox` 但实际返回 `str`
- `get()` 声明返回 `None` 但实际返回 `LocalSandbox`
**影响**: 类型安全破坏，IDE 检查报错
**解决方案**: 修正方法签名，确保与抽象基类契约一致

### 2. Sandbox 资源泄漏风险
**文件**: `src/sandbox/middleware.py`
**问题**: 
- 只有 `before_agent` 获取 sandbox
- 没有 `after_agent` 释放机制
- `LocalSandboxProvider.release()` 是空实现
**影响**: 资源泄漏，Docker 容器堆积
**解决方案**: 实现完整的生命周期管理

## 🟡 中优先级问题 (P1)

### 3. 硬编码路径和个人信息 ✅ 已完成
**文件**: `src/agents/lead_agent/prompt.py`
**问题**: 
- `MOUNT_POINT = "/Users/henry/mnt"`
- 个人信息出现在系统提示中
**影响**: 可移植性差，违反配置分离原则
**解决方案**: 移至配置文件中

### 4. 异常处理过于简单
**文件**: `src/sandbox/tools.py`
**问题**: 所有异常被吞掉，缺乏结构化错误信息
**影响**: 调试困难，用户体验差
**解决方案**: 实现分层异常处理机制

### 5. 全局单例缺乏生命周期管理
**文件**: `src/config/app_config.py`, `src/sandbox/sandbox_provider.py`
**问题**: 全局变量难以测试，无法重新加载配置
**影响**: 可测试性差，多线程风险
**解决方案**: 引入依赖注入或 ContextVar

## 🟢 低优先级问题 (P2)

### 6. 缺乏异步支持
**文件**: `src/community/aio_sandbox/aio_sandbox.py`
**问题**: 所有操作都是同步的
**影响**: 并发性能受限
**解决方案**: 添加 async/await 支持

### 7. 配置验证不足
**文件**: `src/config/model_config.py`
**问题**: `extra="allow"` 允许任意字段
**影响**: 配置错误难以发现
**解决方案**: 使用 `extra="forbid"` 并添加验证器

### 8. 工具配置重复定义
**文件**: `config.yaml` 和 `src/community/tavily/tools.py`
**问题**: 同名工具在不同地方定义
**影响**: 配置切换混淆
**解决方案**: 使用唯一名称或别名机制

## 🔧 架构优化建议

### 9. 自动 Thread Title 生成 ✅ 已完成
**目的**: 自动为对话线程生成标题
**实现**: 
- 使用 `TitleMiddleware` 在首次对话后自动生成 title
- Title 存储在 `ThreadState.title` 中（而非 metadata）
- 支持通过 checkpointer 持久化
- 详见 [AUTO_TITLE_GENERATION.md](docs/AUTO_TITLE_GENERATION.md)

### 10. 引入依赖注入容器
**目的**: 改善可测试性和模块化
**实现**: 创建 `di.py` 提供类型安全的依赖管理

### 11. 添加健康检查接口
**目的**: 监控系统状态
**实现**: 创建 `health.py` 提供系统健康状态检查

### 12. 增加结构化日志
**目的**: 改善可观测性
**实现**: 集成 `structlog` 提供结构化日志输出

## 📊 实施计划

### Phase 1: 安全与稳定性 (Week 1-2)
- [ ] 修复 LocalSandboxProvider 类型问题
- [ ] 实现 Sandbox 生命周期管理
- [ ] 添加异常处理机制

### Phase 2: 架构优化 (Week 3-4)
- [ ] 引入依赖注入
- [ ] 添加健康检查
- [ ] 实现配置验证
- [ ] 移除硬编码路径

### Phase 3: 性能与扩展性 (Week 5-6)
- [ ] 添加异步支持
- [ ] 实现结构化日志
- [ ] 优化工具配置管理

## 🎯 成功标准

- ✅ 所有类型检查通过
- ✅ 配置可安全共享
- ✅ 资源管理无泄漏
- ✅ 异常处理完善
- ✅ 测试覆盖率提升
- ✅ 部署配置标准化

## 📝 备注

- 优先处理高优先级问题，确保系统稳定性和安全性
- 中优先级问题影响开发体验和可维护性
- 低优先级问题可在系统稳定后逐步优化

---

*最后更新: 2026-01-14*