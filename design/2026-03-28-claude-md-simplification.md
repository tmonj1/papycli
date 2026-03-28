# CLAUDE.md 簡潔化 設計ドキュメント

## 目的

CLAUDE.md がコンテキストを圧迫しないよう、約 277 行から約 100 行に削減する。
詳細設計情報は `design_doc.md`（コンテキスト外）に既に存在するため、
CLAUDE.md は「Claude が自力で導出できない情報」と「行動ルール」だけに絞る。

## 方針

削除・圧縮の判断基準:
- **削除**: Glob/ls/コード読解で容易に確認できる情報
- **圧縮**: 有用だが現在の記述量が過剰な情報
- **維持**: 行動ルール・非自明な仕様・コンテキスト節約後も価値が高いもの

## セクション別の変更内容

### 開発環境（22行 → 8行）

ツール表とセットアップ節を削除し、`uv run` コマンド 3 つだけ箇条書きで残す。

```markdown
## 開発環境

- Python 3.12 以上 / uv で仮想環境を管理（Linux / macOS のみ）
- テスト: `uv run pytest`
- Lint・フォーマット: `uv run ruff check` / `uv run ruff format`
- 型チェック: `uv run mypy src/`
```

### ディレクトリ構成ツリー（42行 → 削除）

全ファイル名を列挙したツリーは Claude が Glob/ls で確認できるため削除する。

### 主要モジュール説明（32行 → 12行）

詳細説明をやめ、`file.py — 役割` の1行形式に統一する。

```markdown
## 主要モジュール

- `main.py` — CLI エントリポイント・引数パース
- `init_cmd.py` — `config add`（spec 変換・保存）
- `spec_loader.py` — OpenAPI spec 読み込み・$ref 解決・内部形式変換
- `api_call.py` — HTTP リクエスト実行・パステンプレートマッチング
- `checker.py` — `--check` / `--check-strict` パラメータ検証
- `completion.py` — bash/zsh 補完スクリプト生成
- `config.py` — 設定ファイル読み書き・ログパス管理
- `filters.py` — リクエスト・レスポンスフィルタープラグイン機構
- `response_checker.py` — `--response-check` レスポンス検証
- `spec_loader.py` — OpenAPI spec 読み込み・$ref 解決
- `summary.py` — summary コマンド・CSV 出力
- `i18n.py` — 日英ヘルプテキスト切り替え
```

### 内部データフォーマット（40行 → 15行）

JSON サンプルを削除し、スキーマをインライン記法＋箇条書きで表現する。

```markdown
## 内部データフォーマット

### API 定義ファイル (`apis/<name>.json`)

`{ "<path>": [ { "method", "query_parameters", "post_parameters" } ] }` の形式。
- `method`: `"get"` / `"post"` / `"put"` / `"patch"` / `"delete"`
- `query_parameters` / `post_parameters`: `[{ "name", "type", "required", "enum"(省略可) }]`
- path にはパステンプレート（`/pet/{petId}` 形式）も使用可

### 設定ファイル (`papycli.conf`)

`{ "default": "<api-name>", "<api-name>": { "openapispec", "apidef", "url" } }` の形式。
```

### CLI 仕様（27行 → 15行）

コマンド一覧（15行）とパステンプレートマッチング（2行）を維持する。
パラメータ詳細（`-q`, `-p`, `-d`, `-H`, `--check`, `--response-check` の説明10行）は
`--help` で確認できるため削除する。

### 環境変数・テスト方針・コーディング規約・調査ワークフロー・Git 運用

変更なし。

## 削減後の想定行数

| セクション | 現在 | 変更後 |
|---|---|---|
| プロジェクト概要 | 5 | 5 |
| 開発環境 | 22 | 8 |
| ディレクトリ構成ツリー | 42 | 0 |
| 主要モジュール | 32 | 14 |
| 内部データフォーマット | 40 | 15 |
| CLI 仕様 | 27 | 15 |
| 環境変数 | 5 | 5 |
| テスト方針 | 6 | 6 |
| コーディング規約 | 6 | 6 |
| 調査ワークフロー | 4 | 4 |
| Git 運用 | 30 | 30 |
| **合計** | **277** | **108** |
