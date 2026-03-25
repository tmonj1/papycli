# papycli — OpenAPI 3.0 REST API を操作する Python 製 CLI

`papycli` は OpenAPI 3.0 仕様を読み込み、REST API エンドポイントをターミナルから直接呼び出せるインタラクティブな CLI を提供します。

## 特徴

- OpenAPI 3.0 仕様から CLI を自動生成
- シェル補完（bash / zsh）対応
- 複数 API の登録・切り替え
- `papycli spec` による API スペックの確認
- `--check` / `--check-strict` によるリクエスト前のパラメータ検証
- `--response-check` による OpenAPI spec に基づくレスポンスのステータスコード・ボディ検証
- API 仕様に基づいて `-p` の値を適切な JSON 型（integer / number / boolean）に自動変換
- `papycli config log` によるリクエスト/レスポンスのファイルログ
- リクエストフィルタープラグイン（`papycli.request_filters` エントリポイント）によるリクエスト処理の拡張
- レスポンスフィルタープラグイン（`papycli.response_filters` エントリポイント）によるレスポンスの参照・変換

## 必要環境

| 項目 | 備考 |
|------|------|
| Python | 3.12 以上 |

---

## インストール

```bash
pip install papycli
```

### シェル補完の有効化

**bash の場合：**

```bash
# ~/.bashrc または ~/.bash_profile に追加
eval "$(papycli config completion-script bash)"
```

**zsh の場合：**

```bash
# ~/.zshrc に追加
eval "$(papycli config completion-script zsh)"
```

**Git Bash（Windows）の場合：**

Git Bash は MSYS のパス変換機能を持つため、`$()` コマンド置換の出力が変換されて `eval` が正しく動作しないことがあります。
`eval` を実行する前にパス変換を無効にしてください：

```bash
# ~/.bashrc または ~/.bash_profile に追加
export MSYS_NO_PATHCONV=1
eval "$(papycli config completion-script bash)"
```

設定を反映するためにシェルを再起動するか `source ~/.bashrc` / `source ~/.zshrc` を実行してください。

---

## クイックスタート — Petstore デモ

このリポジトリには [Swagger Petstore](https://github.com/swagger-api/swagger-petstore) を使ったデモが含まれています。

### 1. Petstore サーバーを起動する

```bash
docker compose -f examples/petstore/docker-compose.yml up -d
```

API は `http://localhost:8080/api/v3/` で利用可能になります。

### 2. API を登録する

```bash
papycli config add examples/petstore/petstore-oas3.json
```

### 3. コマンドを試す

```bash
# 利用可能なエンドポイントを表示する
papycli summary

# GET /store/inventory
papycli get /store/inventory

# パスパラメータを指定して GET する
papycli get /pet/99

# クエリパラメータを指定して GET する
papycli get /pet/findByStatus -q status available

# ボディパラメータを指定して POST する
papycli post /pet -p name "My Dog" -p status available -p photoUrls "http://example.com/photo.jpg"

# 生の JSON ボディで POST する
papycli post /pet -d '{"name": "My Dog", "status": "available", "photoUrls": ["http://example.com/photo.jpg"]}'

# 配列パラメータ（同じキーを繰り返す）
papycli put /pet -p id 1 -p name "My Dog" -p photoUrls "http://example.com/a.jpg" -p photoUrls "http://example.com/b.jpg" -p status available

# ネストしたオブジェクト（ドット記法）
papycli put /pet -p id 1 -p name "My Dog" -p category.id 2 -p category.name "Dogs" -p photoUrls "http://example.com/photo.jpg" -p status available

# DELETE /pet/{petId}
papycli delete /pet/1
```

### 4. タブ補完

シェル補完を有効化した後、タブ補完が利用できます：

```
$ papycli <TAB>
  get  post  put  patch  delete  config  spec  summary

$ papycli get <TAB>
  /pet/findByStatus  /pet/{petId}  /store/inventory  ...

$ papycli get /pet/findByStatus <TAB>
  -q  -p  -H  -d  --summary  --verbose  --check  --check-strict  --response-check

$ papycli get /pet/findByStatus -q <TAB>
  status

$ papycli get /pet/findByStatus -q status <TAB>
  available  pending  sold

$ papycli post /pet -p <TAB>
  name*  photoUrls*  status

$ papycli post /pet -p status <TAB>
  available  pending  sold
```

---

## 独自 API の追加

### ステップ 1 — `config add` を実行する

```bash
papycli config add your-api-spec.json
```

このコマンドは以下を行います：

1. OpenAPI spec 内の `$ref` 参照を解決する
2. spec を papycli 内部の API 定義フォーマットに変換する
3. 結果を `$PAPYCLI_CONF_DIR/apis/<name>.json` に保存する
4. `$PAPYCLI_CONF_DIR/papycli.conf` を作成・更新する

API 名はファイル名から導出されます（例：`your-api-spec.json` → `your-api-spec`）。

### ステップ 2 — ベース URL を設定する

spec に `servers[0].url` が含まれている場合は自動で使用されます。含まれていない場合は `$PAPYCLI_CONF_DIR/papycli.conf` を編集して `url` フィールドを設定します：

```json
{
  "default": "your-api-spec",
  "your-api-spec": {
    "openapispec": "your-api-spec.json",
    "apidef": "your-api-spec.json",
    "url": "https://your-api-base-url/"
  }
}
```

### 複数 API の管理

```bash
# 複数の API を登録する
papycli config add petstore-oas3.json
papycli config add myapi.json

# アクティブな API を切り替える
papycli config use myapi

# 登録済み API を削除する
papycli config remove petstore-oas3

# 登録済み API と現在のデフォルトを確認する
papycli config list

# 現在のデフォルト API に対して短いエイリアスコマンドを作成する
papycli config alias petcli

# 設定済みエイリアスを一覧表示する
papycli config alias

# エイリアスを削除する
papycli config alias -d petcli
```

---

## リファレンス

```
# 設定管理コマンド
papycli config add <spec-file>             OpenAPI spec ファイルから API を登録する
papycli config remove <api-name>           登録済み API を削除する
papycli config use <api-name>              アクティブな API を切り替える
papycli config list                        登録済み API と現在の設定を一覧表示する
papycli config log                         現在のログファイルパスを表示する
papycli config log <path>                  ログファイルパスを設定する
papycli config log --unset                 ログを無効化する
papycli config alias [alias-name] [spec-name]  登録済み API のコマンドエイリアスを作成する
papycli config alias                       設定済みエイリアスを一覧表示する
papycli config alias -d <alias-name>       エイリアスを削除する
papycli config completion-script <bash|zsh>  シェル補完スクリプトを出力する

# 確認コマンド
papycli spec [resource]             内部 API スペックを表示する（リソースパスでフィルタ可能）
papycli spec --full [resource]      内部に保存された OpenAPI spec を出力する（RESOURCE 指定で絞り込み可能）
papycli summary [resource]          利用可能なエンドポイントを表示する（リソースでフィルタ可能）
                                      必須パラメータは * 付き、配列パラメータは [] 付きで表示
papycli summary --csv               CSV フォーマットでエンドポイントを表示する

# API 呼び出しコマンド
papycli <method> <resource> [options]

メソッド:
  get | post | put | patch | delete

オプション:
  -H <header: value>      カスタム HTTP ヘッダー（繰り返し可）
  -q <name> <value>       クエリパラメータ（繰り返し可）
                            リソースパスにクエリ文字列を直接埋め込むことも可能:
                            '/pet/findByStatus?status=available'
                            インラインパラメータは -q より先に送信される
  -p <name> <value>       ボディパラメータ（繰り返し可）
                            - API 仕様に基づいて値を適切な JSON 型（integer / number /
                              boolean）に自動変換する。文字列はそのまま送信される。
                            - 同じキーを繰り返すと JSON 配列を構築する:
                              -p tags foo -p tags bar  →  {"tags":["foo","bar"]}
                            - ドット記法でネストしたオブジェクトを構築する:
                              -p category.id 1 -p category.name Dogs
                              →  {"category":{"id":"1","name":"Dogs"}}
  -d <json>               生の JSON ボディ（-p を上書きする）
  --summary               リクエストを送らずにエンドポイント情報を表示する
  --check                 送信前にパラメータを検証する（警告を stderr に出力、リクエストは送信）
  --check-strict          送信前にパラメータを検証する（警告を stderr に出力、問題があればリクエスト中止・exit 1）
  --response-check        レスポンスのステータスコードとボディを OpenAPI spec に照合する
                            （違反は stderr に出力、exit code には影響しない）
  --verbose / -v          HTTP ステータス行を表示する
  --version               バージョンを表示する
  --help / -h             使い方を表示する

環境変数:
  PAPYCLI_CONF_DIR        設定ディレクトリのパス（デフォルト: ~/.papycli）
  PAPYCLI_CUSTOM_HEADER   すべてのリクエストに適用するカスタム HTTP ヘッダー
                            複数のヘッダーは改行で区切る:
                            export PAPYCLI_CUSTOM_HEADER=$'Authorization: Bearer token\nX-Tenant: acme'
```

---

## リクエストフィルタープラグイン

リクエストフィルタープラグインを作成することで、送信前のリクエストを加工できます。

フィルターは `RequestContext` を受け取り、変更した `RequestContext` を返す callable です：

```python
# my_plugin.py
from papycli.filters import RequestContext

def request_filter(ctx: RequestContext) -> RequestContext:
    ctx.headers["X-Request-ID"] = "my-id"
    return ctx
```

パッケージの `pyproject.toml` にエントリポイントを登録します：

```toml
[project.entry-points."papycli.request_filters"]
my-filter = "my_plugin:request_filter"
```

パッケージをインストールすると、すべてのリクエストに対してフィルターがプラグイン名の昇順で自動適用されます。

`RequestContext` のフィールド：

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `method` | `str` | HTTP メソッド（小文字）。変更不可。 |
| `url` | `str` | パスパラメータ展開済みの完全 URL。 |
| `query_params` | `list[tuple[str, str]]` | クエリパラメータ。 |
| `body` | `dict \| list \| str \| int \| float \| bool \| None` | JSON リクエストボディ。 |
| `headers` | `dict[str, str]` | カスタム HTTP ヘッダー。 |
| `spec` | `dict \| None` | API 定義内の該当オペレーションエントリ（参照専用）。解決できない場合は `None`。 |

---

## レスポンスフィルタープラグイン

レスポンスフィルタープラグインを作成することで、受信後のレスポンスを参照・変換できます。

フィルターは `ResponseContext` を受け取り、変更した `ResponseContext` を返す callable です。`None` を返すとレスポンスの出力を抑制し、後続のフィルター実行を中止します：

```python
# my_plugin.py
from papycli.filters import ResponseContext

def response_filter(ctx: ResponseContext) -> ResponseContext | None:
    if isinstance(ctx.body, dict):
        ctx.body["_status"] = ctx.status_code
    return ctx
```

`None` を返すと、そのレスポンスの出力が完全に抑制され、後続フィルターへの処理も中断されます。特定の条件に合致するレスポンスを無音化したい場合に便利です。

パッケージの `pyproject.toml` にエントリポイントを登録します：

```toml
[project.entry-points."papycli.response_filters"]
my-filter = "my_plugin:response_filter"
```

パッケージをインストールすると、すべてのレスポンスに対してフィルターがプラグイン名の昇順で自動適用されます。

`ResponseContext` のフィールド：

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `method` | `str` | リクエストに使用した HTTP メソッド（小文字）。 |
| `url` | `str` | リクエストに使用した完全 URL。 |
| `status_code` | `int` | HTTP レスポンスステータスコード。 |
| `reason` | `str` | HTTP レスポンスの理由フレーズ（例：`"OK"`、`"Not Found"`）。 |
| `headers` | `dict[str, str]` | レスポンスヘッダー。 |
| `body` | `dict \| list \| str \| int \| float \| bool \| None` | パース済みレスポンスボディ。このフィールドを変更するとレスポンスボディを差し替えられる。 |
| `request_body` | `dict \| list \| str \| int \| float \| bool \| None` | サーバーへ送信したリクエストボディ（参照専用）。ボディなしのリクエストは `None`。 |
| `schema` | `dict \| None` | 該当ステータスコードの OpenAPI Response Object（$ref 解決済み、参照専用）。対応する定義がない場合は `None`。 |

---

## 制限事項

- リクエストボディは `application/json` のみ対応
- 配列パラメータはスカラー型（string、integer 等）のみ対応（オブジェクトの配列は非対応）
- ドット記法によるオブジェクトのネストは 1 レベルのみ対応
- 認証ヘッダーは `-H "Authorization: Bearer token"` または `PAPYCLI_CUSTOM_HEADER` 環境変数で渡す

---

## 開発

```bash
git clone https://github.com/tmonj1/papycli.git
cd papycli
pip install -e ".[dev]"
```

### テストの実行

以下のコマンドは [uv](https://docs.astral.sh/uv/) がインストールされていることを前提としています。`pip` で環境をセットアップした場合は、`uv run` を省いて `pytest` を直接実行してください。

**ユニットテスト：**

```bash
uv run pytest
```

**統合テスト：**

統合テストを実行する前に、`papycli` バイナリが `.venv/bin/` に存在している必要があります。まず `uv sync` を実行してください：

```bash
uv sync
uv run pytest -m integration --override-ini addopts= tests/integration/
```

**全テストをまとめて実行：**

```bash
uv sync
uv run pytest --override-ini addopts=
```