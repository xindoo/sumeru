# AGENTS.md - 网文创作专项Skill集合

## 项目概述
本仓库是基于Claude Code Skill体系开发的网文创作全流程专项Skill集合，提供从选题策划到完稿导出的一站式网文创作能力。通过模块化的Skill架构，覆盖网文创作的所有核心环节，支持从创意萌芽到发布准备的完整工作流。

## 技术栈
- Skill框架：Claude Code Skill系统（兼容OpenCode superpowers体系）
- 运行环境：macOS / Linux zsh
- 依赖环境：Python 3.11+、Node.js 20.x（部分工具脚本依赖）
- 当前版本：v1.0.0

## 核心架构结构
```
skills/
├── sumeru-worldbuilder/  # 世界构建师Skill，统筹全流程创作，负责整个故事世界的搭建与落地
├── sumeru-topic/         # 选题策划Skill，市场分析+创意生成
├── sumeru-outline/       # 大纲设计Skill，世界观+人设+剧情框架
├── sumeru-write/         # 章节撰写Skill，单章/批量创作+续写
├── sumeru-review/        # 逻辑审查Skill，时间线+剧情+人物一致性校验
├── sumeru-polish/        # 内容润色Skill，文笔优化+节奏调整+风格统一
└── sumeru-finalize/      # 完稿校验Skill，合规检查+多平台格式导出
```

每个Skill目录采用统一结构：
- `[skill-name].md`：Skill元数据定义与使用说明
- `scripts/`：存放Skill执行所需的脚本文件
- `references/`：存放参考资料、模板、知识库等资源

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
/sumeru-topic 玄幻 "系统+签到+无敌" --platform=起点
/sumeru-topic 言情 "穿越+宫斗+甜宠" --audience=女频 --length=中篇

# 大纲设计：生成完整世界观、人设、剧情大纲
/sumeru-outline "<核心创意描述>"
/sumeru-outline "重生2000年靠互联网创业"
/sumeru-outline --load-from .sumeru/topic/options.json # 复用已有选题数据

# 章节撰写：生成/续写/重写章节内容
/sumeru-write <章节号> "<章节概要>" [参数]
/sumeru-write 第3章 "主角首次使用金手指震惊众人" --style xianxia --cool-face-slap --words 2500
/sumeru-write 第5章 --continue # 续写已有内容
/sumeru-write 第1-100章 --parallel 5 # 批量并行创作

# 逻辑审查：校验剧情一致性、时间线、人物OOC等问题
/sumeru-review <章节范围>
/sumeru-review 第1-50章
/sumeru-review --all # 审查全部内容
/sumeru-review 第1-20章 --only timeline,ooc # 仅检查指定问题类型
/sumeru-review --only-summary --agent-count 5 # 仅生成章节概要（5个Agent并行）
/sumeru-review --skip-summary # 跳过概要生成，直接使用已有的概要进行审查
/sumeru-review --all --agent-count 3 --task-split chunk # 使用3个Agent的chunk模式
/sumeru-review 第1-100章 --full-chapters 5,10,15 # 生成所有概要，对指定章节进行完整审查

# 内容润色：优化文笔、节奏、爽点等
/sumeru-polish <章节范围> [参数]
/sumeru-polish 第10章 --level 2 --style 小白爽文 --focus 爽点强化
/sumeru-polish 第1-3章 --light # 轻度润色，保留原文风格
/sumeru-polish 第5章 --deep --focus 节奏收紧,对话优化

# 完稿校验：检查错误+导出平台适配格式
/sumeru-finalize [参数]
/sumeru-finalize --export qidian # 导出起点平台格式
/sumeru-finalize --export all # 导出全平台格式
/sumeru-finalize --replace --segment # 批量替换+自动分段
```

## Skill核心功能概览
### 1. sumeru-worldbuilder 世界构建师Skill
**定位**：全流程创作协调器/故事世界统筹者，适用于"从零开始写小说"、"帮我写本XX类型的网文"等整体创作需求
**核心能力**：
- 智能编排选题→大纲→写作→审查→润色→完稿全流程，构建完整统一的故事世界
- 交互式需求引导，完善创作参数，确保产出符合预期
- 断点续传支持，创作中断后可恢复进度
- 多版本对比、团队协作、系列作品创作等进阶场景支持
**核心参数**：`--title`、`--length`、`--style`、`--tone`、`--resume`、`--skip-stages`、`--auto-confirm`

### 2. sumeru-topic 选题策划Skill
**定位**：创意生成与市场分析，适用于"不知道写什么"、"帮我想个题材"、"分析什么题材火"等需求
**核心能力**：
- 市场热点分析，基于各大平台榜单数据提供趋势参考
- 生成3-5套差异化选题方案，包含金手指设计、核心卖点、爽点模式
- 多维度可行性评估：市场热度、竞争格局、受众规模、创作难度、变现潜力
- 风险提示：政策风险、市场饱和风险、题材生命周期预警
**核心参数**：`--platform`、`--audience`、`--length`、`--load-existing`

### 3. sumeru-outline 大纲设计Skill
**定位**：故事框架搭建，适用于"写个小说大纲"、"设计人设"、"做世界观设定"等需求
**核心能力**：
- 完整世界观设定：世界背景、力量体系、社会规则、地理设定（全部虚构名称，合规避坑）
- 人物设定卡：主角、配角、反派的性格、背景、成长线、人物关系
- 剧情框架：主线、支线、关键节点、高潮安排、分卷规划
- 爽点排布：遵循黄金爽点密度公式，规划关键爽点、转折点、悬念点位置
- 自动合规检查：禁止使用真实人名/地名，避免侵权风险
**核心参数**：`--load-from`、`--allow-mapping`、`--style`

### 4. sumeru-write 章节撰写Skill
**定位**：内容生成器，适用于"帮我写一章"、"续写内容"、"生成XX情节"等需求
**核心能力**：
- 适配网文节奏：开篇抓眼、中段冲突、结尾留悬念的黄金结构
- 保持人物性格与剧情逻辑一致性，避免OOC
- 支持多种写作模式：续写、重写、扩写、精简、POV切换
- 多Agent并行批量创作，支持同时生成多章内容，效率提升5倍+
**核心参数**：`--style`、`--words`、`--pace`、`--pov`、`--batch`、`--parallel`、`--continue`

### 5. sumeru-review 逻辑审查Skill
**定位**：内容质检官，适用于"检查有没有bug"、"时间线对不对"、"有没有剧情矛盾"等需求
**核心能力**：
- **两阶段审查流程**：先用 Agent Team 并行生成章节概要，再基于概要进行审查，避免上下文超长
- 时间线校验：绝对/相对时间、季节、年龄、事件顺序一致性检查
- 剧情一致性校验：设定、物品状态、信息边界、地理空间合理性检查
- 逻辑漏洞检测：因果关系、人物动机、能力设定、社会常识合理性检查
- OOC检测：人物性格、价值观、能力、语言风格、行为模式一致性检查
- 伏笔追踪：记录所有伏笔位置、类型、回收状态，提供回收建议
**核心参数**：`--all`、`--only`、`--dir`、`--enable-word-count`、`--only-summary`、`--skip-summary`、`--agent-count`、`--task-split`、`--full-chapters`

### 6. sumeru-polish 内容润色Skill
**定位**：内容优化器，适用于"帮我润色一下"、"改改文笔"、"优化节奏"等需求
**核心能力**：
- 4级润色级别：轻度（仅纠错）→中度（优化表达）→深度（重构结构）→精细（逐字打磨）
- 多风格适配：小白爽文、精品文、古风、都市现实、悬疑、科幻等风格转换
- 针对性优化：节奏收紧、爽点强化、对话优化、文笔提升、悬念增强
**核心参数**：`--level`、`--light`/`--deep`、`--style`、`--focus`

### 7. sumeru-finalize 完稿校验Skill
**定位**：发布前最后把关，适用于"完稿检查"、"导出平台格式"、"批量处理"等需求
**核心能力**：
- 错误检查：错别字、标点、语法错误检测与修正
- 敏感内容检测：三级敏感词分类检测与修改建议
- 格式标准化：章节标题、段落格式、标点规范统一
- 多平台导出：适配起点、番茄、晋江、纵横等主流平台格式
- 批量处理：全局替换、正则替换、自动分段等工具功能
**核心参数**：`--export`、`--replace`、`--segment`、`--dir`、`--output-dir`

## 数据持久化规范
### 路径分类规则
- **中间数据**：仅系统内部使用的临时数据、元数据、进度信息、结构化配置等，统一存储在 `.sumeru/` 目录下，支持断点恢复与跨阶段数据复用，用户无需关心
- **用户可见输出**：最终交付给用户的可读文档、章节内容、导出文件等，直接保存在当前工作目录下，用户可直接查看和使用

### 中间数据目录结构（.sumeru/）
```
.sumeru/
├── session/          # 会话全局配置与状态
├── topic/            # 选题阶段中间数据
├── outline/          # 大纲阶段中间数据
├── write/            # 创作阶段中间数据（进度、元数据等）
├── review/           # 审查阶段中间数据
├── polish/           # 润色阶段中间数据（diff记录等）
└── finalize/         # 完稿阶段中间数据
```

### 用户可见输出（当前工作目录）
```
./
├── 选题策划报告.md    # topic阶段输出
├── 小说大纲_*.md      # outline阶段输出
├── chapters/         # write阶段输出的章节文件
├── 剧情审查报告.md    # review阶段输出
├── publish/          # finalize阶段导出的发布格式文件
└── output/           # worldbuilder全流程输出目录
```

## Skill开发规范
新增Skill需遵循现有架构规范：
1. 在`skills/`下创建独立目录，目录名与Skill名一致（英文小写，短横线分隔）
2. 目录内必须包含：
   - 与目录同名的`.md` Skill定义文件，包含完整元数据（name、description、type: skill）
   - 空的`scripts/`目录，存放执行逻辑
   - 空的`references/`目录，存放领域知识与模板
3. Skill描述中必须包含触发关键词与排除规则，确保被正确识别调用
4. 命令参数设计需与现有Skill保持风格一致，避免自定义特殊格式

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

## 核心文件索引
- `AGENTS.md` - 本文件，全局规则与命令说明
- `skills/*/[skill-name].md` - 各Skill的详细使用文档与参数说明
- `scripts/` - 跨Skill共享的工具脚本
- `references/` - 全局公共参考资料（平台规范、通用模板等）