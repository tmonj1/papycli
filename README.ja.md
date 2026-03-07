# papycli — OpenAPI 3.0 REST API を操作する Python 製 CLI

`papycli` は OpenAPI 3.0 仕様を読み込み、REST API エンドポイントをターミナルから直接呼び出せるインタラクティブな CLI を提供します。

## 特徴

- OpenAPI 3.0 仕様から CLI を自動生成
- シェル補完（bash / zsh）対応
- 複数 API の登録・切り替え

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

設定を反映するためにシェルを再起動するか `source ~/.bashrc` / `source ~/.zshrc` を実行してください。

---

## クイックスタート — Petstore デモ

このリポジトリには [Swagger Petstore](https://github.com/swagger-api/swagger-petstore) を使ったデモが含まれています。

### 1. Petstore サーバーを起動する

```bash
docker compose -f examples/docker-compose.yml up -d
```

API は `http://localhost:8080/api/v3/` で利用可能になります。

### 2. API を登録する

```bash
papycli config init examples/petstore-oas3.json
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
  get  post  put  delete  patch  config  summary

$ papycli get <TAB>
  /pet/findByStatus  /pet/{petId}  /store/inventory  ...

$ papycli get /pet/findByStatus <TAB>
  -q  --summary  --help

$ papycli get /pet/findByStatus -q <TAB>
  status

$ papycli get /pet/findByStatus -q status <TAB>
  available  pending  sold
```

---

## 独自 API の追加

### ステップ 1 — `config init` を実行する

```bash
papycli config init your-api-spec.json
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
papycli config init petstore-oas3.json
papycli config init myapi.json

# アクティブな API を切り替える
papycli config use myapi

# 登録済み API と現在のデフォルトを確認する
papycli config show
```

---

## リファレンス

```
# 設定管理コマンド
papycli config init <spec-file>            OpenAPI spec ファイルから API を初期化する
papycli config use <api-name>              アクティブな API を切り替える
papycli config show                        現在の設定を表示する
papycli config completion-script <bash|zsh>  シェル補完スクリプトを出力する

# API 呼び出しコマンド
papycli summary [resource]          利用可能なエンドポイントを表示する（リソースでフィルタ可能）
                                      必須パラメータは * 付き、配列パラメータは [] 付きで表示
papycli summary --csv               CSV フォーマットでエンドポイントを表示する
papycli <method> <resource> [options]

メソッド:
  get | post | put | patch | delete

オプション:
  -H <header: value>      カスタム HTTP ヘッダー（繰り返し可）
  -q <name> <value>       クエリパラメータ（繰り返し可）
  -p <name> <value>       ボディパラメータ（繰り返し可）
                            - 同じキーを繰り返すと JSON 配列を構築する:
                              -p tags foo -p tags bar  →  {"tags":["foo","bar"]}
                            - ドット記法でネストしたオブジェクトを構築する:
                              -p category.id 1 -p category.name Dogs
                              →  {"category":{"id":"1","name":"Dogs"}}
  -d <json>               生の JSON ボディ（-p を上書きする）
  --summary               リクエストを送らずにエンドポイント情報を表示する
  --version               バージョンを表示する
  --help / -h             使い方を表示する

環境変数:
  PAPYCLI_CONF_DIR        設定ディレクトリのパス（デフォルト: ~/.papycli）
  PAPYCLI_CUSTOM_HEADER   すべてのリクエストに適用するカスタム HTTP ヘッダー
                            複数のヘッダーは改行で区切る:
                            export PAPYCLI_CUSTOM_HEADER=$'Authorization: Bearer token\nX-Tenant: acme'
```

---

## 制限事項

- リクエストボディは `application/json` のみ対応
- 配列パラメータはスカラー型（string、integer 等）のみ対応（オブジェクトの配列は非対応）
- ドット記法によるオブジェクトのネストは 1 レベルのみ対応
- 認証ヘッダーは `-H "Authorization: Bearer token"` または `PAPYCLI_CUSTOM_HEADER` 環境変数で渡す

---

## 開発

```bash
git clone https://github.com/<your-org>/papycli.git
cd papycli
pip install -e ".[dev]"
```

詳細は [CLAUDE.md](CLAUDE.md) を参照してください。
