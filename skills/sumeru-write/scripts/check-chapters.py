#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
章节结构校验工具（sumeru-write）

检查项：
  1. 文件命名是否符合 001-标题.md 规范
  2. 章节号是否连续、是否重复
  3. 是否与 chapter-outlines.json 的章节/标题对齐
  4. 每章字数是否落在建议区间
  5. 是否残留模板占位符（TODO/待补充/XXX）

用法：
  python3 skills/sumeru-write/scripts/check-chapters.py
  python3 skills/sumeru-write/scripts/check-chapters.py --chapters chapters --outline .sumeru/outline/chapter-outlines.json --strict

退出码：0 通过（可能存在警告）/ 1 存在结构性错误 / 2 参数错误
"""

import argparse
import json
import re
import sys
from pathlib import Path

NAME_PATTERN = re.compile(r"^(\d{3,4})-(.+)\.md$")
BAD_NAME_HINTS = [
    (re.compile(r"^第\d+章"), "文件名不要带「第X章」前缀"),
    (re.compile(r"^\d{1,2}-"), "章节号必须三位零填充（001-）"),
    (re.compile(r"_"), "章节号与标题之间用短横线 -，不要用下划线"),
]
PLACEHOLDER = re.compile(r"(TODO|待补充|待完善|XXX|\[占位\])")


def count_words(text):
    hanzi = len(re.findall(r"[\u4e00-\u9fa5]", text))
    english = len(re.findall(r"[a-zA-Z]+", text))
    return hanzi + english


def parse_range(value):
    if isinstance(value, int):
        return value, value
    nums = [int(n) for n in re.findall(r"\d+", str(value or ""))]
    if not nums:
        return None
    if len(nums) == 1:
        return nums[0], nums[0]
    return min(nums[:2]), max(nums[:2])


def load_outline(path):
    if not path or not Path(path).exists():
        return None
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return {ch["chapterNumber"]: ch for ch in data.get("chapters", [])
            if isinstance(ch.get("chapterNumber"), int)}


def collect(chapters_dir):
    """扫描章节文件，返回 (valid, invalid)"""
    valid, invalid = [], []
    root = Path(chapters_dir)
    if not root.exists():
        return valid, invalid
    for file in sorted(root.glob("*.md")):
        if file.name.startswith(".") or file.name.upper().startswith("WRITE_PROGRESS"):
            continue
        m = NAME_PATTERN.match(file.name)
        if not m:
            reason = "不符合 {三位章节号}-{标题}.md"
            for pattern, hint in BAD_NAME_HINTS:
                if pattern.search(file.name):
                    reason = hint
                    break
            invalid.append({"file": file.name, "reason": reason})
            continue
        valid.append({
            "file": file.name,
            "path": str(file),
            "number": int(m.group(1)),
            "title": m.group(2),
        })
    valid.sort(key=lambda x: x["number"])
    return valid, invalid


def check(chapters_dir, outline_path=None, strict=False):
    errors, warnings = [], []
    chapters, invalid = collect(chapters_dir)

    for item in invalid:
        errors.append(f"{item['file']}：{item['reason']}")

    if not chapters:
        errors.append(f"目录 {chapters_dir} 下没有符合规范的章节文件")
        return errors, warnings, {"totalChapters": 0, "totalWords": 0}

    # 章节号连续与重复
    numbers = [c["number"] for c in chapters]
    dup = sorted({n for n in numbers if numbers.count(n) > 1})
    if dup:
        errors.append(f"章节号重复：{dup}")
    expected = list(range(1, max(numbers) + 1))
    missing = [n for n in expected if n not in set(numbers)]
    if missing:
        errors.append(f"章节号缺失：{missing[:20]}{'...' if len(missing) > 20 else ''}")

    outline = load_outline(outline_path)
    total_words = 0
    stats_rows = []
    for ch in chapters:
        text = Path(ch["path"]).read_text(encoding="utf-8", errors="ignore")
        words = count_words(text)
        total_words += words
        row = {"number": ch["number"], "file": ch["file"], "words": words}

        if PLACEHOLDER.search(text):
            errors.append(f"{ch['file']}：残留占位符（TODO/待补充/XXX）")
        if words < 500:
            errors.append(f"{ch['file']}：仅 {words} 字，疑似空章/截断")

        if outline is not None:
            ref = outline.get(ch["number"])
            if not ref:
                warnings.append(f"{ch['file']}：细纲中不存在该章节")
            else:
                expected_title = str(ref.get("chapterTitle", "")).strip()
                if expected_title and expected_title != ch["title"]:
                    warnings.append(
                        f"{ch['file']}：标题与细纲不一致（细纲：{expected_title}）"
                    )
                rng = parse_range(ref.get("suggestedWords"))
                if rng:
                    low, high = rng
                    if words < low * 0.8 or words > high * 1.2:
                        warnings.append(
                            f"{ch['file']}：{words} 字，超出建议区间 {low}-{high} 的 ±20%"
                        )
                    row["suggested"] = f"{low}-{high}"
        stats_rows.append(row)

    if outline is not None:
        existing = set(numbers)
        missing_in_files = sorted(set(outline) - existing)
        if missing_in_files:
            errors.append(
                f"细纲中有 {len(missing_in_files)} 章尚未生成：{missing_in_files[:20]}"
                f"{'...' if len(missing_in_files) > 20 else ''}"
            )

    # 标题重复
    titles = [c["title"] for c in chapters]
    dup_titles = sorted({t for t in titles if titles.count(t) > 1})
    if dup_titles:
        warnings.append(f"章节标题重复：{dup_titles[:5]}")

    stats = {
        "totalChapters": len(chapters),
        "totalWords": total_words,
        "averageWords": round(total_words / len(chapters), 1) if chapters else 0,
        "invalidNames": len(invalid),
        "chapters": stats_rows,
    }

    if strict and warnings:
        errors.extend(f"[strict] {w}" for w in warnings)
    return errors, warnings, stats


def write_report(stats, errors, warnings, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "chapter-check.json").write_text(
        json.dumps({"stats": stats, "errors": errors, "warnings": warnings},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# 章节结构校验报告",
        "",
        "| 指标 | 数值 |",
        "|------|------|",
        f"| 章节数 | {stats['totalChapters']} |",
        f"| 总字数 | {stats['totalWords']:,} |",
        f"| 平均字数 | {stats['averageWords']:,} |",
        f"| 命名错误 | {stats['invalidNames']} |",
        f"| 错误数 | {len(errors)} |",
        f"| 警告数 | {len(warnings)} |",
        "",
    ]
    if errors:
        lines += ["## ❌ 错误", ""] + [f"- {e}" for e in errors] + [""]
    if warnings:
        lines += ["## ⚠️ 警告", ""] + [f"- {w}" for w in warnings] + [""]
    (out / "chapter-check.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="章节结构与命名校验")
    parser.add_argument("--chapters", "-c", default="chapters", help="章节目录（默认 chapters）")
    parser.add_argument("--outline", "-o", default=".sumeru/outline/chapter-outlines.json",
                        help="细纲文件路径")
    parser.add_argument("--report-dir", default=".sumeru/write", help="报告输出目录")
    parser.add_argument("--strict", action="store_true", help="严格模式：警告也算失败")
    args = parser.parse_args()

    if not Path(args.chapters).exists():
        print(f"❌ 章节目录不存在：{args.chapters}")
        return 2

    errors, warnings, stats = check(args.chapters, args.outline, args.strict)
    write_report(stats, errors, warnings, args.report_dir)

    print(f"📚 章节数 {stats['totalChapters']}，总字数 {stats['totalWords']:,}，"
          f"平均 {stats['averageWords']:,}")
    for w in warnings:
        print(f"⚠️  {w}")
    for e in errors:
        print(f"❌ {e}")
    print(f"📝 报告：{Path(args.report_dir) / 'chapter-check.md'}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
