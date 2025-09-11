# 自动模式文档 (Auto Mode Documentation)

## 📋 概述 (Overview)

自动模式是一个智能命令处理系统，可以根据预设规则自动批准或拒绝命令执行，减少人工干预的需要。系统提供 5 种不同的自动模式，从完全手动到完全自动，满足不同安全级别的需求。

## 🔧 自动模式类型 (Auto Mode Types)

### 1. 🤚 Manual Mode (手动模式)

**配置值**: `manual`  
**行为**: 所有命令都需要人工确认  
**适用场景**: 高安全要求环境，学习阶段  
**示例**:

```
⚠️ Non-whitelisted command, requires confirmation: rm -rf /tmp/test
```

### 2. 🚫 Blacklist Reject (黑名单拒绝)

**配置值**: `blacklist_reject`  
**行为**: 自动拒绝危险命令，其他命令需要确认  
**适用场景**: 防止误操作，保留灵活性  
**示例**:

```
🚫 Auto-rejected: dangerous command in blacklist: sudo rm -rf /
⚠️ Blacklist reject mode - non-blacklist commands need manual confirmation: ls -la
```

### 3. ⛔ Universal Reject (全部拒绝)

**配置值**: `universal_reject`  
**行为**: 自动拒绝所有需要确认的命令  
**适用场景**: 只读模式，纯查询场景  
**示例**:

```
🚫 Auto-rejected: universal reject mode: any-command
```

### 4. ✅ Whitelist Accept (白名单接受)

**配置值**: `whitelist_accept`  
**行为**: 自动接受非危险命令，拒绝黑名单命令  
**适用场景**: 平衡安全和效率  
**示例**:

```
🤖 Auto-approved: non-blacklist command (safe): ls -la
🚫 Auto-rejected: dangerous command in blacklist: sudo systemctl stop nginx
```

### 5. 🟢 Universal Accept (全部接受)

**配置值**: `universal_accept`  
**行为**: 自动接受所有命令（包括危险命令）  
**适用场景**: 完全信任环境，自动化脚本  
**⚠️ 警告**: 极高风险，谨慎使用  
**示例**:

```
🤖 Auto-approved: universal accept mode (dangerous): sudo rm -rf /important-data
```

## 🎯 使用建议 (Usage Recommendations)

| 场景         | 推荐模式           | 理由            |
| ------------ | ------------------ | --------------- |
| 生产环境     | `manual`           | 最高安全性      |
| 开发环境     | `blacklist_reject` | 平衡安全和效率  |
| 只读查询     | `universal_reject` | 防止意外修改    |
| 受信任脚本   | `whitelist_accept` | 提高自动化程度  |
| 完全信任环境 | `universal_accept` | ⚠️ 仅限特殊情况 |

## 🛡️ 安全注意事项 (Security Notes)

1. **谨慎使用 `universal_accept`**: 可能执行危险命令
2. **定期审查日志**: 检查自动决策的合理性
3. **测试环境验证**: 新模式先在测试环境使用
4. **备份重要数据**: 自动模式无法完全避免误操作
5. **权限最小化**: 运行用户应具有最小必要权限
