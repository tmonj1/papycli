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

公開リポジトリへのアクセスは未認証でも可能ですが、レート制限が厳しく（60回/時間）、プライベートリポジトリや Issue の作成など書き込み操作には Personal Access Token (PAT) が必要です。PAT を設定しておくことを推奨します（5000回/時間）。

#### PAT の種類

GitHub には2種類の PAT があります。

| 種類 | 説明 |
|------|------|
| **classic PAT** | スコープ（`repo`、`read:user` など）で権限を付与する従来方式 |
| **fine-grained PAT** | リポジトリ単位・権限単位で細かく制御できる新方式（推奨） |

#### classic PAT を使う場合

1. GitHub の [Settings > Developer settings > Personal access tokens > Tokens (classic)](https://github.com/settings/tokens) を開く
2. **Generate new token (classic)** をクリックし、必要なスコープを付与する
   - リポジトリ読み取り: `public_repo`（公開リポジトリのみ）または `repo`（プライベートも含む）
   - Issue 操作: `repo` スコープ

#### fine-grained PAT を使う場合

1. GitHub の [Settings > Developer settings > Personal access tokens > Fine-grained tokens](https://github.com/settings/tokens?type=beta) を開く
2. **Generate new token** をクリックし、対象リポジトリと必要な権限を選択する
   - Issues 読み取り・書き込み: `Issues: Read and write`
   - コンテンツ読み取り: `Contents: Read-only`

#### トークンの設定方法

トークンをシェル履歴に残さないよう、`.env` ファイルに記載することを推奨します。

```bash
# ~/.papycli/.env または作業ディレクトリの .env に記載する（シェル履歴に残らない）
echo 'PAPYCLI_CUSTOM_HEADER=Authorization: Bearer YOUR_PAT' >> ~/.papycli/.env
```

一時的に試す場合は環境変数に直接設定することもできます。

```bash
export PAPYCLI_CUSTOM_HEADER=$'Authorization: Bearer YOUR_PAT'
```

papycli は起動時に CWD と `~/.papycli/` の `.env` ファイルを自動で読み込みます（`PAPYCLI_DISABLE_DOTENV=1` で無効化）。この環境変数を設定しておくと、以降の `papycli` コマンドすべてに自動で認証ヘッダーが付与されます。

## 使い方

以降のコマンド例の `YOUR_USERNAME` / `YOUR_REPO` は実際のユーザー名・リポジトリ名に置き換えてください。

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
papycli get /repos/YOUR_USERNAME/YOUR_REPO/issues
```

状態でフィルタリングする場合:

```bash
# オープンな issue のみ（デフォルト）
papycli get /repos/YOUR_USERNAME/YOUR_REPO/issues -q state open

# クローズされた issue のみ
papycli get /repos/YOUR_USERNAME/YOUR_REPO/issues -q state closed
```

### Issue を作成する

```bash
papycli post /repos/YOUR_USERNAME/YOUR_REPO/issues \
  -d '{"title": "バグ報告: xxxxxx", "body": "詳細な説明", "labels": ["bug"]}'
```

### Pull Request 一覧を取得する

```bash
papycli get /repos/YOUR_USERNAME/YOUR_REPO/pulls
```

### リリース一覧を取得する

```bash
papycli get /repos/YOUR_USERNAME/YOUR_REPO/releases
```

### コミット一覧を取得する

```bash
papycli get /repos/YOUR_USERNAME/YOUR_REPO/commits -q per_page 5
```

## レスポンス検証

`--response-check` オプションを使うと、レスポンスが OpenAPI spec に準拠しているか検証できます。

```bash
papycli get /user --response-check
```
