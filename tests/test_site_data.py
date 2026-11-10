"""The landing page and README state facts about the skill; keep them true.

site/data.js bundles copies of rules.json, the reference entries and sample
scans (site/build_data.py rebuilds them), and index.html and app.js state
counts, phases and corpus results. A change to the skill that makes any of
them stale fails here instead of shipping to the published page.
"""
import io
import json
import re
import sys
import unittest
from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "site"))
sys.path.insert(0, str(ROOT / "skills" / "deslop" / "scripts"))

import build_data  # noqa: E402
import serve  # noqa: E402

SCRIPTS = ROOT / "skills" / "deslop" / "scripts"
HTML = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
PAGE = HTML + APP


def rounded(value):
    """Floats compared to 9 places: Python versions differ in the last digit."""
    if isinstance(value, float):
        return round(value, 9)
    if isinstance(value, dict):
        return {k: rounded(v) for k, v in value.items()}
    if isinstance(value, list):
        return [rounded(v) for v in value]
    return value


def skill_phases():
    table = (ROOT / "skills" / "deslop" / "SKILL.md").read_text(encoding="utf-8").split("## Phases", 1)[1].split("\n## ", 1)[0]
    return re.findall(r"^\| ([A-Z]+) \|", table, re.M)


class SiteDataTests(unittest.TestCase):
    def test_bundled_data_matches_its_sources(self):
        current = build_data.read_data()
        self.assertEqual(rounded(build_data.build(current)), rounded(current),
                         "site/data.js is stale; run python3 site/build_data.py")

    def test_bundled_data_is_written_in_its_canonical_form(self):
        # A hand edit that keeps the content but not the layout still round-trips.
        text = build_data.DATA.read_text(encoding="utf-8")
        self.assertEqual(build_data.render(build_data.read_data()), text)

    def test_every_count_on_the_page_matches_the_skill(self):
        rules, perspectives = serve.RULES["rules"], serve.RULES["perspectives"]
        clis = [p for p in SCRIPTS.glob("*.py") if 'if __name__ == "__main__":' in p.read_text(encoding="utf-8")]
        claims = {
            r"(\d+) ?(?:の決定論的ルール|決定論的ルール|ルール|Rules|<span>rules)": len(rules),
            r"(\d+) ?(?:の観点|観点|<span>perspectives)": len(perspectives),
            r"(\d+) ?(?:種のジャンル|種類の文書ジャンル|<span>genres)": len(serve.RULES["genres"]),
            r"(\d+) ?(?:フェーズ|Phases)": len(skill_phases()),
            r"(\d+)つの Python スクリプト": len(clis),
        }
        for pattern, expected in claims.items():
            found = re.findall(pattern, PAGE)
            with self.subTest(pattern=pattern):
                self.assertTrue(found)
                self.assertEqual({int(n) for n in found}, {expected})

    def test_rule_breakdown_matches_rules_json(self):
        counts = Counter(r["id"].split("-")[0] for r in serve.RULES["rules"])
        note = re.search(r'<div class="strip-note">(ART \d+[^<]*)</div>', HTML).group(1)
        self.assertEqual({k: int(v) for k, v in re.findall(r"([A-Z]+) (\d+)", note)}, dict(counts))
        kinds = Counter(p["id"].split("-")[0] for p in serve.RULES["perspectives"])
        self.assertIn(f"Content {kinds['CON']}種 ＋ Structure {kinds['STR']}種", HTML)

    def test_atlas_filter_counts_match_the_filters(self):
        rules, perspectives = serve.RULES["rules"], serve.RULES["perspectives"]
        expected = {
            "all": len(rules) + len(perspectives),
            "artifact": sum(r["tier"] == "artifact" for r in rules),
            "ja": sum(r["id"].startswith("JA-") for r in rules),
            "en": sum(r["id"].startswith("EN-") for r in rules),
            # app.js renderAtlas: the density filter also shows CNT-01 and EMO-01.
            "density": sum(r["tier"] in ("density", "content") or r["id"] == "EMO-01" for r in rules),
            "perspective": len(perspectives),
        }
        found = dict(re.findall(r'data-atlas-filter="(\w+)">[^<(]*\((\d+)\)</button>', HTML))
        self.assertEqual({k: int(v) for k, v in found.items()}, expected)
        self.assertIn(f"{expected['all']} / {expected['all']} 件を表示中", HTML)

    def test_hero_hit_counts_match_the_sample_scans(self):
        data = build_data.read_data()
        self.assertEqual(re.findall(r'<span class="bad">(\d+) hits</span>', HTML),
                         [str(data["samples"]["ja_cache"]["before_scan"]["summary"]["total"])])
        self.assertEqual(re.findall(r'<span class="bad">(\d+) hits</span>', APP),
                         [str(data["samples"]["en_cache"]["before_scan"]["summary"]["total"])])

    def test_test_count_on_the_page_is_the_suite_size(self):
        count = sum(len(re.findall(r"^\s*def test_", p.read_text(encoding="utf-8"), re.M))
                    for p in (ROOT / "tests").glob("test_*.py"))
        stated = re.search(r'<div class="strip-number">(\d+)<span>tests</span></div>', HTML).group(1)
        self.assertEqual(int(stated), count)

    def test_phase_stepper_follows_skill_md(self):
        phases = skill_phases()
        self.assertEqual(re.findall(r'<span class="phase-title">([A-Z]+)</span>', HTML), phases)
        self.assertEqual(re.findall(r'^\s+id: "([A-Z]+)",$', APP, re.M), phases)

    def test_genre_corpus_results_match_the_detector(self):
        details = APP[APP.index("const GENRE_DETAILS"):APP.index("const PHASES")]
        found = re.findall(r'\n    (\w+): \{.*?corpus: "(\S+\.md) \(([\d,]+)字: (\d+) hits → (\d+) open', details, re.S)
        self.assertEqual(sorted(g for g, *_ in found), sorted(g["id"] for g in serve.RULES["genres"]))
        for genre, path, chars, total, open_ in found:
            with self.subTest(genre=genre, path=path):
                result = serve.run_detection((ROOT / path).read_text(encoding="utf-8"), genre)
                self.assertEqual((int(chars.replace(",", "")), int(total), int(open_)),
                                 (result["metrics"]["chars"], result["summary"]["total"], result["summary"]["open"]))

    def test_genre_adjustments_match_rules_json(self):
        details = APP[APP.index("const GENRE_DETAILS"):APP.index("const PHASES")]
        genres = {g["id"]: g for g in serve.RULES["genres"]}
        defaults = {r["id"]: r.get("max") for r in serve.RULES["rules"]}
        for genre, text in re.findall(r'\n    (\w+): \{.*?adjust: "([^"]*)"', details, re.S):
            g = genres[genre]
            with self.subTest(genre=genre):
                named = set(re.findall(r"(?:ART|CNT|DEN|EMO|EN|JA)-\d+", text))
                self.assertEqual(named, set(g["exempt"]) | set(g["limits"]))
                for rule, value in re.findall(r"(DEN-\d+)[^/、]*?上限(?:を)? ?([\d.]+)", text):
                    self.assertEqual(float(value), g["limits"][rule]["max"])
        general = re.search(r'adjust: "デフォルト密度上限（太字 ([\d.]+)/1000字、見出し ([\d.]+)/1000字、リスト比率 ([\d.]+)）"', details)
        self.assertEqual([float(v) for v in general.groups()], [defaults["DEN-01"], defaults["DEN-05"], defaults["DEN-06"]])

    def test_readme_pipeline_and_counts_match_the_skill(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("`" + " → ".join(skill_phases()) + "`", readme)
        tiers = Counter(r["tier"] for r in serve.RULES["rules"])
        self.assertIn(f"{tiers['artifact']} chat-artifact rules", readme)
        self.assertIn(f"{tiers['lexical']} lexical rules", readme)
        self.assertIn(f"{tiers['density']} density", readme)
        words = {8: "Eight", 17: "seventeen"}
        kinds = Counter(p["id"].split("-")[0] for p in serve.RULES["perspectives"])
        self.assertIn(f"{words[kinds['CON']]} content perspectives", readme)
        self.assertIn(f"{words[kinds['STR']]} structural perspectives", readme)

    def test_build_check_reports_staleness(self):
        stale = json.loads(json.dumps(build_data.read_data()))
        stale["rules"][0]["note"] = "edited by hand"
        self.assertNotEqual(build_data.build(stale)["rules"][0]["note"], "edited by hand")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(build_data.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
