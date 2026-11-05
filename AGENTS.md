# AGENTS.md

Agent skill `deslop` (`skills/deslop/SKILL.md`): rewrites Japanese and English
documents until no machine-generated style remains, modelled on security-scan's
phase, run-contract and contract-check structure.

- `make check` before reporting done (it runs the tests).
- Scripts are standard library only, so the skill stays self-contained when symlinked.
- Every rule in `scripts/rules.json` has a `### \`ID\`` entry in `reference/patterns.md`, every perspective one in `reference/structure.md`; the tests enforce it.
- Every genre in `scripts/rules.json` has a row in `reference/rewrite.md` §Genre; a genre may exempt lexical and density rules and move density limits, never touch artifact rules — except `template`, which exempts ART-07 (unfilled placeholders are its fields).
- Every `reference/*.md` must be cited from SKILL.md and open with a `**Read when:**` line.
- `site/data.js` is generated: after changing rules, reference entries or samples, run `python3 site/build_data.py`. `tests/test_site_data.py` also checks the counts, phases and corpus results the page states.
- `examples/before.*.md` and `examples/after.*.md` are fixtures; the tests depend on their exact contents. An `after` sample must stay free of every rule hit.
