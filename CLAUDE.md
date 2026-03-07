# CLAUDE.md

## プロジェクト概要

`papycli` は OpenAPI 3.0 仕様を読み込み、REST API エンドポイントをターミナルから直接呼び出せるインタラクティブな CLI を提供する Python 製ツールです。

---

## 開発環境

- Python 3.8 以上
- 依存ライブラリは `pyproject.toml` で管理する

### セットアップ

```bash
pip install -e ".[dev]"
```

### 開発用ツール

| ツール | 用途 |
|--------|------|
| `pytest` | テスト実行 |
| `ruff` | Lint + フォーマット |
| `mypy` | 型チェック |

---

## アーキテクチャ

### ディレクトリ構成

```
papycli/
├── src/
│   └── papycli/
│       ├── __init__.py
│       ├── main.py          # エントリポイント・引数パース
│       ├── init_cmd.py      # --init コマンド（spec の変換・保存）
│       ├── api_call.py      # HTTP リクエスト実行
│       ├── completion.py    # シェル補完スクリプト生成
│       ├── config.py        # 設定ファイルの読み書き
│       ├── spec_loader.py   # OpenAPI spec の読み込み・$ref 解決
│       └── summary.py       # --summary / --summary-csv
├── tests/
├── examples/
│   ├── docker-compose.yml
│   └── petstore-oas3.json
├── pyproject.toml
├── README.md
└── CLAUDE.md
```

### 主要モジュール

**`main.py`** — CLI エントリポイント
引数をパースし、各コマンド（`init`、`use`、`conf`、`summary`、`completion-script`、メソッド呼び出し）に処理を委譲する。シェル補完用の `_complete` 内部コマンドもここで定義する。

**`init_cmd.py`** — API 初期化
OpenAPI spec ファイルを受け取り、`$ref` を解決した上で papycli 内部の API 定義フォーマットに変換し、`$PAPYCLI_CONF_DIR/apis/<name>.json` に保存する。設定ファイル (`papycli.conf`) も更新する。

**`spec_loader.py`** — spec 読み込み・変換
OpenAPI spec の JSON/YAML を読み込み、`$ref` を再帰的に解決して、papycli の内部フォーマット（後述）に変換する。Python 標準ライブラリのみ（または最小限の依存）で実装する。

**`api_call.py`** — HTTP リクエスト実行
メソッド・リソースパス・オプションを受け取り、`requests` ライブラリで HTTP リクエストを実行する。パステンプレート（`/pet/{petId}`）のマッチングと値の埋め込みも担当する。

**`completion.py`** — シェル補完
bash / zsh 向けの補完スクリプトを生成する。補完の候補はメソッド、リソースパス、パラメータ名、enum 値の順にコンテキストに応じて提供する。

**`config.py`** — 設定管理
`papycli.conf` の読み書きと、`PAPYCLI_CONF_DIR` 環境変数の解決を行う。

**`summary.py`** — サマリー表示
登録済み API のエンドポイント一覧を整形して出力する。`--summary-csv` では CSV 形式で出力する。

---

## 内部データフォーマット

### API 定義ファイル (`apis/<name>.json`)

```json
{
  "/pet": [
    {
      "method": "post",
      "query_parameters": [],
      "post_parameters": [
        {"name": "name", "type": "string", "required": true},
        {"name": "status", "type": "string", "required": false, "enum": ["available", "pending", "sold"]},
        {"name": "photoUrls", "type": "array", "required": true}
      ]
    }
  ],
  "/pet/findByStatus": [
    {
      "method": "get",
      "query_parameters": [
        {"name": "status", "type": "string", "required": false, "enum": ["available", "pending", "sold"]}
      ],
      "post_parameters": []
    }
  ],
  "/pet/{petId}": [
    {
      "method": "get",
      "query_parameters": [],
      "post_parameters": []
    },
    {
      "method": "delete",
      "query_parameters": [],
      "post_parameters": []
    }
  ]
}
```

### 設定ファイル (`papycli.conf`)

```json
{
  "default": "petstore",
  "petstore": {
    "openapispec": "petstore.json",
    "apidef": "petstore.json",
    "url": "http://localhost:8080/api/v3"
  }
}
```

---

## CLI 仕様

### コマンド構文

```
papycli <method> <resource> [options]
papycli init <spec-file>
papycli use <api-name>
papycli conf
papycli summary [resource] [--csv]
papycli completion-script <bash|zsh>
papycli --version
papycli --help / -h
```

### サポートするメソッド

`get | post | put | patch | delete` をサポートする。

### パラメータ処理

- `-q <name> <value>` — URL クエリパラメータ。同じ名前を繰り返し可能（`?status=a&status=b`）
- `-p <name> <value>` — JSON ボディパラメータ。同じキーを繰り返すと配列を構築する
- `-p <name.subname> <value>` — ドット記法で 1 レベルのネストオブジェクトを構築する
- `-d <json>` — 生の JSON 文字列。`-p` オプションを上書きする
- `-H <header: value>` — カスタム HTTP ヘッダー

### パステンプレートのマッチング

リソースパスに数値や文字列が含まれる場合（例：`/pet/99`）、API 定義内のテンプレート（`/pet/{petId}`）にマッチさせ、値を埋め込んでリクエストを送信する。

---

## 環境変数

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `PAPYCLI_CONF_DIR` | `~/.papycli` | 設定ディレクトリのパス |
| `PAPYCLI_CUSTOM_HEADER` | （なし） | 全リクエストに付与するカスタムヘッダー（改行区切りで複数指定可） |

---

## テスト方針

- `tests/` 以下にユニットテストを配置する
- HTTP リクエストは `responses` ライブラリ等でモックして実テストしない
- OpenAPI spec の変換ロジックは代表的なケースを網羅するテストを書く

---

## コーディング規約

- フォーマッタ・Lint は `ruff` を使用する
- 型ヒントを積極的に使用し、`mypy` でチェックを通す
- 関数・モジュールの公開 API にのみ docstring を書く（内部実装には不要）
- エラーメッセージはユーザーが原因を特定しやすい内容にする
