# 时间线数据结构规范（timeline.json）

> `sumeru-review` 第一阶段必须产出本结构，然后跑 `validate-timeline.py` 做机器校验。
> 模型负责从章节中**抽取**事件，脚本负责**验算**；不要把验算工作交给模型心算。

## 一、文件位置

```
.sumeru/review/timeline.json        # 时间线数据（本文件规范）
.sumeru/review/timeline-check.json  # 校验结果
.sumeru/review/timeline-check.md    # 可读校验报告
```

## 二、结构定义

```json
{
  "meta": {
    "storyStartDate": "2024-03-01",
    "calendar": "solar",
    "notes": "主线时间跨度约 2 年"
  },
  "characters": [
    {
      "id": "c1",
      "name": "陆照野",
      "birthDate": "2000-05-01",
      "initialAge": 24
    }
  ],
  "events": [
    {
      "id": "e001",
      "chapter": 1,
      "title": "主角觉醒",
      "date": "2024-03-01",
      "dayOffset": 0,
      "season": "春",
      "type": "main",
      "characters": ["c1"],
      "ages": {"c1": 24},
      "durationDays": 0,
      "location": "临川城",
      "causedBy": [],
      "parallel": false,
      "timeSkip": false,
      "notes": ""
    }
  ]
}
```

## 三、字段说明

### meta
| 字段 | 必填 | 说明 |
|------|------|------|
| storyStartDate | 否 | 故事第 0 天的绝对日期，ISO 格式 `YYYY-MM-DD`；没有绝对时间线可省略 |
| calendar | 否 | `solar`（默认）或其他；架空历法请只用 `dayOffset` |
| notes | 否 | 时间线整体说明 |

### characters
| 字段 | 必填 | 说明 |
|------|------|------|
| id | 是 | 唯一标识，事件里引用 |
| name | 是 | 人物名（仅内部使用，不进入用户报告时也建议保留） |
| birthDate | 否 | ISO 日期，用于年龄验算 |
| birthYear | 否 | 只有年份时使用，年龄验算容差 ±1 |
| initialAge | 否 | 首次出场年龄，用于交叉验算 |

### events
| 字段 | 必填 | 说明 |
|------|------|------|
| id | 是 | 唯一标识 |
| chapter | 是 | 叙事顺序对应的章节号（从 1 开始） |
| title | 是 | 事件简述，10-20 字 |
| date | 否 | 事件发生日期，ISO；与 dayOffset 二选一或同时给 |
| dayOffset | 否 | 相对 `storyStartDate` 的天数，整数，可为负 |
| season | 否 | 春/夏/秋/冬，有日期时会做一致性检查 |
| type | 否 | `main`（默认）/ `flashback`（回忆，跳过时序校验） |
| characters | 否 | 参与人物 id 列表 |
| ages | 否 | 该事件时各人物年龄，`{"c1": 25}` |
| durationDays | 否 | 事件持续天数，默认 0 |
| location | 否 | 地点 |
| causedBy | 否 | 直接因哪些事件导致（事件 id 列表） |
| parallel | 否 | 与上一事件并行发生，跳过区间重叠检查 |
| timeSkip | 否 | 明确标注的大跨度时间跳跃，跳过 >365 天警告 |
| notes | 否 | 补充说明 |

## 四、脚本校验规则

`validate-timeline.py` 会检查：

| # | 规则 | 级别 |
|---|------|------|
| 1 | 事件/人物 id 唯一，必填字段齐全 | 错误 |
| 2 | `chapter` 为正整数；给了 `--chapters` 时不得超过实际章节数 | 错误 |
| 3 | 同一 `causedBy` 引用必须存在，且原因事件不能晚于结果事件（回忆除外） | 错误 |
| 4 | 有 `date` 时必须能解析，或退化为 `dayOffset` | 错误/警告 |
| 5 | `date` 与 `dayOffset` 同时存在时必须一致 | 错误 |
| 6 | 按章节顺序，事件时间不得倒流（`flashback` 除外） | 错误 |
| 7 | 上一事件 `date + durationDays` 不得晚于下一事件（`parallel` 除外） | 错误 |
| 8 | `ages` 必须与 `birthDate/birthYear` 推算一致（±1 岁） | 错误 |
| 9 | 同一人物年龄不得倒退 | 错误 |
| 10 | `season` 与日期月份不一致 | 警告 |
| 11 | 无任何时间锚点的事件 | 警告 |
| 12 | 相邻事件间隔 >365 天且未标 `timeSkip` | 警告 |

## 五、使用方式

```bash
# 生成空模板
python3 skills/sumeru-review/scripts/validate-timeline.py --template .sumeru/review/timeline.json

# 校验
python3 skills/sumeru-review/scripts/validate-timeline.py \
  --timeline .sumeru/review/timeline.json \
  --chapters chapters

# 严格模式：警告也阻断
python3 skills/sumeru-review/scripts/validate-timeline.py --timeline .sumeru/review/timeline.json --strict
```

## 六、抽取要求（给模型的约束）

1. **只记录有叙事意义的事件**：转折、战斗、关系变化、关键获得/失去、地图切换。日常过渡不必逐条记录。
2. **每条事件必须能定位到章节**；无法定位的不要写进事件列表。
3. **相对时间要换算**：把「三天后」「半月后」「翌日」换算成 `dayOffset` 或日期，并在 `notes` 保留原文表述。
4. **不确定就留空**：没有绝对日期的，用 `dayOffset`；连相对锚点都没有的，留空并接受警告，不要编造日期。
5. **回忆单独标注** `type: "flashback"`，避免被时序校验误判。
6. **年龄只在有明确依据时填写**，不要凭感觉推算。
