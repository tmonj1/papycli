# CLAUDE.md

## プロジェクト概要

`papycli` は OpenAPI 3.0 で記述された API 定義ファイルを解釈し、REST API エンドポイントに対してターミナルから直接呼び出せるインタラクティブな CLI を提供する Python 製ツールです。

## 開発環境

- Python 3.12 以上 
- uv で仮想環境を管理（Linux / macOS のみ）

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
- `summary.py` — summary コマンド・CSV 出力
- `i18n.py` — 日英ヘルプテキスト切り替え

## コーディング規約

- フォーマッタ・Lint は `ruff` を使用する (`uv run ruff check`)
- 型ヒントを積極的に使用し、`mypy` でチェックを通す (`uv run mypy src`)
- 関数・モジュールの公開 API にのみ docstring を書く（内部実装には不要）
- エラーメッセージはユーザーが原因を特定しやすい内容にする

## テスト方針

- `pytest` でテストコードを実行する (`uv run pytest`)
- `tests/unittest/` 以下にユニットテストを配置する
- `tests/integration/` 以下に統合テストを配置する
- HTTP リクエストは `responses` ライブラリ等でモックして実テストしない
- OpenAPI spec の解釈ロジックは代表的なケースを網羅するテストを書く

## 追加ルール

詳細なルールは `.claude/rules/` 以下を参照。

- `.claude/rules/workflow.md` — 開発ワークフロー・issue 管理・Conventional Commits（常時ロード）
- `.claude/rules/data-format.md` — 内部データフォーマット・環境変数（Python ファイル編集時にロード）
- `.claude/rules/cli-spec.md` — CLI 仕様（`src/papycli/main.py` 編集時にロード）
