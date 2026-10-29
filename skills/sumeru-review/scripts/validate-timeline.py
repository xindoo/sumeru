#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间线机器校验（sumeru-review）

校验 .sumeru/review/timeline.json 中的事件时序、年龄、季节、持续时长与因果引用。
模型负责抽取事件，本脚本负责验算，避免"看起来差不多"的时间线蒙混过关。

用法：
  # 生成空模板
  python3 skills/sumeru-review/scripts/validate-timeline.py --template .sumeru/review/timeline.json

  # 校验
  python3 skills/sumeru-review/scripts/validate-timeline.py \\
    --timeline .sumeru/review/timeline.json --chapters chapters

  # 严格模式
  python3 skills/sumeru-review/scripts/validate-timeline.py --timeline .sumeru/review/timeline.json --strict

退出码：0 通过 / 1 存在错误 / 2 参数错误
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SEASON_BY_MONTH = {
    3: "春", 4: "春", 5: "春",
    6: "夏", 7: "夏", 8: "夏",
    9: "秋", 10: "秋", 11: "秋",
    12: "冬", 1: "冬", 2: "冬",
}


def parse_date(value):
    """只接受 ISO 日期（允许 / 或 . 分隔）；失败返回 None"""
    if not isinstance(value, str):
        return None
    text = value.strip().replace("/", "-").replace(".", "-")
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def template():
    return {
        "meta": {
            "storyStartDate": "2024-01-01",
            "calendar": "solar",
            "notes": "",
        },
        "characters": [
            {"id": "c1", "name": "主角", "birthDate": "2000-01-01", "initialAge": 24}
        ],
        "events": [
            {
                "id": "e001",
                "chapter": 1,
                "title": "故事开始",
                "date": "2024-01-01",
                "dayOffset": 0,
                "season": "冬",
                "type": "main",
                "characters": ["c1"],
                "ages": {"c1": 24},
                "durationDays": 0,
                "location": "",
                "causedBy": [],
                "parallel": False,
                "timeSkip": False,
                "notes": "",
            }
        ],
    }


def validate(data, chapter_count=None, strict=False):
    errors, warnings = [], []

    meta = data.get("meta", {}) if isinstance(data, dict) else {}
    characters = data.get("characters", [])
    events = data.get("events", [])
    if not isinstance(events, list) or not events:
        return ["events 必须是非空数组"], [], {}

    # ---------- 人物 ----------
    people = {}
    for idx, person in enumerate(characters):
        pid = person.get("id")
        if not pid:
            errors.append(f"characters[{idx}] 缺少 id")
            continue
        if pid in people:
            errors.append(f"人物 id 重复：{pid}")
        people[pid] = person
        if not person.get("name"):
            warnings.append(f"人物 {pid} 缺少 name")
        if person.get("birthDate") and not parse_date(person["birthDate"]):
            errors.append(f"人物 {pid} 的 birthDate 无法解析：{person['birthDate']}")

    explicit_origin = parse_date(meta.get("storyStartDate"))
    # 没有显式起始日时，用「第一个非回忆事件」的日期作为排序基准，
    # 避免闪回把整条时间线拉偏。
    ordered_raw = sorted(
        [e for e in events if isinstance(e, dict)],
        key=lambda e: (e.get("chapter") if isinstance(e.get("chapter"), int) else 10**9),
    )
    first_main_date = next(
        (parse_date(e["date"]) for e in ordered_raw
         if e.get("date") and e.get("type") != "flashback" and parse_date(e["date"])),
        None,
    )
    origin = explicit_origin or first_main_date

    # ---------- 事件基础字段 ----------
    seen_ids = {}
    prepared = []
    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            errors.append(f"events[{idx}] 不是对象")
            continue
        eid = event.get("id")
        if not eid:
            errors.append(f"events[{idx}] 缺少 id")
            continue
        if eid in seen_ids:
            errors.append(f"事件 id 重复：{eid}")
        seen_ids[eid] = idx

        chapter = event.get("chapter")
        if not isinstance(chapter, int) or chapter < 1:
            errors.append(f"事件 {eid} 的 chapter 必须是正整数")
        elif chapter_count and chapter > chapter_count:
            errors.append(f"事件 {eid} 指向第 {chapter} 章，但实际只有 {chapter_count} 章")

        if not event.get("title"):
            errors.append(f"事件 {eid} 缺少 title")

        ev_date = parse_date(event.get("date"))
        if event.get("date") and not ev_date:
            # 架空历法允许只用 dayOffset
            if event.get("dayOffset") is None:
                warnings.append(f"事件 {eid} 的 date 无法解析且未提供 dayOffset：{event.get('date')}")

        offset = event.get("dayOffset")
        if offset is not None and not isinstance(offset, int):
            errors.append(f"事件 {eid} 的 dayOffset 必须是整数")
            offset = None
        if ev_date and offset is None and origin:
            offset = (ev_date - origin).days
        if ev_date and offset is not None and explicit_origin:
            derived = (ev_date - explicit_origin).days
            if offset != derived:
                errors.append(
                    f"事件 {eid} 的 date({event['date']}) 与 dayOffset({offset}) 不一致，"
                    f"按起始日推算应为 {derived}"
                )

        if offset is None and not ev_date:
            warnings.append(f"事件 {eid} 没有任何时间锚点（date/dayOffset）")

        season = event.get("season")
        if season and ev_date:
            expected = SEASON_BY_MONTH.get(ev_date.month)
            if expected and season != expected:
                warnings.append(
                    f"事件 {eid} 标注季节「{season}」，但日期 {event['date']} 属于{expected}"
                )

        duration = event.get("durationDays", 0)
        if duration is not None and (not isinstance(duration, int) or duration < 0):
            errors.append(f"事件 {eid} 的 durationDays 必须是非负整数")

        for pid in event.get("characters", []) or []:
            if pid not in people:
                errors.append(f"事件 {eid} 引用了不存在的人物 id：{pid}")

        for pid, age in (event.get("ages") or {}).items():
            if pid not in people:
                errors.append(f"事件 {eid} 的 ages 引用了不存在的人物 id：{pid}")
                continue
            if not isinstance(age, int) or age < 0:
                errors.append(f"事件 {eid} 中人物 {pid} 的年龄非法：{age}")
                continue
            person = people[pid]
            birth = parse_date(person.get("birthDate"))
            if birth and ev_date:
                expected = ev_date.year - birth.year - (
                    (ev_date.month, ev_date.day) < (birth.month, birth.day)
                )
                if abs(expected - age) > 1:
                    errors.append(
                        f"事件 {eid}：人物 {pid} 标注 {age} 岁，"
                        f"按生日推算应为 {expected} 岁（容差 ±1）"
                    )
            elif person.get("birthYear") and ev_date:
                expected = ev_date.year - int(person["birthYear"])
                if abs(expected - age) > 1:
                    errors.append(
                        f"事件 {eid}：人物 {pid} 标注 {age} 岁，"
                        f"按出生年推算应为约 {expected} 岁"
                    )

        prepared.append({
            **event,
            "_date": ev_date,
            "_offset": offset,
            "_index": idx,
            "_sortChapter": chapter if isinstance(chapter, int) else 10**9,
        })

    # ---------- 因果引用 ----------
    for event in prepared:
        for cause in event.get("causedBy", []) or []:
            if cause not in seen_ids:
                errors.append(f"事件 {event['id']} 的 causedBy 引用了不存在的事件：{cause}")
                continue
            if cause == event["id"]:
                errors.append(f"事件 {event['id']} 不能以自己为原因")
                continue
            cause_event = prepared[seen_ids[cause]]
            if (event.get("type") != "flashback"
                    and isinstance(cause_event.get("chapter"), int)
                    and isinstance(event.get("chapter"), int)
                    and cause_event["chapter"] > event["chapter"]):
                errors.append(
                    f"事件 {event['id']}（第{event['chapter']}章）引用了后续章节的"
                    f"原因事件 {cause}（第{cause_event['chapter']}章）"
                )

    # ---------- 时序 ----------
    ordered = sorted(prepared, key=lambda e: (e["_sortChapter"], e["_index"]))
    prev = None
    age_tracker = {}
    for event in ordered:
        if event.get("type") == "flashback":
            continue
        for pid, age in (event.get("ages") or {}).items():
            if pid in age_tracker and isinstance(age, int) and age < age_tracker[pid]:
                errors.append(
                    f"事件 {event['id']}：人物 {pid} 年龄从 {age_tracker[pid]} 降到 {age}，"
                    f"时间线倒流"
                )
            if isinstance(age, int):
                age_tracker[pid] = age

        if event["_offset"] is None:
            prev = event
            continue

        if prev is not None and prev["_offset"] is not None:
            if event["_offset"] < prev["_offset"]:
                errors.append(
                    f"事件 {event['id']}（第{event['chapter']}章）时间早于前一事件 "
                    f"{prev['id']}（第{prev['chapter']}章）：dayOffset "
                    f"{event['_offset']} < {prev['_offset']}"
                )
            elif not event.get("parallel"):
                prev_end = prev["_offset"] + (prev.get("durationDays") or 0)
                if event["_offset"] < prev_end:
                    errors.append(
                        f"事件 {event['id']} 与前一事件 {prev['id']} 时间区间重叠："
                        f"{prev['id']} 持续到 day {prev_end}，但 {event['id']} 从 day {event['_offset']} 开始"
                    )
                gap = event["_offset"] - prev_end
                if gap > 365 and not event.get("timeSkip"):
                    warnings.append(
                        f"事件 {event['id']} 与前一事件间隔 {gap} 天，未标注 timeSkip"
                    )
        prev = event

    # ---------- 汇总 ----------
    all_offsets = [e["_offset"] for e in prepared if e["_offset"] is not None]
    span_offsets = [e["_offset"] for e in prepared
                    if e["_offset"] is not None and e.get("type") != "flashback"]
    stats = {
        "events": len(events),
        "characters": len(people),
        "timedEvents": len(all_offsets),
        "spanDays": (max(span_offsets) - min(span_offsets)) if span_offsets else 0,
        "errors": len(errors),
        "warnings": len(warnings),
    }
    if strict:
        errors.extend(f"[strict] {w}" for w in warnings)
        stats["errors"] = len(errors)

    timeline = [
        {
            "id": e["id"],
            "chapter": e.get("chapter"),
            "title": e.get("title", ""),
            "date": e.get("date", ""),
            "dayOffset": e["_offset"],
            "durationDays": e.get("durationDays", 0),
            "type": e.get("type", "main"),
        }
        for e in ordered
    ]
    return errors, warnings, {"summary": stats, "timeline": timeline}


def write_report(result, path_dir):
    out = Path(path_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "timeline-check.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    s = result["summary"]
    lines = [
        "# 时间线机器校验报告",
        "",
        "| 指标 | 数值 |",
        "|------|------|",
        f"| 事件数 | {s['events']} |",
        f"| 人物数 | {s['characters']} |",
        f"| 有时间锚点的事件 | {s['timedEvents']} |",
        f"| 时间跨度 | {s['spanDays']} 天 |",
        f"| 错误 | {s['errors']} |",
        f"| 警告 | {s['warnings']} |",
        "",
        f"**结论：{'✅ 通过' if not result['errors'] else '❌ 未通过'}**",
        "",
    ]
    if result["errors"]:
        lines += ["## ❌ 错误", ""] + [f"- {e}" for e in result["errors"]] + [""]
    if result["warnings"]:
        lines += ["## ⚠️ 警告", ""] + [f"- {w}" for w in result["warnings"]] + [""]
    lines += [
        "## 事件时序表",
        "",
        "| 章 | dayOffset | 日期 | 事件 | 类型 | 持续 |",
        "|----|-----------|------|------|------|------|",
    ]
    for e in result["timeline"]:
        lines.append(
            f"| {e['chapter'] if e['chapter'] is not None else '-'} "
            f"| {e['dayOffset'] if e['dayOffset'] is not None else '-'} "
            f"| {e['date'] or '-'} | {e['title']} | {e['type']} | {e['durationDays']} |"
        )
    (out / "timeline-check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="时间线机器校验")
    parser.add_argument("--timeline", "-t", help="timeline.json 路径")
    parser.add_argument("--chapters", "-c", help="章节目录，用于校验 chapter 上界")
    parser.add_argument("--report-dir", default=".sumeru/review", help="报告输出目录")
    parser.add_argument("--template", metavar="PATH", help="写出空模板后退出")
    parser.add_argument("--strict", action="store_true", help="警告也视为失败")
    parser.add_argument("--force", action="store_true", help="--template 时覆盖已存在文件")
    args = parser.parse_args()

    if args.template:
        path = Path(args.template)
        if path.exists() and not args.force:
            print(f"❌ 文件已存在：{path}（如需覆盖请加 --force）")
            return 2
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(template(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📝 模板已写入：{path}")
        return 0

    if not args.timeline:
        parser.error("必须提供 --timeline 或 --template")

    path = Path(args.timeline)
    if not path.exists():
        print(f"❌ 时间线文件不存在：{args.timeline}")
        return 2
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"❌ JSON 解析失败：{exc}")
        return 2

    chapter_count = None
    if args.chapters:
        chapter_dir = Path(args.chapters)
        if not chapter_dir.exists():
            print(f"❌ 章节目录不存在：{args.chapters}")
            return 2
        chapter_count = len([f for f in chapter_dir.glob("*.md") if re.match(r"^\d{3,4}-", f.name)])

    errors, warnings, details = validate(data, chapter_count, args.strict)
    result = {**details, "errors": errors, "warnings": warnings, "passed": not errors}
    write_report(result, args.report_dir)

    s = result["summary"]
    print(f"🧭 {s['events']} 个事件 / {s['timedEvents']} 个有时间锚点 / 跨度 {s['spanDays']} 天")
    for w in warnings:
        print(f"⚠️  {w}")
    for e in errors:
        print(f"❌ {e}")
    print(f"{'✅ 通过' if not errors else '❌ 未通过'}：{len(errors)} 错误 / {len(warnings)} 警告")
    print(f"📝 报告：{Path(args.report_dir) / 'timeline-check.md'}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
