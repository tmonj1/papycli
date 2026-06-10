# GitHub API example

[papycli](https://github.com/tmonj1/papycli) から [GitHub REST API](https://docs.github.com/en/rest) を呼び出すサンプルです。

OpenAPI spec は GitHub が公式に公開している [github/rest-api-description](https://github.com/github/rest-api-description) を使用します。

## 事前準備

以下の手順はすべて `examples/github` ディレクトリで実行してください。

```bash
cd examples/github
```

### 1. OpenAPI spec をダウンロードする

GitHub が公式公開している OpenAPI spec（OpenAPI 3.0、バンドル済み JSON）をダウンロードします。
ファイルサイズは約 40MB です。

```bash
curl -L -o api.github.com.json \
  https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json
```

### 2. papycli に登録する

```bash
papycli config add api.github.com.json
```

設定ファイル (`~/.papycli/papycli.conf`) を開き、登録された `api.github.com` エントリの `url` を確認・設定します。

```json
"api.github.com": {
  "openapispec": "api.github.com.json",
  "apidef": "api.github.com.json",
  "url": "https://api.github.com"
}
```

> `url` が空の場合は `https://api.github.com` を手動で設定してください。

アクティブな API を切り替えます。

```bash
papycli config use api.github.com
```

### 3. Personal Access Token を設定する

GitHub API を呼び出すには Personal Access Token (PAT) が必要です。

1. GitHub の [Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens) を開く
2. **Generate new token** をクリックして必要なスコープを付与してトークンを生成する
   - リポジトリ読み取り: `repo` スコープ（または `public_repo`）
   - Issue 操作: `repo` スコープ
3. 生成されたトークンを `PAPYCLI_CUSTOM_HEADER` 環境変数に設定する

```bash
export PAPYCLI_CUSTOM_HEADER=$'Authorization: Bearer <your-personal-access-token>'
```

この環境変数を設定しておくと、以降の `papycli` コマンドすべてに自動で認証ヘッダーが付与されます。

## 使い方

### エンドポイント一覧を確認する

```bash
papycli summary
```

### 認証ユーザーの情報を取得する

```bash
papycli get /user
```

### ユーザーのリポジトリ一覧を取得する

```bash
# 例: octocat のリポジトリを最大10件取得
papycli get /users/octocat/repos -q per_page 10
```

パスパラメータ（`{username}` など）は URL に直接値を埋め込みます。`-q` はクエリパラメータ専用です。

### リポジトリの詳細を取得する

```bash
papycli get /repos/octocat/Hello-World
```

### Issue 一覧を取得する

```bash
papycli get /repos/<your-username>/<your-repo>/issues
```

状態でフィルタリングする場合:

```bash
# オープンな issue のみ（デフォルト）
papycli get /repos/<your-username>/<your-repo>/issues -q state open

# クローズされた issue のみ
papycli get /repos/<your-username>/<your-repo>/issues -q state closed
```

### Issue を作成する

```bash
papycli post /repos/<your-username>/<your-repo>/issues \
  -d '{"title": "バグ報告: xxxxxx", "body": "詳細な説明", "labels": ["bug"]}'
```

### Pull Request 一覧を取得する

```bash
papycli get /repos/<your-username>/<your-repo>/pulls
```

### リリース一覧を取得する

```bash
papycli get /repos/<your-username>/<your-repo>/releases
```

### コミット一覧を取得する

```bash
papycli get /repos/<your-username>/<your-repo>/commits -q per_page 5
```

## レスポンス検証

`--response-check` オプションを使うと、レスポンスが OpenAPI spec に準拠しているか検証できます。

```bash
papycli get /user --response-check
```
