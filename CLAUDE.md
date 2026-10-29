# AGENTS.md - 网文创作专项Skill集合

## 项目概述
本仓库是基于Claude Code Skill体系开发的网文创作全流程专项Skill集合，提供从选题策划到完稿导出的一站式网文创作能力。通过模块化的Skill架构，覆盖网文创作的所有核心环节，支持从创意萌芽到发布准备的完整工作流。

## 技术栈
- Skill框架：Claude Code Skill系统（兼容OpenCode superpowers体系）
- 运行环境：macOS / Linux zsh
- 依赖环境：Python 3.11+、Node.js 20.x（部分工具脚本依赖）
- 当前版本：v0.2.0

## 核心架构结构
```
skills/
├── sumeru-worldbuilder/  # 世界构建师Skill，统筹全流程创作，负责整个故事世界的搭建与落地
├── sumeru-topic/         # 选题策划Skill，市场分析+创意生成
├── sumeru-deconstruct/   # 拆书分析Skill，结构拆解+节奏曲线+仿写模板（不抄文本）
├── sumeru-outline/       # 大纲设计Skill，世界观+人设+剧情框架
├── sumeru-write/         # 章节撰写Skill，单章/批量创作+续写
├── sumeru-review/        # 逻辑审查Skill，时间线+剧情+人物一致性校验
├── sumeru-polish/        # 内容润色Skill，文笔优化+节奏调整+风格统一
└── sumeru-finalize/      # 完稿校验Skill，合规检查+多平台格式导出
```

每个Skill目录采用统一结构：
- `SKILL.md`：Skill元数据定义与使用说明
- `scripts/`（按需创建）：存放Skill执行所需的脚本文件
- `references/`（按需创建）：存放参考资料、模板、知识库等资源

## 章节篇幅口径（全局统一）

所有Skill必须使用同一套篇幅/字数口径，禁止各自定义：

| 篇幅 | 目标总字数 | 建议章节区间* | 适用场景 |
|------|-----------|--------------|----------|
| 短篇 | 20 万字 | 40-70 章 | 试水、短平快、平台征文 |
| 中篇 | 20-50 万字 | 70-170 章 | 主流连载起步 |
| 长篇 | 50-100 万字 | 170-340 章 | 主流商业连载 |
| 超长篇 | 100 万字以上 | 340 章以上 | 长线养书、大IP |

\* 按单章 3000 字基准估算（区间 = 总字数 ÷ 3000，允许 ±15%）。

### 单章字数基准（按平台）

| 平台 | 单章建议字数 | 说明 |
|------|-------------|------|
| 起点 | 3000-5000 | 付费订阅，长章更有黏性 |
| 番茄 | 2000-3000 | 免费+广告，短章提升完读率 |
| 晋江 | 2500-4000 | 女频为主，重情绪密度 |
| 纵横 | 3000-6000 | 男频长篇 |
| 17K | 2000-4000 | 灵活 |

未指定平台时默认 **3000 字/章**。章节总数 = ceil(目标总字数 / 单章字数)，由 `skills/sumeru-outline/scripts/plan-chapters.py` 计算，不要手算。

## 合规底线（写死，不可协商）

1. **人名**：禁止真实人物、知名 IP 角色名及其改字/拆字版本。
2. **地名**：禁止真实国家/省市/区县/山川/景点全称；现实题材仅可使用「帝都」「魔都」这类泛称。
3. **机构**：禁止真实公司、银行、学校、法院、军队番号、赛事、俱乐部，以及谐音碰瓷版本。
4. **宗教/民族**：禁止真实宗教人物与场所，禁止民族/地域歧视性设定。
5. **技术细节**：禁止可复现的危险品配方、武器制造、黑客攻击、诈骗操作。
6. **判定基准**：统一使用 `skills/sumeru-outline/references/ip-blocklist.md`，该文件是唯一黑名单源。
7. **门禁**：`compliance-check.json` 的 `passed` 不为 `true` 时，禁止进入写作阶段；完稿阶段 `build.py` 扫描命中禁用名称时，禁止导出。

## 公共工具脚本（确定性保障）

涉及统计、校验、导出的环节一律优先调用脚本，不要靠模型心算：

```bash
# 1. 章节规划 / 细纲骨架 / 细纲校验（outline）
python3 skills/sumeru-outline/scripts/plan-chapters.py --total-words 1000000 --chapter-words 3000 --volumes 5
python3 skills/sumeru-outline/scripts/plan-chapters.py --total-words 300000 --emit-skeleton
python3 skills/sumeru-outline/scripts/plan-chapters.py --validate .sumeru/outline/chapter-outlines.json

# 2. 章节结构 / 命名 / 缺章校验（write）
python3 skills/sumeru-write/scripts/check-chapters.py --chapters chapters \
  --outline .sumeru/outline/chapter-outlines.json

# 3. 字数统计（review）
python3 skills/sumeru-review/scripts/chapter-word-counter.py --dir chapters

# 4. 时间线机器校验（review）
python3 skills/sumeru-review/scripts/validate-timeline.py \
  --timeline .sumeru/review/timeline.json --chapters chapters

# 5. 拆书结构统计 + 报告原创性检查（deconstruct）
python3 skills/sumeru-deconstruct/scripts/analyze-book.py --file 参考书.txt
python3 skills/sumeru-deconstruct/scripts/check-derivative.py \
  --source 参考书.txt --output 拆书报告_某书.md --forbid "原作主角名"

# 6. 完稿检查 + 多平台导出（finalize）
python3 skills/sumeru-finalize/scripts/build.py --check-only
python3 skills/sumeru-finalize/scripts/build.py --platform all --format md,txt,html,epub --title "书名"
```

脚本退出码约定：`0` 通过 / `1` 存在错误 / `2` 参数或环境错误。

### 测试

```bash
python3 -m unittest discover -s tests -v
```

新增或修改 `scripts/` 下任何脚本，必须同步补充 `tests/test_tools.py` 用例。

## 常用命令速查
### 全流程创作
```bash
# 启动完整网文创作流程，自动协调所有环节
/sumeru-worldbuilder <题材类型> "<核心创意关键词>"
/sumeru-worldbuilder 玄幻 "废柴逆袭+系统流+穿越"
/sumeru-worldbuilder 都市 "重生+投资+创业"
```

### 单环节独立调用
```bash
# 选题策划：生成多套选题方案与市场分析
/sumeru-topic <题材类型> "<核心关键词>"
/sumeru-topic 玄幻 "系统+签到+无敌" 起点平台
/sumeru-topic 言情 "穿越+宫斗+甜宠" 女频 中篇

# 大纲设计：生成完整世界观、人设、剧情大纲和**完整章节细纲**
/sumeru-outline "<核心创意描述>"
/sumeru-outline "重生2000年靠互联网创业"
/sumeru-outline 复用已有选题数据 # 复用已有选题数据

# 章节撰写：生成/续写/重写章节内容（**支持细纲驱动并行生成**）
/sumeru-write <章节号> "<章节概要>"
/sumeru-write 第3章 "主角首次使用金手指震惊众人" 仙侠风格 强化爽点 2500字
/sumeru-write 第5章 续写 # 续写已有内容
/sumeru-write 全部章节 # 从细纲生成所有章节（并行）
/sumeru-write 第1-100章 批量并行创作指定范围

# 拆书分析：拆结构、节奏、人物功能位（不抄文本）
/sumeru-deconstruct <原作文件或章节目录>
/sumeru-deconstruct 参考书.txt 分析黄金三章和爽点节奏

# 逻辑审查：校验剧情一致性、时间线、人物OOC等问题
/sumeru-review <章节范围>
/sumeru-review 第1-50章
/sumeru-review 审查全部内容
/sumeru-review 第1-20章 仅检查时间线和人物OOC

# 内容润色：优化文笔、节奏、爽点等
/sumeru-polish <章节范围>
/sumeru-polish 第10章 中度润色 小白爽文风格 强化爽点
/sumeru-polish 第1-3章 轻度润色
/sumeru-polish 第5章 深度润色 节奏收紧+对话优化

# 完稿校验：检查错误+导出平台适配格式
/sumeru-finalize
/sumeru-finalize 导出起点格式
/sumeru-finalize 导出全平台格式
/sumeru-finalize 批量替换+自动分段
```

## Skill核心功能概览
### 1. sumeru-worldbuilder 世界构建师Skill
**定位**：全流程创作协调器/故事世界统筹者，适用于"从零开始写小说"、"帮我写本XX类型的网文"等整体创作需求
**核心能力**：
- 智能编排选题→大纲→写作→审查→润色→完稿全流程，构建完整统一的故事世界
- 交互式需求引导，完善创作参数，确保产出符合预期
- 断点续传支持，创作中断后可恢复进度
- 多版本对比、团队协作、系列作品创作等进阶场景支持
**核心参数**：作品类型、核心关键词、标题、篇幅、风格、调性

### 2. sumeru-deconstruct 拆书分析Skill
**定位**：结构研究，适用于"帮我拆书"、"分析这本书为什么火"、"仿写这本书"等需求
**核心能力**：
- 机械统计：章节字数、对话占比、段句长、章末钩子类型、视角、高频重复短语
- 十二维结构拆解：黄金三章、人物功能位、爽点密度、伏笔台账、换图节奏、信息释放
- 抽象化模板：所有角色/地名替换为功能位占位符，只输出可复用结构
- 原创性门禁：报告与原作最长连续重合 ≤12 字，原作专名零出现
**核心参数**：原作范围、分析重点、是否生成仿写方案

### 3. sumeru-topic 选题策划Skill
**定位**：创意生成与市场分析，适用于"不知道写什么"、"帮我想个题材"、"分析什么题材火"等需求
**核心能力**：
- 市场热点分析，基于各大平台榜单数据提供趋势参考
- 生成3-5套差异化选题方案，包含金手指设计、核心卖点、爽点模式
- 多维度可行性评估：市场热度、竞争格局、受众规模、创作难度、变现潜力
- 风险提示：政策风险、市场饱和风险、题材生命周期预警
**核心参数**：目标平台、目标受众、预期篇幅

### 4. sumeru-outline 大纲设计Skill
**定位**：故事框架搭建，适用于"写个小说大纲"、"设计人设"、"做世界观设定"等需求
**核心能力**：
- 完整世界观设定：世界背景、力量体系、社会规则、地理设定（全部虚构名称，合规避坑）
- 人物设定卡：主角、配角、反派的性格、背景、成长线、人物关系
- 剧情框架：主线、支线、关键节点、高潮安排、分卷规划
- **完整章节细纲：生成所有章节的详细细纲，保存为 chapter-outlines.json，供并行写作使用**
- 爽点排布：遵循黄金爽点密度公式，规划关键爽点、转折点、悬念点位置
- 自动合规检查：禁止使用真实人名/地名，避免侵权风险
**核心参数**：复用数据源、大纲风格

### 5. sumeru-write 章节撰写Skill
**定位**：内容生成器，适用于"帮我写一章"、"续写内容"、"生成XX情节"等需求
**核心能力**：
- **细纲驱动生成：自动读取 chapter-outlines.json，支持单章或批量并行生成所有章节**
- 适配网文节奏：开篇抓眼、中段冲突、结尾留悬念的黄金结构
- 保持人物性格与剧情逻辑一致性，避免OOC
- 支持多种写作模式：续写、重写、扩写、精简、POV切换
- 多Agent并行批量创作，支持同时生成多章内容，效率提升5倍+，**每个Agent最多负责3个章节**
**核心参数**：写作风格、目标字数、节奏、视角、并行模式

### 6. sumeru-review 逻辑审查Skill
**定位**：内容质检官，适用于"检查有没有bug"、"时间线对不对"、"有没有剧情矛盾"等需求
**核心能力**：
- **三阶段审查修复流程**：全局审查→章节细节审查（Agent Team并行，遵循3章/Agent全局约束）→轻量修复+严重问题自动修订大纲并重写章节（底线问题零遗漏核验）
- 时间线校验：绝对/相对时间、季节、年龄、事件顺序一致性检查
- 剧情一致性校验：设定、物品状态、信息边界、地理空间合理性检查
- 逻辑漏洞检测：因果关系、人物动机、能力设定、社会常识合理性检查
- OOC检测：人物性格、价值观、能力、语言风格、行为模式一致性检查
- 伏笔追踪：记录所有伏笔位置、类型、回收状态，提供回收建议
**核心参数**：审查范围、检查类型、字数检查

### 7. sumeru-polish 内容润色Skill
**定位**：内容优化器，适用于"帮我润色一下"、"改改文笔"、"优化节奏"等需求
**核心能力**：
- 3级润色级别：轻度（优化表达）→中度（重构结构）→深度（逐字打磨）
- 多风格适配：小白爽文、精品文、古风、都市现实、悬疑、科幻等风格转换
- 针对性优化：节奏收紧、爽点强化、对话优化、文笔提升、悬念增强
**核心参数**：润色级别、目标风格、优化重点

### 8. sumeru-finalize 完稿校验Skill
**定位**：发布前最后把关，适用于"完稿检查"、"导出平台格式"、"批量处理"等需求
**核心能力**：
- 错误检查：错别字、标点、语法错误检测与修正
- 敏感内容检测：三级敏感词分类检测与修改建议
- 格式标准化：章节标题、段落格式、标点规范统一
- 多平台导出：适配起点、番茄、晋江、纵横等主流平台格式
- 批量处理：全局替换、正则替换、自动分段等工具功能
**核心参数**：导出平台、批量替换、自动分段

## 数据持久化规范
### 路径分类规则
- **中间数据**：仅系统内部使用的临时数据、元数据、进度信息、结构化配置等，统一存储在 `.sumeru/` 目录下，支持断点恢复与跨阶段数据复用，用户无需关心
- **用户可见输出**：最终交付给用户的可读文档、章节内容、导出文件等，直接保存在当前工作目录下，用户可直接查看和使用

### 中间数据目录结构（.sumeru/）
```
.sumeru/
├── session/          # 会话全局配置与状态
├── topic/            # 选题阶段中间数据
├── deconstruct/      # 拆书阶段中间数据
│   ├── structure.json        # 逐章结构统计
│   └── derivative-check.json # 拆书报告原创性检查
├── outline/          # 大纲阶段中间数据
│   ├── chapter-plan.json      # 章节/分卷规划（plan-chapters.py 输出）
│   ├── chapter-outlines.json  # **完整章节细纲（write阶段的输入）**
│   └── compliance-check.json  # 命名合规检查结果（passed=true 才能写作）
├── write/            # 创作阶段中间数据
│   ├── original/     # 原始章节备份（review/polish修改前自动备份）
│   └── chapter-check.json     # 章节结构/命名校验（check-chapters.py 输出）
├── review/           # 审查阶段中间数据
│   ├── fix-plan.json # 修复执行记录（记录所有已执行的修复操作详情）
│   ├── timeline.json # 结构化时间线（schema 见 references/timeline-schema.md）
│   ├── timeline-check.json # 时间线机器校验结果
│   └── word-count.json # 字数统计（chapter-word-counter.py 输出）
├── polish/           # 润色阶段中间数据
└── finalize/         # 完稿阶段中间数据
    ├── stats.json    # 统计与导出结果
    └── report.md     # 完稿校验报告
```

### 用户可见输出（当前工作目录）
```
./
├── 选题策划报告.md      # topic阶段输出
├── 拆书数据报告.md      # deconstruct阶段输出（机械统计）
├── 拆书报告_*.md        # deconstruct阶段输出（结构拆解）
├── 小说大纲_*.md        # outline阶段输出（世界观/剧情/章节细纲）
├── chapters/           # write阶段输出的章节文件（001-标题.md）
├── 剧情审查报告.md      # review阶段输出
├── 完稿校验报告.md      # finalize阶段输出
├── publish/            # finalize阶段导出的发布格式文件（按平台分目录）
│   └── {platform}/     # full.md / full.txt / full.html / book.epub / chapters/
└── output/             # worldbuilder全流程输出目录
```

## Skill开发规范
新增Skill需遵循现有架构规范：
1. 在`skills/`下创建独立目录，目录名与Skill名一致（英文小写，短横线分隔）
2. 目录内必须包含：
   - `SKILL.md` Skill定义文件，包含完整元数据（name、description、type: skill）
   - `scripts/`目录（按需创建）：存放执行逻辑脚本
   - `references/`目录（按需创建）：存放领域知识与模板
3. Skill描述中必须包含触发关键词与排除规则，确保被正确识别调用
4. 命令参数采用自然语言描述，避免命令行风格（如 `--param`），保持用户友好
5. 涉及统计、校验、导出的能力必须提供 `scripts/` 脚本，并在 `tests/test_tools.py` 补测试用例，禁止只写“请模型自行计算”
6. 新增题材参考库时，只提供构词法/结构模板，不提供成品知名角色名；必须与 `skills/sumeru-outline/references/ip-blocklist.md` 对齐

## 边界与权限说明
### ✅ 可直接执行
- 读取所有Skill定义文件与参考资料
- 运行Skill命令进行测试与创作
- 在`tmp/`目录下创建临时草稿文件
- 执行`scripts/`目录下的公共工具脚本

### ⚠️ 需要确认后执行
- 新增第三方依赖库
- 修改现有Skill的核心逻辑
- 变更目录结构或命令语法
- 向主分支提交代码

### 🚫 禁止操作
- 提交任何用户生成的小说内容到仓库
- 未经校验修改`references/`目录下的参考资料
- 硬编码平台特有规则，破坏多平台兼容性
- 在脚本中引入任何跟踪或数据收集逻辑

## 关键规则
1. **遵循现有模式**：修改或新增Skill时，需与现有Skill的结构、命令语法、输出格式保持一致
2. **上下文轻量化**：所有 bulky 参考资料（题材规范、剧情模板等）存放在各Skill的`references/`目录，不要在AGENTS.md中冗余存储
3. **输出确定性**：所有Skill对相同输入应产生一致、可复现的输出
4. **错误友好**：所有脚本需返回清晰、可操作的错误信息，说明解决方法
5. **子Agent并行处理规则（全局强制约束）**：所有涉及章节级批量操作的Skill（sumeru-write、sumeru-review、sumeru-polish、sumeru-finalize、sumeru-outline的细纲生成），在处理大量章节时必须使用子Agent并行处理，且**每个子Agent最多负责3个章节**。这是硬性约束，不可违反。各Skill定义文件中不再重复完整描述此规则，统一引用本条。
   - **设计原因**：防止单个Agent处理过多章节导致上下文溢出和质量下降，3章是兼顾效率（保持章节间上下文连贯性）与质量（避免任务过重降低产出）的平衡点
   - **适用场景**：写作、审查、润色、校验、细纲生成等所有无前后依赖的章节级批量操作
   - **调度计算**：所需Agent数 = ceil(总章节数 / 3)，分配策略为按章节顺序连续分配
   - **Skill内引用方式**：各Skill中使用"⚠️ 遵循全局约束：每个子Agent最多负责3个章节（详见 AGENTS.md '子Agent并行处理规则'）"格式引用，不再完整重述
6. **自动备份规则（全局强制约束）**：review修复和polish润色直接修改 `chapters/` 目录中的文件，修改前自动备份原始章节到 `.sumeru/write/original/`，确保可回滚。无需用户手动确认应用步骤。
7. **Skill间解耦规则**：禁止下游Skill直接调用上游Skill（如review不得调用sumeru-write）。review发现严重问题时，由自身使用子Agent（遵循3章/Agent约束）自动修订大纲并重写对应章节，修复结果直接修改 chapters/（自动备份到 .sumeru/write/original/），全部修复操作记录到 fix-plan.json，供worldbuilder编排确认和用户查阅。
8. **拆书不抄书规则（全局强制约束）**：`sumeru-deconstruct` 只输出结构模板、节奏参数与功能位配置，不输出原文段落、原作专名或换名后的角色关系图。拆书报告必须通过 `check-derivative.py`（最长连续重合 ≤12 字、原作专名零命中）才能交付或传给下游 Skill。
9. **阶段门禁规则**：阶段交接必须通过可执行校验，不允许“看起来差不多”就进入下一阶段。
   - deconstruct → 交付/下游：`derivative-check.json` 的 `passed` 为 `true`
   - outline → write：`plan-chapters.py --validate` 通过，且 `compliance-check.json` 的 `passed` 为 `true`
   - write → review：`check-chapters.py` 无 error（缺章、命名错误、空章均为 error）
   - review → polish：`bottom-line-checklist.json` 中无「待修复」项，且 `validate-timeline.py` 无 error
   - polish → finalize：`chapters/` 中无 TODO/占位符
   - finalize → 交付：`build.py` 无 error，且所有目标平台目录生成成功

## 核心文件索引
- `AGENTS.md` / `CLAUDE.md` - 全局规则与命令说明（软链接指向同一文件）
- `README.md` - 面向用户的项目介绍与使用示例
- `skills/*/SKILL.md` - 各Skill的详细使用文档与参数说明
- `skills/*/scripts/` - Skill专属工具脚本（按需存在）
- `skills/*/references/` - Skill专属参考资料（按需存在）
- `skills/sumeru-outline/references/ip-blocklist.md` - **IP/合规唯一黑名单源**
- `skills/sumeru-review/references/timeline-schema.md` - 时间线数据结构与校验规则
- `skills/sumeru-deconstruct/references/deconstruct-framework.md` - 拆书十二维与报告模板
- `tests/test_tools.py` - 脚本回归测试
- `LICENSE` - MIT 许可证
