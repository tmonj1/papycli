# .env ファイル自動読み込み Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** papycli 起動時にカレントディレクトリと `PAPYCLI_CONF_DIR` の `.env` を自動読み込みし、`PAPYCLI_CUSTOM_HEADER` などの環境変数をシェルセッション外でも設定できるようにする。

**Architecture:** `main.py` に `_load_env_files()` を追加し、`cli()` を呼ぶ `main()` ラッパー関数の冒頭で呼び出す。エントリポイントを `papycli.main:cli` から `papycli.main:main` に変更する。`override=False` で読み込むためシェルで既にセットされた環境変数は上書きされない。

**Tech Stack:** `python-dotenv`（新規依存）、`click`、`pytest`

---

## File Map

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `pyproject.toml` | 変更 | `python-dotenv` を dependencies に追加、エントリポイントを `main` に変更 |
| `src/papycli/main.py` | 変更 | `_load_env_files()` と `main()` ラッパーを追加 |
| `tests/unittest/test_main.py` | 変更 | `_load_env_files()` のテストを追加 |

---

### Task 1: `python-dotenv` を依存に追加してエントリポイントを変更する

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: `pyproject.toml` の dependencies に `python-dotenv` を追加し、エントリポイントを変更する**

`pyproject.toml` の `dependencies` セクションを以下のように変更する:

```toml
dependencies = [
    "click>=8.1",
    "requests>=2.32",
    "rich>=13.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0",
]
```

`[project.scripts]` セクションを以下のように変更する:

```toml
[project.scripts]
papycli = "papycli.main:main"
```

- [ ] **Step 2: 依存を解決してインストール確認する**

```bash
uv sync
```

Expected: エラーなく完了し、`python-dotenv` がインストールされる。

- [ ] **Step 3: import が通るか確認する**

```bash
uv run python -c "from dotenv import load_dotenv; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: コミット**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add python-dotenv dependency and update entry point to main()"
```

---

### Task 2: `_load_env_files()` と `main()` を `main.py` に追加する

**Files:**
- Modify: `src/papycli/main.py`

- [ ] **Step 1: `main.py` の import セクションに `load_dotenv` を追加する**

`main.py` の先頭の import 群（現在は `import json` から始まる）に以下を追加する:

```python
import os
from dotenv import load_dotenv
```

注: `os` はすでに `import` されていないので追加する。`Path` はすでに `from pathlib import Path` でインポート済みのため不要。

- [ ] **Step 2: `_load_env_files()` 関数を追加する**

`main.py` の末尾（`for _method in ...` ブロックと `cmd_complete` の後）に以下を追加する:

```python
def _load_env_files() -> None:
    """Load .env files from CWD and PAPYCLI_CONF_DIR (shell env takes precedence)."""
    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)
    conf_dir = Path(os.environ.get("PAPYCLI_CONF_DIR", "~/.papycli")).expanduser()
    load_dotenv(dotenv_path=conf_dir / ".env", override=False)


def main() -> None:
    """Entry point wrapper: load .env files before invoking CLI."""
    _load_env_files()
    cli()
```

- [ ] **Step 3: `mypy` と `ruff` でチェックする**

```bash
uv run mypy src/
uv run ruff check src/
```

Expected: 警告・エラーなし。

- [ ] **Step 4: 既存テストが通ることを確認する**

```bash
uv run pytest tests/unittest/ -x -q
```

Expected: すべて PASS。

- [ ] **Step 5: コミット**

```bash
git add src/papycli/main.py
git commit -m "feat: add _load_env_files() and main() entry point for .env auto-loading"
```

---

### Task 3: `_load_env_files()` のテストを追加する

**Files:**
- Modify: `tests/unittest/test_main.py`

- [ ] **Step 1: テストを書く**

`test_main.py` の既存 import 群に以下を追加する（`monkeypatch` は pytest 組み込みなので追加不要）:

```python
from papycli.main import _load_env_files
```

次に、ファイル末尾に以下のテストクラスを追加する:

```python
class TestLoadEnvFiles:
    def test_loads_cwd_dotenv(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """カレントディレクトリの .env が読み込まれること。"""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR_CWD=hello_cwd\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("TEST_VAR_CWD", raising=False)

        _load_env_files()

        assert os.environ.get("TEST_VAR_CWD") == "hello_cwd"

    def test_loads_conf_dir_dotenv(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """PAPYCLI_CONF_DIR 配下の .env が読み込まれること。"""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR_CONF=hello_conf\n", encoding="utf-8")
        monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
        monkeypatch.delenv("TEST_VAR_CONF", raising=False)
        # カレントディレクトリには .env を置かない（tmp_path とは別ディレクトリ）
        cwd_without_env = tmp_path / "subdir"
        cwd_without_env.mkdir()
        monkeypatch.chdir(cwd_without_env)

        _load_env_files()

        assert os.environ.get("TEST_VAR_CONF") == "hello_conf"

    def test_shell_env_takes_precedence(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """シェルで既にセットされた環境変数が .env の値で上書きされないこと。"""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR_OVERRIDE=from_dotenv\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TEST_VAR_OVERRIDE", "from_shell")

        _load_env_files()

        assert os.environ.get("TEST_VAR_OVERRIDE") == "from_shell"

    def test_no_error_when_no_dotenv(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """.env が存在しない場合にエラーにならないこと。"""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))

        # 例外が発生しないことを確認する
        _load_env_files()

    def test_cwd_takes_precedence_over_conf_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """カレントディレクトリの .env が PAPYCLI_CONF_DIR の .env より優先されること。"""
        cwd_dir = tmp_path / "cwd"
        conf_dir = tmp_path / "conf"
        cwd_dir.mkdir()
        conf_dir.mkdir()
        (cwd_dir / ".env").write_text("TEST_VAR_PRIO=from_cwd\n", encoding="utf-8")
        (conf_dir / ".env").write_text("TEST_VAR_PRIO=from_conf\n", encoding="utf-8")
        monkeypatch.chdir(cwd_dir)
        monkeypatch.setenv("PAPYCLI_CONF_DIR", str(conf_dir))
        monkeypatch.delenv("TEST_VAR_PRIO", raising=False)

        _load_env_files()

        assert os.environ.get("TEST_VAR_PRIO") == "from_cwd"
```

テストファイルの先頭 import 群に `import os` も追加する（まだなければ）。

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/unittest/test_main.py::TestLoadEnvFiles -v
```

Expected: ImportError または AttributeError（`_load_env_files` が未定義のため）— Task 2 完了後は PASS になるはず。Task 2 を先に完了している場合はこのステップをスキップする。

- [ ] **Step 3: テストを実行して全 PASS することを確認する**

```bash
uv run pytest tests/unittest/test_main.py::TestLoadEnvFiles -v
```

Expected:
```
PASSED tests/unittest/test_main.py::TestLoadEnvFiles::test_loads_cwd_dotenv
PASSED tests/unittest/test_main.py::TestLoadEnvFiles::test_loads_conf_dir_dotenv
PASSED tests/unittest/test_main.py::TestLoadEnvFiles::test_shell_env_takes_precedence
PASSED tests/unittest/test_main.py::TestLoadEnvFiles::test_no_error_when_no_dotenv
PASSED tests/unittest/test_main.py::TestLoadEnvFiles::test_cwd_takes_precedence_over_conf_dir
5 passed
```

- [ ] **Step 4: テスト全体を実行して既存テストが壊れていないことを確認する**

```bash
uv run pytest tests/unittest/ -q
```

Expected: すべて PASS。

- [ ] **Step 5: `mypy` と `ruff` でチェックする**

```bash
uv run mypy src/
uv run ruff check src/
```

Expected: 警告・エラーなし。

- [ ] **Step 6: コミット**

```bash
git add tests/unittest/test_main.py
git commit -m "test: add tests for _load_env_files() .env auto-loading"
```
