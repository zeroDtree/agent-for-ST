# Auto Mode Documentation

## 📋 Overview

Auto mode is an intelligent command processing system that can automatically approve or reject command execution based on preset rules, reducing the need for manual intervention. The system provides 5 different auto modes, from fully manual to fully automatic, to meet different security level requirements.

## 🔧 Auto Mode Types

### 1. 🤚 Manual Mode

**Configuration Value**: `manual`  
**Behavior**: All commands require manual confirmation  
**Use Cases**: High security requirement environments, learning phase  
**Example**:

```
⚠️ Non-whitelisted command, requires confirmation: rm -rf /tmp/test
```

### 2. 🚫 Blacklist Reject

**Configuration Value**: `blacklist_reject`  
**Behavior**: Automatically reject dangerous commands, other commands require confirmation  
**Use Cases**: Prevent misoperations while maintaining flexibility  
**Example**:

```
🚫 Auto-rejected: dangerous command in blacklist: sudo rm -rf /
⚠️ Blacklist reject mode - non-blacklist commands need manual confirmation: ls -la
```

### 3. ⛔ Universal Reject

**Configuration Value**: `universal_reject`  
**Behavior**: Automatically reject all commands that require confirmation  
**Use Cases**: Read-only mode, pure query scenarios  
**Example**:

```
🚫 Auto-rejected: universal reject mode: any-command
```

### 4. ✅ Whitelist Accept

**Configuration Value**: `whitelist_accept`  
**Behavior**: Automatically accept non-dangerous commands, reject blacklisted commands  
**Use Cases**: Balance security and efficiency  
**Example**:

```
🤖 Auto-approved: non-blacklist command (safe): ls -la
🚫 Auto-rejected: dangerous command in blacklist: sudo systemctl stop nginx
```

### 5. 🟢 Universal Accept

**Configuration Value**: `universal_accept`  
**Behavior**: Automatically accept all commands (including dangerous ones)  
**Use Cases**: Fully trusted environment, automated scripts  
**⚠️ Warning**: Extremely high risk, use with caution  
**Example**:

```
🤖 Auto-approved: universal accept mode (dangerous): sudo rm -rf /important-data
```

## 🎯 Usage Recommendations

| Scenario | Recommended Mode | Reason |
| -------- | ---------------- | ------ |
| Production Environment | `manual` | Highest security |
| Development Environment | `blacklist_reject` | Balance security and efficiency |
| Read-only Query | `universal_reject` | Prevent accidental modifications |
| Trusted Scripts | `whitelist_accept` | Improve automation level |
| Fully Trusted Environment | `universal_accept` | ⚠️ Special cases only |

## 🛡️ Security Notes

1. **Use `universal_accept` with caution**: May execute dangerous commands
2. **Regularly review logs**: Check the rationality of automatic decisions
3. **Validate in test environment**: Use new modes in test environment first
4. **Backup important data**: Auto mode cannot completely avoid misoperations
5. **Minimize privileges**: Running user should have minimal necessary permissions
