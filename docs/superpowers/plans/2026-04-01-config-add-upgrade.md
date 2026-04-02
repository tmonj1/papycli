# config add --upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `papycli config add` を新規登録専用にし、既存 API の更新には `--upgrade` フラグを必須とする。

**Architecture:** `src/papycli/main.py` の `cmd_config_add` にのみ変更を加える。`--upgrade` フラグ追加・既存 API チェック・出力メッセージの分岐のすべてをこの関数内で完結させる。`init_cmd.py` は変更しない。

**Tech Stack:** Python 3.12, click, pytest, Click CliRunner (テスト)

---

## ファイルマップ

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `src/papycli/main.py` | 修正 | `cmd_config_add` に `--upgrade` フラグと既存 API チェックを追加 |
| `tests/unittest/test_main.py` | 修正 | `--upgrade` 関連テストを追加 |

---

### Task 1: 既存 API への `config add` がエラーになるテストを書く

**Files:**
- Modify: `tests/unittest/test_main.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/unittest/test_main.py` の `# papycli config add` セクション末尾に以下を追加する:

```python
def test_cmd_add_already_registered_errors(
    tmp_path: Path, minimal_spec_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """config add を同じ API 名で2回実行するとエラーになる。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()
    runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    result = runner.invoke(cli, ["config", "add", str(minimal_spec_file)])
    assert result.exit_code != 0
    assert "already registered" in result.output
    assert "--upgrade" in result.output
```

- [ ] **Step 2: テストが失敗することを確認する**

```
uv run pytest tests/unittest/test_main.py::test_cmd_add_already_registered_errors -v
```

Expected: FAIL（現状は2回目も exit 0 で成功してしまう）

---

### Task 2: `config add` に既存 API チェックを実装する

**Files:**
- Modify: `src/papycli/main.py:85-119`

- [ ] **Step 1: `--upgrade` フラグと既存チェックを追加する**

`main.py` の `cmd_config_add` コマンド定義を以下のように変更する:

```python
@cmd_config.command(
    "add",
    help=h(
        "Register an API from an OpenAPI spec file.",
        "OpenAPI spec ファイルから API を登録する。",
    ),
)
@click.argument("spec_file", metavar="SPEC_FILE", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--upgrade", "upgrade", is_flag=True,
    help=h(
        "Update an existing registered API with a new spec.",
        "既存の登録済み API を新しい spec で更新する。",
    ),
)
def cmd_config_add(spec_file: str, upgrade: bool) -> None:
    spec_path = Path(spec_file)
    conf_dir = get_conf_dir()

    if spec_path.stem in ("default", "aliases"):
        click.echo(
            f"Error: '{spec_path.stem}' is a reserved name and cannot be used as an API name.",
            err=True,
        )
        sys.exit(1)

    conf = load_conf(conf_dir)
    api_name = spec_path.stem
    already_registered = api_name in conf and isinstance(conf[api_name], dict)

    if not upgrade and already_registered:
        click.echo(
            f"Error: API '{api_name}' is already registered. Use --upgrade to update it.",
            err=True,
        )
        sys.exit(1)

    try:
        api_name, base_url = init_api(spec_path, conf_dir)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    register_initialized_api(conf, api_name, spec_path, base_url)
    save_conf(conf, conf_dir)

    if upgrade and already_registered:
        click.echo(f"Updated API '{api_name}'")
    else:
        click.echo(f"Registered API '{api_name}'")
    if base_url:
        click.echo(f"  Base URL : {base_url}")
    else:
        click.echo("  Base URL : (not set — edit papycli.conf to add url)")
    click.echo(f"  Conf dir : {conf_dir}")
```

- [ ] **Step 2: Task 1 のテストが通ることを確認する**

```
uv run pytest tests/unittest/test_main.py::test_cmd_add_already_registered_errors -v
```

Expected: PASS

- [ ] **Step 3: 既存テストが壊れていないことを確認する**

```
uv run pytest tests/unittest/test_main.py -v
```

Expected: すべて PASS

---

### Task 3: `--upgrade` で既存 API を更新するテストを書いて通す

**Files:**
- Modify: `tests/unittest/test_main.py`

- [ ] **Step 1: テストを書く**

`test_cmd_add_already_registered_errors` の直後に以下を追加する:

```python
def test_cmd_add_upgrade_updates_existing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--upgrade で既存 API の spec・apidef・URL が更新される。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    runner = CliRunner()

    # 旧 spec で登録
    old_spec: dict[str, Any] = {
        "openapi": "3.0.2",
        "servers": [{"url": "http://old.example.com/api"}],
        "paths": {
            "/items": {"get": {"parameters": []}},
        },
    }
    spec_file = tmp_path / "myapi.json"
    spec_file.write_text(json.dumps(old_spec), encoding="utf-8")
    runner.invoke(cli, ["config", "add", str(spec_file)])

    # 新 spec で --upgrade
    new_spec: dict[str, Any] = {
        "openapi": "3.0.2",
        "servers": [{"url": "http://new.example.com/api"}],
        "paths": {
            "/items": {"get": {"parameters": []}},
            "/users": {"get": {"parameters": []}},
        },
    }
    spec_file.write_text(json.dumps(new_spec), encoding="utf-8")
    result = runner.invoke(cli, ["config", "add", "--upgrade", str(spec_file)])

    assert result.exit_code == 0
    assert "Updated API 'myapi'" in result.output
    assert "http://new.example.com/api" in result.output

    conf = json.loads((tmp_path / "papycli.conf").read_text(encoding="utf-8"))
    assert conf["myapi"]["url"] == "http://new.example.com/api"

    apidef = json.loads((tmp_path / "apis" / "myapi.json").read_text(encoding="utf-8"))
    assert "/users" in apidef


def test_cmd_add_upgrade_on_new_api_registers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--upgrade で未登録 API を指定すると新規登録として扱われる。"""
    monkeypatch.setenv("PAPYCLI_CONF_DIR", str(tmp_path))
    spec: dict[str, Any] = {
        "openapi": "3.0.2",
        "servers": [{"url": "http://localhost:9000/api"}],
        "paths": {"/items": {"get": {"parameters": []}}},
    }
    spec_file = tmp_path / "myapi.json"
    spec_file.write_text(json.dumps(spec), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "add", "--upgrade", str(spec_file)])

    assert result.exit_code == 0
    assert "Registered API 'myapi'" in result.output
    conf = json.loads((tmp_path / "papycli.conf").read_text(encoding="utf-8"))
    assert conf["default"] == "myapi"
```

- [ ] **Step 2: テストが通ることを確認する**

```
uv run pytest tests/unittest/test_main.py::test_cmd_add_upgrade_updates_existing tests/unittest/test_main.py::test_cmd_add_upgrade_on_new_api_registers -v
```

Expected: 両方 PASS

---

### Task 4: Lint・型チェックを通してコミットする

**Files:**
- No new files

- [ ] **Step 1: ruff チェック**

```
uv run ruff check src/papycli/main.py tests/unittest/test_main.py
```

Expected: 警告・エラーなし

- [ ] **Step 2: ruff フォーマット**

```
uv run ruff format src/papycli/main.py tests/unittest/test_main.py
```

- [ ] **Step 3: mypy チェック**

```
uv run mypy src/
```

Expected: エラーなし

- [ ] **Step 4: テストスイート全体を実行する**

```
uv run pytest tests/unittest/ -v
```

Expected: すべて PASS

- [ ] **Step 5: コミットする**

```bash
git add src/papycli/main.py tests/unittest/test_main.py
git commit -m "feat: add --upgrade option to config add command"
```

---

### Task 5: GitHub issue を作成してトピックブランチを切る

> このタスクは実装前に行う（issue → branch の順）。Task 1 の前に実施すること。

- [ ] **Step 1: issue を作成する**

```bash
gh issue create \
  --title "feat: config add に --upgrade オプションを追加する" \
  --label "feature" \
  --body "$(cat <<'EOF'
## 概要

\`papycli config add\` コマンドに \`--upgrade\` オプションを追加する。

## 動作

- \`config add <spec>\`: 新規登録専用。既存 API 名があればエラー。
- \`config add --upgrade <spec>\`: 既存 API の spec・apidef・URL を更新する。未登録の場合は新規登録。

## 参考

設計書: \`docs/superpowers/specs/2026-04-01-config-add-upgrade-design.md\`
EOF
)"
```

- [ ] **Step 2: issue 番号を確認してトピックブランチを作成する**

（issue 番号を `<N>` に置き換えて実行する）

```bash
git checkout main
git pull
git checkout -b feature/config-add-upgrade-<N>
```

---

### Task 6: PR を作成する

- [ ] **Step 1: push する**

```bash
git push -u origin feature/config-add-upgrade-<N>
```

- [ ] **Step 2: PR を作成する**

（issue 番号を `<N>` に置き換えて実行する）

```bash
gh pr create \
  --title "feat: config add に --upgrade オプションを追加する" \
  --body "$(cat <<'EOF'
## Summary

- \`papycli config add\` を新規登録専用に変更し、既存 API への再登録はエラーにする
- \`--upgrade\` フラグを追加し、既存 API の spec・apidef・base URL を更新できるようにする
- \`--upgrade\` で未登録 API を指定した場合は新規登録として扱う

Closes #<N>

## Test plan

- [ ] \`config add\` で既存 API 名を指定するとエラー終了・"already registered" メッセージが出る
- [ ] \`config add --upgrade\` で既存 API を更新すると conf と apidef が書き換わる
- [ ] \`config add --upgrade\` で未登録 API を指定すると新規登録される
- [ ] \`uv run pytest tests/unittest/\` がすべて PASS する

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## 実行順序

Tasks は以下の順で実行する:

1. **Task 5**（issue 作成・ブランチ作成）
2. **Task 1**（失敗テスト追加）
3. **Task 2**（実装）
4. **Task 3**（upgrade テスト追加・確認）
5. **Task 4**（lint・型チェック・コミット）
6. **Task 6**（PR 作成）
