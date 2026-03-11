# CLAUDE.md

## プロジェクト概要

`papycli` は OpenAPI 3.0 仕様を読み込み、REST API エンドポイントをターミナルから直接呼び出せるインタラクティブな CLI を提供する Python 製ツールです。

---

## 開発環境

- Python 3.12 以上
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
│       ├── init_cmd.py      # config add コマンド（spec の変換・保存）
│       ├── api_call.py      # HTTP リクエスト実行
│       ├── checker.py       # --check / --check-strict のパラメータ検証
│       ├── completion.py    # シェル補完スクリプト生成
│       ├── config.py        # 設定ファイルの読み書き
│       ├── i18n.py          # 日英ヘルプテキストの切り替えユーティリティ
│       ├── request_filter.py # リクエストフィルタープラグイン機構
│       ├── spec_loader.py   # OpenAPI spec の読み込み・$ref 解決
│       └── summary.py       # summary コマンド・CSV 出力
├── tests/
│   ├── test_api_call.py
│   ├── test_checker.py
│   ├── test_completion.py
│   ├── test_config.py
│   ├── test_i18n.py
│   ├── test_init_cmd.py
│   ├── test_main.py
│   ├── test_request_filter.py
│   ├── test_spec_loader.py
│   └── test_summary.py
├── examples/
│   ├── docker-compose.yml
│   └── petstore-oas3.json
├── pyproject.toml
├── README.md
├── README.ja.md
├── design_doc.md
└── CLAUDE.md
```

### 主要モジュール

**`main.py`** — CLI エントリポイント
引数をパースし、各コマンド（`config add`/`use`/`remove`/`list`/`completion-script`、`spec`、`summary`、メソッド呼び出し）に処理を委譲する。シェル補完用の `_complete` 内部コマンドもここで定義する。

**`init_cmd.py`** — API 初期化（`config add` コマンドの実処理）
OpenAPI spec ファイルを受け取り、`$ref` を解決した上で papycli 内部の API 定義フォーマットに変換し、`$PAPYCLI_CONF_DIR/apis/<name>.json` に保存する。設定ファイル (`papycli.conf`) も更新する。

**`spec_loader.py`** — spec 読み込み・変換
OpenAPI spec の JSON/YAML を読み込み、`$ref` を再帰的に解決して、papycli の内部フォーマット（後述）に変換する。Python 標準ライブラリのみ（または最小限の依存）で実装する。

**`api_call.py`** — HTTP リクエスト実行
メソッド・リソースパス・オプションを受け取り、`requests` ライブラリで HTTP リクエストを実行する。パステンプレート（`/pet/{petId}`）のマッチングと値の埋め込みも担当する。リクエストフィルタープラグインの適用と、リクエスト/レスポンスのファイルログ記録も行う。

**`checker.py`** — パラメータ検証
`--check` / `--check-strict` オプション用のリクエスト前バリデーションロジック。必須パラメータの存在確認、型チェック（integer / boolean）、enum 値の検証を行い、警告メッセージのリストを返す。

**`completion.py`** — シェル補完
bash / zsh 向けの補完スクリプトを生成する。補完の候補はメソッド、リソースパス、パラメータ名、enum 値の順にコンテキストに応じて提供する。

**`config.py`** — 設定管理
`papycli.conf` の読み書きと、`PAPYCLI_CONF_DIR` 環境変数の解決を行う。ログファイルパスの取得・設定・削除も担当する。

**`request_filter.py`** — リクエストフィルタープラグイン機構
エントリポイントグループ `papycli.request_filters` に登録されたフィルター関数をプラグイン名の昇順で呼び出し、リクエスト送信前に URL・クエリパラメータ・ボディ・ヘッダーを変換できるようにする。`RequestContext` データクラスと `load_filters()` / `apply_filters()` 関数を提供する。

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
papycli config add <spec-file>
papycli config use <api-name>
papycli config remove <api-name>
papycli config list
papycli config log [PATH] [--unset]
papycli config completion-script <bash|zsh>
papycli spec [resource]
papycli summary [resource] [--csv]
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
- `--check` — 送信前にパラメータを検証する（警告を stderr に出力、リクエストは送信）
- `--check-strict` — 送信前にパラメータを検証する（警告を stderr に出力、問題があればリクエスト中止・exit 1）

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

---

## Git リポジトリ運用

### issue 管理

- ソースコードやドキュメントの追加・修正は原則として issue を作成し、それに対応する形で行う
- issue のタイトルには適切なプレフィックスをつける

| プレフィックス | 用途 |
|---------------|------|
| `feat:` | 新機能の追加 |
| `fix:` | バグ修正 |
| `refactor:` | 機能変更を伴わないリファクタリング |
| `chore:` | ビルド・依存関係・設定等のメンテナンス |
| `docs:` | ドキュメントのみの変更 |

### ブランチ・コミット・PR

- ソースコードの修正は適切な粒度でコミットし、プルリクエスト (PR) を提出する
- PR でレビュー指摘を受けた場合、必要であればコードを修正し、PR に修正した旨のコメントを追加する
