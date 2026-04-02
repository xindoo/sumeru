#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网文章节字数统计工具
功能：精确统计各章节字数，识别过长/过短章节，生成统计报告
输出：自动保存到 .sumeru/review/word-count-report.json 和 .sumeru/review/word-count-report.md
"""

import os
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

# 配置参数
DEFAULT_CHAPTER_PATTERN = r"chapter-\d+\.md|第\d+章.*\.md|\d+\.md"
DEFAULT_WORD_RANGE = (2000, 3000)  # 默认理想章节字数范围：2000-3000字
WARNING_RANGE = (1500, 3500)        # 警告范围：小于1500或大于3500字触发警告


def count_words(text: str) -> Tuple[int, int, int, int]:
    """
    精确统计文本字数
    返回：(总字数, 汉字数, 英文单词数, 标点符号数)
    """
    # 统计汉字
    hanzi_pattern = re.compile(r'[\u4e00-\u9fa5]')
    hanzi_count = len(hanzi_pattern.findall(text))

    # 统计英文单词（连续英文字母序列）
    english_pattern = re.compile(r'[a-zA-Z]+')
    english_words = english_pattern.findall(text)
    english_count = len(english_words)

    # 统计标点符号（全角+半角）
    punctuation_pattern = re.compile(r'[^\w\s]|[_]')
    punctuation_count = len(punctuation_pattern.findall(text))

    # 总字数计算规则：汉字算1字，英文单词算1字，标点不算入正文字数统计
    total_words = hanzi_count + english_count

    return total_words, hanzi_count, english_count, punctuation_count


def scan_chapters(chapters_dir: str, pattern: str = DEFAULT_CHAPTER_PATTERN) -> List[Path]:
    """扫描目录下的所有章节文件"""
    chapter_files = []
    path = Path(chapters_dir)

    if not path.exists():
        raise FileNotFoundError(f"章节目录不存在: {chapters_dir}")

    for file in path.iterdir():
        if file.is_file() and re.match(pattern, file.name, re.IGNORECASE):
            chapter_files.append(file)

    # 按章节号排序
    def get_chapter_num(file_path: Path) -> int:
        nums = re.findall(r'\d+', file_path.stem)
        return int(nums[0]) if nums else 0

    chapter_files.sort(key=get_chapter_num)
    return chapter_files


def analyze_chapters(chapter_files: List[Path],
                    ideal_range: Tuple[int, int] = DEFAULT_WORD_RANGE,
                    warning_range: Tuple[int, int] = WARNING_RANGE) -> Dict:
    """分析所有章节的字数情况"""
    chapters_data = []
    total_words = 0
    min_words = float('inf')
    max_words = 0
    too_short = []
    too_long = []

    for idx, file_path in enumerate(chapter_files, 1):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            words, hanzi, english, punctuation = count_words(content)
            total_words += words

            if words < min_words:
                min_words = words
            if words > max_words:
                max_words = words

            # 判断字数状态
            status = "normal"
            if words < warning_range[0]:
                status = "too_short"
                too_short.append({
                    "chapter": file_path.name,
                    "words": words,
                    "gap": warning_range[0] - words
                })
            elif words > warning_range[1]:
                status = "too_long"
                too_long.append({
                    "chapter": file_path.name,
                    "words": words,
                    "gap": words - warning_range[1]
                })
            elif words < ideal_range[0] or words > ideal_range[1]:
                status = "warning"

            chapters_data.append({
                "chapter_num": idx,
                "file_name": file_path.name,
                "file_path": str(file_path.absolute()),
                "total_words": words,
                "hanzi_count": hanzi,
                "english_count": english,
                "punctuation_count": punctuation,
                "status": status
            })

        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {str(e)}")
            continue

    # 统计汇总
    avg_words = total_words / len(chapter_files) if chapter_files else 0

    return {
        "summary": {
            "total_chapters": len(chapter_files),
            "total_words": total_words,
            "average_words": round(avg_words, 2),
            "min_words": min_words if min_words != float('inf') else 0,
            "max_words": max_words,
            "ideal_range": ideal_range,
            "warning_range": warning_range,
            "too_short_count": len(too_short),
            "too_long_count": len(too_long)
        },
        "too_short_chapters": too_short,
        "too_long_chapters": too_long,
        "chapters": chapters_data
    }


def generate_report(analysis_result: Dict, output_dir: str = ".sumeru/review") -> None:
    """生成统计报告"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 保存JSON格式报告
    json_path = os.path.join(output_dir, "word-count-report.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)

    # 生成Markdown格式报告
    md_path = os.path.join(output_dir, "word-count-report.md")
    summary = analysis_result["summary"]

    md_content = f"""# 章节字数统计报告

## 汇总信息
| 指标 | 数值 |
|------|------|
| 总章节数 | {summary['total_chapters']} |
| 总字数 | {summary['total_words']:,} |
| 平均章节字数 | {summary['average_words']:,} |
| 最短章节字数 | {summary['min_words']:,} |
| 最长章节字数 | {summary['max_words']:,} |
| 理想字数范围 | {summary['ideal_range'][0]:,} - {summary['ideal_range'][1]:,} 字 |
| 警告字数范围 | < {summary['warning_range'][0]:,} 或 > {summary['warning_range'][1]:,} 字 |
| 过短章节数量 | {summary['too_short_count']} |
| 过长章节数量 | {summary['too_long_count']} |

"""

    # 过短章节
    if analysis_result["too_short_chapters"]:
        md_content += "## ⚠️ 过短章节列表\n"
        md_content += "| 章节 | 字数 | 差多少达标 |\n"
        md_content += "|------|------|------------|\n"
        for item in analysis_result["too_short_chapters"]:
            md_content += f"| {item['chapter']} | {item['words']:,} | 少 {item['gap']:,} 字 |\n"
        md_content += "\n"

    # 过长章节
    if analysis_result["too_long_chapters"]:
        md_content += "## ⚠️ 过长章节列表\n"
        md_content += "| 章节 | 字数 | 超出多少 |\n"
        md_content += "|------|------|----------|\n"
        for item in analysis_result["too_long_chapters"]:
            md_content += f"| {item['chapter']} | {item['words']:,} | 多 {item['gap']:,} 字 |\n"
        md_content += "\n"

    # 全部章节明细
    md_content += "## 各章节明细\n"
    md_content += "| 章节号 | 文件名 | 总字数 | 汉字 | 英文 | 标点 | 状态 |\n"
    md_content += "|--------|--------|--------|------|------|------|------|\n"

    status_map = {
        "normal": "✅ 正常",
        "warning": "⚠️ 警告",
        "too_short": "🔴 过短",
        "too_long": "🔴 过长"
    }

    for chap in analysis_result["chapters"]:
        md_content += f"| {chap['chapter_num']} | {chap['file_name']} | {chap['total_words']:,} | {chap['hanzi_count']:,} | {chap['english_count']:,} | {chap['punctuation_count']:,} | {status_map[chap['status']]} |\n"

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"✅ 字数统计报告已生成：")
    print(f"   JSON格式: {json_path}")
    print(f"   Markdown格式: {md_path}")
    print(f"\n📊 统计结果：")
    print(f"   总章节数: {summary['total_chapters']}, 总字数: {summary['total_words']:,}")
    print(f"   平均字数: {summary['average_words']:,}, 最短: {summary['min_words']:,}, 最长: {summary['max_words']:,}")

    if summary['too_short_count'] > 0:
        print(f"⚠️  发现 {summary['too_short_count']} 章过短")
    if summary['too_long_count'] > 0:
        print(f"⚠️  发现 {summary['too_long_count']} 章过长")


def main():
    parser = argparse.ArgumentParser(description='网文章节字数统计工具')
    parser.add_argument('--dir', '-d', default='./chapters/',
                        help='章节文件所在目录 (默认: ./chapters/)')
    parser.add_argument('--pattern', '-p', default=DEFAULT_CHAPTER_PATTERN,
                        help=f'章节文件名匹配正则 (默认: {DEFAULT_CHAPTER_PATTERN})')
    parser.add_argument('--min', type=int, default=DEFAULT_WORD_RANGE[0],
                        help=f'理想最小字数 (默认: {DEFAULT_WORD_RANGE[0]})')
    parser.add_argument('--max', type=int, default=DEFAULT_WORD_RANGE[1],
                        help=f'理想最大字数 (默认: {DEFAULT_WORD_RANGE[1]})')
    parser.add_argument('--warn-min', type=int, default=WARNING_RANGE[0],
                        help=f'警告最小字数 (默认: {WARNING_RANGE[0]})')
    parser.add_argument('--warn-max', type=int, default=WARNING_RANGE[1],
                        help=f'警告最大字数 (默认: {WARNING_RANGE[1]})')
    parser.add_argument('--output', '-o', default='.sumeru/review/',
                        help='报告输出目录 (默认: .sumeru/review/)')

    args = parser.parse_args()

    try:
        chapter_files = scan_chapters(args.dir, args.pattern)
        if not chapter_files:
            print(f"❌ 在目录 {args.dir} 中未找到匹配的章节文件")
            return

        print(f"🔍 找到 {len(chapter_files)} 个章节文件，正在统计...")
        analysis_result = analyze_chapters(
            chapter_files,
            ideal_range=(args.min, args.max),
            warning_range=(args.warn_min, args.warn_max)
        )

        generate_report(analysis_result, args.output)

    except Exception as e:
        print(f"❌ 执行出错: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
