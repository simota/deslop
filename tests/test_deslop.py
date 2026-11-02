"""Regression coverage for detection, preservation and the run contract."""
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "deslop"
EXAMPLES = ROOT / "examples"
sys.path.insert(0, str(SKILL / "scripts"))

import contract_check  # noqa: E402
import cues  # noqa: E402
import detect  # noqa: E402
import findings  # noqa: E402
import preserve_check  # noqa: E402
import snapshot  # noqa: E402
from common import assign_genres, code_blocks, genre_table, infer_genre, is_markdown, load_json, load_rules  # noqa: E402

RULES = load_rules()


def scan(text):
    return detect.scan_text(text, detect.compile_rules(RULES), RULES["min_chars"])[2]


def rules_of(text):
    return {h["rule"] for h in scan(text)}


def cues_of(text, genre="general"):
    prose = detect.mask_urls(detect.mask_code(text))
    lang = detect.language(prose)
    quiet = {p["id"] for p in RULES["perspectives"] if genre in p.get("quiet", [])}
    return detect.perspective_cues(text, lang, detect.metrics(prose, lang)["chars"], RULES["min_chars"], True, quiet)


def cued(text, genre="general"):
    return {c["perspective"] for c in cues_of(text, genre)}


class DetectTests(unittest.TestCase):
    def test_before_samples_hit_every_tier(self):
        for name, expected in {
            "before.ja.md": {"ART-04", "JA-02", "JA-04", "JA-08", "JA-11", "JA-17", "JA-31", "CNT-01", "EMO-01", "DEN-04"},
            "before.en.md": {"ART-01", "ART-03", "ART-08", "EN-03", "EN-07", "EN-09", "EN-12", "DEN-02"},
        }.items():
            found = rules_of((EXAMPLES / name).read_text(encoding="utf-8"))
            self.assertLessEqual(expected, found, name)

    def test_after_samples_are_clean(self):
        for name in ("after.ja.md", "after.en.md"):
            self.assertEqual(scan((EXAMPLES / name).read_text(encoding="utf-8")), [], name)

    def test_code_front_matter_and_urls_are_not_prose(self):
        text = (
            "---\ntitle: delve\n---\n"
            "```\nI hope this helps — leverage seamless\n```\n"
            "Run `leverage --robust` first.\n"
            "See https://example.com/delve-into-tapestry for the log.\n"
        )
        self.assertEqual(scan(text), [])

    def test_code_nested_in_lists_and_indented_code_are_not_prose(self):
        nested = "1. Install:\n\n    ```sh\n    curl https://x.test/INSERT_API_URL  # robust\n    ```\n\n2. Run it.\n"
        self.assertEqual(scan(nested), [])
        self.assertEqual(scan("Call it:\n\n    robust = leverage(seamless)\n\nDone.\n"), [])
        self.assertEqual(scan("- Use it:\n\n      ```\n      robust\n      ```\n"), [])

    def test_indented_list_paragraphs_are_still_prose(self):
        self.assertIn("EN-04", rules_of("- Install it.\n\n    The installer is robust.\n"))
        self.assertIn("EN-04", rules_of("1. Install it.\n\n    The installer is robust.\n"))
        self.assertIn("EN-04", rules_of("Install it.\n    The installer is robust.\n"))

    def test_fences_open_and_close_within_their_container(self):
        inner = "```python\ndef f():\n    \"\"\"\n    ```\n    \"\"\"\n```\n\nIt is crucial 42.\n"
        self.assertEqual(len(code_blocks(inner)), 1)
        self.assertIn("EN-05", rules_of(inner.replace("It is crucial", "It plays a crucial role in")))
        self.assertIn("EN-01", rules_of("Some prose\n    ```\nI delve into 5 things.\n"))
        self.assertIn("EN-01", rules_of("- item\n  ```\n  code\n\nProse 5 delve.\n"))

    def test_indented_code_after_headings_and_breaks(self):
        self.assertEqual(scan("# Title\n    robust code\n"), [])
        self.assertEqual(scan("Text\n\n* * *\n\n    robust code\n"), [])

    def test_indented_text_files_are_prose(self):
        text = "    This paragraph is indented and robust.\n"
        self.assertEqual(detect.scan_text(text, detect.compile_rules(RULES), RULES["min_chars"], markdown=False)[2][0]["rule"],
                         "EN-04")
        self.assertFalse(is_markdown("notes.txt") or is_markdown("doc.rst"))
        self.assertTrue(is_markdown("README.md") and is_markdown("README"))

    def test_backticks_in_an_info_string_open_no_fence(self):
        self.assertIn("EN-04", rules_of("```js``` is inline.\n\nWe use a robust tool.\n"))

    def test_artifact_inside_url_is_still_found(self):
        self.assertIn("ART-06", rules_of("Source: https://example.com/a?utm_source=chatgpt.com\n"))

    def test_hit_records_line_column_and_context(self):
        hit = next(h for h in scan("Intro.\n\n> I hope this helps\n") if h["rule"] == "ART-03")
        self.assertEqual((hit["line"], hit["col"], hit["context"]), (3, 3, "quote"))

    def test_density_needs_enough_prose(self):
        self.assertNotIn("DEN-01", rules_of("**a** **b** **c** **d**\n"))

    def test_artifact_exemption_applies_only_inside_quotations(self):
        exemptions = [{"path": "a.md", "rule": "ART-03", "reason": "quoting a chatbot transcript"}]
        quoted, plain = scan("> I hope this helps\n")[0], scan("I hope this helps\n")[0]
        self.assertTrue(detect.exemption_for(quoted, "a.md", exemptions))
        self.assertIsNone(detect.exemption_for(plain, "a.md", exemptions))

    def test_quotation_opened_on_a_list_item_line_is_quoted(self):
        exemptions = [{"path": "a.md", "rule": "ART-03", "reason": "quoting a chatbot transcript"}]
        for text in ("- > I hope this helps\n", "1. > I hope this helps\n", "- - > I hope this helps\n"):
            hit = scan(text)[0]
            self.assertEqual(hit["context"], "quote", text)
            self.assertTrue(detect.exemption_for(hit, "a.md", exemptions), text)
        self.assertEqual(scan("- I hope this helps > all\n")[0]["context"], "list")

    def test_lexical_exemption_can_name_the_text(self):
        hit = scan("We use robust statistics here.\n")[0]
        named = [{"path": "a.md", "rule": "EN-04", "text": "robust", "reason": "term of art: robust statistics"}]
        other = [{"path": "a.md", "rule": "EN-04", "text": "seamless", "reason": "x"}]
        self.assertTrue(detect.exemption_for(hit, "a.md", named))
        self.assertIsNone(detect.exemption_for(hit, "a.md", other))

    def test_triads_count_only_lists_of_exactly_three(self):
        self.assertEqual(detect.triads("It is fast, cheap, and safe."), 1)
        self.assertEqual(detect.triads("Keep numbers, URLs, inline code, code blocks and footnotes."), 0)

    def test_curly_apostrophes_match_like_straight_ones(self):
        found = rules_of("It’s important to note this. Let’s dive in. We’re excited.\n")
        self.assertLessEqual({"EN-06", "EN-12", "EN-17"}, found)

    def test_short_japanese_text_gets_japanese_rules(self):
        self.assertEqual(detect.language("設定することが可能です。"), "ja")
        self.assertIn("JA-04", rules_of("設定することが可能です。\n"))
        self.assertIn("JA-04", rules_of("設定することができます。\n"))

    def test_each_paragraph_gets_the_rules_of_its_language(self):
        mixed = ("本記事では、キャッシュの設定を変える手順を説明します。設定ファイルは一つだけです。\n\n"
                 "We delve into the cache settings.\n")
        hits = scan(mixed)
        self.assertEqual(detect.language(detect.mask_urls(detect.mask_code(mixed))), "ja")
        self.assertEqual({h["rule"] for h in hits} & {"JA-08", "EN-01"}, {"JA-08", "EN-01"})
        self.assertIn("EN-01", rules_of("The cache layer is described below.\n\n変更点を徹底解説します。\n\nWe delve in.\n"))
        self.assertIn("JA-14", rules_of("The cache layer is described below in some detail for operators.\n\n変更点を徹底解説します。\n"))

    def test_code_span_wrapped_across_lines_is_masked(self):
        self.assertNotIn("ART-03", rules_of("Closers (`I hope\nthis helps`) go.\n"))
        self.assertIn("ART-03", rules_of("A stray ` tick.\n\nI hope this helps\n"))

    def test_pivotal_is_counted_once(self):
        for text, rule in [("It was a pivotal moment.\n", "EN-14"), ("The cache is pivotal.\n", "EN-05"),
                           ("It plays a pivotal role.\n", "EN-05")]:
            found = [h["rule"] for h in scan(text)]
            self.assertEqual(found, [rule], text)

    def test_link_text_is_not_a_placeholder(self):
        self.assertNotIn("ART-07", rules_of("See [Your first project](tutorial.md) and [Name][ref].\n"))
        self.assertIn("ART-07", rules_of("Signed, [Your Name]\n"))

    def test_template_fields_are_placeholders(self):
        fields = ["[HH:MM]", "[N] failed", "[link]", "[YYYY-MM-DD]", "[owner]", "[取引先会社名]", "[リンク]", "【担当者名】"]
        for field in fields:
            with self.subTest(field=field):
                self.assertIn("ART-07", rules_of(f"Value: {field}\n"))
        for text in ("See [link](x.md).\n", "Note [n] and [Note] and [1].\n", "見る [リンク](https://example.com)\n",
                     "| 期限 | [N/A] |\n", "See the [link] for details.\n\n[link]: https://example.com\n"):
            with self.subTest(text=text):
                self.assertNotIn("ART-07", rules_of(text))

    def test_corpus_detection_gaps_are_closed(self):
        for text, rule in [("ご不明な点やご懸念がございましたら、お気軽にお申し付けください。\n", "JA-21"),
                           ("ご不明な点がございましたらご連絡ください。\n", "JA-21"),
                           ("## ⏱ 時間の使い方\n", "EMO-01"),
                           ("参加者は〇名です。\n", "ART-07"), ("○○株式会社 御中\n", "ART-07"), ("○月○日に開催\n", "ART-07")]:
            with self.subTest(text=text):
                self.assertIn(rule, rules_of(text))
        for text in ("| 項目 | 対応 |\n|---|---|\n| A | 〇 |\n", "評価は ○ と × で示す。\n", "ショートカットは ⌘⇧M です。\n",
                     "二〇〇〇年に創業。\n", "一〇〇円です。\n", "二〇二〇年の資料。\n", "○日時：11月1日\n", "○年間計画を立てる。\n"):
            with self.subTest(text=text):
                self.assertEqual(rules_of(text) & {"ART-07", "EMO-01"}, set())

    def test_ending_runs_stop_at_headings_and_tables(self):
        ends = ["設定を保存します。", "値を削除します。", "ログを出力します。", "結果を確認します。"]
        run = lambda text: detect.metrics(text, "ja")["ending_run"]
        self.assertEqual(run("".join(ends) + "\n"), 4)
        self.assertEqual(run("\n\n".join(ends) + "\n"), 4)
        self.assertEqual(run("".join(f"## {n}\n\n{s}\n\n" for n, s in enumerate(ends))), 1)
        table = "| 列 | 説明 |\n|---|---|\n| x | 値です |\n"
        self.assertEqual(run("\n\n".join(ends[:2]) + "\n\n" + table + "\n" + "\n\n".join(ends[2:]) + "\n"), 2)

    def test_generator_disclaimer_in_japanese(self):
        for text in ("実際の仕様は確認できていません。\n", "一般的なデプロイ CLI を参考にした仮の内容です。\n",
                     "実際のAPI仕様が未提示のため、以下のフィールドと動作を仮定しています。\n"):
            with self.subTest(text=text):
                self.assertIn("JA-33", rules_of(text))
        for text in ("原因はまだ確認できていません。\n", "二重決済は確認されていません。\n", "この値は仮の設定として後で変える。\n"):
            with self.subTest(text=text):
                self.assertNotIn("JA-33", rules_of(text))

    def test_business_greeting_is_not_over_polite(self):
        self.assertNotIn("JA-19", rules_of("いつもお世話になっております。\n"))
        self.assertIn("JA-19", rules_of("こちらが対象となっております。\n"))
        self.assertIn("JA-19", rules_of("料金は有料になっております。\n"))

    def test_ai_self_reference_only_when_the_model_speaks(self):
        self.assertNotIn("ART-05", rules_of("The tool ships as an AI agent for triage.\n"))
        self.assertNotIn("ART-05", rules_of("ChatGPTは対話型AIとして、多くの場面で使われる。\n"))
        self.assertIn("ART-05", rules_of("As an AI language model, I cannot browse.\n"))
        self.assertIn("ART-05", rules_of("前置きです。AIとして、私は意見を持ちません。\n"))
        self.assertNotIn("ART-05", rules_of("We frame it as an AI, not a person.\n"))
        self.assertNotIn("ART-05", rules_of("We ship it as an AI tool, i.e. a classifier.\n"))
        self.assertIn("ART-05", rules_of("As an AI developed by a lab, I cannot browse.\n"))
        self.assertIn("ART-05", rules_of("はい、AIアシスタントとして、お答えします。\n"))
        self.assertIn("ART-05", rules_of("- AIとして、意見は持ちません。\n"))

    def test_crlf_and_empty_front_matter_are_masked(self):
        self.assertEqual(scan("---\r\ntitle: delve\r\n---\r\nPlain text.\r\n"), [])
        self.assertEqual(scan("---\n---\nPlain text.\n"), [])

    def test_missing_path_and_non_utf8_file_are_usage_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = Path(tmp) / "a.md", Path(tmp) / "b.txt"
            good.write_text("Plain text.\n", encoding="utf-8")
            bad.write_bytes("設定".encode("shift_jis"))
            listed = Path(tmp) / "list.json"
            listed.write_text("[]", encoding="utf-8")
            for args in ([str(good), str(Path(tmp) / "typo.md")], [str(bad)], [str(good), "--exempt", str(listed)]):
                with self.assertRaises(SystemExit) as ctx, contextlib.redirect_stderr(io.StringIO()):
                    detect.main(["--root", tmp, *args])
                self.assertEqual(ctx.exception.code, 2)

    def test_exemption_text_narrows_to_its_occurrence(self):
        text = "We fit a robust regression.\nIt has a robust cache layer.\n"
        exemptions = [{"path": "a.md", "rule": "EN-04", "text": "robust regression", "reason": "term of art"}]
        lines = text.split("\n")
        exempt = [bool(detect.exemption_for(h, "a.md", exemptions, lines[h["line"] - 1])) for h in scan(text)]
        self.assertEqual(exempt, [True, False])
        line = "We fit a robust regression, then a robust cache layer."
        self.assertEqual([bool(detect.exemption_for(h, "a.md", exemptions, line)) for h in scan(line + "\n")],
                         [True, False])

    def test_ordinary_openers_and_message_closers(self):
        self.assertNotIn("ART-01", rules_of("Of course, the cache is cleared on restart.\n"))
        self.assertIn("ART-01", rules_of("**Certainly!** Here is the guide.\n"))
        self.assertIn("ART-01", rules_of("Sure, here's the revised README.\n"))
        self.assertIn("ART-01", rules_of("**Sure**, here's the guide.\n"))
        hit = scan("Let me know if you have any questions about the migration.\n")[0]
        self.assertEqual((hit["rule"], hit["tier"]), ("EN-20", "lexical"))
        self.assertEqual({h["rule"] for h in scan("ご不明な点があればお気軽にご相談ください。\n")}, {"JA-21"})

    def test_connectives_in_list_items(self):
        self.assertLessEqual({"EN-08", "EN-09"}, rules_of("- Moreover, it caches.\n- In conclusion, it works.\n"))
        self.assertLessEqual({"EN-08", "EN-09"}, rules_of("**Moreover**, it caches.\n**In conclusion**, it works.\n"))

    def test_root_defaults_to_common_parent_outside_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd, docs = Path(tmp) / "cwd", Path(tmp) / "docs"
            cwd.mkdir()
            docs.mkdir()
            doc = docs / "a.md"
            doc.write_text("I hope this helps\n", encoding="utf-8")
            out = Path(tmp) / "r.json"
            with mock.patch.object(Path, "cwd", return_value=cwd), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(detect.main([str(doc), "--out", str(out)]), 1)
            self.assertEqual(load_json(out)["hits"][0]["path"], "a.md")
            self.assertEqual(load_json(out)["root"], str(docs.resolve()))

    def test_root_defaults_to_cwd_for_documents_beneath_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            docs.mkdir()
            doc = docs / "a.md"
            doc.write_text("I hope this helps\n", encoding="utf-8")
            out = Path(tmp) / "r.json"
            with mock.patch.object(Path, "cwd", return_value=Path(tmp)), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(detect.main([str(doc), "--out", str(out)]), 1)
            self.assertEqual(load_json(out)["hits"][0]["path"], "docs/a.md")
            self.assertEqual(load_json(out)["root"], str(Path(tmp).resolve()))

    def test_japanese_rules_added_for_common_tells(self):
        for text, rule in [
            ("さらに、TTL も変えられます。\n", "JA-22"),
            ("前置きです。このように、設定は大切です。\n", "JA-22"),
            ("それでは早速、設定を見ていきましょう。\n", "JA-23"),
            ("キャッシュは高速な応答を可能にします。\n", "JA-24"),
            ("遅くなる可能性があるかもしれません。\n", "JA-25"),
            ("設定が難しいと思ったことはありませんか？\n", "JA-26"),
            ("速度、安定性、そして拡張性を高めます。\n", "JA-27"),
            ("本記事が設定の一助となれば幸いです。\n", "ART-04"),
            ("以上、キャッシュの設定について解説しました。\n", "JA-09"),
            ("強力なキャッシュを備えます。\n", "JA-06"),
        ]:
            self.assertIn(rule, rules_of(text), text)
        for text in ("また、TTL も変えられます。\n", "これは速度と安定性を高めます。\n", "遅くなるかもしれません。\n"):
            self.assertEqual(rules_of(text), set(), text)

    def test_researched_tells_are_found(self):
        for text, rule in [
            ("You're absolutely right! The cache is cold.\n", "ART-03"),
            ("Up to my last knowledge update, the API was v2.\n", "ART-05"),
            ("See https://example.com/a?utm_source=openai for details.\n", "ART-06"),
            ("Released on 2025-XX-XX at INSERT_SOURCE_URL_30.\n", "ART-07"),
            ("The release showcases the new parser.\n", "EN-01"),
            ("The interplay of cache and disk matters.\n", "EN-02"),
            ("It's not a cache — it's a store.\n", "EN-10"),
            ("The tool rose to the top, highlighting its importance.\n", "EN-21"),
            ("The file serves as the entry point.\n", "EN-22"),
            ("The town is nestled in the hills.\n", "EN-23"),
            ("Experts agree that caching helps.\n", "EN-24"),
            ("While specific details are limited, it ships in May.\n", "EN-25"),
            ("Despite these challenges, the project grew.\n", "EN-26"),
            ("キャッシュには3つの理由があります。\n", "JA-13"),
            ("大切なのは、設定を見直すことです。\n", "JA-28"),
            ("どちらが良いかは一概には言えません。\n", "JA-29"),
            ("この“設定”を変えます。\n", "JA-30"),
        ]:
            self.assertIn(rule, rules_of(text), text)
        for text in ("It serves as a reminder.\n", "It's not ready; ship it later.\n",
                     "The test stub stands in for the server.\n"):
            self.assertNotIn("EN-22", rules_of(text), text)
            self.assertNotIn("EN-10", rules_of(text), text)

    def test_content_tells_are_found(self):
        for text, rule in [
            ("Imagine you're a developer with a slow build.\n", "EN-27"),
            ("キャッシュは重要だと言われています。\n", "JA-31"),
            ("多くの企業がキャッシュを導入しています。\n", "JA-31"),
            ("例えば、あなたが店長だとします。\n", "JA-32"),
            ("導入企業の約30%が効果を実感しています。\n", "CNT-01"),
            ("73% of teams adopt it.\n", "CNT-01"),
            ("ドキュメント間の整合性は 85%程度 保たれています。\n", "CNT-01"),
        ]:
            self.assertIn(rule, rules_of(text), text)

    def test_statistics_with_a_source_in_their_paragraph_pass(self):
        for text in ("応答は 2 倍速くなります（[計測](bench.md)）。\n",
                     "Hit rate rose to 91%, according to the load test log.\n",
                     "Set `ratio = 50%` in the file.\n",
                     "2割引で提供します。\n",
                     "| 設定 | 15-30% |\n|---|---|\n| 既定 | 50% 向上 |\n",
                     "Font rebuilds cost 58% less main-thread time (63 → 27 ms).\n",
                     "仮定値: 広告の視聴率40%で売上が増加する。\n",
                     "音量を 50% にします。\n"):
            self.assertNotIn("CNT-01", rules_of(text), text)
        hit = next(h for h in scan("Intro.\n\n73% of teams adopt it.\n") if h["rule"] == "CNT-01")
        self.assertEqual((hit["line"], hit["col"], hit["tier"]), (3, 1, "content"))

    def test_content_perspectives_are_recorded_like_structural_ones(self):
        record = {"schema_version": 1,
                  "meta": {"target": "d", "lang": "en", "mode": "copy", "assessor": "t", "date": "2026-10-31"},
                  "voice": {"source": "inferred", "rules": ["plain"]},
                  "perspectives": [{"id": "CON-03", "result": "applied", "note": "hook statistic deleted"}],
                  "findings": [{"id": "T-001", "path": "a.md", "rule": "CON-01", "occurrences": 2,
                                "action": "deleted", "before": "Security is a top priority."}]}
        findings.check_record(record)
        record["perspectives"][0]["id"] = "CNT-01"
        with self.assertRaises(findings.RecordError):
            findings.check_record(record)

    def test_horizontal_rules_count_but_setext_underlines_do_not(self):
        body = "Plain sentence about the cache layer and its settings. " * 8
        ruled = f"{body}\n\n---\n\n{body}\n\n***\n\n{body}\n\n___\n\n{body}\n"
        self.assertIn("DEN-10", rules_of(ruled))
        setext = f"Title\n---\n\n{body}\n\nSection\n---\n\n{body}\n"
        self.assertNotIn("DEN-10", rules_of(setext))

    def test_japanese_sentences_join_wrapped_lines_and_skip_quoted_stops(self):
        wrapped = "キャッシュは同じ要求を\nディスクを読まずに返します。上限は max\nentries で決まります。\n"
        self.assertEqual(detect.sentences(wrapped, "ja"),
                         ["キャッシュは同じ要求をディスクを読まずに返します。", "上限は max entries で決まります。"])
        quoted = "画面に「保存しました。」と出たら完了です。\n"
        self.assertEqual(detect.sentences(quoted, "ja"), ["画面に「保存しました。」と出たら完了です。"])
        items = "- 一つ目の項目です。\n- 二つ目の項目です。\n"
        self.assertEqual(detect.sentences(items, "ja"), ["一つ目の項目です。", "二つ目の項目です。"])

    def test_every_rule_compiles_and_has_a_note(self):
        for rule, _ in detect.compile_rules(RULES):
            self.assertTrue(rule.get("note"), rule["id"])


class CueTests(unittest.TestCase):
    FILLER = "The worker renders map tiles once and keeps them on local disk until their TTL ends. "

    def test_before_samples_are_cued_and_after_samples_are_not(self):
        self.assertLessEqual({"STR-01", "STR-02", "STR-14"}, cued((EXAMPLES / "before.ja.md").read_text(encoding="utf-8")))
        self.assertLessEqual({"STR-02", "STR-13"}, cued((EXAMPLES / "before.en.md").read_text(encoding="utf-8")))
        for name in ("after.ja.md", "after.en.md"):
            self.assertEqual(cues_of((EXAMPLES / name).read_text(encoding="utf-8")), [], name)

    def test_opening_that_announces_or_repeats_the_title(self):
        self.assertIn("STR-01", cued("# Tiles\n\nThis guide explains how tiles are cached.\n"))
        self.assertIn("STR-01", cued("# Tile caching in tilecache\n\nTile caching in tilecache.\n"))
        self.assertNotIn("STR-01", cued("# tilecache\n\ntilecache keeps rendered map tiles on disk so each tile renders once.\n"))
        self.assertNotIn("STR-01", cued("# Tiles\n\n## Setup\n\nThis guide explains how tiles are cached.\n"))

    def test_closing_named_as_summary_or_made_of_used_words(self):
        body = "# Tiles\n\n## Cache\n\nTiles stay on disk until their TTL ends; ttl_seconds sets it.\n\n"
        self.assertIn("STR-02", cued(body + "## Conclusion\n\nThat is all.\n"))
        self.assertIn("STR-02", cued(body + "## Next\n\nTiles stay on disk until their TTL ends.\n"))
        self.assertNotIn("STR-02", cued(body + "## License\n\nReleased under the Apache license, version two.\n"))
        self.assertNotIn("STR-02", cued(body + "## Conclusion\n\nText.\n\n```sh\nmake\n```\n"))

    def test_moral_endings_need_a_pattern_across_paragraphs(self):
        para = "Tiles in zone {} render once per hour in the pool. {}"
        moral = "\n\n".join(para.format(i, "This makes the map much faster for everyone.") for i in range(5))
        self.assertEqual(sum(c["perspective"] == "STR-03" for c in cues_of(f"# T\n\n{moral}\n")), 5)
        plain = "\n\n".join(para.format(i, "The pool has eight workers in zone {}.".format(i)) for i in range(5))
        once = plain.replace("eight workers in zone 0.", "eight workers. This makes it fast.")
        self.assertNotIn("STR-03", cued(f"# T\n\n{once}\n"))

    def test_lists_of_three_again_and_again(self):
        text = f"# T\n\n{self.FILLER * 3}\n\n- a\n- b\n- c\n\n{self.FILLER}\n\n- d\n- e\n- f\n\n{self.FILLER * 2}\n"
        self.assertIn("STR-04", cued(text))
        self.assertNotIn("STR-04", cued(text.replace("- c\n", "- c\n- g\n")))
        loose = text.replace("- a\n- b\n- c\n", "- a\n\n- b\n\n  more on b\n\n- c\n")
        self.assertIn("STR-04", cued(loose))

    def test_thin_and_symmetric_sections_are_quiet_where_the_genre_needs_them(self):
        part = "## Part {}\n\nPart {} covers one step of the setup in some detail. It has two sentences.\n\n- one\n- two\n- three\n\n"
        sym = "# Guide\n\n" + "".join(part.format(i, i) for i in range(4)) + self.FILLER * 2 + "\n"
        self.assertIn("STR-06", cued(sym))
        self.assertNotIn("STR-06", cued(sym, "reference"))
        thin = "# Guide\n\n" + "".join(f"## Step {i}\n\n{self.FILLER}\n\n" for i in range(5))
        self.assertIn("STR-05", cued(thin))
        self.assertNotIn("STR-05", cued(thin, "readme"))
        coded = "# Guide\n\n" + "".join(f"## Step {i}\n\n{self.FILLER}\n\n```sh\nrun {i}\n```\n\n" for i in range(5))
        self.assertNotIn("STR-05", cued(coded))

    def test_restatement_and_uniform_paragraphs(self):
        self.assertIn("STR-11", cued("# X\n\nThe worker renders tiles hourly. In other words, it renders them every hour.\n"))
        self.assertIn("STR-11", cued("# X\n\nTiles render hourly for every zoom level.\nEvery zoom level renders tiles hourly.\n"))
        self.assertNotIn("STR-11", cued("# X\n\nTiles render hourly. The disk holds ten thousand entries by default.\n"))
        two = "\n\n".join(f"Zone {i} renders on worker {i} every hour. Its tiles stay on disk for a day." for i in range(6))
        self.assertIn("STR-13", cued(f"# X\n\n{two}\n"))
        self.assertNotIn("STR-13", cued(f"# X\n\n{two}\n".replace("for a day.", "for a day. It logs.", 2)))

    def test_headings_that_ask_or_name_stock_sections(self):
        self.assertIn("STR-14", cued("# X\n\n## Why use tilecache?\n\nIt caches tiles.\n"))
        self.assertIn("STR-14", cued("# X\n\n## キャッシュとは\n\nタイルを保存します。\n"))
        self.assertIn("CON-05", cued("# X\n\n## Benefits\n\nFast.\n\n## Best practices\n\nSet a TTL.\n"))
        self.assertNotIn("CON-05", cued("# X\n\n## Benefits\n\nFast.\n\n## Setup\n\nSet a TTL.\n"))

    def test_mixed_japanese_register(self):
        paras = ["TTL は ttl_seconds で指定します。既定値は 300 秒です。容量は max_entries で指定します。",
                 "退避方式は LRU を使う。古いエントリから消える。設定は再起動で反映される。",
                 "ログは標準出力に出ます。レベルは log_level で変えられます。既定値は info です。"]
        mixed = "# 設定\n\n" + "\n\n".join(paras * 4) + "\n"
        self.assertIn("STR-16", cued(mixed))
        polite = mixed.replace("使う。", "使います。").replace("消える。", "消えます。").replace("される。", "されます。")
        self.assertNotIn("STR-16", cued(polite))
        self.assertNotIn("STR-16", cued("# 設定\n\n" + "\n\n".join(paras) + "\n"), "too little prose to judge")

    def test_cues_are_capped_and_never_hits(self):
        text = "# X\n\n" + "".join(f"## Q{i}?\n\nA.\n\n" for i in range(9))
        self.assertEqual(sum(c["perspective"] == "STR-14" for c in cues_of(text)), cues.PER_PERSPECTIVE)
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        (tmp / "doc.md").write_text(text, encoding="utf-8")
        out = tmp / "detect.json"
        with contextlib.redirect_stdout(io.StringIO()) as stdout, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(detect.main(["--root", str(tmp), str(tmp / "doc.md"), "--out", str(out)]), 0)
        result = load_json(out)
        self.assertEqual((result["summary"]["open"], result["summary"]["cues"]), (0, cues.PER_PERSPECTIVE))
        self.assertIn("doc.md:3 STR-14 cue: ", stdout.getvalue())

    def test_quiet_lists_name_real_genres(self):
        genres = set(genre_table(RULES))
        for p in RULES["perspectives"]:
            self.assertLessEqual(set(p.get("quiet", [])), genres, p["id"])


class GenreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp)

    def doc(self, name, text):
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_only_the_template_genre_keeps_placeholders(self):
        form = self.doc("form.md", "Owner: [name], due [YYYY-MM-DD].\n\nAs an AI language model, I cannot fill this in.\n")
        kept = detect.scan([form], self.tmp, RULES, [], {"form.md": "template"})
        exempt = {h["rule"] for h in kept["hits"] if h["exempt"]}
        open_rules = {h["rule"] for h in kept["hits"] if not h["exempt"]}
        self.assertEqual(exempt, {"ART-07"})
        self.assertIn("ART-05", open_rules)
        plain = detect.scan([form], self.tmp, RULES, [], {"form.md": "general"})
        self.assertIn("ART-07", {h["rule"] for h in plain["hits"] if not h["exempt"]})

    def test_template_keeps_bold_field_labels(self):
        form = self.doc("status.md", "".join(f"- **Field {n}:** [value {n}], to be filled in by the team lead before Friday\n"
                                             for n in range(8)))
        hits = detect.scan([form], self.tmp, RULES, [], {"status.md": "template"})["hits"]
        self.assertTrue(all(h["exempt"] for h in hits if h["rule"] in ("DEN-04", "ART-07")))
        self.assertIn("DEN-04", {h["rule"] for h in hits})
        plain = detect.scan([form], self.tmp, RULES, [], {"status.md": "general"})["hits"]
        self.assertIn("DEN-04", {h["rule"] for h in plain if not h["exempt"]})

    def test_genres_only_touch_rules_they_may(self):
        tiers = {r["id"]: r["tier"] for r in RULES["rules"]}
        self.assertEqual(RULES["genres"][0]["id"], "general")
        self.assertEqual(len(genre_table(RULES)), len(RULES["genres"]))
        for g in RULES["genres"]:
            for rid, reason in g["exempt"].items():
                if (g["id"], rid) != ("template", "ART-07"):
                    self.assertIn(tiers.get(rid), {"lexical", "density"}, f"{g['id']} exempts {rid}")
                self.assertTrue(reason.strip())
            for rid, bound in g["limits"].items():
                self.assertEqual(tiers.get(rid), "density", f"{g['id']} limits {rid}")
                rule = next(r for r in RULES["rules"] if r["id"] == rid)
                self.assertEqual(set(bound), {"max", "min"} & set(rule), f"{g['id']} {rid}")
            self.assertEqual(g["match"], [p.lower() for p in g["match"]])

    def test_genre_is_inferred_from_the_file_name(self):
        self.assertEqual(infer_genre("README.md", RULES), "readme")
        self.assertEqual(infer_genre("docs/CHANGELOG.md", RULES), "changelog")
        self.assertEqual(infer_genre("docs/readme-notes/guide.md", RULES), "general")

    def test_explicit_genres_override_inference(self):
        readme, guide = self.doc("README.md", "x\n"), self.doc("guide.md", "x\n")
        files = [readme, guide]
        self.assertEqual(assign_genres([], files, self.tmp, RULES), {"README.md": "readme", "guide.md": "general"})
        self.assertEqual(assign_genres(["spec"], files, self.tmp, RULES), {"README.md": "spec", "guide.md": "spec"})
        self.assertEqual(assign_genres(["article", "guide.md=tutorial"], files, self.tmp, RULES),
                         {"README.md": "article", "guide.md": "tutorial"})
        for bad in (["poem"], ["typo.md=spec"], ["spec", "pr"]):
            with self.assertRaises(ValueError):
                assign_genres(bad, files, self.tmp, RULES)

    def test_message_genre_exempts_the_reply_invitation_visibly(self):
        mail = self.doc("mail.md", "The build is green again.\n\nLet me know if you have any questions.\n")
        general = detect.scan([mail], self.tmp, RULES, [])
        message = detect.scan([mail], self.tmp, RULES, [], {"mail.md": "message"})
        self.assertEqual(general["summary"]["open"], 1)
        hit = message["hits"][0]
        self.assertEqual((hit["rule"], hit["exempt_by"], message["summary"]["open"]), ("EN-20", "genre", 0))
        self.assertIn("Email / message", hit["exempt"])
        self.assertEqual(message["files"][0]["genre"], "message")

    def test_genre_exemption_never_covers_artifacts(self):
        mail = self.doc("mail.md", "Done.\n\nI hope this helps!\n")
        self.assertEqual(detect.scan([mail], self.tmp, RULES, [], {"mail.md": "message"})["summary"]["open"], 1)

    def test_genre_limits_tighten_and_relax_density(self):
        body = "".join(f"## Part {n}\n\n" + "The worker reads one batch, writes it and moves on to the next queue. " * 4 + "\n\n"
                       for n in range(6))
        params = "".join(f"- **opt{n}**: sets the size of buffer number {n} in bytes for each worker.\n" for n in range(12))
        compiled = detect.compile_rules(RULES)
        table = genre_table(RULES)

        def found(text, gid):
            return {h["rule"] for h in detect.scan_text(text, compiled, RULES["min_chars"], limits=table[gid]["limits"])[2]}

        self.assertNotIn("DEN-05", found(body, "general"))
        self.assertIn("DEN-05", found(body, "article"))
        self.assertIn("DEN-04", found(params, "general"))
        reference = detect.scan([self.doc("api.md", params)], self.tmp, RULES, [], {"api.md": "reference"})
        self.assertEqual(reference["summary"]["open"], 0)

    def test_tutorial_steps_may_each_have_a_heading(self):
        step = "Run the command below and check that the service answers on port 8080 before moving on. " * 2
        steps = "".join(f"## Step {n}\n\n{step}\n\n" for n in range(1, 10))
        doc = self.doc("guide.md", steps)
        self.assertGreater(detect.metrics(steps, "en")["chars"], 1500)
        hits = {h["rule"]: h["exempt"] for h in detect.scan([doc], self.tmp, RULES, [], {"guide.md": "tutorial"})["hits"]}
        self.assertIn("DEN-05", hits)
        self.assertTrue(hits["DEN-05"])
        self.assertIn("DEN-05", {h["rule"] for h in detect.scan([doc], self.tmp, RULES, [], {"guide.md": "article"})["hits"] if not h["exempt"]})

    def test_short_documents_skip_structural_shares_but_not_counts(self):
        part = "The worker reads one batch, writes it and moves on to the next queue. " * 3
        short = "# Title\n\n" + "".join(f"## Part {n}\n\n{part}\n\n- step one\n- step two\n\n" for n in range(4))
        compiled = detect.compile_rules(RULES)
        limits = genre_table(RULES)["article"]["limits"]
        lang, m, hits = detect.scan_text(short, compiled, RULES["min_chars"], limits=limits)
        self.assertLess(m["chars"], 1500)
        self.assertGreater(m["heading_per_1000"], limits["DEN-05"]["max"])
        self.assertGreater(m["list_ratio"], limits["DEN-06"]["max"])
        found = {h["rule"] for h in hits}
        self.assertNotIn("DEN-05", found)
        self.assertNotIn("DEN-06", found)

        bold = short + "".join(f"- **opt{n}**: sets buffer {n}.\n" for n in range(3))
        self.assertIn("DEN-04", {h["rule"] for h in detect.scan_text(bold, compiled, RULES["min_chars"], limits=limits)[2]})

    def test_detect_cli_takes_genres_and_refuses_them_with_a_snapshot(self):
        mail = self.doc("mail.md", "Done.\n\nFeel free to reach out.\n")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(detect.main([str(mail), "--quiet"]), 1)
            self.assertEqual(detect.main([str(mail), "--genre", "message", "--quiet"]), 0)
            with self.assertRaises(SystemExit):
                detect.main([str(mail), "--genre", "poem"])
            with self.assertRaises(SystemExit):
                detect.main(["--snapshot", str(self.tmp), "--genre", "message"])


class PreserveTests(unittest.TestCase):
    def facts_diff(self, before, after):
        return {(d["change"], d["kind"], d["value"])
                for d in preserve_check.compare(preserve_check.facts(before), preserve_check.facts(after), before)}

    def test_lost_and_added_values(self):
        diff = self.facts_diff("TTL is 300 seconds. See https://a.example/x.\n", "TTL is 3000 seconds.\n")
        self.assertEqual(diff, {("lost", "number", "300"), ("added", "number", "3000"),
                                ("lost", "url", "https://a.example/x")})

    def test_changed_code_block_is_reported(self):
        diff = self.facts_diff("```\nx = 1\n```\n", "```\nx = 2\n```\n")
        self.assertEqual({k for _, k, _ in diff}, {"code_block"})

    def test_link_targets_are_facts(self):
        diff = self.facts_diff("See [setup](docs/v2.md#install).\n\n[ref]: ../api.md\n", "See setup.\n")
        self.assertEqual(diff, {("lost", "url", "docs/v2.md#install"), ("lost", "url", "../api.md")})

    def test_angle_bracket_link_targets_match_bare_ones(self):
        self.assertEqual(self.facts_diff("[g](https://example.com/guide)\n",
                                         "[g][r]\n\n[r]: <https://example.com/guide>\n"), set())
        self.assertEqual(self.facts_diff("[g](<docs/a b.md>)\n", "[g][r]\n\n[r]: <docs/a b.md>\n"), set())

    def test_link_forms_agree_and_titles_keep_their_numbers(self):
        self.assertEqual(self.facts_diff("[g](https://example.com/a_(b))\n",
                                         "[g][r]\n\n[r]: https://example.com/a_(b)\n"), set())
        self.assertEqual(self.facts_diff('[s]: report.pdf "Revenue 100"\n', '[s]: report.pdf "Revenue 200"\n'),
                         {("lost", "number", "100"), ("added", "number", "200")})

    def test_longer_closing_fence_and_unclosed_fence(self):
        self.assertEqual(self.facts_diff("```\nx = 1\n````\nTTL 300.\n", "```\nx = 1\n````\nTTL 300.\n"), set())
        self.assertEqual(preserve_check.facts("```\nx = 1\n````\nTTL 300.\n")["number"], {"300": 1})
        self.assertEqual(preserve_check.facts("```\nport 8080\n")["number"], {})

    def test_code_nested_in_lists_and_indented_code_are_code_blocks(self):
        nested = "1. Run:\n\n    ```sh\n    serve --port 8080\n    ```\n"
        indented = "Run:\n\n    serve --port 8080\n"
        for text in (nested, indented):
            self.assertEqual(preserve_check.facts(text)["number"], {"1": 1} if text is nested else {})
            diff = self.facts_diff(text, text.replace("8080", "9090"))
            self.assertEqual({(c, k) for c, k, _ in diff}, {("lost", "code_block"), ("added", "code_block")})

    def test_unclosed_fence_in_a_list_item_ends_with_the_item(self):
        self.assertEqual(preserve_check.facts("- item\n  ```\n  code\n\nProse 5.\n")["number"], {"5": 1})
        self.assertEqual(preserve_check.facts("    port 8080\n", markdown=False)["number"], {"8080": 1})

    def test_backticks_in_an_info_string_open_no_fence(self):
        self.assertEqual(preserve_check.facts("```js``` is inline.\n\nTTL 300.\n")["number"], {"300": 1})

    def test_rewrapping_a_code_span_is_not_a_change(self):
        self.assertEqual(preserve_check.facts("Run `make\n  check` now.\n")["inline_code"],
                         preserve_check.facts("Run `make check` now.\n")["inline_code"])

    def test_wrapping_prose_in_backticks_is_an_added_value(self):
        diff = self.facts_diff("We leverage a robust cache.\n", "We `leverage` a `robust` cache.\n")
        self.assertEqual(diff, {("added", "inline_code", "leverage"), ("added", "inline_code", "robust")})
        code = "```\nrobust_scaler = 1\ncache_ttl = 2\n```\n"
        diff = self.facts_diff("A robust cache.\n" + code, "A `robust` `cache`.\n" + code)
        self.assertEqual(diff, {("added", "inline_code", "robust"), ("added", "inline_code", "cache")})

    def test_prose_after_a_bracket_label_is_not_a_link_target(self):
        self.assertEqual(preserve_check.facts("[Note]: this matters a lot.\n")["url"], {})
        self.assertEqual(preserve_check.facts('[r]: ../api.md "API"\n')["url"], {"../api.md": 1})

    def test_restating_existing_values_is_not_a_change(self):
        before = "Set `ttl` to 300.\n```\n[cache]\nttl = 300\n```\n"
        after = "Set `ttl` in `[cache]` to 300; 300 is the default.\n```\n[cache]\nttl = 300\n```\n"
        self.assertEqual(self.facts_diff(before, after), set())


class RunContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.docs, self.out = self.tmp / "docs", self.tmp / "run"
        self.docs.mkdir()
        shutil.copyfile(EXAMPLES / "before.ja.md", self.docs / "guide.md")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def fragment(self, data):
        path = self.tmp / f"frag-{len(list(self.tmp.glob('frag-*')))}.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def setUp_quiet(self):
        stack = contextlib.ExitStack()
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
        self.addCleanup(stack.close)

    def complete_run(self, *genre):
        self.setUp_quiet()
        self.assertEqual(snapshot.main([str(self.out), str(self.docs), "--root", str(self.docs), "--copy", *genre]), 0)
        self.assertEqual(detect.main(["--snapshot", str(self.out), "--out", str(self.out / "detect.before.json"), "--quiet"]), 1)
        shutil.copyfile(EXAMPLES / "after.ja.md", self.out / "rewritten" / "guide.md")
        before = load_json(self.out / "detect.before.json")["hits"]
        pairs = sorted({(h["path"], h["rule"]) for h in before if h.get("exempt_by") != "genre"})
        record = self.out / "findings.json"
        findings.merge(record, [self.fragment({
            "schema_version": 1,
            "meta": {"target": str(self.docs), "lang": "ja", "mode": "copy", "assessor": "test", "date": "2026-10-31"},
            "voice": {"source": "inferred", "rules": ["です・ます調", "設定名はコードで示す"]},
        })])
        findings.merge(record, [self.fragment({"findings": [
            {"id": f"T-{n:03d}", "path": path, "rule": rule, "occurrences": 1,
             "action": "deleted", "before": rule} for n, (path, rule) in enumerate(pairs, 1)
        ]})])
        findings.merge(record, [self.fragment({
            "perspectives": [{"id": p["id"], "result": "applied", "note": "read end to end"} for p in RULES["perspectives"]],
            "preservation": [{"path": "guide.md", "kind": "number", "value": "2",
                              "reason": "unsupported 'tune these two' advice deleted under CON-06"},
                             {"path": "guide.md", "kind": "number", "value": "30",
                              "reason": "unsourced hook statistic deleted under CON-03"}],
        })])
        self.assertEqual(detect.main(["--snapshot", str(self.out), "--exempt", str(record),
                                      "--out", str(self.out / "detect.after.json"), "--quiet"]), 0)
        self.assertEqual(preserve_check.main([str(self.out)]), 0)
        findings.render(self.out)

    def test_complete_run_passes(self):
        self.complete_run()
        self.assertEqual(contract_check.problems(self.out), [])
        report = (self.out / "report.md").read_text(encoding="utf-8")
        self.assertIn("AI文体除去レポート", report)
        self.assertIn("本文の文字数", report)
        self.assertIn("CON-01", report)

    def test_genre_exempt_before_hits_need_no_finding(self):
        self.complete_run("--genre", "reference")
        self.assertEqual(load_json(self.out / "snapshot.json")["files"][0]["genre"], "reference")
        data = load_json(self.out / "findings.json")
        self.assertNotIn("DEN-04", {f["rule"] for f in data["findings"]})
        self.assertEqual(contract_check.problems(self.out), [])
        report = (self.out / "report.md").read_text(encoding="utf-8")
        self.assertIn("| `guide.md` | API / reference (`reference`) | DEN-01 exempt;", report)

    def test_unknown_genre_in_snapshot_fails(self):
        self.complete_run()
        snap = load_json(self.out / "snapshot.json")
        snap["files"][0]["genre"] = "poem"
        (self.out / "snapshot.json").write_text(json.dumps(snap), encoding="utf-8")
        self.assertTrue(any("unknown genre 'poem'" in p for p in contract_check.problems(self.out)))

    def test_copy_mode_leaves_originals_untouched(self):
        self.complete_run()
        self.assertEqual((self.docs / "guide.md").read_bytes(), (EXAMPLES / "before.ja.md").read_bytes())

    def test_reintroduced_tell_fails(self):
        self.complete_run()
        doc = self.out / "rewritten" / "guide.md"
        doc.write_text(doc.read_text(encoding="utf-8") + "\n参考になれば幸いです。\n", encoding="utf-8")
        self.assertTrue(any("open hit" in p and "ART-04" in p for p in contract_check.problems(self.out)))

    def test_unaccounted_before_hit_fails(self):
        self.complete_run()
        record = self.out / "findings.json"
        data = load_json(record)
        data["findings"] = [f for f in data["findings"] if f["rule"] != "JA-02"]
        record.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        findings.render(self.out)
        self.assertTrue(any("JA-02 has no finding" in p for p in contract_check.problems(self.out)))

    def test_stale_report_and_missing_perspective_fail(self):
        self.complete_run()
        record = self.out / "findings.json"
        data = load_json(record)
        data["perspectives"] = data["perspectives"][1:]
        record.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        problems = contract_check.problems(self.out)
        self.assertTrue(any("STR-01" in p for p in problems))
        self.assertTrue(any("report.md differs" in p for p in problems))

    def test_cued_perspective_cannot_be_not_applicable(self):
        self.complete_run()
        record = self.out / "findings.json"
        findings.merge(record, [self.fragment({"perspectives": [{"id": "STR-14", "result": "N/A", "note": "no headings"}]})])
        findings.render(self.out)
        self.assertTrue(any("STR-14 is N/A but detect.py cues it" in p for p in contract_check.problems(self.out)))

    def test_invented_number_fails(self):
        self.complete_run()
        doc = self.out / "rewritten" / "guide.md"
        doc.write_text(doc.read_text(encoding="utf-8") + "\nヒット率は 95% 向上します。\n", encoding="utf-8")
        self.assertTrue(any("added number '95'" in p for p in contract_check.problems(self.out)))

    def test_changed_number_sign_fails_even_with_a_fresh_report(self):
        (self.docs / "limits.md").write_text("The lower bound is -10.\n", encoding="utf-8")
        self.complete_run()
        (self.out / "rewritten" / "limits.md").write_text("The lower bound is 10.\n", encoding="utf-8")
        findings.render(self.out)
        self.assertTrue(any("lost number '-10'" in p for p in contract_check.problems(self.out)))

    def test_bad_fragment_changes_nothing(self):
        self.complete_run()
        record = self.out / "findings.json"
        before = record.read_bytes()
        with self.assertRaises(findings.RecordError):
            findings.merge(record, [self.fragment({"findings": [{"id": "T-999", "path": "guide.md", "rule": "NOPE-1"}]})])
        self.assertEqual(record.read_bytes(), before)

    def test_snapshot_refuses_run_inside_root_and_reuse(self):
        self.setUp_quiet()
        with self.assertRaises(SystemExit):
            snapshot.main([str(self.docs / "run"), str(self.docs), "--root", str(self.docs)])
        self.complete_run()
        with self.assertRaises(SystemExit):
            snapshot.main([str(self.out), str(self.docs), "--root", str(self.docs)])

    def test_snapshot_refuses_non_empty_run_and_missing_path(self):
        self.setUp_quiet()
        self.out.mkdir()
        (self.out / "findings.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(SystemExit):
            snapshot.main([str(self.out), str(self.docs), "--root", str(self.docs)])
        with self.assertRaises(SystemExit):
            snapshot.main([str(self.tmp / "run2"), str(self.docs / "typo.md"), "--root", str(self.docs)])
        self.assertFalse((self.tmp / "run2" / "snapshot.json").exists())

    def test_snapshot_records_a_file_named_twice_once(self):
        self.setUp_quiet()
        doc = self.docs / "guide.md"
        snapshot.main([str(self.out), "--root", str(self.docs), str(doc), os.path.relpath(doc)])
        self.assertEqual([f["path"] for f in load_json(self.out / "snapshot.json")["files"]], ["guide.md"])

    def test_preserve_check_refuses_a_missing_run(self):
        with self.assertRaises(SystemExit) as ctx, contextlib.redirect_stderr(io.StringIO()):
            preserve_check.main([str(self.tmp / "nowhere")])
        self.assertEqual(ctx.exception.code, 2)

    def test_preserve_check_refuses_malformed_findings(self):
        self.complete_run()
        record = self.out / "findings.json"
        valid = load_json(record)
        for bad in ([], {**valid, "preservation": ["not an object"]},
                    {**valid, "preservation": [{"path": "guide.md", "kind": [],
                                               "value": "2", "reason": "bad kind"}]}):
            with self.subTest(record=bad):
                record.write_text(json.dumps(bad), encoding="utf-8")
                with self.assertRaises(SystemExit) as ctx:
                    preserve_check.main([str(self.out)])
                self.assertEqual(ctx.exception.code, 2)

    def test_missing_working_copy_is_reported_not_raised(self):
        self.complete_run()
        (self.out / "rewritten" / "guide.md").unlink()
        self.assertEqual(contract_check.problems(self.out), ["working copy guide.md is missing"])

    def test_edited_report_body_fails(self):
        self.complete_run()
        report = self.out / "report.md"
        report.write_text(report.read_text(encoding="utf-8").split("\n")[0] + "\nanything\n", encoding="utf-8")
        self.assertTrue(any("report.md differs" in p for p in contract_check.problems(self.out)))

    def test_missing_original_is_reported_not_raised(self):
        self.complete_run()
        (self.out / "original" / "guide.md").unlink()
        self.assertEqual(contract_check.problems(self.out), ["original/guide.md no longer matches snapshot.json"])
        self.assertEqual(preserve_check.check(self.out)["files"][0]["missing"], "original")

    def test_before_hits_are_rescanned_from_originals(self):
        self.complete_run()
        before = self.out / "detect.before.json"
        data = load_json(before)
        data["hits"] = []
        before.write_text(json.dumps(data), encoding="utf-8")
        record = self.out / "findings.json"
        data = load_json(record)
        data["findings"] = [f for f in data["findings"] if f["rule"] != "JA-02"]
        record.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        findings.render(self.out)
        self.assertTrue(any("JA-02 has no finding" in p for p in contract_check.problems(self.out)))

    def test_record_path_outside_snapshot_fails(self):
        self.complete_run()
        findings.merge(self.out / "findings.json", [self.fragment({"exemptions": [
            {"path": "gude.md", "rule": "EN-04", "reason": "typo in path"}]})])
        findings.render(self.out)
        self.assertTrue(any("'gude.md', which is not in snapshot.json" in p for p in contract_check.problems(self.out)))

    def test_malformed_fragments_are_refused(self):
        self.complete_run()
        record = self.out / "findings.json"
        before = record.read_bytes()
        for bad in ([1], {"findings": {"id": "T-001"}}, {"findings": ["T-001"]}, {"meta": []},
                    {"schema_version": 2}, {"exemptions": [{"path": "guide.md", "rule": "EN-04", "text": 1, "reason": "x"}]}):
            with self.assertRaises(findings.RecordError, msg=bad):
                findings.merge(record, [self.fragment(bad)])
        self.assertEqual(record.read_bytes(), before)


class DocumentationTests(unittest.TestCase):
    def test_every_rule_and_perspective_is_documented(self):
        patterns = (SKILL / "reference" / "patterns.md").read_text(encoding="utf-8")
        structure = (SKILL / "reference" / "structure.md").read_text(encoding="utf-8")
        content = (SKILL / "reference" / "content.md").read_text(encoding="utf-8")
        documented = set(re.findall(r"^### `([A-Z]+-\d+)`", patterns, re.M))
        self.assertEqual(documented, {r["id"] for r in RULES["rules"]})
        self.assertEqual(set(re.findall(r"^### `(STR-\d+)`", structure, re.M)),
                         {p["id"] for p in RULES["perspectives"] if p["id"].startswith("STR-")})
        self.assertEqual(set(re.findall(r"^### `(CON-\d+)`", content, re.M)),
                         {p["id"] for p in RULES["perspectives"] if p["id"].startswith("CON-")})

    def test_every_genre_is_documented(self):
        rewrite = (SKILL / "reference" / "rewrite.md").read_text(encoding="utf-8")
        self.assertEqual(set(re.findall(r"^\| [^|]+ \(`([a-z]+)`\) \|", rewrite, re.M)), set(genre_table(RULES)))

    def test_references_are_cited_and_headed(self):
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        for ref in (SKILL / "reference").glob("*.md"):
            self.assertIn(f"reference/{ref.name}", skill)
            self.assertIn("**Read when:**", "\n".join(ref.read_text(encoding="utf-8").splitlines()[:5]), ref.name)
        for cited in set(re.findall(r"reference/[a-z-]+\.md", skill)):
            self.assertTrue((SKILL / cited).is_file(), cited)

    def test_skill_docs_are_free_of_the_tells_they_describe(self):
        for doc in [ROOT / "README.md", SKILL / "SKILL.md", SKILL / "reference" / "rewrite.md",
                    SKILL / "reference" / "verify.md"]:
            hits = [h for h in scan(doc.read_text(encoding="utf-8"))
                    if h["tier"] != "density" and h["context"] != "quote"]
            self.assertEqual(hits, [], doc.name)


if __name__ == "__main__":
    unittest.main()
