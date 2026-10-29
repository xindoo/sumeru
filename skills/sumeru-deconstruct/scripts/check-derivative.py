#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拆书报告原创性检查（sumeru-deconstruct）

检查拆书/仿写报告是否过度复制原作文本，避免“拆书”变成“洗稿”。
检查项：
  1. 报告与原文的最长连续重合片段（默认 >=12 字即违规）
  2. 报告中是否出现指定的原作角色名/地名（--forbid）
  3. 是否直接复用原作章节标题

用法：
  python3 skills/sumeru-deconstruct/scripts/check-derivative.py \\
    --source 参考书.txt --output 拆书报告_某书.md \\
    --forbid "原作主角名,原作地名"

  # 目录输入
  python3 ... --source reference/chapters --output 拆书报告.md

退出码：0 通过 / 1 存在违规 / 2 参数错误
"""

import argparse
import json
import re
import sys
from pathlib import Path

CHAPTER_TITLE = re.compile(r"^\s*(第[0-9零〇一二三四五六七八九十百千万两]+章[^\n]{0,40})$")
CJK = re.compile(r"[\u4e00-\u9fa5]")


def read_source(path):
    p = Path(path)
    if p.is_file():
        return p.read_text(encoding="utf-8", errors="ignore")
    texts = []
    for file in sorted(p.iterdir()):
        if file.suffix.lower() in {".txt", ".md"} and file.is_file():
            texts.append(file.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(texts)


def normalize_with_map(text):
    """保留汉字/字母/数字，返回 (规范串, 规范串每个字符对应的原文下标)"""
    norm, mapping = [], []
    for idx, ch in enumerate(text):
        if ch.isalnum() and (CJK.match(ch) or ch.isascii()):
            norm.append(ch)
            mapping.append(idx)
    return "".join(norm), mapping


def longest_overlaps(source_norm, output_norm, min_len, limit=20):
    """找出报告与原文的最长连续重合片段"""
    if len(output_norm) < min_len or len(source_norm) < min_len:
        return []
    source_grams = {source_norm[i:i + min_len] for i in range(len(source_norm) - min_len + 1)}
    runs = []
    i = 0
    n = len(output_norm)
    while i <= n - min_len:
        gram = output_norm[i:i + min_len]
        if gram not in source_grams:
            i += 1
            continue
        pos = source_norm.find(gram)
        # 向左右扩展成最长公共片段
        left = 0
        while (i - left - 1 >= 0 and pos - left - 1 >= 0
               and output_norm[i - left - 1] == source_norm[pos - left - 1]):
            left += 1
        right = min_len
        while (i + right < n and pos + right < len(source_norm)
               and output_norm[i + right] == source_norm[pos + right]):
            right += 1
        start, end = i - left, i + right
        runs.append((start, end))
        i = end
    # 合并重叠/相邻
    merged = []
    for start, end in runs:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    merged.sort(key=lambda x: x[1] - x[0], reverse=True)
    return [{"start": s, "end": e, "length": e - s} for s, e in merged[:limit]]


def check_derivative(source, report, forbid="", min_length=12):
    """核心检查逻辑，返回结果字典（便于测试与复用）"""
    source_norm, _ = normalize_with_map(source)
    report_norm, report_map = normalize_with_map(report)

    overlaps = longest_overlaps(source_norm, report_norm, min_length)
    violations = []
    for run in overlaps:
        raw_start = report_map[run["start"]]
        raw_end = report_map[run["end"] - 1] + 1
        snippet = report[raw_start:raw_end]
        run["snippet"] = snippet[:60]
        violations.append(f"连续重合 {run['length']} 字：{run['snippet'][:40]}")

    forbid_hits = []
    for name in (n.strip() for n in forbid.split(",") if n.strip()):
        if name in report:
            count = report.count(name)
            forbid_hits.append({"name": name, "count": count})
            violations.append(f"报告中出现原作专有名词「{name}」×{count}")

    titles = []
    for line in source.splitlines():
        m = CHAPTER_TITLE.match(line)
        if m:
            title = m.group(1).strip()
            if len(title) >= 4 and title in report:
                titles.append(title)
    for title in sorted(set(titles)):
        violations.append(f"直接复用原作章节标题「{title}」")

    return {
        "minLength": min_length,
        "overlaps": overlaps,
        "forbiddenHits": forbid_hits,
        "reusedTitles": sorted(set(titles)),
        "passed": not violations,
        "violations": violations,
    }


def main():
    parser = argparse.ArgumentParser(description="拆书报告原创性检查")
    parser.add_argument("--source", "-s", required=True, help="原作文件或章节目录")
    parser.add_argument("--output", "-o", required=True, help="拆书/仿写报告文件")
    parser.add_argument("--forbid", default="", help="禁止出现的原作专有名词，逗号分隔")
    parser.add_argument("--min-length", type=int, default=12, help="允许的最长连续重合字数（默认12）")
    parser.add_argument("--report-dir", default=".sumeru/deconstruct", help="检查结果输出目录")
    args = parser.parse_args()

    if not Path(args.source).exists():
        print(f"❌ 原作路径不存在：{args.source}")
        return 2
    if not Path(args.output).exists():
        print(f"❌ 报告文件不存在：{args.output}")
        return 2

    source = read_source(args.source)
    report = Path(args.output).read_text(encoding="utf-8", errors="ignore")
    result = check_derivative(source, report, args.forbid, args.min_length)
    result["source"] = args.source
    result["output"] = args.output
    overlaps = result["overlaps"]
    forbid_hits = result["forbiddenHits"]
    titles = result["reusedTitles"]
    violations = result["violations"]

    out = Path(args.report_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "derivative-check.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 拆书报告原创性检查",
        "",
        "| 指标 | 数值 |",
        "|------|------|",
        f"| 最长连续重合 | {overlaps[0]['length'] if overlaps else 0} 字 |",
        f"| 重合片段数 | {len(overlaps)} |",
        f"| 禁用名词命中 | {len(forbid_hits)} |",
        f"| 复用章节标题 | {len(set(titles))} |",
        f"| 结论 | {'✅ 通过' if not violations else '❌ 未通过'} |",
        "",
    ]
    if violations:
        lines += ["## 违规项", ""] + [f"- {v}" for v in violations] + [""]
    else:
        lines += ["未发现超阈值原文复制。", ""]
    (out / "derivative-check.md").write_text("\n".join(lines), encoding="utf-8")

    for v in violations:
        print(f"❌ {v}")
    print(f"{'✅ 通过' if not violations else '❌ 未通过'}：最长重合 "
          f"{overlaps[0]['length'] if overlaps else 0} 字")
    print(f"📝 报告：{out / 'derivative-check.md'}")
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
