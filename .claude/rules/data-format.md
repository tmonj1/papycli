---
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
---

# 内部データフォーマット・環境変数

## API 定義ファイル (`apis/<name>.json`)

`{ "<path>": [ { "method", "query_parameters", "post_parameters" } ] }` の形式。

- `method`: `"get"` / `"post"` / `"put"` / `"patch"` / `"delete"`
- `query_parameters` / `post_parameters`: `[{ "name", "type", "required", "enum"(省略可) }]`
- path にはパステンプレート（`/pet/{petId}` 形式）も使用可

## 設定ファイル (`papycli.conf`)

`{ "default": "<api-name>", "aliases": { "<alias-name>": "<api-name>" }, "logfile": "<log-path>", "<api-name>": { "openapispec", "apidef", "url" } }` の形式。

- `default`: デフォルトで使用する API 名
- `aliases`: エイリアス名 → スペック名のマップ
- `logfile`: ログ出力先のパス（省略可）
- `<api-name>`: 各 API エントリ。`openapispec` / `apidef` / `url` を持つ

## 環境変数

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `PAPYCLI_CONF_DIR` | `~/.papycli` | 設定ディレクトリのパス |
| `PAPYCLI_CUSTOM_HEADER` | （なし） | 全リクエストに付与するカスタムヘッダー（改行区切りで複数指定可） |
