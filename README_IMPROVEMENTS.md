# 系统改进说明

## 新增功能

### 📊 **配置管理**
- `config/config.py`: 中央化配置管理
- 支持线程ID、递归限制、日志级别等配置

### 📁 **日志系统**
- `utils/logger.py`: 完善的日志记录
- 命令执行审计日志
- 日志分级和日志文件管理

### 🔄 **缓存机制**
- `utils/cache.py`: 白名单检查缓存
- LRU缓存策略，提高性能

### ⏱️ **性能监控**
- `utils/monitor.py`: 性能监控装饰器
- 慢速操作警报
- 响应时间统计

### 📊 **历史管理**
- `utils/history.py`: 会话历史清理
- 防止内存溢出

### ⚙️ **工具更新**
- `tools/shell.py`: 完善的shell工具
- 命令超时控制
- 安全的命令解析
- 错误处理和日志

### 📊 **主程序重构**
- 依赖注入支持
- 更好的错误处理
- 用户体验优化
- 进度显示和状态提示

### 📝 **测试覆盖**
- `tests/`: 单元测试和集成测试
- 测试白名单路由逻辑
- 测试图创建函数

## 使用方法

1. **启动系统**:
   ```bash
   python main.py
   ```

2. **运行测试**:
   ```bash
   python -m unittest discover tests
   ```

3. **查看日志**:
   ```bash
   tail -f logs/app_*.log
   tail -f logs/commands_*.log
   ```

## 配置调整

编辑 `config/config.py` 来修改:
- `command_timeout`: 命令执行超时时间
- `max_history_messages`: 最大历史消息数
- `log_level`: 日志级别

## 安全特性

- 命令执行超时控制
- 白名单缓存加速
- 命令审计日志
- 安全的命令解析
- 用户确认机制

## 性能优化

- 白名单检查缓存
- 性能监控和警报
- 历史消息清理
- 异常处理和恢复
