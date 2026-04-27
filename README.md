# 须弥写作 (Sumeru Writing)

专门用于网文创作的AI Agent技能集合，适配Claude Code、OpenCode等AI编程工具，通过Vibe Coding的方式一站式完成从创意到完稿的全流程小说写作。

> 🎯 **定位**: 网文作者的AI创作副驾驶，覆盖选题→大纲→写作→审稿→润色→导出全流程，让创作更高效。

## ✨ 核心特性

- **全流程覆盖**: 从选题策划到多平台导出，覆盖网文创作所有核心环节
- **模块化架构**: 7个独立Skill模块，可单独调用也可全流程自动编排
- **Vibe Coding**: 自然语言指令驱动，无需学习复杂操作
- **市场导向**: 基于主流平台榜单数据分析，提供选题可行性评估
- **逻辑自洽**: 自动校验时间线、剧情一致性、人物OOC等问题
- **风格适配**: 支持小白爽文、精品文、古风、都市等多种写作风格
- **多平台兼容**: 导出适配起点、番茄、晋江、纵横等主流平台格式
- **断点续传**: 所有创作数据自动持久化，支持中断后恢复进度

## 🏗️ 系统架构

须弥写作采用模块化Skill架构，各模块独立工作又可协同编排：

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

## 🚀 安装方式

在Claude Code / OpenCode项目中执行：
```bash
npx skills add xindoo/sumeru
```

## 📖 快速开始

### 全流程创作（推荐）
直接启动完整创作流程，系统会自动引导你完成所有环节，自动协调选题→大纲→写作→审查→润色→导出全流程：
```bash
/sumeru-worldbuilder <题材类型> "<核心创意关键词>" [参数]
```

**核心参数说明：**
| 参数 | 说明 | 示例 |
|------|------|------|
| `--title` | 自定义小说名称 | `--title "重生之互联网大亨"` |
| `--length` | 预期篇幅 | `--length 长篇/中篇/短篇` |
| `--style` | 写作风格 | `--style 小白爽文/精品文/古风` |
| `--tone` | 整体调性 | `--tone 轻松/严肃/搞笑` |
| `--resume` | 中断后恢复创作 | `--resume` |
| `--skip-stages` | 跳过指定环节 | `--skip-stages review,polish` |
| `--auto-confirm` | 自动确认所有选择，无需人工干预 | `--auto-confirm` |

**示例：**
```bash
# 基础用法
/sumeru-worldbuilder 玄幻 "废柴逆袭+系统流+穿越"
/sumeru-worldbuilder 都市 "重生+投资+创业"
/sumeru-worldbuilder 言情 "穿越+宫斗+甜宠"

# 带高级参数的完整用法
/sumeru-worldbuilder 都市 "重生2000年+互联网创业+商战" --title "重生之网络帝国" --length 长篇 --style 精品文 --auto-confirm
/sumeru-worldbuilder 科幻 "星际冒险+机甲+无限流" --resume --skip-stages topic # 恢复之前的科幻题材创作，跳过选题环节
```

### 独立功能调用
你也可以单独调用任意环节的Skill，灵活组合使用：

---

#### 1. 选题策划 Skill
**适用场景**：不知道写什么、想找热门题材、需要市场可行性分析
**功能**：基于主流平台榜单数据分析，生成3-5套差异化选题方案，包含金手指设计、核心卖点、爽点模式，以及市场热度、竞争格局、变现潜力等多维度评估。

```bash
/sumeru-topic <题材类型> "<核心关键词>" [参数]
```

**核心参数说明：**
| 参数 | 说明 | 示例 |
|------|------|------|
| `--platform` | 目标发布平台 | `--platform 起点/番茄/晋江/纵横` |
| `--audience` | 目标受众 | `--audience 男频/女频/中性` |
| `--length` | 预期篇幅 | `--length 长篇/中篇/短篇` |
| `--load-existing` | 加载历史选题数据 | `--load-existing` |

**示例：**
```bash
# 基础用法
/sumeru-topic 玄幻 "系统+签到+无敌" --platform=起点
/sumeru-topic 言情 "穿越+宫斗+甜宠" --audience=女频 --length=中篇

# 更多实用场景
/sumeru-topic 都市 "异能+鉴宝+赘婿" --platform=番茄 --audience=男频 # 生成番茄男频都市异能选题
/sumeru-topic 悬疑 "无限流+密室逃脱+灵异" --audience=中性 --length=中篇 # 生成中性向悬疑中篇选题
/sumeru-topic --load-existing # 加载之前生成的选题，继续优化
```

---

#### 2. 大纲设计 Skill
**适用场景**：写小说大纲、设计人设、做世界观设定
**功能**：生成完整世界观、人物设定卡、剧情框架、爽点排布规划，自动生成虚构名称避免侵权风险。

```bash
/sumeru-outline "<核心创意描述>" [参数]
```

**核心参数说明：**
| 参数 | 说明 | 示例 |
|------|------|------|
| `--load-from` | 复用已有选题数据 | `--load-from .sumeru/sumeru-topic/options.json` |
| `--allow-mapping` | 允许映射真实地名/事件（需自行合规审核） | `--allow-mapping` |
| `--style` | 大纲风格 | `--style 详细/精简/分卷` |

**示例：**
```bash
# 基础用法
/sumeru-outline "重生2000年靠互联网创业"
/sumeru-outline --load-from .sumeru/sumeru-topic/options.json  # 复用选题阶段生成的创意

# 更多实用场景
/sumeru-outline "高武世界+校花+系统+高考逆袭" --style 分卷 # 生成分卷式大纲
/sumeru-outline "古代权谋+皇子夺嫡+穿越" --allow-mapping # 允许映射真实历史背景
/sumeru-outline "星际文明+机甲战斗+虫族入侵" --load-from .sumeru/sumeru-outline/draft.json # 复用之前的大纲草稿继续完善
```

---

#### 3. 章节撰写 Skill
**适用场景**：生成章节内容、续写、重写、批量创作
**功能**：遵循网文黄金节奏结构，保持人物性格与剧情一致性，支持多Agent并行批量创作。

```bash
/sumeru-write <章节号> "<章节概要>" [参数]
```

**核心参数说明：**
| 参数 | 说明 | 示例 |
|------|------|------|
| `--style` | 写作风格 | `--style xianxia/urban/historical` |
| `--words` | 目标字数 | `--words 2000/3000` |
| `--pace` | 节奏控制 | `--pace 快/中/慢` |
| `--pov` | 视角 | `--pov 主角/配角/上帝视角` |
| `--parallel` | 并行创作数量 | `--parallel 5` |
| `--continue` | 续写已有内容 | `--continue` |
| `--cool-face-slap` | 强化爽点/打脸情节 | `--cool-face-slap` |

**示例：**
```bash
# 基础用法
/sumeru-write 第3章 "主角首次使用金手指震惊众人" --style xianxia --cool-face-slap --words 2500
/sumeru-write 第5章 --continue  # 续写第4章之后的内容
/sumeru-write 第1-100章 --parallel 5  # 并行批量生成100章内容，同时启用5个Agent

# 更多实用场景
/sumeru-write 第1章 "主角重生回到高考前一天" --style urban --pace 快 --words 2000 # 快节奏开篇
/sumeru-write 第20-30章 --pov 女配 --style historical # 从女配视角写10章内容
/sumeru-write 第15章 "拍卖会冲突" --cool-face-slap --words 3000 # 强化打脸爽点的章节
```

---

#### 4. 逻辑审查 Skill
**适用场景**：检查剧情bug、时间线错误、人物OOC、逻辑漏洞
**功能**：校验时间线、剧情一致性、人物行为合理性、伏笔追踪，自动发现剧情矛盾和不合理之处。修复结果保存到staging区域，通过`--apply`应用到章节文件。

```bash
/sumeru-review <章节范围> [参数]
```

**核心参数说明：**
| 参数 | 说明 | 示例 |
|------|------|------|
| `--all` | 审查全部章节 | `--all` |
| `--only` | 仅检查指定问题类型 | `--only timeline,ooc,plot` |
| `--dir` | 指定章节文件目录 | `--dir ./my-novel/chapters` |
| `--word-count` | 同时统计字数/节奏数据 | `--word-count` |
| `--apply` | 将修复结果应用到 chapters/ 目录 | `--apply` |

**支持检查的问题类型：**
- `timeline`：时间线/年龄/事件顺序一致性
- `ooc`：人物性格/行为OOC检查
- `plot`：剧情逻辑/设定一致性
- `foreshadow`：伏笔回收检查
- `common`：常识/因果合理性检查

**示例：**
```bash
# 基础用法
/sumeru-review 第1-50章
/sumeru-review --all  # 审查全部内容
/sumeru-review 第1-20章 --only timeline,ooc  # 仅检查时间线和人物OOC问题

# 更多实用场景
/sumeru-review 第30-80章 --only plot,foreshadow # 检查剧情矛盾和伏笔回收情况
/sumeru-review --all --dir ./old-novel/chapters --word-count # 审查旧作品全本，同时输出节奏分析
/sumeru-review 第10-15章 --only common # 检查这几章的常识/逻辑合理性
```

---

#### 5. 内容润色 Skill
**适用场景**：优化文笔、调整节奏、强化爽点、统一风格
**功能**：3级润色级别，专注文笔与内容层面优化，支持多风格转换，针对性优化节奏、爽点、对话、悬念等。

```bash
/sumeru-polish <章节范围> [参数]
```

**核心参数说明：**
| 参数 | 说明 | 示例 |
|------|------|------|
| `--level` | 润色级别（1-3） | `--level 2` |
| `--deep` | 深度润色（重构结构/节奏） | `--deep` |
| `--style` | 目标风格 | `--style 小白爽文/精品文/古风` |
| `--focus` | 优化重点 | `--focus 爽点强化,节奏收紧,对话优化` |
| `--apply` | 将润色结果应用到 chapters/ 目录 | `--apply` |

**润色级别说明：**
- Level 1/轻度：优化句式表达，去除冗余表述，精炼用词，提升文字流畅度
- Level 2/中度：重构段落结构，优化叙事视角，全面提升文笔质感
- Level 3/深度：逐字打磨，雕琢细节，追求最佳阅读体验

**示例：**
```bash
# 基础用法
/sumeru-polish 第10章 --level 2 --style 小白爽文 --focus 爽点强化
/sumeru-polish 第1-3章 --level 1  # 轻度润色，优化表达流畅度
/sumeru-polish 第5章 --deep --focus 节奏收紧,对话优化 # 深度优化节奏和对话

# 更多实用场景
/sumeru-polish 第1-20章 --style 古风 --focus 文笔提升 # 将前20章转为古风风格，提升文笔
/sumeru-polish 第35章 --deep --focus 悬念增强,爽点强化 # 深度优化章节悬念和爽点
/sumeru-polish 第1-100章 --level 1 # 全本轻度润色，优化文字流畅度
```

---

#### 6. 完稿校验 Skill
**适用场景**：完稿检查、敏感词检测、多平台格式导出
**功能**：错别字/标点/语法错误修正，敏感内容检测，格式标准化，多平台格式导出。

```bash
/sumeru-finalize [参数]
```

**核心参数说明：**
| 参数 | 说明 | 示例 |
|------|------|------|
| `--export` | 导出平台格式 | `--export qidian/tomato/jinjiang/all` |
| `--replace` | 启用全局替换功能 | `--replace "旧词":"新词"` |
| `--segment` | 自动分段优化（适配手机阅读） | `--segment` |
| `--dir` | 指定源文件目录 | `--dir ./chapters` |
| `--output-dir` | 指定导出目录 | `--output-dir ./publish` |

**支持导出的平台：**
- `qidian`：起点中文网格式
- `tomato`：番茄小说格式
- `jinjiang`：晋江文学城格式
- `zongheng`：纵横中文网格式
- `all`：导出全部平台格式

**示例：**
```bash
# 基础用法
/sumeru-finalize --export qidian  # 导出起点平台格式
/sumeru-finalize --export all  # 导出全平台格式
/sumeru-finalize --replace --segment  # 批量替换+自动分段优化

# 更多实用场景
/sumeru-finalize --export tomato --segment --output-dir ./tomato-publish # 导出番茄格式，自动分段
/sumeru-finalize --replace "张三":"李玄" "李四":"王虎" --dir ./chapters # 批量替换全文主角名称
/sumeru-finalize --export all --dir ./old-novel --output-dir ./old-novel/publish # 导出旧作品的全平台格式
```

## 💾 数据持久化

### 数据存储规范
- **中间数据**：仅系统内部使用的临时数据、元数据、进度信息等，统一存储在 `.sumeru/` 目录下，支持断点恢复与数据复用，用户无需关心
- **用户可见输出**：所有最终成果直接保存在当前工作目录下，用户可直接查看和使用

#### 中间数据目录（.sumeru/）
```
.sumeru/
├── session/          # 会话全局配置与状态
├── topic/            # 选题阶段中间数据
├── outline/          # 大纲阶段中间数据
├── write/            # 创作阶段中间数据
│   └── original/     # 原始章节备份（--apply前自动备份）
├── review/           # 审查阶段中间数据
│   ├── fixed/        # 轻量修复后的章节（staging区域，需--apply应用）
│   └── fix-plan.json # 重写修复计划
├── polish/           # 润色阶段中间数据
│   └── modified/     # 润色后的章节（staging区域，需--apply应用）
└── finalize/         # 完稿阶段中间数据
```

#### 用户可见输出（当前工作目录）
```
./
├── 选题策划报告.md    # 选题策划阶段最终成果
├── 小说大纲_*.md      # 大纲设计阶段最终成果
├── chapters/         # 章节内容文件
├── 剧情审查报告.md    # 逻辑审查阶段最终成果
├── publish/          # 完稿导出的各平台格式文件
└── output/           # 全流程创作的最终输出目录
```

所有创作过程支持断点恢复，中断后无需重头开始。

## 🎨 核心优势

### 合规安全
- 自动生成虚构的人名、地名、势力名，避免侵权风险
- 三级敏感词检测与修正建议，降低发布风险
- 符合各大平台内容规范要求

### 效率提升
- 多Agent并行创作，效率提升5倍以上
- 智能爽点排布，遵循网文创作黄金节奏公式
- 自动追踪伏笔，提醒回收时机

### 质量保障
- 人物性格与剧情逻辑一致性校验
- 时间线与世界设定合理性检查
- 多轮润色优化，兼顾文笔与节奏

## 🤝 参与贡献

欢迎提交Issue和PR来完善须弥写作！
- 新增Skill需遵循现有架构规范
- 所有新增功能需包含对应的测试用例
- 提交前请确保通过所有现有测试

## 📄 许可证

MIT License

---

**让AI成为你的创作伙伴，释放想象力，专注故事本身 ✍️**
