#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完稿构建与导出工具（sumeru-finalize）

功能：
  1. 结构检查：命名、缺章、空章、重复段落、占位符
  2. 合规扫描：命中 ip-blocklist.md 中的禁用名称则报错
  3. 版式规范化：标点、空行、段落缩进
  4. 多平台导出：md / txt / html / epub，多平台一次生成
  5. 统计报告：总字数、章节字数、异常项

用法：
  python3 skills/sumeru-finalize/scripts/build.py --check-only
  python3 skills/sumeru-finalize/scripts/build.py --platform all --format md,txt,html,epub --title "书名"
  python3 skills/sumeru-finalize/scripts/build.py --platform fanqie --format txt --strict

退出码：0 通过 / 1 检查失败 / 2 参数错误
"""

import argparse
import hashlib
import html
import json
import re
import sys
import zipfile
from pathlib import Path

DEFAULT_PLATFORMS = {
    "qidian": {
        "label": "起点", "indent": "\u3000\u3000", "blank_between": True,
        "word_range": (3000, 5000), "quote": "“”",
    },
    "fanqie": {
        "label": "番茄", "indent": "", "blank_between": True,
        "word_range": (2000, 3000), "quote": "“”",
    },
    "jjwxc": {
        "label": "晋江", "indent": "\u3000\u3000", "blank_between": True,
        "word_range": (2500, 4000), "quote": "“”",
    },
    "zongheng": {
        "label": "纵横", "indent": "\u3000\u3000", "blank_between": True,
        "word_range": (3000, 6000), "quote": "“”",
    },
    "17k": {
        "label": "17K", "indent": "\u3000\u3000", "blank_between": True,
        "word_range": (2000, 4000), "quote": "“”",
    },
}

CHAPTER_NAME = re.compile(r"^(\d{3,4})-(.+)\.md$")
PLACEHOLDER = re.compile(r"(TODO|待补充|待完善|XXX|\[占位\])")
ASCII_PUNCT = re.compile(r"[\u4e00-\u9fa5][,.!?;:]|[,.!?;:][\u4e00-\u9fa5]")
REPEAT_CHAR = re.compile(r"(的的|了了|是是|在在|他他|她她|我我)")

FALLBACK_BLOCKLIST = {
    "萧炎", "林动", "叶凡", "石昊", "唐三", "韩立", "陈平安",
    "李逍遥", "赵灵儿", "萧薰儿", "美杜莎", "小医仙",
    "王语嫣", "桑稚", "温以凡", "秦苒", "祁醉", "桑延",
    "冷锋", "龙百川", "赵蒙生", "周卫国", "叶寸心",
    "莱戈拉斯", "索林", "二向箔", "赛博坦星", "潘多拉星",
}


# ---------------------------------------------------------------- 基础工具

def count_words(text):
    """中文按字、英文按词；标点不计入（与平台口径一致）"""
    hanzi = len(re.findall(r"[\u4e00-\u9fa5]", text))
    english = len(re.findall(r"[a-zA-Z]+", text))
    return hanzi + english


def load_blocklist(path):
    """从 ip-blocklist.md 的「绝对禁用清单」小节提取名称集合"""
    names = set(FALLBACK_BLOCKLIST)
    p = Path(path) if path else None
    if not p or not p.exists():
        return names
    text = p.read_text(encoding="utf-8")
    m = re.search(r"## 二、绝对禁用清单(.*?)(?=\n## )", text, re.S)
    if not m:
        return names
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line.startswith("**") or "：" not in line:
            continue
        payload = line.split("：", 1)[1]
        for token in payload.split("、"):
            token = re.sub(r"（[^）]*）|\([^)]*\)", "", token).strip(" 　*`")
            if 2 <= len(token) <= 12:
                names.add(token)
    return names


def collect_chapters(chapters_dir):
    chapters = []
    for file in sorted(Path(chapters_dir).glob("*.md")):
        m = CHAPTER_NAME.match(file.name)
        if not m:
            continue
        chapters.append({
            "file": file,
            "number": int(m.group(1)),
            "title": m.group(2).strip(),
        })
    chapters.sort(key=lambda x: x["number"])
    return chapters


def normalize_body(text):
    """去掉标题行、统一空行、清理行尾空白"""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    # 移除文件内自带的标题行（第X章 ...），标题由导出版式统一生成
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and re.match(r"^\s*第\s*\d+\s*章", lines[0]):
        lines.pop(0)
    cleaned = [line.rstrip() for line in lines]
    text = "\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def paragraphs(body):
    return [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]


def apply_replacements(text, rules):
    """rules: ['旧词=>新词', ...]，返回 (新文本, 替换次数)"""
    count = 0
    for rule in rules or []:
        if "=>" not in rule:
            continue
        old, new = rule.split("=>", 1)
        if not old:
            continue
        count += text.count(old)
        text = text.replace(old, new)
    return text, count


def auto_paragraph(body, max_len=300):
    """把超长段落按句末标点拆开，避免移动端大段文字"""
    if not max_len or max_len <= 0:
        return body
    result = []
    for para in paragraphs(body):
        if len(para) <= max_len:
            result.append(para)
            continue
        buf = ""
        for sentence in re.split(r"(?<=[。！？…])", para):
            if not sentence:
                continue
            if len(buf) + len(sentence) > max_len and buf:
                result.append(buf)
                buf = sentence
            else:
                buf += sentence
        if buf:
            result.append(buf)
    return "\n\n".join(result)


def format_plain(chapter, profile):
    head = f"第{chapter['number']}章 {chapter['title']}"
    indent = profile["indent"]
    blocks = []
    for para in paragraphs(chapter["body"]):
        para = re.sub(r"[ \t]+", " ", para).strip()
        for line in para.split("\n"):
            line = line.strip()
            if line:
                blocks.append(indent + line)
    sep = "\n\n" if profile["blank_between"] else "\n"
    return head + "\n\n" + sep.join(blocks) + "\n"


def format_html(chapter, profile):
    head = html.escape(f"第{chapter['number']}章 {chapter['title']}")
    body = "\n".join(f"<p>{html.escape(p.strip())}</p>" for p in paragraphs(chapter["body"]))
    return f'<h2 id="ch{chapter["number"]}">{head}</h2>\n{body}\n'


# ---------------------------------------------------------------- 检查

def find_invalid_files(chapters_dir):
    """找出目录中不符合命名规范的 .md（排除进度报告）"""
    invalid = []
    for file in sorted(Path(chapters_dir).glob("*.md")):
        if CHAPTER_NAME.match(file.name):
            continue
        if file.name.upper().startswith("WRITE_PROGRESS"):
            continue
        invalid.append(file.name)
    return invalid


def check_chapters(chapters, blocklist, strict=False, invalid_files=None):
    errors, warnings = [], []
    for name in invalid_files or []:
        errors.append(f"{name}：命名不符合 {{三位章节号}}-{{标题}}.md")
    if not chapters:
        return ["未找到符合 {章节号}-{标题}.md 的章节文件"] + errors, [], {}

    numbers = [c["number"] for c in chapters]
    dup = sorted({n for n in numbers if numbers.count(n) > 1})
    if dup:
        errors.append(f"章节号重复：{dup}")
    missing = [n for n in range(1, max(numbers) + 1) if n not in set(numbers)]
    if missing:
        errors.append(f"章节号缺失：{missing[:20]}{'...' if len(missing) > 20 else ''}")

    total_words = 0
    rows = []
    for ch in chapters:
        text = ch["file"].read_text(encoding="utf-8", errors="ignore")
        body = normalize_body(text)
        words = count_words(body)
        total_words += words
        row = {"number": ch["number"], "title": ch["title"], "words": words,
               "file": ch["file"].name}

        if PLACEHOLDER.search(text):
            errors.append(f"{ch['file'].name}：残留占位符")
        if words < 500:
            errors.append(f"{ch['file'].name}：仅 {words} 字，疑似空章")
        if ASCII_PUNCT.search(body):
            warnings.append(f"{ch['file'].name}：中英文标点混用")
        if REPEAT_CHAR.search(body):
            warnings.append(f"{ch['file'].name}：疑似叠字错误")

        # 合规名称扫描
        hits = sorted({name for name in blocklist if name in body})
        if hits:
            errors.append(f"{ch['file'].name}：命中禁用名称 {hits}")

        # 重复段落（同一章内 40 字以上完全重复）
        seen, dup_paras = set(), set()
        for para in paragraphs(body):
            if len(para) >= 40:
                if para in seen:
                    dup_paras.add(para[:20])
                seen.add(para)
        if dup_paras:
            warnings.append(f"{ch['file'].name}：存在重复段落 {list(dup_paras)[:2]}")

        rows.append(row)

    # 全书中重复段落（跨章复制粘贴）
    para_owner = {}
    for ch in chapters:
        for para in set(paragraphs(normalize_body(ch["file"].read_text(encoding="utf-8", errors="ignore")))):
            if len(para) >= 60:
                para_owner.setdefault(para, []).append(ch["number"])
    cross = {p[:20]: nums for p, nums in para_owner.items() if len(nums) > 1}
    if cross:
        warnings.append(f"跨章重复段落 {len(cross)} 处，可能是复制粘贴：{list(cross.items())[:3]}")

    stats = {
        "totalChapters": len(chapters),
        "totalWords": total_words,
        "averageWords": round(total_words / len(chapters), 1),
        "minWords": min(r["words"] for r in rows),
        "maxWords": max(r["words"] for r in rows),
        "chapters": rows,
    }
    if strict:
        errors.extend(f"[strict] {w}" for w in warnings)
    return errors, warnings, stats


# ---------------------------------------------------------------- 导出

def write_epub(chapters, profile, out_file, title, author):
    uid = "urn:uuid:" + hashlib.md5(f"{title}{author}".encode()).hexdigest()
    chapter_files = []
    for ch in chapters:
        name = f"chapter-{ch['number']:03d}.xhtml"
        chapter_files.append((name, ch))
        xhtml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" lang="zh-CN">\n'
            f"<head><title>第{ch['number']}章 {html.escape(ch['title'])}</title>"
            '<link rel="stylesheet" href="style.css"/></head>\n'
            f"<body>{format_html(ch, profile)}</body>\n</html>\n"
        )
        (out_file.parent / name).write_text(xhtml, encoding="utf-8")

    nav_items = "\n".join(
        f'<li><a href="{name}">第{ch["number"]}章 {html.escape(ch["title"])}</a></li>'
        for name, ch in chapter_files
    )
    nav = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN">\n'
        f"<head><title>{html.escape(title)}</title></head><body>"
        f'<nav epub:type="toc" id="toc"><h1>{html.escape(title)}</h1><ol>{nav_items}</ol></nav>'
        "</body></html>\n"
    )
    manifest = "\n".join(
        f'<item id="ch{n}" href="{name}" media-type="application/xhtml+xml"/>'
        for name, ch in chapter_files for n in [ch["number"]]
    )
    spine = "\n".join(f'<itemref idref="ch{ch["number"]}"/>' for _, ch in chapter_files)
    opf = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">\n'
        f'<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f'<dc:identifier id="bookid">{uid}</dc:identifier>'
        f"<dc:title>{html.escape(title)}</dc:title>"
        f"<dc:language>zh-CN</dc:language>"
        f"<dc:creator>{html.escape(author)}</dc:creator>"
        "</metadata>\n"
        f'<manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
        f'<item id="css" href="style.css" media-type="text/css"/>{manifest}</manifest>\n'
        f"<spine>{spine}</spine>\n</package>\n"
    )
    (out_file.parent / "nav.xhtml").write_text(nav, encoding="utf-8")
    (out_file.parent / "content.opf").write_text(opf, encoding="utf-8")
    (out_file.parent / "style.css").write_text(
        "body{line-height:1.8;} p{text-indent:2em;margin:0.6em 0;} h2{text-align:center;margin:1.5em 0;}",
        encoding="utf-8",
    )

    container = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        '<rootfiles><rootfile full-path="OEBPS/content.opf" '
        'media-type="application/oebps-package+xml"/></rootfiles></container>\n'
    )

    tmp = out_file.parent / "_epub_tmp"
    if tmp.exists():
        import shutil
        shutil.rmtree(tmp)
    (tmp / "META-INF").mkdir(parents=True)
    (tmp / "OEBPS").mkdir(parents=True)
    (tmp / "META-INF" / "container.xml").write_text(container, encoding="utf-8")
    for filename in ("content.opf", "nav.xhtml", "style.css"):
        (tmp / "OEBPS" / filename).write_text(
            (out_file.parent / filename).read_text(encoding="utf-8"), encoding="utf-8")
    for name, _ in chapter_files:
        (tmp / "OEBPS" / name).write_text(
            (out_file.parent / name).read_text(encoding="utf-8"), encoding="utf-8")

    with zipfile.ZipFile(out_file, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.write(tmp / "META-INF" / "container.xml", "META-INF/container.xml")
        for file in sorted((tmp / "OEBPS").rglob("*")):
            if file.is_file():
                zf.write(file, str(file.relative_to(tmp)))

    import shutil
    shutil.rmtree(tmp)
    for stray in ("content.opf", "nav.xhtml", "style.css"):
        (out_file.parent / stray).unlink(missing_ok=True)
    for name, _ in chapter_files:
        (out_file.parent / name).unlink(missing_ok=True)


def export_platform(chapters, key, profile, out_root, formats, title, author,
                    replacements=None, max_paragraph=None):
    out_dir = Path(out_root) / key
    out_dir.mkdir(parents=True, exist_ok=True)

    prepared = []
    total_replaced = 0
    for ch in chapters:
        ch = dict(ch)
        raw = ch["file"].read_text(encoding="utf-8", errors="ignore")
        raw, replaced = apply_replacements(raw, replacements)
        total_replaced += replaced
        body = normalize_body(raw)
        if max_paragraph:
            body = auto_paragraph(body, max_paragraph)
        ch["body"] = body
        prepared.append(ch)

    book_title = title or (prepared[0]["title"] if prepared else "未命名作品")
    full_md = [f"# {book_title}\n"]
    full_txt = [book_title, ""]
    html_parts = []
    for ch in prepared:
        full_md.append(format_plain(ch, profile))
        full_txt.append(format_plain(ch, profile))
        html_parts.append(format_html(ch, profile))

    if "md" in formats:
        (out_dir / "full.md").write_text("\n".join(full_md), encoding="utf-8")
    if "txt" in formats:
        (out_dir / "full.txt").write_text("\n".join(full_txt), encoding="utf-8")
    if "html" in formats:
        doc = (
            '<!DOCTYPE html>\n<html lang="zh-CN"><head><meta charset="utf-8"/>'
            f"<title>{html.escape(book_title)}</title>"
            "<style>body{max-width:42em;margin:2em auto;line-height:1.9;font-family:serif;"
            "padding:0 1em;}h2{text-align:center;margin:2em 0 1em;}p{text-indent:2em;margin:.6em 0;}"
            "</style></head><body>\n"
            f"<h1>{html.escape(book_title)}</h1>\n" + "\n".join(html_parts) + "</body></html>\n"
        )
        (out_dir / "full.html").write_text(doc, encoding="utf-8")
    if "epub" in formats:
        write_epub(prepared, profile, out_dir / "book.epub", book_title, author)

    # 平台分章版本
    per_dir = out_dir / "chapters"
    per_dir.mkdir(exist_ok=True)
    for ch in prepared:
        (per_dir / f"{ch['number']:03d}-{ch['title']}.txt").write_text(
            format_plain(ch, profile), encoding="utf-8")

    return out_dir


# ---------------------------------------------------------------- 报告

def write_report(stats, errors, warnings, platform_results, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "stats": stats,
        "exports": platform_results,
        "errors": errors,
        "warnings": warnings,
        "passed": not errors,
    }
    (out / "stats.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 完稿校验报告", "",
        "| 指标 | 数值 |", "|------|------|",
        f"| 章节数 | {stats['totalChapters']} |",
        f"| 总字数 | {stats['totalWords']:,} |",
        f"| 平均字数 | {stats['averageWords']:,} |",
        f"| 最短/最长 | {stats['minWords']:,} / {stats['maxWords']:,} |",
        f"| 错误 / 警告 | {len(errors)} / {len(warnings)} |", "",
    ]
    if platform_results:
        lines += ["## 导出结果", "", "| 平台 | 目录 |", "|------|------|"]
        lines += [f"| {p['label']} | {p['path']} |" for p in platform_results]
        lines += [""]
    if errors:
        lines += ["## ❌ 错误", ""] + [f"- {e}" for e in errors] + [""]
    if warnings:
        lines += ["## ⚠️ 警告", ""] + [f"- {w}" for w in warnings] + [""]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    # 用户可见的完稿报告
    Path("完稿校验报告.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="完稿构建与多平台导出")
    parser.add_argument("--chapters", "-c", default="chapters", help="章节目录")
    parser.add_argument("--out", default="publish", help="导出根目录")
    parser.add_argument("--platform", default="all",
                        help="all 或逗号分隔：" + ",".join(DEFAULT_PLATFORMS))
    parser.add_argument("--format", default="md,txt,html,epub",
                        help="md,txt,html,epub 的组合")
    parser.add_argument("--title", default="", help="书名")
    parser.add_argument("--author", default="", help="作者")
    parser.add_argument("--blocklist", default=None,
                        help="IP 黑名单文件（默认自动定位 skills/sumeru-outline/references/ip-blocklist.md）")
    parser.add_argument("--allow", default="",
                        help="白名单，逗号分隔；用于放行确认无风险的误报名称")
    parser.add_argument("--report-dir", default=".sumeru/finalize")
    parser.add_argument("--replace", action="append", default=[], metavar="旧=>新",
                        help="批量替换，可重复传入，例如 --replace 张三=>李玄")
    parser.add_argument("--max-paragraph", type=int, default=0,
                        help="自动分段阈值（字数），0 表示不启用")
    parser.add_argument("--check-only", action="store_true", help="只检查不导出")
    parser.add_argument("--strict", action="store_true", help="警告也视为失败")
    args = parser.parse_args()

    if not Path(args.chapters).exists():
        print(f"❌ 章节目录不存在：{args.chapters}")
        return 2

    chapters = collect_chapters(args.chapters)
    blocklist_path = args.blocklist or str(
        Path(__file__).resolve().parents[2] / "sumeru-outline/references/ip-blocklist.md"
    )
    blocklist = load_blocklist(blocklist_path)
    for name in (n.strip() for n in args.allow.split(",") if n.strip()):
        blocklist.discard(name)
    errors, warnings, stats = check_chapters(
        chapters, blocklist, args.strict, find_invalid_files(args.chapters)
    )

    print(f"📚 {stats.get('totalChapters', 0)} 章 / {stats.get('totalWords', 0):,} 字")
    for w in warnings:
        print(f"⚠️  {w}")
    for e in errors:
        print(f"❌ {e}")

    platform_results = []
    if not args.check_only and not errors:
        keys = list(DEFAULT_PLATFORMS) if args.platform == "all" else \
            [k.strip() for k in args.platform.split(",") if k.strip()]
        unknown = [k for k in keys if k not in DEFAULT_PLATFORMS]
        if unknown:
            print(f"❌ 未知平台：{unknown}，可选：{list(DEFAULT_PLATFORMS)}")
            return 2
        formats = {f.strip() for f in args.format.split(",") if f.strip()}
        for key in keys:
            out_dir = export_platform(
                chapters, key, DEFAULT_PLATFORMS[key], args.out,
                formats, args.title, args.author,
                replacements=args.replace, max_paragraph=args.max_paragraph,
            )
            platform_results.append({"platform": key, "label": DEFAULT_PLATFORMS[key]["label"],
                                     "path": str(out_dir)})
            print(f"✅ 导出 {DEFAULT_PLATFORMS[key]['label']}：{out_dir}")

    write_report(stats, errors, warnings, platform_results, args.report_dir)
    print(f"📝 报告：{Path(args.report_dir) / 'report.md'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
