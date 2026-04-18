# config use 補完ヒント表示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `papycli config use` 実行後、現在のシェルに応じた補完再登録コマンドをヒントとして表示する。

**Architecture:** `src/papycli/main.py` の `cmd_config_use` 関数末尾に、`os.environ.get("SHELL", "")` でシェルを検出し、bash/zsh に対応したヒントメッセージを出力する数行を追加する。外部ライブラリ・新規ファイルは不要。

**Tech Stack:** Python 3.12, Click, pytest

---

### Task 1: GitHub issue 登録・ブランチ作成

**Files:**
- なし（git / gh コマンド操作のみ）

- [ ] **Step 1: GitHub issue を登録する**

```bash
gh issue create \
  --title "config use 実行時にシェル補完再登録ヒントを表示する" \
  --body "## 概要\n\`papycli config use\` で API を切り替えても静的補完スクリプトは自動更新されない。\n切り替え後に現在のシェル（bash/zsh）向けの再登録コマンドをヒントとして表示することで UX を改善する。\n\n## 動作\n- bash の場合: \`eval \"\$(papycli config completion-script bash)\"\` を表示\n- zsh の場合: \`eval \"\$(papycli config completion-script zsh)\"\` を表示\n- シェル不明の場合: bash/zsh 両方を表示" \
  --label "feature"
```

- [ ] **Step 2: main ブランチを最新化してトピックブランチを作成する**

```bash
git checkout main && git pull
git checkout -b feat/config-use-completion-hint
```

---

### Task 2: テストを書いて失敗させる

**Files:**
- Modify: `tests/unittest/test_main.py`（`papycli config use` セクションの末尾に追加）

- [ ] **Step 1: bash ヒント表示テストを追加する**

`tests/unittest/test_main.py` の `papycli config use` セクション末尾（327行目付近）に以下を追加：

```python
def test_cmd_use_shows_completion_hint_bash(
    tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """bash シェルでは bash 向けの補完ヒントを表示する。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    monkeypatch.setenv("SHELL", "/bin/bash")
    runner = CliRunner()
    spec2 = tmp_path / "otherapi.json"
    spec2.write_text(json.dumps({**MINIMAL_SPEC, "servers": [{"url": "http://other"}]}), encoding="utf-8")
    runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    runner.invoke(cli, ["config", "add", str(spec2)])

    result = runner.invoke(cli, ["config", "use", "myapi"])
    assert result.exit_code == 0
    assert 'eval "$(papycli config completion-script bash)"' in result.output


def test_cmd_use_shows_completion_hint_zsh(
    tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """zsh シェルでは zsh 向けの補完ヒントを表示する。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    monkeypatch.setenv("SHELL", "/bin/zsh")
    runner = CliRunner()
    spec2 = tmp_path / "otherapi.json"
    spec2.write_text(json.dumps({**MINIMAL_SPEC, "servers": [{"url": "http://other"}]}), encoding="utf-8")
    runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    runner.invoke(cli, ["config", "add", str(spec2)])

    result = runner.invoke(cli, ["config", "use", "myapi"])
    assert result.exit_code == 0
    assert 'eval "$(papycli config completion-script zsh)"' in result.output


def test_cmd_use_shows_completion_hint_unknown_shell(
    tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """シェルが不明な場合は bash/zsh 両方のヒントを表示する。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    monkeypatch.delenv("SHELL", raising=False)
    runner = CliRunner()
    spec2 = tmp_path / "otherapi.json"
    spec2.write_text(json.dumps({**MINIMAL_SPEC, "servers": [{"url": "http://other"}]}), encoding="utf-8")
    runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    runner.invoke(cli, ["config", "add", str(spec2)])

    result = runner.invoke(cli, ["config", "use", "myapi"])
    assert result.exit_code == 0
    assert 'eval "$(papycli config completion-script bash)"' in result.output
    assert 'eval "$(papycli config completion-script zsh)"' in result.output
```

- [ ] **Step 2: テストを実行して FAIL を確認する**

```bash
uv run pytest tests/unittest/test_main.py::test_cmd_use_shows_completion_hint_bash \
              tests/unittest/test_main.py::test_cmd_use_shows_completion_hint_zsh \
              tests/unittest/test_main.py::test_cmd_use_shows_completion_hint_unknown_shell \
              -v
```

期待結果: 3件 FAIL（ヒストメッセージがまだ出力されないため）

---

### Task 3: 実装する

**Files:**
- Modify: `src/papycli/main.py:179-202`（`cmd_config_use` 関数）

- [ ] **Step 1: `cmd_config_use` にヒント表示を追加する**

`src/papycli/main.py` の `cmd_config_use` 関数末尾（`click.echo(f"Switched default API to '{api_name}'")`の直後）を以下に置き換える：

```python
    set_default_api(conf, api_name)
    save_conf(conf, conf_dir)
    click.echo(f"Switched default API to '{api_name}'")

    # シェル補完の再登録ヒントを表示する
    import os
    shell = os.environ.get("SHELL", "")
    cmd_name = click.get_current_context().find_root().info_name or "papycli"
    cmd_name = Path(cmd_name).stem
    if shell.endswith("zsh"):
        click.echo(
            f'To update shell completion, run: eval "$({cmd_name} config completion-script zsh)"'
        )
    elif shell.endswith("bash"):
        click.echo(
            f'To update shell completion, run: eval "$({cmd_name} config completion-script bash)"'
        )
    else:
        click.echo(
            f'To update shell completion, run: eval "$({cmd_name} config completion-script bash)"'
            f'  # bash\n'
            f'To update shell completion, run: eval "$({cmd_name} config completion-script zsh)"'
            f'   # zsh'
        )
```

- [ ] **Step 2: テストを実行して PASS を確認する**

```bash
uv run pytest tests/unittest/test_main.py::test_cmd_use_shows_completion_hint_bash \
              tests/unittest/test_main.py::test_cmd_use_shows_completion_hint_zsh \
              tests/unittest/test_main.py::test_cmd_use_shows_completion_hint_unknown_shell \
              -v
```

期待結果: 3件 PASS

- [ ] **Step 3: 既存テストが壊れていないか確認する**

```bash
uv run pytest tests/unittest/test_main.py -v
```

期待結果: 全件 PASS

---

### Task 4: lint/型チェックを通してコミット・PR 作成

**Files:**
- なし（コード変更は Task 3 で完了）

- [ ] **Step 1: ruff チェックを通す**

```bash
uv run ruff check src/papycli/main.py tests/unittest/test_main.py
```

期待結果: 警告なし。`import os` が関数内にある場合は `ruff` の `E402` / `PLC0415` 指摘に注意。警告が出たら `import os` をファイル先頭の既存 import ブロックに移動する。

- [ ] **Step 2: mypy チェックを通す**

```bash
uv run mypy src
```

期待結果: エラーなし

- [ ] **Step 3: 全テストを実行して確認する**

```bash
uv run pytest
```

期待結果: 全件 PASS

- [ ] **Step 4: コミットする**

```bash
git add src/papycli/main.py tests/unittest/test_main.py
git commit -m "feat(config): config use 実行後にシェル補完再登録ヒントを表示する

Close #<issue番号>"
```

- [ ] **Step 5: PR を作成する**

```bash
git push -u origin feat/config-use-completion-hint
gh pr create \
  --title "feat(config): config use 実行後にシェル補完再登録ヒントを表示する" \
  --body "## 概要\n\`papycli config use\` で API を切り替えた際、静的補完スクリプトが古いままになる問題を UX 改善で対処。切り替え後に現在のシェル向けの補完再登録コマンドをヒントとして表示するようにした。\n\n## 変更内容\n- \`cmd_config_use\` に \`SHELL\` 環境変数を参照してシェルを検出するロジックを追加\n- bash → bash 向けヒント、zsh → zsh 向けヒント、不明 → 両方を表示\n\n## テスト\n- bash/zsh/不明シェルの 3 パターンのユニットテストを追加\n\nClose #<issue番号>"
```

- [ ] **Step 6: PR を 2 分おきに監視してレビューコメントに対応する**

```bash
gh pr view --comments
```

レビューコメントが追加されたら修正・追加コミット・プッシュし、修正内容をまとめて PR にコメントする。10分以上コメントがなければ監視終了。
