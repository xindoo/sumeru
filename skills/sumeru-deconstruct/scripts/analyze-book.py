#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拆书结构分析工具（sumeru-deconstruct）

只做机械统计：章节切分、字数、对话占比、段落长度、句长、章首/章末钩子类型、
POV 倾向、高频重复短语。定性结论（爽点、人物功能位、伏笔）由模型基于数据完成。

用法：
  # 分析整本书（txt/md 单文件，按「第X章」切分）
  python3 skills/sumeru-deconstruct/scripts/analyze-book.py --file 参考书.txt

  # 分析已拆分的章节目录
  python3 skills/sumeru-deconstruct/scripts/analyze-book.py --chapters reference/chapters

  # 指定输出目录
  python3 skills/sumeru-deconstruct/scripts/analyze-book.py --file 参考书.txt --out .sumeru/deconstruct

退出码：0 成功 / 1 输入错误 / 2 参数错误
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

CHAPTER_TITLE = re.compile(r"^\s*(第[0-9零〇一二三四五六七八九十百千万两]+章[^\n]{0,40})$")
DIALOGUE = re.compile(r"“[^”]*”|「[^」]*」|『[^』]*』")
SENTENCE = re.compile(r"[^。！？…\n]+[。！？…]?")
CJK = re.compile(r"[\u4e00-\u9fa5]")

OPENING_DIALOGUE = re.compile(r"^\s*[“「『\"]")
OPENING_SCENE = re.compile(r"(天|日|夜|雨|风|雪|晨|黄昏|清晨|傍晚|城|山|街|屋|房间|空气|阳光|月光)")
ENDING_QUESTION = re.compile(r"[？?]\s*[”」』\"]?\s*$")
ENDING_EXCLAIM = re.compile(r"[！!]\s*[”」』\"]?\s*$")
ENDING_DIALOGUE = re.compile(r"[”」』\"]\s*$")
SUSPENSE_WORDS = [
    "突然", "忽然", "竟然", "没想到", "却是", "只见", "就在这时", "门外",
    "电话", "消息", "原来", "怎么", "为什么", "不可能", "不对劲", "身后",
]
FIRST_PERSON = re.compile(r"我(?!们)")
THIRD_PERSON = re.compile(r"他|她")


def count_words(text):
    return len(CJK.findall(text)) + len(re.findall(r"[a-zA-Z]+", text))


def split_chapters_from_text(text):
    """按「第X章」标题行切分；没有标题则整篇作为一章"""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    chapters, current, title = [], [], "开篇"
    for line in lines:
        m = CHAPTER_TITLE.match(line)
        if m:
            if current and any(l.strip() for l in current):
                chapters.append({"title": title, "body": "\n".join(current).strip()})
            title, current = m.group(1).strip(), []
        else:
            current.append(line)
    if current and any(l.strip() for l in current):
        chapters.append({"title": title, "body": "\n".join(current).strip()})
    return chapters


def split_chapters_from_dir(directory):
    files = []
    for file in Path(directory).iterdir():
        if file.suffix.lower() in {".txt", ".md"} and file.is_file():
            nums = re.findall(r"\d+", file.stem)
            files.append((int(nums[0]) if nums else 10**9, file))
    files.sort()
    chapters = []
    for _, file in files:
        text = file.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        title = lines[0].strip() if lines else file.stem
        body = "\n".join(lines[1:]).strip() if lines else ""
        chapters.append({"title": title or file.stem, "body": body})
    return chapters


def paragraph_stats(body):
    paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    if len(paras) <= 1:
        # 很多 txt 用单换行分段，没有空行
        paras = [p.strip() for p in body.splitlines() if p.strip()]
    lengths = [count_words(p) for p in paras]
    if not lengths:
        return {"count": 0, "avg": 0, "max": 0, "over300": 0}
    return {
        "count": len(lengths),
        "avg": round(sum(lengths) / len(lengths), 1),
        "max": max(lengths),
        "over300": sum(1 for n in lengths if n > 300),
    }


def analyze_chapter(title, body, index):
    words = count_words(body)
    dialogue_chars = sum(len(m) for m in DIALOGUE.findall(body))
    sentences = [s.strip() for s in SENTENCE.findall(body) if s.strip()]
    sent_lengths = [count_words(s) for s in sentences] or [0]
    opening = body.strip()[:120]
    ending = body.strip()[-120:]
    first = len(FIRST_PERSON.findall(body))
    third = len(THIRD_PERSON.findall(body))
    pov = "第一人称" if first > third * 1.5 else ("第三人称" if third > first * 1.5 else "混合/不确定")

    opening_type = "描写开头"
    if OPENING_DIALOGUE.match(opening):
        opening_type = "对话开头"
    elif re.search(r"[他她我]", opening[:20]) and not OPENING_SCENE.search(opening[:40]):
        opening_type = "叙述开头"

    ending_type = "陈述收尾"
    if ENDING_QUESTION.search(ending):
        ending_type = "疑问收尾"
    elif ENDING_DIALOGUE.search(ending):
        ending_type = "对话收尾"
    elif ENDING_EXCLAIM.search(ending):
        ending_type = "感叹收尾"
    if any(word in ending for word in SUSPENSE_WORDS):
        ending_type = "悬念收尾"

    return {
        "index": index,
        "title": title,
        "words": words,
        "dialogueRatio": round(min(1.0, dialogue_chars / max(1, words)), 3),
        "paragraphs": paragraph_stats(body),
        "sentences": {
            "count": len(sentences),
            "avgWords": round(sum(sent_lengths) / max(1, len(sent_lengths)), 1),
            "maxWords": max(sent_lengths),
        },
        "pov": pov,
        "openingType": opening_type,
        "endingType": ending_type,
        "suspenseHits": sum(ending.count(w) for w in SUSPENSE_WORDS),
    }


def repeated_phrases(chapters, n=5, top=15, max_chars=1_000_000):
    counter = Counter()
    first_seen = {}
    cleaned = []
    budget = max_chars
    for idx, ch in enumerate(chapters, 1):
        text = re.sub(r"\s+", "", ch["body"])
        if budget <= 0:
            break
        text = text[:budget]
        budget -= len(text)
        cleaned.append((idx, text))
    for idx, text in cleaned:
        for i in range(len(text) - n + 1):
            gram = text[i:i + n]
            if CJK.search(gram) is None:
                continue
            counter[gram] += 1
            first_seen.setdefault(gram, idx)
    results = []
    for gram, count in counter.most_common(200):
        if count < 3 or gram in {"第一", "第二", "第三"}:
            continue
        results.append({"phrase": gram, "count": count, "firstChapter": first_seen[gram]})
        if len(results) >= top:
            break
    return results


def summarize(chapters):
    total_words = sum(c["words"] for c in chapters)
    lengths = [c["words"] for c in chapters]
    ending_counter = Counter(c["endingType"] for c in chapters)
    opening_counter = Counter(c["openingType"] for c in chapters)
    dialogue_avg = round(sum(c["dialogueRatio"] for c in chapters) / max(1, len(chapters)), 3)
    return {
        "chapterCount": len(chapters),
        "totalWords": total_words,
        "averageWords": round(total_words / max(1, len(chapters)), 1),
        "minWords": min(lengths) if lengths else 0,
        "maxWords": max(lengths) if lengths else 0,
        "averageDialogueRatio": dialogue_avg,
        "endingTypes": dict(ending_counter),
        "openingTypes": dict(opening_counter),
        "povDistribution": dict(Counter(c["pov"] for c in chapters)),
    }


def render_markdown(result):
    s = result["summary"]
    lines = [
        "# 拆书结构数据报告",
        "",
        f"> 数据来源：{result['meta']['source']}",
        "> 本报告只包含统计值与结构特征，不包含原文段落，不能用于替代原作。",
        "",
        "## 一、总体数据",
        "",
        "| 指标 | 数值 |",
        "|------|------|",
        f"| 章节数 | {s['chapterCount']} |",
        f"| 总字数 | {s['totalWords']:,} |",
        f"| 平均单章 | {s['averageWords']:,} |",
        f"| 最短/最长 | {s['minWords']:,} / {s['maxWords']:,} |",
        f"| 平均对话占比 | {s['averageDialogueRatio']:.1%} |",
        "",
        "### 章末钩子类型分布",
        "",
        "| 类型 | 数量 |",
        "|------|------|",
    ]
    for key, value in sorted(s["endingTypes"].items(), key=lambda x: -x[1]):
        lines.append(f"| {key} | {value} |")
    lines += ["", "### 章首类型分布", "", "| 类型 | 数量 |", "|------|------|"]
    for key, value in sorted(s["openingTypes"].items(), key=lambda x: -x[1]):
        lines.append(f"| {key} | {value} |")
    lines += ["", "### 视角分布", "", "| 视角 | 数量 |", "|------|------|"]
    for key, value in sorted(s["povDistribution"].items(), key=lambda x: -x[1]):
        lines.append(f"| {key} | {value} |")

    lines += ["", "## 二、逐章数据", "",
              "| 章 | 字数 | 对话占比 | 段落数 | 平均段长 | 平均句长 | 章首 | 章末 |",
              "|----|------|----------|--------|----------|----------|------|------|"]
    for c in result["chapters"]:
        lines.append(
            f"| {c['index']} | {c['words']:,} | {c['dialogueRatio']:.0%} | "
            f"{c['paragraphs']['count']} | {c['paragraphs']['avg']} | {c['sentences']['avgWords']} | "
            f"{c['openingType']} | {c['endingType']} |"
        )

    if result["repetitions"]:
        lines += ["", "## 三、高频重复短语（候选）", "",
                  "> 用于识别作者口头禅或注水表达。高频不等于错误，需结合上下文判断。", "",
                  "| 短语 | 次数 | 首次出现章 |", "|------|------|------------|"]
        for r in result["repetitions"]:
            lines.append(f"| {r['phrase']} | {r['count']} | {r['firstChapter']} |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="拆书结构分析")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", "-f", help="单文件 txt/md")
    src.add_argument("--chapters", "-c", help="章节目录")
    parser.add_argument("--out", "-o", default=".sumeru/deconstruct", help="输出目录")
    parser.add_argument("--markdown", default="拆书数据报告.md", help="用户可见报告文件名（相对当前目录）")
    args = parser.parse_args()

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"❌ 文件不存在：{args.file}")
            return 1
        raw_chapters = split_chapters_from_text(path.read_text(encoding="utf-8", errors="ignore"))
        source = path.name
    else:
        path = Path(args.chapters)
        if not path.exists():
            print(f"❌ 目录不存在：{args.chapters}")
            return 1
        raw_chapters = split_chapters_from_dir(path)
        source = str(path)

    if not raw_chapters:
        print("❌ 未解析到任何章节内容")
        return 1

    chapters = [analyze_chapter(ch["title"], ch["body"], i + 1)
                for i, ch in enumerate(raw_chapters)]
    result = {
        "meta": {"source": source, "chapterSplit": "第X章" if args.file else "目录文件"},
        "summary": summarize(chapters),
        "chapters": chapters,
        "repetitions": repeated_phrases(raw_chapters),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "structure.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.markdown).write_text(render_markdown(result), encoding="utf-8")

    s = result["summary"]
    print(f"📖 解析 {s['chapterCount']} 章 / {s['totalWords']:,} 字")
    print(f"   平均单章 {s['averageWords']:,} 字，对话占比 {s['averageDialogueRatio']:.1%}")
    print(f"   章末钩子：{s['endingTypes']}")
    print(f"📝 数据：{out / 'structure.json'}")
    print(f"📝 报告：{args.markdown}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
