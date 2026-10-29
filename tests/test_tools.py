#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sumeru 工具脚本回归测试（仅依赖标准库）

运行：
  python3 -m unittest discover -s tests -v
"""

import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(rel_path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


plan = load_module("skills/sumeru-outline/scripts/plan-chapters.py", "plan_chapters")
check = load_module("skills/sumeru-write/scripts/check-chapters.py", "check_chapters")
build = load_module("skills/sumeru-finalize/scripts/build.py", "build_finalize")
counter = load_module("skills/sumeru-review/scripts/chapter-word-counter.py", "word_counter")
analyze = load_module("skills/sumeru-deconstruct/scripts/analyze-book.py", "analyze_book")
derivative = load_module("skills/sumeru-deconstruct/scripts/check-derivative.py", "check_derivative")
timeline = load_module("skills/sumeru-review/scripts/validate-timeline.py", "validate_timeline")


def write_chapter(directory, number, title, paragraphs=60, body=None):
    directory.mkdir(parents=True, exist_ok=True)
    content = body if body is not None else "\n\n".join(
        f"第{i}段：陆照野站在临川城头，看云海翻涌。" for i in range(paragraphs)
    )
    (directory / f"{number:03d}-{title}.md").write_text(
        f"第{number}章 {title}\n\n{content}\n", encoding="utf-8"
    )


class PlanChaptersTest(unittest.TestCase):
    def test_chapter_math(self):
        result = plan.build_plan(300_000, 3_000, 3)
        self.assertEqual(result["meta"]["totalChapters"], 100)
        self.assertEqual(result["meta"]["totalWords"], 300_000)
        volumes = result["meta"]["volumes"]
        self.assertEqual(sum(v["chapterCount"] for v in volumes), 100)
        self.assertEqual(volumes[0]["chapterStart"], 1)
        self.assertEqual(volumes[-1]["chapterEnd"], 100)

    def test_invalid_volume_count(self):
        with self.assertRaises(ValueError):
            plan.build_plan(10_000, 3_000, 10)

    def test_skeleton_passes_after_fill(self):
        skeleton = plan.emit_skeleton(plan.build_plan(60_000, 3_000, 2))
        self.assertEqual(len(skeleton["chapters"]), 20)
        # 填充必填字段后应通过校验
        for ch in skeleton["chapters"]:
            ch.update({
                "chapterTitle": f"事件{ch['chapterNumber']}",
                "coreEvent": "推进主线",
                "characters": ["陆照野"],
                "plotProgression": ["铺垫", "冲突", "收束"],
                "coolPoint": "打脸",
                "suspense": "下一章会发生什么",
                "connection": "承上启下",
                "location": "临川城",
                "mood": "紧张",
            })
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "outline.json"
            path.write_text(json.dumps(skeleton, ensure_ascii=False), encoding="utf-8")
            errors, warnings, stats = plan.validate(path)
        self.assertEqual(errors, [])
        self.assertEqual(stats["totalChapters"], 20)

    def test_validate_detects_gap(self):
        skeleton = plan.emit_skeleton(plan.build_plan(30_000, 3_000, 1))
        for ch in skeleton["chapters"]:
            ch.update({
                "chapterTitle": f"事件{ch['chapterNumber']}",
                "coreEvent": "x", "characters": ["a"],
                "plotProgression": ["1", "2", "3"],
                "coolPoint": "x", "suspense": "x",
                "connection": "x", "location": "x", "mood": "x",
            })
        skeleton["chapters"] = skeleton["chapters"][:-1]  # 删掉最后一章
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "outline.json"
            path.write_text(json.dumps(skeleton, ensure_ascii=False), encoding="utf-8")
            errors, _, _ = plan.validate(path)
        self.assertTrue(any("不连续" in e or "卷" in e for e in errors))


class CheckChaptersTest(unittest.TestCase):
    def test_naming_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chapters = root / "chapters"
            write_chapter(chapters, 1, "初见")
            write_chapter(chapters, 3, "打脸")
            (chapters / "第2章-觉醒.md").write_text("错误命名", encoding="utf-8")
            errors, warnings, stats = check.check(chapters, None)
        self.assertEqual(stats["totalChapters"], 2)
        self.assertEqual(stats["invalidNames"], 1)
        self.assertTrue(any("章节号缺失" in e for e in errors))

    def test_outline_title_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chapters = root / "chapters"
            write_chapter(chapters, 1, "初见")
            outline = root / "outline.json"
            outline.write_text(json.dumps({
                "chapters": [{
                    "chapterNumber": 1, "chapterTitle": "初见", "suggestedWords": "3000-4000",
                    "coreEvent": "x", "characters": ["a"], "plotProgression": ["1", "2", "3"],
                    "coolPoint": "x", "suspense": "x", "connection": "x",
                    "location": "x", "pov": "x", "mood": "x", "volumeNumber": 1,
                }]
            }, ensure_ascii=False), encoding="utf-8")
            errors, warnings, _ = check.check(chapters, outline)
            self.assertEqual(errors, [])
            self.assertTrue(any("超出建议区间" in w for w in warnings))


class BuildTest(unittest.TestCase):
    def test_check_flags_blocklist_and_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chapters = root / "chapters"
            write_chapter(chapters, 1, "初见", body="萧炎站在城头。TODO")
            collected = build.collect_chapters(chapters)
            blocklist = build.load_blocklist(ROOT / "skills/sumeru-outline/references/ip-blocklist.md")
            errors, warnings, stats = build.check_chapters(collected, blocklist)
        self.assertTrue(any("禁用名称" in e for e in errors))
        self.assertTrue(any("占位符" in e for e in errors))
        self.assertEqual(stats["totalChapters"], 1)

    def test_check_flags_invalid_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            chapters = Path(tmp) / "chapters"
            write_chapter(chapters, 1, "初见")
            (chapters / "第2章-觉醒.md").write_text("内容", encoding="utf-8")
            collected = build.collect_chapters(chapters)
            invalid = build.find_invalid_files(chapters)
            errors, _, _ = build.check_chapters(collected, set(), invalid_files=invalid)
        self.assertTrue(any("命名不符合" in e for e in errors))

    def test_ascii_punct_ignores_decimal(self):
        self.assertFalse(build.ASCII_PUNCT.search("价格是 3.5 元"))
        self.assertTrue(build.ASCII_PUNCT.search("他说,好"))

    def test_blocklist_loads_from_reference(self):
        names = build.load_blocklist(ROOT / "skills/sumeru-outline/references/ip-blocklist.md")
        self.assertIn("萧炎", names)
        self.assertIn("冷锋", names)
        self.assertGreater(len(names), 20)

    def test_export_all_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chapters = root / "chapters"
            write_chapter(chapters, 1, "初见")
            write_chapter(chapters, 2, "觉醒")
            collected = build.collect_chapters(chapters)
            out = root / "publish"
            build.export_platform(
                collected, "qidian", build.DEFAULT_PLATFORMS["qidian"],
                out, {"md", "txt", "html", "epub"}, "云海纪", "测试",
            )
            target = out / "qidian"
            for name in ("full.md", "full.txt", "full.html", "book.epub"):
                self.assertTrue((target / name).exists(), name)
            with zipfile.ZipFile(target / "book.epub") as zf:
                self.assertEqual(zf.read("mimetype"), b"application/epub+zip")
                self.assertIn("OEBPS/content.opf", zf.namelist())
            text = (target / "full.txt").read_text(encoding="utf-8")
            self.assertIn("第1章 初见", text)
            self.assertIn("\u3000\u3000", text)  # 起点版式首行缩进

    def test_replace_and_auto_paragraph(self):
        body, count = build.apply_replacements("陆照野走了。陆照野回头。", ["陆照野=>江砚舟"])
        self.assertEqual(count, 2)
        self.assertNotIn("陆照野", body)
        long_text = "。".join(["这是一句测试文本"] * 20) + "。"
        out = build.auto_paragraph(long_text, max_len=60)
        self.assertGreater(len(out.split("\n\n")), 1)
        self.assertTrue(all(len(p) <= 120 for p in out.split("\n\n")))


class WordCounterTest(unittest.TestCase):
    def test_count_words(self):
        total, hanzi, english, _ = counter.count_words("你好 world，测试。")
        self.assertEqual(hanzi, 4)
        self.assertEqual(english, 1)
        self.assertEqual(total, 5)


class DeconstructAnalyzeTest(unittest.TestCase):
    def test_split_chapters_from_text(self):
        text = "第1章 初见\n\n正文一。\n\n第2章 觉醒\n\n正文二。"
        chapters = analyze.split_chapters_from_text(text)
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0]["title"], "第1章 初见")
        self.assertIn("正文一", chapters[0]["body"])

    def test_analyze_chapter_fields(self):
        body = "“你来了。”他说。\n\n" + "临川城的风很大。" * 20
        ch = analyze.analyze_chapter("第1章 风起", body, 1)
        self.assertGreater(ch["words"], 0)
        self.assertGreater(ch["dialogueRatio"], 0)
        self.assertIn(ch["openingType"], {"对话开头", "描写开头", "叙述开头"})

    def test_repeated_phrases(self):
        chapters = [{"body": "临川城的风很大。" * 10} for _ in range(2)]
        reps = analyze.repeated_phrases(chapters, n=5, top=5)
        self.assertTrue(reps)
        self.assertGreaterEqual(reps[0]["count"], 3)


class DerivativeTest(unittest.TestCase):
    SOURCE = "第1章 风起\n\n“你终于来了。”陆照野抬头，看着城楼下的人影。江砚舟沉默片刻。"

    def test_clean_report_passes(self):
        result = derivative.check_derivative(self.SOURCE, "开篇用一句话同时点人物、画面和悬念。", "", 12)
        self.assertTrue(result["passed"])
        self.assertEqual(result["overlaps"], [])

    def test_copied_text_fails(self):
        report = "原作写：“你终于来了。”陆照野抬头，看着城楼下的人影。"
        result = derivative.check_derivative(self.SOURCE, report, "", 12)
        self.assertFalse(result["passed"])
        self.assertTrue(result["overlaps"])
        self.assertGreaterEqual(result["overlaps"][0]["length"], 12)

    def test_forbidden_name_fails(self):
        result = derivative.check_derivative(self.SOURCE, "主角陆照野登场。", "陆照野", 12)
        self.assertFalse(result["passed"])
        self.assertEqual(result["forbiddenHits"][0]["name"], "陆照野")


class TimelineTest(unittest.TestCase):
    def base(self):
        return timeline.template()

    def test_template_passes(self):
        errors, warnings, details = timeline.validate(self.base())
        self.assertEqual(errors, [])
        self.assertEqual(details["summary"]["events"], 1)

    def test_out_of_order_fails(self):
        data = self.base()
        data["events"].append({
            "id": "e002", "chapter": 2, "title": "回到过去", "date": "2023-12-01",
            "type": "main", "durationDays": 0,
        })
        errors, _, _ = timeline.validate(data)
        self.assertTrue(any("时间早于" in e for e in errors))

    def test_flashback_skips_order(self):
        data = self.base()
        data["events"].append({
            "id": "e002", "chapter": 2, "title": "回忆", "date": "2010-01-01",
            "type": "flashback",
        })
        data["events"].append({
            "id": "e003", "chapter": 3, "title": "继续", "date": "2024-01-05",
            "type": "main",
        })
        errors, _, details = timeline.validate(data)
        self.assertEqual(errors, [])
        self.assertEqual(details["summary"]["spanDays"], 4)

    def test_age_mismatch_fails(self):
        data = self.base()
        data["events"][0]["ages"] = {"c1": 30}
        errors, _, _ = timeline.validate(data)
        self.assertTrue(any("推算" in e for e in errors))

    def test_duration_overlap_fails(self):
        data = self.base()
        data["events"][0]["durationDays"] = 5
        data["events"].append({
            "id": "e002", "chapter": 2, "title": "第三天", "date": "2024-01-04",
            "type": "main",
        })
        errors, _, _ = timeline.validate(data)
        self.assertTrue(any("重叠" in e for e in errors))

    def test_cause_from_future_fails(self):
        data = self.base()
        data["events"].append({
            "id": "e002", "chapter": 2, "title": "结果", "date": "2024-01-02",
            "type": "main", "causedBy": ["e003"],
        })
        data["events"].append({
            "id": "e003", "chapter": 3, "title": "原因", "date": "2024-01-03",
            "type": "main",
        })
        errors, _, _ = timeline.validate(data)
        self.assertTrue(any("后续章节" in e for e in errors))

    def test_strict_promotes_warning(self):
        data = self.base()
        data["events"].append({
            "id": "e002", "chapter": 2, "title": "没有时间锚点",
            "type": "main",
        })
        errors, warnings, _ = timeline.validate(data)
        self.assertEqual(errors, [])
        self.assertTrue(warnings)
        strict_errors, _, _ = timeline.validate(data, strict=True)
        self.assertTrue(strict_errors)


if __name__ == "__main__":
    unittest.main()
