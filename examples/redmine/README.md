# Redmine example

[papycli](https://github.com/tmonj1/papycli) から [Redmine](https://www.redmine.org/) の REST API を呼び出すサンプルです。

OpenAPI spec は [d-yoshi/redmine-openapi](https://github.com/d-yoshi/redmine-openapi) の非公式仕様 (OpenAPI 3.0.3) を使用しています。

## 事前準備

### 1. OpenAPI spec を取得する

このディレクトリには OpenAPI spec ファイルは含まれていません。
以下のコマンドで [d-yoshi/redmine-openapi](https://github.com/d-yoshi/redmine-openapi) から取得してください。

```bash
curl -o examples/redmine/openapi.yaml \
  https://raw.githubusercontent.com/d-yoshi/redmine-openapi/main/openapi.yaml
```

### 2. Redmine を起動する

```bash
cd examples/redmine
docker compose up -d
```

起動時に以下を自動で実行します。

- REST API の有効化
- トラッカー・ステータス・優先度などのデフォルトデータの投入（初回のみ）

起動完了まで数十秒〜数分かかります。以下のコマンドで `200` が返れば準備完了です。

```bash
curl -o /dev/null -w "%{http_code}\n" http://localhost:3000/projects.json
```

### 3. API キーを取得する

```bash
docker compose exec redmine bash -c \
  "cd /usr/src/redmine && bundle exec rails runner \
  'Rails.logger = Logger.new(IO::NULL); puts User.find_by(login: \"admin\").api_key'"
```

表示された API キーを以下の手順で使用します。

### 4. papycli に登録する

```bash
papycli config add examples/redmine/openapi.yaml
```

設定ファイル (`~/.papycli/papycli.conf`) を開き、登録された `openapi` エントリの `url` と名前を編集します。

```json
"redmine": {
  "openapispec": "openapi.yaml",
  "apidef": "openapi.json",
  "url": "http://localhost:3000"
}
```

アクティブな API を redmine に切り替えます。

```bash
papycli config use redmine
```

## 使い方

API キーを環境変数に設定しておくと便利です。

```bash
export REDMINE_API_KEY=<your-api-key>
```

### プロジェクト一覧を取得する

```bash
papycli get /projects.json -H "X-Redmine-API-Key: $REDMINE_API_KEY"
```

### プロジェクトを作成する

```bash
papycli post /projects.json \
  -H "X-Redmine-API-Key: $REDMINE_API_KEY" \
  -d '{"project": {"name": "My Project", "identifier": "my-project"}}'
```

> **注意:** issue を作成する前に、プロジェクトにトラッカーを関連付ける必要があります。
>
> ```bash
> papycli put /projects/1.json \
>   -H "X-Redmine-API-Key: $REDMINE_API_KEY" \
>   -d '{"project": {"tracker_ids": [1, 2, 3]}}'
> ```

### issue を作成する

```bash
papycli post /issues.json \
  -H "X-Redmine-API-Key: $REDMINE_API_KEY" \
  -d '{"issue": {"project_id": 1, "tracker_id": 1, "priority_id": 2, "subject": "My issue"}}'
```

パラメータの目安:

| フィールド | 値 | 意味 |
|-----------|---|------|
| `tracker_id` | 1 / 2 / 3 | Bug / Feature / Support |
| `priority_id` | 1〜5 | Low / Normal / High / Urgent / Immediate |

### issue 一覧を取得する

```bash
papycli get /issues.json -H "X-Redmine-API-Key: $REDMINE_API_KEY"
```

### issue を更新する

```bash
papycli put /issues/1.json \
  -H "X-Redmine-API-Key: $REDMINE_API_KEY" \
  -d '{"issue": {"done_ratio": 50, "notes": "進捗を更新"}}'
```

### ログインユーザー情報を取得する

```bash
papycli get /users/current.json -H "X-Redmine-API-Key: $REDMINE_API_KEY"
```

### エンドポイント一覧を確認する

```bash
papycli summary
```

## コンテナを停止する

```bash
docker compose down
```

データを削除する場合は `-v` オプションを付けてください。

```bash
docker compose down -v
```
