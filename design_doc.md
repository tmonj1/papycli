# papycli 設計ドキュメント

## 現状

- Python 3.12 / uv でパッケージ管理
- `examples/petstore-oas3.json` と `examples/docker-compose.yml` 準備済み
- Milestone 1〜5 の実装が完了し、`papycli` コマンドとして動作する状態

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
│       ├── init_cmd.py      # config add コマンドの処理
│       ├── api_call.py      # HTTP リクエスト実行・パステンプレートマッチング
│       ├── checker.py       # --check / --check-strict のパラメータ検証
│       ├── summary.py       # summary コマンドの出力
│       ├── completion.py    # bash / zsh 補完スクリプト生成
│       ├── filters.py        # リクエスト・レスポンスフィルタープラグイン機構
│       └── i18n.py          # 日英ヘルプテキストの切り替えユーティリティ
├── tests/
│   ├── test_api_call.py
│   ├── test_checker.py
│   ├── test_completion.py
│   ├── test_config.py
│   ├── test_i18n.py
│   ├── test_init_cmd.py
│   ├── test_main.py
│   ├── test_filters.py
│   ├── test_spec_loader.py
│   └── test_summary.py
├── examples/
│   ├── docker-compose.yml
│   └── petstore-oas3.json
├── design_doc.md
├── CLAUDE.md
├── README.md
├── README.ja.md
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

### Milestone 2 — spec ローダーと `config add` / `config list` / `config use`

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
  - API エントリの登録・削除・デフォルト変更
- `init_cmd.py`
  - spec ロード → 変換 → `apis/<name>.json` 保存 → conf 更新
- `main.py` に `config add`、`config use`、`config remove`、`config list` コマンド追加
- テスト: `test_spec_loader.py`、`test_config.py`、`test_init_cmd.py`
  - `$ref` 解決のパターン（内部参照、外部参照、循環参照ガード）
  - 変換結果の検証（petstore-oas3.json を使用）
  - config の CRUD

**完了条件**: `papycli config add examples/petstore-oas3.json` が成功し、`~/.papycli/apis/petstore-oas3.json` が正しい内容で生成される。`papycli config list` で設定が表示される。テストがパスする。

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
- `main.py` に `papycli spec [resource]` コマンド追加（内部 API 定義の JSON 表示）
- `checker.py`
  - `--check` / `--check-strict` オプション用のパラメータ検証ロジック
  - 必須パラメータの存在確認、型チェック（integer / boolean）、enum 値の検証
  - `--check`: 問題があっても警告を出力してリクエストを送信する
  - `--check-strict`: 問題があれば警告を出力してリクエストを中止し exit 1
- テスト: `test_api_call.py`、`test_checker.py`
  - パステンプレートマッチングの各ケース
  - `-p` による JSON 構築（配列、ネスト）
  - `responses` ライブラリで HTTP をモックしたエンドツーエンドテスト
  - `check_request()` の各検証ケース（必須・型・enum・raw body）

**完了条件**: `papycli get /store/inventory`、`papycli post /pet -p name "My Dog" -p status available` 等が Petstore サーバーに対して動作する。`papycli spec` で内部 API 定義が表示される。`--check` / `--check-strict` でパラメータ検証が動作する。テストがパスする。

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
- 補完候補の強化（`spec` コマンド、`summary --csv`、`--check`/`--check-strict` オプションを追加）
- Windows 対応: `_complete` の出力を binary stream（LF のみ）に変更
- 手動テスト手順をドキュメント化

**完了条件**: `eval "$(papycli config completion-script zsh)"` 後にタブ補完が動作する。メソッド・リソース・クエリパラメータ名・ボディパラメータ名・enum 値が補完候補として表示される。`spec`・`summary`・`--check`・`--check-strict` も補完候補に含まれる。

---

### Milestone 6 — リクエストフィルタープラグイン機構

**目的**: サードパーティプラグインがリクエスト送信前に URL・クエリ・ボディ・ヘッダーを変換できる拡張ポイントを提供する。

**実装内容**:
- `filters.py`
  - `RequestContext` データクラス（`method`, `url`, `query_params`, `body`, `headers`）
  - `load_filters()`: `papycli.request_filters` エントリポイントグループからフィルターをロードし、callable 検証後にプラグイン名の昇順で返す
  - `apply_filters()`: フィルターを順番に適用。各フィルター呼び出し前にスナップショットを作成し（body は deepcopy、他はシャローコピー）、例外・戻り値不正の場合は警告して前の ctx を維持する
- `api_call.py` の `call_api()` でフィルターを適用するよう更新
  - フィルター適用後の `method` は使用しない（API 定義マッチング時に確定した元の値を使う）
- テスト: `test_filters.py`
  - フィルターの読み込み・適用・例外処理・戻り値型検証など

**プラグイン登録例** (`pyproject.toml`):

```toml
[project.entry-points."papycli.request_filters"]
my-filter = "my_plugin:request_filter"
```

**完了条件**: `papycli.request_filters` エントリポイントに登録したフィルターが全リクエストで自動適用される。フィルターが例外を送出してもリクエスト送信に影響しない。テストがパスする。

---

### Milestone 7 — `config log` コマンドとリクエスト/レスポンスログ

**目的**: リクエストとレスポンスの内容をファイルに記録できるようにし、デバッグや監査を容易にする。

**実装内容**:
- `config.py`
  - `get_logfile()` / `set_logfile()` / `unset_logfile()`: ログファイルパスの取得・設定・削除
  - `load_current_apidef()` に `conf` オプション引数を追加し、設定ファイルの二重読み込みを防止
- `api_call.py`
  - `_SENSITIVE_HEADERS`: ログに記録する際にマスクするヘッダー名の集合（Authorization, Cookie 等）
  - `_LOG_BODY_MAX_CHARS`: ログに記録するボディの最大文字数（10,000 文字）。超過時は `...[truncated]` を付与
  - `_write_log()`: フィルター適用前の URL・クエリ・ボディ・ヘッダーをログに記録。エラー時は警告のみでリクエストには影響しない
  - `call_api()` に `logfile` 引数を追加。`~` 展開に `Path.expanduser()` を使用
- `main.py` に `papycli config log [PATH] [--unset]` コマンド追加
- テスト: `test_config.py`、`test_api_call.py`、`test_main.py`

**ログフォーマット例**:

```
[2026-03-10T12:34:56+00:00] GET https://example.com/pet/99
  Query: (none)
  Body: (none)
  Headers: {"Authorization": "***"}
  Status: 200
  Response: {"id": 99, "name": "My Dog"}
```

**完了条件**: `papycli config log ~/papycli.log` 設定後、リクエストごとにログファイルへ追記される。機密ヘッダーはマスクされる。大きなボディは切り詰められる。テストがパスする。

---

### Milestone 8 — `spec --full` とレスポンスフィルタープラグイン機構

**目的**: `papycli spec --full` で生の OpenAPI spec を表示できるようにする。また response filter プラグインによりレスポンスの参照・変換を可能にする。

**実装内容**:
- `main.py` に `papycli spec --full [resource]` サブコマンドを追加
  - 内部変換後の API 定義ではなく、元の OpenAPI spec を JSON で出力する
  - `resource` 指定時は該当パスのみ絞り込んで表示する
- `filters.py` にレスポンスフィルター機構を追加
  - `ResponseContext` データクラス（`status_code`, `reason`, `body`, `headers`）
  - `load_response_filters()`: `papycli.response_filters` エントリポイントグループからフィルターをロード
  - `apply_response_filters()`: フィルターを順番に適用。例外・戻り値不正の場合は警告して前の ctx を維持する
- `api_call.py` でレスポンス受信後にフィルターを適用するよう更新

**完了条件**: `papycli spec --full` で生の OpenAPI spec が出力される。`papycli.response_filters` エントリポイントに登録したフィルターがレスポンス受信後に自動適用される。テストがパスする。

---

### Milestone 9 — `--response-check` レスポンス検証

**目的**: `--response-check` オプションを追加し、実際のレスポンスを OpenAPI spec に照合して違反を警告できるようにする。

**実装内容**:
- `response_checker.py`
  - `check_response()`: レスポンスのステータスコードとボディを spec に照合し、違反メッセージのリストを返す
    - ステータスコード照合: exact match (`"200"`) → 範囲指定 (`"2XX"`, `"2xx"`) → `"default"` の順で探索。どれにも一致しない場合に警告する
    - ボディスキーマ照合: `application/json` および `+json` サフィックスのメディアタイプに対して実施。型・enum・必須フィールド・additionalProperties・配列 items を再帰的に検証する
    - スキーマ存在確認を先に行い、スキーマが定義されていない場合はボディパースをスキップする（204 等での誤警告防止）
    - YAML 由来の整数キー（`200:` → `200`）を文字列に正規化してから照合する
  - `_check_value()`: 値とスキーマを再帰的に照合するヘルパー
    - union type（`type: ["object", "null"]`）・type 省略スキーマ（`properties`/`items` から推論）をサポート
    - 不正なスキーマ形状（`properties` が非 dict 等）に対して型ガードを設けクラッシュを防止する
- `main.py` に `--response-check` フラグを追加
- `api_call.py` の `call_api()` で response filter 適用前に `check_response()` を呼び出す
- テスト: `test_response_checker.py`、`test_main.py`

**完了条件**: `papycli get /pet/1 --response-check` で spec と一致しないレスポンスが返された場合に stderr へ警告が出力される。ステータスコード不一致・ボディスキーマ違反ともに検出される。テストがパスする。

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
