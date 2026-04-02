# .env ファイル自動読み込み 設計ドキュメント

**日付**: 2026-04-02

---

## 概要

papycli 起動時に `.env` ファイルを自動読み込みし、`PAPYCLI_CUSTOM_HEADER` などの環境変数をシェルセッション外でも設定できるようにする。

主なユースケースは API の Bearer トークンなど認証情報を `.env` に書いておき、`PAPYCLI_CUSTOM_HEADER` 経由で渡すこと。

---

## スコープ

- **対象**: `main.py` のエントリポイントで起動時に一度だけ読み込む
- **対象外**: `.env.local`、`.env.production` など複数ファイルの読み分けは実装しない
- **対象外**: `--env-file` による明示的な指定オプションは実装しない

---

## 読み込み優先順位

1. シェルで既にセットされた環境変数（最優先・上書きしない）
2. カレントディレクトリの `.env`
3. `PAPYCLI_CONF_DIR` 内の `.env`（デフォルト `~/.papycli/.env`）

カレントディレクトリと `PAPYCLI_CONF_DIR` の両方に `.env` がある場合はカレントディレクトリを優先する。`override=False` で読み込むため、先に読んだ値が勝つ。

---

## 依存ライブラリ

`python-dotenv` を `pyproject.toml` の `dependencies` に追加する。

---

## 実装詳細

### `main.py`

`cli()` グループの実行前、`main()` 冒頭で `_load_env_files()` を呼び出す。

```python
from pathlib import Path
import os
from dotenv import load_dotenv

def _load_env_files() -> None:
    # カレントディレクトリの .env（override=False でシェル優先）
    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)
    # PAPYCLI_CONF_DIR の .env（カレントディレクトリで設定済みの値は上書きしない）
    conf_dir = Path(os.environ.get("PAPYCLI_CONF_DIR", "~/.papycli")).expanduser()
    load_dotenv(dotenv_path=conf_dir / ".env", override=False)
```

### 動作上の注意点

- `.env` ファイルが存在しない場合、`load_dotenv` は何もしないため安全
- カレント `.env` で `PAPYCLI_CONF_DIR` を設定した場合、グローバル `.env` の読み込み時には既にその値が環境変数として反映されている（プロジェクトごとに `PAPYCLI_CONF_DIR` を切り替えるユースケースをサポート）

---

## テスト方針

`tests/unittest/test_main.py` に以下を追加する。

| テストケース | 検証内容 |
|---|---|
| カレントディレクトリの `.env` 読み込み | `.env` に書いた変数が環境変数として設定されること |
| グローバル `.env` 読み込み | `PAPYCLI_CONF_DIR` 配下の `.env` が読み込まれること |
| シェル優先 | シェルで既にセットされた環境変数が `.env` の値で上書きされないこと |
| ファイルなし | `.env` が存在しない場合にエラーにならないこと |
