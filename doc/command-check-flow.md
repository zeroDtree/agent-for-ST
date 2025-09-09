## 命令检查流程

```mermaid
flowchart TD
    A[🤖 AI 发起工具调用] --> B{工具类型分类}

    B -->|Knowledge Base Tools| C[🟢 安全工具<br/>直接执行]
    B -->|Shell Command Tools| D[Shell命令验证流程]
    B -->|Confirm Required Tools| E[⚠️ 需要用户确认]
    B -->|Unknown Tools| F[⚠️ 未知工具<br/>需要确认]

    D --> G{检查执行模式}

    G -->|受限模式| H[受限模式验证]
    G -->|普通模式| I[普通模式验证]

    H --> J[is_safe_command_with_restrictions]
    I --> K[cached_is_safe_command<br/>LRU缓存检查]

    J --> L[基础安全检查<br/>is_safe_command]
    K --> L

    L --> M[提取命令第一个单词]
    M --> N{检查黑名单<br/>DANGEROUS_COMMANDS}
    N -->|在黑名单| O[❌ 危险命令被阻止]
    N -->|不在黑名单| P{检查白名单<br/>SAFE_COMMANDS}

    P -->|不在白名单| O
    P -->|在白名单| Q{受限模式?}

    Q -->|否| R[✅ 基础安全通过]
    Q -->|是| S[路径验证<br/>validate_command_paths]

    S --> T[提取命令路径<br/>extract_paths_from_command]
    T --> U[正则匹配文件路径]
    U --> V{检查每个路径<br/>is_path_allowed}

    V --> W[路径规范化<br/>normalize_path]
    W --> X{路径位置检查}

    X -->|在允许目录内| Y[✅ 路径验证通过]
    X -->|父目录且允许读取| Y
    X -->|其他位置| Z[❌ 路径被阻止]

    R --> AA[🟢 路由到 my_tools]
    Y --> AA
    Z --> BB[🚫 路由到 human_confirm]
    O --> BB

    AA --> CC[run_shell_command_popen_tool]

    CC --> DD{再次检查受限模式}
    DD -->|受限模式| EE[二次路径验证<br/>validate_command_paths]
    DD -->|普通模式| FF[获取工作目录<br/>working_directory]

    EE --> GG{路径验证结果}
    GG -->|通过| HH[获取安全工作目录<br/>get_safe_working_directory]
    GG -->|失败| II[🚫 返回错误信息]

    HH --> JJ[subprocess.run<br/>cwd=safe_directory]
    FF --> KK[subprocess.run<br/>cwd=working_directory]

    JJ --> LL[📊 记录执行日志<br/>log_command_execution]
    KK --> LL
    II --> MM[📊 记录阻止日志]

    LL --> NN[🔄 返回命令结果给用户]
    MM --> NN

    C --> NN
    E --> OO[👤 等待用户确认]
    F --> OO
    BB --> OO

    OO --> PP{用户选择}
    PP -->|确认| AA
    PP -->|拒绝| QQ[❌ 用户拒绝执行]

    QQ --> NN

    style A fill:#e1f5fe
    style C fill:#c8e6c9
    style AA fill:#c8e6c9
    style O fill:#ffcdd2
    style Z fill:#ffcdd2
    style II fill:#ffcdd2
    style QQ fill:#ffcdd2
    style OO fill:#fff3e0
    style NN fill:#f3e5f5

    classDef processBox fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef decisionBox fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    classDef errorBox fill:#ffebee,stroke:#f44336,stroke-width:2px
    classDef successBox fill:#e8f5e8,stroke:#4caf50,stroke-width:2px

    class L,J,K,T,U,W,EE,HH,JJ,KK processBox
    class B,G,N,P,Q,V,X,DD,GG,PP decisionBox
    class O,Z,II,QQ errorBox
    class C,AA,Y,R successBox
```

## 关键验证节点说明

### 🔍 工具分类阶段

- **安全工具**: 知识库相关工具，直接执行
- **Shell 工具**: 需要经过复杂的安全验证
- **确认工具**: 明确需要用户确认的工具
- **未知工具**: 默认需要确认

### 🛡️ Shell 命令验证阶段

#### 第一层：基础安全检查

1. **黑名单检查**: 阻止明确危险的命令
2. **白名单检查**: 只允许预定义的安全命令

#### 第二层：受限模式检查（可选）

1. **路径提取**: 使用正则表达式提取命令中的文件路径
2. **路径验证**: 检查路径是否在允许的目录范围内
3. **权限检查**: 区分读写操作，应用不同的限制规则

#### 第三层：执行阶段验证

1. **二次验证**: 在实际执行前再次检查
2. **工作目录限制**: 使用 `subprocess.cwd` 限制命令执行范围
3. **日志记录**: 完整记录所有操作用于审计

### 📊 缓存优化

- **LRU 缓存**: 对常用命令的安全检查结果进行缓存
- **性能监控**: 记录检查耗时，优化瓶颈点

这个流程确保了多层防护，既保证了安全性，又维持了系统的可用性。

### workdir

```mermaid
flowchart TD
    A[调用 get_safe_working_directory] --> B{检查 restricted_mode}

    B -->|False 普通模式| C[返回 working_directory]
    B -->|True 受限模式| D[获取 allowed_directory]

    D --> E{allowed_dir 存在且有效?}
    E -->|是| F[normalize_path 规范化路径]
    E -->|否| G[返回 working_directory 作为兜底]

    F --> H[返回受限目录路径]

    style A fill:#e1f5fe
    style C fill:#c8e6c9
    style H fill:#fff3e0
    style G fill:#ffcdd2
```
