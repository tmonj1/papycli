# CLI リファレンス

## 設定管理コマンド

| コマンド | 説明 |
|---------|------|
| `papycli config add <spec-file>` | OpenAPI spec ファイルから API を登録する |
| `papycli config remove <api-name>` | 登録済み API を削除する |
| `papycli config use <api-name>` | アクティブな API を切り替える |
| `papycli config list` | 登録済み API と現在の設定を一覧表示する |
| `papycli config log` | 現在のログファイルパスを表示する |
| `papycli config log <path>` | ログファイルパスを設定する |
| `papycli config log --unset` | ログを無効化する |
| `papycli config completion-script <bash\|zsh>` | シェル補完スクリプトを出力する |
| `papycli config completion-script --api <api-name> <bash\|zsh>` | 独自 CLI 用の補完スクリプトを出力する（[独自 CLI の作成](quickstart.md#特定-api-の独自-cli-を作成する) を参照） |

## 確認コマンド

| コマンド | 説明 |
|---------|------|
| `papycli spec [resource]` | 内部 API スペックを表示する（リソースパスでフィルタ可能） |
| `papycli spec --full [resource]` | 内部に保存された OpenAPI spec を出力する（RESOURCE 指定で絞り込み可能） |
| `papycli summary [resource]` | 利用可能なエンドポイントを表示する（リソースでフィルタ可能）。必須パラメータは `*` 付き、配列パラメータは `[]` 付きで表示 |
| `papycli summary --csv` | CSV フォーマットでエンドポイントを表示する |

## API 呼び出しコマンド

```
papycli <method> <resource> [options]
```

**サポートするメソッド:** `get | post | put | patch | delete`

### オプション

| オプション | 説明 |
|-----------|------|
| `-H <header: value>` | カスタム HTTP ヘッダー（繰り返し可） |
| `-q <name> <value>` | クエリパラメータ（繰り返し可）。リソースパスにクエリ文字列を直接埋め込むことも可能: `/pet/findByStatus?status=available`。インラインパラメータは `-q` より先に送信される。 |
| `-p <name> <value>` | ボディパラメータ（繰り返し可）。API 仕様に基づいて値を適切な JSON 型（integer / number / boolean）に自動変換する。文字列はそのまま送信される。同じキーを繰り返すと JSON 配列を構築する。ドット記法でネストしたオブジェクトを構築できる。 |
| `-d <json>` | 生の JSON ボディ（`-p` を上書きする） |
| `--summary` | リクエストを送らずにエンドポイント情報を表示する |
| `--check` | 送信前にパラメータを検証する（警告を stderr に出力、リクエストは送信） |
| `--check-strict` | 送信前にパラメータを検証する（警告を stderr に出力、問題があればリクエスト中止・exit 1） |
| `--response-check` | レスポンスのステータスコードとボディを OpenAPI spec に照合する（違反は stderr に出力、exit code には影響しない） |
| `--verbose / -v` | HTTP ステータス行を表示する |
| `--version` | バージョンを表示する |
| `--help / -h` | 使い方を表示する |

### パラメータ例

```bash
# 同じキーを繰り返して JSON 配列を構築する
papycli put /pet -p photoUrls "http://example.com/a.jpg" -p photoUrls "http://example.com/b.jpg"
# → {"photoUrls": ["http://example.com/a.jpg", "http://example.com/b.jpg"]}

# ドット記法でネストしたオブジェクトを構築する
papycli put /pet -p category.id 2 -p category.name "Dogs"
# → {"category": {"id": 2, "name": "Dogs"}}

# 生の JSON ボディ
papycli post /pet -d '{"name": "My Dog", "status": "available"}'
```

## 環境変数

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `PAPYCLI_CONF_DIR` | `~/.papycli` | 設定ディレクトリのパス |
| `PAPYCLI_CUSTOM_HEADER` | （なし） | すべてのリクエストに適用するカスタム HTTP ヘッダー。複数のヘッダーは改行で区切る: `export PAPYCLI_CUSTOM_HEADER=$'Authorization: Bearer token\nX-Tenant: acme'` |
