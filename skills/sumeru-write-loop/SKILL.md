---
name: sumeru-write-loop
description: 适用于需要连续创作大量章节、需要进度跟踪和断点续传功能的场景
type: skill
---

# 循环章节写作 Skill (write-loop)

## 概述
sumeru-write-loop skill 是对 sumeru-write skill 的扩展，专门用于大量章节的连续创作。它通过并行多agent调用 sumeru-write skill 来快速完成多章节写作，并使用进度文件记录写作状态，支持断点续传和任务恢复。

## 触发关键词
帮我写100章小说、批量生成50章内容、循环写大量章节、继续之前的写作任务、恢复写作进度、批量写网文章节、大量章节创作

## 核心功能
1. **细纲感知模式**：自动检测 `.sumeru/outline/chapter-outlines.json`，优先使用细纲驱动
2. **循环执行 sumeru-write skill**：按章节顺序连续调用 sumeru-write skill 生成多章内容
3. **进度跟踪**：在 `.sumeru/sumeru-write-loop/progress.md` 中记录详细的写作进度
4. **断点续传**：支持从上次中断的位置继续写作
5. **任务状态管理**：记录每章的状态（待写、进行中、已完成）
6. **错误处理**：单章生成失败时自动重试，不影响整体进度
7. **Agent team 并行处理**：支持启动多个子 Agent 并行写作，大幅提升效率
8. **自 Agent 调度**：智能分配章节任务给子 Agent，自动管理工作负载

## 进度文件格式
`.sumeru/sumeru-write-loop/progress.md` 包含以下信息：
```markdown
# 写作任务进度

## 任务元数据
- 开始时间：2026-04-04 22:00
- 总章节数：100
- 当前进度：第25章
- 已完成：24章
- 并行模式：Agent team (3个Agent)
- 任务分配策略：round-robin

## Agent 状态
- Agent-1: 运行中，正在处理第25章
- Agent-2: 运行中，正在处理第26章
- Agent-3: 空闲，等待任务

## 章节状态
- 第1章：已完成 ✓ (Agent-1)
- 第2章：已完成 ✓ (Agent-2)
- 第3章：已完成 ✓ (Agent-3)
- ...
- 第25章：进行中 🔄 (Agent-1)
- 第26章：进行中 🔄 (Agent-2)
- 第27章：待写 ⏳
```

## 使用方法
```bash
# 从细纲读取，生成所有章节（自动检测chapter-outlines.json）
/sumeru-write-loop --all

# 从第1章开始，生成50章（使用细纲）
/sumeru-write-loop 第1-50章

# 从指定章节开始
/sumeru-write-loop 第20-100章

# 继续上次的写作任务
/sumeru-write-loop --resume

# 指定每章字数
/sumeru-write-loop 第1-100章 --words 3000

# 恢复特定任务
/sumeru-write-loop --resume-from .sumeru/sumeru-write-loop/progress.md

# 显式指定细纲文件
/sumeru-write-loop --all --outline-file .sumeru/outline/chapter-outlines.json
```

## 核心参数
- `--resume`：从上次中断位置继续
- `--resume-from <path>`：从指定进度文件恢复
- `--retry <次数>`：失败重试次数（默认3次）
- `--parallel <数量>`：并行生成章节数（默认1，即串行）
- `--skip <章节列表>`：跳过指定章节
- `--only <章节列表>`：只生成指定章节
- `--confirm`：每章生成后确认（默认自动继续）
- `--agent-count <数量>`：启动的子 Agent 数量（默认3，推荐3-5）
- `--team-mode`：启用 Agent team 协作模式
- `--task-split <策略>`：任务分配策略（round-robin、smart、chunk）

## Agent Team 并行架构

### 工作原理
sumeru-write-loop 采用子 Agent 并行架构来处理大量章节写作任务：

```
sumeru-write-loop 主 Agent
    ├── 创建任务队列（按章节顺序）
    ├── 启动 N 个子 Agent（默认3个）
    ├── 子 Agent 从队列拉取任务
    ├── 子 Agent 调用 sumeru-write skill 生成章节
    ├── 完成后立即保存并更新进度
    └── 继续拉取下一个任务直到队列为空
```

### Agent Team 协作模式
#### 1. Round-Robin 分配（默认）
- 章节按顺序轮流分配给各个子 Agent
- 适合：章节之间相对独立，无特殊依赖关系
- 示例：Agent 1 → 第1,4,7章；Agent 2 → 第2,5,8章；Agent 3 → 第3,6,9章

#### 2. Smart 分配
- 智能分析章节内容复杂度
- 根据子 Agent 历史表现动态分配
- 适合：章节难度差异较大的情况

#### 3. Chunk 分配
- 将连续章节分块分配给同一 Agent
- 适合：需要保持连续章节风格一致性的场景
- 示例：Agent 1 → 第1-10章；Agent 2 → 第11-20章；Agent 3 → 第21-30章

### 子 Agent 隔离机制
每个子 Agent 完全独立：
- **上下文隔离**：每个子 Agent 只携带必要的上下文（大纲、前一章摘要）
- **错误隔离**：单个子 Agent 失败不影响其他 Agent
- **资源隔离**：自动管理内存，完成后释放资源
- **进度隔离**：每个 Agent 独立报告进度，主 Agent 汇总

### 并行性能优化
- **增量写入**：每完成一章立即保存，无需等待全部完成
- **动态负载均衡**：根据 Agent 处理速度调整任务分配
- **智能重试**：失败章节重新分配给空闲 Agent
- **流水线模式**：支持前置章节完成后自动触发后续依赖章节

## Team 协作模式的使用场景

### 大规模批量创作（推荐）
```bash
# 启动5个 Agent 并行生成100章
/sumeru-write-loop 第1-100章 --agent-count 5 --team-mode

# 使用 chunk 模式保持连续章节风格一致
/sumeru-write-loop 第1-100章 --agent-count 5 --team-mode --task-split chunk

# Round-Robin 模式，快速分散任务
/sumeru-write-loop 第1-100章 --agent-count 5 --team-mode --task-split round-robin
```

### 分段渐进创作
```bash
# 先生成前50章
/sumeru-write-loop 第1-50章 --agent-count 3 --team-mode

# 再继续生成后50章
/sumeru-write-loop 第51-100章 --agent-count 3 --team-mode
```

### 从中断处恢复并行任务
```bash
# 恢复上次的并行任务，保持原有的 Agent 分配
/sumeru-write-loop --resume --team-mode

# 恢复时调整 Agent 数量
/sumeru-write-loop --resume --agent-count 5 --team-mode
```

## 与 sumeru-write skill 并行模式的区别
- **sumeru-write skill 的 --parallel**：单 Agent 内的简单循环，适合少量章节
- **sumeru-write-loop 的 --team-mode**：多 Agent 并行，适合大量章节（>20章），具有完整的任务调度和进度管理

## 进度记录规则
1. 任务启动时创建 `.sumeru/write-loop/` 目录（如果不存在）
2. 每完成一章立即更新 `progress.md`
3. 记录章节状态：待写、进行中、已完成、失败
4. 保存失败章节的错误信息，支持单独重试
5. 记录时间戳、字数统计等元数据

## 断点恢复逻辑
1. 检查 `.sumeru/sumeru-write-loop/progress.md` 是否存在
2. 读取当前进度和章节状态
3. 跳过已完成章节，从最新未完成章节继续
4. 自动验证已完成章节的完整性
5. 支持手动指定恢复位置

## 与 sumeru-write skill 的关系
- sumeru-write-loop 完全复用 sumeru-write skill 的核心能力
- sumeru-write-loop 负责调度、进度跟踪、错误处理
- **细纲数据传递**：自动将 `chapter-outlines.json` 中的对应章节细纲传递给 sumeru-write
- 所有章节生成的实际工作由 sumeru-write skill 完成
- 支持透传 sumeru-write skill 的所有参数

## 数据持久化
### 用户可见输出（当前工作目录）
- 生成的章节保存到 `chapters/` 目录

### 中间数据（仅系统内部使用）
所有进度和状态信息统一存储在 `.sumeru/write-loop/` 目录：
```
.sumeru/
└── write-loop/
    ├── progress.md              # 主进度文件
    ├── task-meta.json           # 任务元数据（JSON格式）
    ├── chapter-logs/            # 每章的生成日志
    │   ├── chapter-1.log
    │   └── chapter-2.log
    ├── agent-logs/              # 子 Agent 运行日志
    │   ├── Agent-1.log
    │   ├── Agent-2.log
    │   └── Agent-3.log
    ├── agent-state/             # Agent 状态快照
    │   ├── Agent-1.state.json
    │   ├── Agent-2.state.json
    │   └── Agent-3.state.json
    └── errors/                  # 失败章节的错误信息
        └── chapter-5.err
```

## 任务元数据 (task-meta.json)
```json
{
  "taskId": "uuid",
  "startedAt": "2026-04-05T22:00:00Z",
  "totalChapters": 100,
  "completedChapters": 24,
  "currentChapter": 25,
  "usesChapterOutlines": true,
  "outlineSource": ".sumeru/outline/chapter-outlines.json",
  "parameters": {
    "style": "xianxia",
    "words": 3000,
    "agentCount": 3,
    "teamMode": true,
    "taskSplit": "round-robin"
  },
  "failedChapters": [5, 12],
  "agentStatus": {
    "Agent-1": {"status": "running", "currentChapter": 25, "startTime": "2026-04-05T22:00:00Z"},
    "Agent-2": {"status": "running", "currentChapter": 26, "startTime": "2026-04-05T22:00:10Z"},
    "Agent-3": {"status": "idle", "currentChapter": null, "startTime": null}
  },
  "chapterAssignment": {
    "Agent-1": [1, 4, 7, 10, ..., 25],
    "Agent-2": [2, 5, 8, 11, ..., 26],
    "Agent-3": [3, 6, 9, 12, ...]
  }
}
```

## 常见使用场景
1. **一次性批量生成**：指定章节范围，自动完成所有章节
2. **分段渐进创作**：先生成前50章，再继续生成后50章
3. **中断后恢复**：意外中断后，使用 `--resume` 继续
4. **选择性重写**：用 `--only` 参数重写特定章节
5. **错误修复**：单独重试失败的章节
6. **大规模并行创作**：使用 Agent team 快速生成100+章节
7. **风格一致性并行**：使用 chunk 模式保持连续章节风格一致
8. **混合模式创作**：关键章节单 Agent 精雕，普通章节多 Agent 并行
