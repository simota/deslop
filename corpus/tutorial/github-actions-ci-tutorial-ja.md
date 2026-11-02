# Python プロジェクト（pytest + ruff）に GitHub Actions CI を設定する

このチュートリアルでは、push と Pull Request のたびに次の 2 つを自動で実行する CI を作ります。

- **ruff** による lint とフォーマットのチェック
- **pytest** による複数の Python バージョンでのテスト

---

## 前提条件

- GitHub リポジトリがあること
- ローカルに Python 3.10 以上と Git がインストールされていること
- YAML の基本的な書き方を知っていること

---

## Step 1: プロジェクト構成を確認する

この例では次の構成を使います（`src` レイアウト）。

```text
my-project/
├── .github/
│   └── workflows/
│       └── ci.yml        ← Step 4 で作成
├── src/
│   └── mypkg/
│       ├── __init__.py
│       └── calc.py
├── tests/
│   └── test_calc.py
└── pyproject.toml
```

サンプルコード:

```python
# src/mypkg/calc.py
def add(a: int, b: int) -> int:
    return a + b
```

```python
# tests/test_calc.py
from mypkg.calc import add


def test_add() -> None:
    assert add(2, 3) == 5
```

---

## Step 2: `pyproject.toml` に依存関係とツール設定をまとめる

CI とローカルで同じ設定を使えるように、設定は 1 か所に集めます。

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mypkg"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "ruff>=0.6",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"

[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "I",   # isort
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
]
```

ポイント:

- `dev` extra に pytest と ruff を入れておくと、`pip install -e ".[dev]"` の 1 コマンドで開発環境がそろいます。
- `target-version` は `requires-python` の下限に合わせます。

---

## Step 3: CI に入れる前にローカルで動作確認する

CI で失敗する原因の大半は、ローカルでも再現できます。まずはローカルで通ることを確認しましょう。

```bash
python -m venv .venv
source .venv/bin/activate        # Windows の場合: .venv\Scripts\activate
pip install -e ".[dev]"

ruff check .
ruff format --check .
pytest
```

フォーマット違反が見つかった場合は、`ruff format .` で自動修正できます。lint の一部も `ruff check --fix .` で修正できます。

---

## Step 4: ワークフローファイルを作成する

`.github/workflows/ci.yml` を作成します。

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:   # Actions タブから手動実行できるようにする

# 同じブランチで新しい実行が始まったら、古い実行をキャンセルする
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

# GITHUB_TOKEN の権限を最小限にする
permissions:
  contents: read

jobs:
  lint:
    name: Lint (ruff)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5

      - uses: actions/setup-python@v6
        with:
          python-version: "3.13"
          cache: pip
          cache-dependency-path: pyproject.toml

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Ruff lint
        run: ruff check --output-format=github .

      - name: Ruff format check
        run: ruff format --check .

  test:
    name: Test (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v5

      - uses: actions/setup-python@v6
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
          cache-dependency-path: pyproject.toml

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run pytest
        run: pytest
```

### 各部分の解説

| 項目 | 役割 |
|---|---|
| `on` | `main` への push、すべての Pull Request、手動実行をトリガーにする |
| `concurrency` | 連続で push したときに古い実行を止め、実行時間を節約する |
| `permissions: contents: read` | ワークフローに与える権限を読み取りのみに絞る |
| `lint` ジョブ | lint の結果は Python バージョンに依存しないので、1 バージョンでだけ実行する |
| `test` ジョブの `matrix` | サポートするすべての Python バージョンでテストする |
| `fail-fast: false` | 1 つのバージョンが失敗しても、他のバージョンの結果を最後まで確認できる |
| `cache: pip` | pip のダウンロードキャッシュを再利用して、インストールを速くする |
| `--output-format=github` | ruff の指摘を PR の差分上に注釈として表示する |

> **Note:** `lint` と `test` は並列に実行されます。lint が通ってからテストを実行したい場合は、`test` ジョブに `needs: lint` を追加してください。

---

## Step 5: コミットして push する

```bash
git add .github/workflows/ci.yml pyproject.toml src tests
git commit -m "ci: add GitHub Actions workflow for ruff and pytest"
git push origin main
```

---

## Step 6: 実行結果を確認する

1. GitHub のリポジトリページで **Actions** タブを開きます。
2. `CI` ワークフローの実行をクリックします。
3. `Lint (ruff)` と `Test (Python 3.x)` の各ジョブが緑のチェックになっていれば成功です。

失敗したジョブをクリックすると、どのステップでどのようなエラーが出たかをログで確認できます。

---

## Step 7: Pull Request で動作を確かめる

わざと失敗するブランチを作って、CI が問題を検出できるか確かめます。

```bash
git switch -c test-ci
```

`src/mypkg/calc.py` に未使用の import を追加します。

```python
import os  # 未使用 → ruff の F401 で検出される


def add(a: int, b: int) -> int:
    return a + b
```

```bash
git commit -am "test: trigger ruff failure"
git push -u origin test-ci
```

このブランチで Pull Request を作成すると、`Lint (ruff)` が失敗し、該当行に注釈が表示されます。確認できたら PR を閉じてブランチを削除してください。

---

## Step 8: ブランチ保護で CI の通過を必須にする

CI が失敗している PR をマージできないようにします。

1. **Settings → Branches**（または **Settings → Rules → Rulesets**）を開きます。
2. `main` ブランチに対するルールを追加します。
3. **Require status checks to pass before merging** を有効にします。
4. 必須チェックとして次を追加します。
   - `Lint (ruff)`
   - `Test (Python 3.10)` 〜 `Test (Python 3.13)`

> **Note:** ステータスチェックは、そのワークフローが一度でも実行されていないと候補に表示されません。先に Step 5 を終わらせておいてください。

---

## Step 9（任意）: README にステータスバッジを付ける

`README.md` に次の 1 行を追加すると、CI の状態がひと目でわかるようになります。`OWNER/REPO` は自分のリポジトリに置き換えてください。

```markdown
![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)
```

---

## トラブルシューティング

| 症状 | 原因と対処 |
|---|---|
| `ModuleNotFoundError: No module named 'mypkg'` | パッケージがインストールされていません。`pip install -e ".[dev]"` を実行しているか、`[build-system]` が定義されているかを確認してください。 |
| ローカルでは通るのに CI で ruff だけ失敗する | ruff のバージョンが違う可能性があります。`ruff==0.x.y` のようにバージョンを固定すると、結果が安定します。 |
| `ruff format --check` が失敗する | ローカルで `ruff format .` を実行し、その結果をコミットしてください。 |
| 特定の Python バージョンだけ失敗する | `match` 文や新しい型構文など、古いバージョンにない構文を使っていないか確認してください。ruff の `target-version` を `requires-python` の下限に合わせると、こうした問題を検出しやすくなります。 |
| ワークフローが起動しない | ファイルの場所が `.github/workflows/` の直下になっているか、YAML のインデントが正しいかを確認してください。 |

---

## まとめ

この手順で、次の仕組みができました。

- push と PR のたびに ruff（lint とフォーマット）と pytest が自動で実行される
- 複数の Python バージョンで互換性を確認できる
- pip のキャッシュと実行のキャンセルで CI が速くなる
- ブランチ保護で、CI を通過したコードだけが `main` にマージされる

次のステップとしては、`pytest-cov` によるカバレッジ計測、pre-commit による commit 前の ruff 実行、Dependabot による Actions のバージョン自動更新などを追加するのがおすすめです。
