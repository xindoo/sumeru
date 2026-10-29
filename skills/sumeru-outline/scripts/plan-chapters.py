#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
章节规划与细纲校验工具（sumeru-outline）

用法：
  # 1. 按总字数生成章节/分卷规划
  python3 skills/sumeru-outline/scripts/plan-chapters.py --total-words 1000000 --chapter-words 3000 --volumes 5

  # 2. 直接生成 chapter-outlines.json 骨架（供并行写细纲）
  python3 skills/sumeru-outline/scripts/plan-chapters.py --total-words 300000 --emit-skeleton

  # 3. 校验已生成的细纲
  python3 skills/sumeru-outline/scripts/plan-chapters.py --validate .sumeru/outline/chapter-outlines.json

退出码：0 通过 / 1 校验失败 / 2 参数错误
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path

REQUIRED_CHAPTER_FIELDS = [
    "chapterNumber", "chapterTitle", "suggestedWords", "coreEvent",
    "characters", "plotProgression", "coolPoint", "suspense",
    "connection", "location", "pov", "mood", "volumeNumber",
]

DEFAULT_CHAPTER_WORDS = 3000

# 篇幅 → 建议总字数（与 AGENTS.md / sumeru-outline SKILL.md 保持一致）
LENGTH_PRESETS = {
    "短篇": 200_000,
    "中篇": 500_000,
    "长篇": 1_000_000,
    "超长篇": 2_000_000,
}


def parse_int_range(value):
    """解析 '3000-4000' 或 3000 形式的字数建议，返回 (min, max)"""
    if isinstance(value, int):
        return value, value
    if not isinstance(value, str):
        return None
    nums = [int(n) for n in re.findall(r"\d+", value)]
    if not nums:
        return None
    if len(nums) == 1:
        return nums[0], nums[0]
    return min(nums[:2]), max(nums[:2])


def build_plan(total_words, chapter_words, volumes):
    """按总字数和单章字数计算章节数，并均分到各卷"""
    if total_words <= 0 or chapter_words <= 0 or volumes <= 0:
        raise ValueError("total_words / chapter_words / volumes 必须为正整数")

    total_chapters = math.ceil(total_words / chapter_words)
    if total_chapters < volumes:
        raise ValueError(
            f"章节数({total_chapters})小于卷数({volumes})，请减少卷数或增加总字数"
        )

    base = total_chapters // volumes
    remainder = total_chapters % volumes

    plan_volumes = []
    start = 1
    for i in range(volumes):
        count = base + (1 if i < remainder else 0)
        end = start + count - 1
        plan_volumes.append({
            "volumeNumber": i + 1,
            "volumeName": f"第{i + 1}卷",
            "chapterStart": start,
            "chapterEnd": end,
            "chapterCount": count,
            "plannedWords": count * chapter_words,
            "coreConflict": "",
            "upgradeNode": "",
            "turningPoint": "",
            "volumeHook": "",
        })
        start = end + 1

    return {
        "meta": {
            "totalChapters": total_chapters,
            "totalWords": total_chapters * chapter_words,
            "targetWords": total_words,
            "chapterWords": chapter_words,
            "volumeCount": volumes,
            "volumes": plan_volumes,
        },
        "chapters": [],
    }


def emit_skeleton(plan):
    """把规划展开成 chapter-outlines.json 骨架（字段为空，供并行填充）"""
    skeleton = {
        "meta": plan["meta"],
        "chapters": [],
    }
    for vol in plan["meta"]["volumes"]:
        for num in range(vol["chapterStart"], vol["chapterEnd"] + 1):
            skeleton["chapters"].append({
                "chapterNumber": num,
                "chapterTitle": "",
                "suggestedWords": f"{max(500, plan['meta']['chapterWords'] - 500)}-{plan['meta']['chapterWords'] + 500}",
                "volumeNumber": vol["volumeNumber"],
                "coreEvent": "",
                "characters": [],
                "plotProgression": [],
                "coolPoint": "",
                "suspense": "",
                "foreshadowing": "",
                "connection": "",
                "location": "",
                "pov": "主角视角",
                "mood": "",
            })
    return skeleton


def validate(outline_path, strict=False):
    """校验细纲完整性，返回 (errors, warnings, stats)"""
    errors, warnings = [], []
    path = Path(outline_path)
    if not path.exists():
        return [f"文件不存在：{outline_path}"], [], {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"JSON 解析失败：{exc}"], [], {}

    chapters = data.get("chapters")
    meta = data.get("meta", {})
    if not isinstance(chapters, list) or not chapters:
        return ["chapters 必须是非空数组"], [], {}

    # 1. 必填字段（按字段聚合，避免上百章时刷屏）
    missing_fields = {}
    for idx, ch in enumerate(chapters):
        where = f"chapters[{idx}]"
        for field in REQUIRED_CHAPTER_FIELDS:
            if field not in ch or ch[field] in ("", [], None):
                missing_fields.setdefault(field, []).append(ch.get("chapterNumber", "?"))
        title = str(ch.get("chapterTitle", "")).strip()
        if title and (title.startswith("第") and "章" in title):
            warnings.append(f"第{ch.get('chapterNumber')}章标题包含「第X章」前缀，导出时会重复")
        prog = ch.get("plotProgression")
        if isinstance(prog, list) and 0 < len(prog) < 3:
            warnings.append(f"第{ch.get('chapterNumber')}章 plotProgression 少于3个节点，细纲可能不足以独立成章")
    for field, nums in missing_fields.items():
        sample = nums[:8]
        errors.append(
            f"缺失必填字段 {field}：共 {len(nums)} 章（第 {sample} 章"
            f"{'...' if len(nums) > len(sample) else ''}）"
        )

    # 2. 章节号连续
    nums = [ch.get("chapterNumber") for ch in chapters]
    if any(not isinstance(n, int) for n in nums):
        errors.append("存在非整数的 chapterNumber")
    else:
        expected = list(range(1, len(nums) + 1))
        if sorted(nums) != expected:
            missing = sorted(set(expected) - set(nums))
            extra = sorted(set(nums) - set(expected))
            if missing:
                errors.append(f"章节号不连续，缺失：{missing[:10]}{'...' if len(missing) > 10 else ''}")
            if extra:
                errors.append(f"存在越界/重复章节号：{extra[:10]}{'...' if len(extra) > 10 else ''}")

    # 3. 卷覆盖
    volumes = meta.get("volumes") or []
    covered = set()
    for vol in volumes:
        start, end = vol.get("chapterStart"), vol.get("chapterEnd")
        if not isinstance(start, int) or not isinstance(end, int) or start > end:
            errors.append(f"卷{vol.get('volumeNumber')}的 chapterStart/chapterEnd 非法")
            continue
        covered.update(range(start, end + 1))
        actual = [n for n in nums if isinstance(n, int) and start <= n <= end]
        if len(actual) != end - start + 1:
            errors.append(
                f"卷{vol.get('volumeNumber')}({start}-{end}) 实际章节数 {len(actual)}，应为 {end - start + 1}"
            )
    if volumes and isinstance(nums[0], int):
        uncovered = sorted(set(nums) - covered)
        if uncovered:
            errors.append(f"以下章节未被任何卷覆盖：{uncovered[:10]}")

    # 4. 字数预算
    total_words = 0
    for ch in chapters:
        rng = parse_int_range(ch.get("suggestedWords"))
        if not rng:
            errors.append(f"第{ch.get('chapterNumber')}章 suggestedWords 无法解析")
            continue
        total_words += (rng[0] + rng[1]) / 2
    stats = {
        "totalChapters": len(chapters),
        "estimatedWords": int(total_words),
        "volumeCount": len(volumes),
        "targetWords": meta.get("targetWords"),
    }
    if meta.get("targetWords") and total_words:
        diff = abs(total_words - meta["targetWords"]) / meta["targetWords"]
        if diff > 0.15:
            msg = (
                f"细纲字数预算({int(total_words):,})与目标字数({meta['targetWords']:,})偏差 "
                f"{diff:.0%}，超过15%"
            )
            (errors if strict else warnings).append(msg)

    # 5. 标题重复
    titles = [str(ch.get("chapterTitle", "")).strip() for ch in chapters if ch.get("chapterTitle")]
    dup = {t for t in titles if titles.count(t) > 1}
    if dup:
        warnings.append(f"重复章节标题：{sorted(dup)[:5]}")

    return errors, warnings, stats


def print_plan(plan):
    meta = plan["meta"]
    print(f"📐 章节规划：{meta['totalChapters']} 章 / {meta['volumeCount']} 卷 / 单章约 {meta['chapterWords']} 字")
    print(f"   预计总字数：{meta['totalWords']:,}（目标 {meta['targetWords']:,}）")
    print()
    print("| 卷 | 章节范围 | 章数 | 预计字数 |")
    print("|----|----------|------|----------|")
    for vol in meta["volumes"]:
        print(f"| 第{vol['volumeNumber']}卷 | {vol['chapterStart']}-{vol['chapterEnd']} "
              f"| {vol['chapterCount']} | {vol['plannedWords']:,} |")


def main():
    parser = argparse.ArgumentParser(description="章节规划与细纲校验工具")
    parser.add_argument("--total-words", type=int, help="目标总字数")
    parser.add_argument("--length", choices=LENGTH_PRESETS.keys(), help="按篇幅预设总字数")
    parser.add_argument("--chapter-words", type=int, default=DEFAULT_CHAPTER_WORDS,
                        help=f"单章目标字数（默认 {DEFAULT_CHAPTER_WORDS}）")
    parser.add_argument("--volumes", type=int, default=5, help="分卷数（默认5）")
    parser.add_argument("--emit-skeleton", action="store_true", help="输出 chapter-outlines.json 骨架")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--validate", metavar="OUTLINE_JSON", help="校验已有细纲文件")
    parser.add_argument("--strict", action="store_true", help="严格模式：字数偏差15%%也视为错误")
    args = parser.parse_args()

    if args.validate:
        errors, warnings, stats = validate(args.validate, strict=args.strict)
        print(f"🔍 校验 {args.validate}")
        if stats:
            print(f"   章节数：{stats['totalChapters']}，卷数：{stats['volumeCount']}，"
                  f"预算字数：{stats['estimatedWords']:,}")
        for w in warnings:
            print(f"   ⚠️  {w}")
        for e in errors:
            print(f"   ❌ {e}")
        if errors:
            print(f"\n校验未通过：{len(errors)} 个错误，{len(warnings)} 个警告")
            return 1
        print(f"\n✅ 校验通过（{len(warnings)} 个警告）")
        return 0

    total_words = args.total_words or (LENGTH_PRESETS[args.length] if args.length else None)
    if not total_words:
        parser.error("必须提供 --total-words 或 --length")

    try:
        plan = build_plan(total_words, args.chapter_words, args.volumes)
    except ValueError as exc:
        print(f"❌ {exc}")
        return 2

    print_plan(plan)

    if args.emit_skeleton:
        out = args.output or ".sumeru/outline/chapter-outlines.json"
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(
            json.dumps(emit_skeleton(plan), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n📝 细纲骨架已写入：{out}")
    elif args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n📝 规划已写入：{args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
