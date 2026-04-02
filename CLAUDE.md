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

## 内部データフォーマット

### API 定義ファイル (`apis/<name>.json`)

`{ "<path>": [ { "method", "query_parameters", "post_parameters" } ] }` の形式。

- `method`: `"get"` / `"post"` / `"put"` / `"patch"` / `"delete"`
- `query_parameters` / `post_parameters`: `[{ "name", "type", "required", "enum"(省略可) }]`
- path にはパステンプレート（`/pet/{petId}` 形式）も使用可

### 設定ファイル (`papycli.conf`)

`{ "default": "<api-name>", "<api-name>": { "openapispec", "apidef", "url" } }` の形式。

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
papycli spec --full [resource]
papycli summary [resource] [--csv]
papycli --version
papycli --help / -h
```

### サポートするメソッド

`get | post | put | patch | delete` をサポートする。

### パステンプレートのマッチング

リソースパスに数値や文字列が含まれる場合（例：`/pet/99`）、API 定義内のテンプレート（`/pet/{petId}`）にマッチさせ、値を埋め込んでリクエストを送信する。

## 環境変数

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `PAPYCLI_CONF_DIR` | `~/.papycli` | 設定ディレクトリのパス |
| `PAPYCLI_CUSTOM_HEADER` | （なし） | 全リクエストに付与するカスタムヘッダー（改行区切りで複数指定可） |

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

## 開発ワークフロー

コードの追加・修正は以下のフローに従う。ドキュメントだけの追加・修正時も同じ（テストは実行不要）。

- 修正の内容を簡潔に記述し、GitHub の issue に登録する (issueのない修正は厳禁)
- `main` ブランチを最新化する
- `main` ブランチからトピックブランチを作成する (`main` ブランチへの直接コミットは厳禁)
- コードの追加・修正をおこなう
- `ruff` と `mypy` でチェックし、警告がなくなるまで修正する
- コードが完成したらコミットする (コミットメッセージは Conventional Commits に従う)
- PR を作成する
- PR レビューで指摘を受けた場合、必要であればコードを修正し、修正コミットをプッシュする
- プッシュ後、修正内容を簡潔にまとめてPRに返信する

## issue 管理

- issue には適切なラベルをつける。使用するラベルは以下のいずれか
- 機能以外のバグの場合、`ci`、`chore` など適切なラベルを追加する

| ラベル | 用途 |
|---------------|------|
| `feature` | 新機能の追加 |
| `bug` | バグ修正 |
| `refactor` | 機能変更を伴わないリファクタリング |
| `test` | テストコードの追加 |
| `ci` | GitHub Actions など Continuous Integration に関係する変更 |
| `documentation` | ドキュメントのみの変更 |
| `chore` | 上記以外 (ビルド・依存関係・設定等のメンテナンス) |

## Conventional Commits の注意点

- ユーザーから見て機能に変更がないときは `feat` は使わない
- 破壊的変更を伴う場合、`feat!:` や `fix!` のようにコミットメッセージのタイプに**必ず**`!`を付ける
- `ci` や `chore` のバグ修正の場合、`fix(ci):`、`fix(chore)` のように機能上の不具合修正でないことがわかるように明記する
- コミットに互換性を損なう破壊的変更が含まれる場合、"BREAKING CHANGE:" フッターを**必ず**追加する