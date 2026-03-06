# papycli 設計ドキュメント

## 現状

- Python 3.12 / uv でパッケージ管理
- `examples/petstore-oas3.json` と `examples/docker-compose.yml` 準備済み
- ソースコードはまだない状態

---

## 技術スタック

| 役割 | ライブラリ | 選定理由 |
|------|-----------|---------|
| CLI フレームワーク | `click` | サブコマンド・オプション処理が簡潔、シェル補完の仕組みが内蔵 |
| HTTP クライアント | `requests` | デファクトスタンダード、テスト時のモックが容易 |
| 出力整形 | `rich` | テーブル・カラー出力が簡単、`--summary` の見やすい表示に活用 |
| YAML サポート | `pyyaml` | OpenAPI spec の YAML フォーマットに対応するため |
| テスト | `pytest` | 標準的な選択 |
| HTTP モック | `responses` | requests のモックライブラリ、テストで実 HTTP を避けるため |
| Lint / フォーマット | `ruff` | 高速、1 ツールで Lint とフォーマットを兼ねる |
| 型チェック | `mypy` | 型安全性の確保 |

`$ref` の解決は外部ライブラリに頼らず Python で内製する。OpenAPI spec に現れる `$ref` パターン（ドキュメント内参照 `#/components/...` と外部ファイル参照 `./file.json`）を再帰的に解決する実装で十分。

---

## プロジェクト構成

```
papycli/
├── src/
│   └── papycli/
│       ├── __init__.py
│       ├── main.py          # CLI エントリポイント（click コマンド定義）
│       ├── config.py        # 設定ファイル (papycli.conf) の読み書き
│       ├── spec_loader.py   # OpenAPI spec 読み込み・$ref 解決・内部形式変換
│       ├── init_cmd.py      # --init コマンドの処理
│       ├── api_call.py      # HTTP リクエスト実行・パステンプレートマッチング
│       ├── summary.py       # --summary / --summary-csv の出力
│       └── completion.py    # bash / zsh 補完スクリプト生成
├── tests/
│   ├── conftest.py          # pytest fixtures
│   ├── test_spec_loader.py
│   ├── test_config.py
│   ├── test_init_cmd.py
│   ├── test_api_call.py
│   └── test_summary.py
├── examples/
│   ├── docker-compose.yml
│   └── petstore-oas3.json
├── design_doc.md
├── CLAUDE.md
├── README.md
├── pyproject.toml
└── uv.lock
```

---

## 内部データフォーマット（再掲）

### API 定義ファイル (`~/.papycli/apis/<name>.json`)

```json
{
  "/pet": [
    {
      "method": "post",
      "query_parameters": [],
      "post_parameters": [
        {"name": "name",      "type": "string",  "required": true},
        {"name": "status",    "type": "string",  "required": false, "enum": ["available", "pending", "sold"]},
        {"name": "photoUrls", "type": "array",   "required": true}
      ]
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

パスパラメータ（`{petId}` 等）は API 定義のキーに保持したまま管理し、実行時にマッチングして値を埋め込む。

### 設定ファイル (`~/.papycli/papycli.conf`)

```json
{
  "default": "petstore",
  "petstore": {
    "openapispec": "petstore-oas3.json",
    "apidef": "petstore-oas3.json",
    "url": "http://localhost:8080/api/v3"
  }
}
```

---

## 実装マイルストーン

### Milestone 1 — プロジェクトスキャフォールド

**目的**: `papycli --help` / `--version` が動く骨格を作る。CI の土台を整える。

**実装内容**:
- `src/papycli/` ディレクトリ作成、`__init__.py`、`main.py`
- `pyproject.toml` に依存ライブラリ追加（click, requests, rich, pyyaml）
- 開発用依存（pytest, responses, ruff, mypy）追加
- `papycli` コマンドの entry point 登録
- `--version`、`--help` の動作確認
- `tests/conftest.py` と最初のスモークテスト

**完了条件**: `papycli --version` と `papycli --help` が動く。`pytest` がゼロエラーで通る。

---

### Milestone 2 — spec ローダーと `--init` / `--conf` / `--use`

**目的**: OpenAPI spec を読み込んで内部形式に変換し、設定ファイルを管理できるようにする。

**実装内容**:
- `spec_loader.py`
  - JSON / YAML ファイルの読み込み
  - `$ref` の再帰解決（ドキュメント内参照・外部ファイル参照）
  - OpenAPI spec → 内部 API 定義フォーマットへの変換
    - `paths` を走査してエンドポイントごとに `query_parameters` / `post_parameters` を抽出
    - `required`、`enum`、`type` を保持
- `config.py`
  - `PAPYCLI_CONF_DIR` 環境変数の解決（デフォルト `~/.papycli`）
  - `papycli.conf` の読み書き
- `init_cmd.py`
  - spec ロード → 変換 → `apis/<name>.json` 保存 → conf 更新
- `main.py` に `--init`、`--use`、`--conf` コマンド追加
- テスト: `test_spec_loader.py`、`test_config.py`、`test_init_cmd.py`
  - `$ref` 解決のパターン（内部参照、外部参照、循環参照ガード）
  - 変換結果の検証（petstore-oas3.json を使用）
  - config の CRUD

**完了条件**: `papycli --init examples/petstore-oas3.json` が成功し、`~/.papycli/apis/petstore-oas3.json` が正しい内容で生成される。`papycli --conf` で設定が表示される。テストがパスする。

---

### Milestone 3 — API 実行（コア機能）

**目的**: `papycli <method> <resource> [options]` で実際に HTTP リクエストを送れるようにする。

**実装内容**:
- `api_call.py`
  - パステンプレートマッチング
    - 例: ユーザー入力 `/pet/99` → 定義 `/pet/{petId}` にマッチ → URL を `/pet/99` に展開
    - 複数テンプレートに曖昧マッチする場合は最も具体的なものを優先
  - パラメータ処理
    - `-q name value` → URL クエリパラメータ
    - `-p name value` → JSON ボディ構築（同キー繰り返しで配列、ドット記法でネスト）
    - `-d json` → 生 JSON ボディ（`-p` を上書き）
    - `-H "Header: value"` → カスタムヘッダー
    - `PAPYCLI_CUSTOM_HEADER` 環境変数の適用
  - `requests` による HTTP 実行
  - レスポンスの出力（JSON は整形表示、それ以外はそのまま）
- `main.py` に `papycli <method> <resource>` コマンド追加
- テスト: `test_api_call.py`
  - パステンプレートマッチングの各ケース
  - `-p` による JSON 構築（配列、ネスト）
  - `responses` ライブラリで HTTP をモックしたエンドツーエンドテスト

**完了条件**: `papycli get /store/inventory`、`papycli post /pet -p name "My Dog" -p status available` 等が Petstore サーバーに対して動作する。テストがパスする。

---

### Milestone 4 — `--summary` 表示

**目的**: 登録済み API のエンドポイント一覧を見やすく表示する。

**実装内容**:
- `summary.py`
  - エンドポイント一覧の整形表示（`rich` のテーブルを使用）
  - 必須パラメータに `*` 付与、配列パラメータに `[]` 付与
  - `--summary=<resource>` でリソースパスによるフィルタリング
  - `papycli <method> <resource> --summary` で特定メソッド+リソースの詳細表示
  - `--summary-csv` で CSV 出力
- `main.py` に `--summary` / `--summary-csv` オプション追加
- テスト: `test_summary.py`
  - 出力フォーマットの検証
  - フィルタリングの動作確認

**完了条件**: `papycli --summary` で全エンドポイントの一覧が表示される。CSV 出力が正しい形式。テストがパスする。

---

### Milestone 5 — シェル補完

**目的**: bash / zsh でタブ補完が動作するようにする。

**実装内容**:
- `completion.py`
  - bash / zsh 向け補完スクリプトの生成
  - 補完の文脈（コンテキスト）に応じた候補提供
    1. メソッド補完: `get | post | put | patch | delete`
    2. リソースパス補完: API 定義のパスキー一覧
    3. オプション補完: `-q`, `-p`, `-H`, `-d`, `--summary`
    4. パラメータ名補完: `-q <TAB>` → クエリパラメータ名の候補
    5. enum 値補完: `-q status <TAB>` → `available pending sold` 等
- `main.py` に `--completion-script <bash|zsh>` コマンド追加
- 手動テスト手順をドキュメント化

**完了条件**: `eval "$(papycli --completion-script zsh)"` 後にタブ補完が動作する。メソッド・リソース・パラメータ名・enum 値が補完候補として表示される。

---

## 開発上の方針

### ブランチ・コミット戦略
- 原則としてトピックブランチで開発し PR を出す（今回はユーザー指示により main への直接コミットも許容）
- コミットの粒度: 各マイルストーン内で意味のまとまりごとにコミット
- コミットメッセージは Conventional Commits 形式（`feat:`, `test:`, `fix:`, `docs:`, `chore:`）

### テスト方針
- HTTP リクエストは `responses` ライブラリでモックし、実サーバーに依存しない
- Petstore サーバーへの接続テストは手動（`examples/` の docker-compose を使用）
- `pytest` のみでテスト実行（`uv run pytest`）

### コーディング規約
- `ruff` でフォーマット・Lint（CI チェック対象）
- `mypy` で型チェック（厳格モード）
- 公開 API にのみ docstring（内部実装は不要）
- 過度な抽象化を避ける：現在必要な機能のみ実装する
