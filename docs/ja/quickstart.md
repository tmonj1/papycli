# クイックスタート

## Petstore デモ

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

## 複数 API の管理

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
