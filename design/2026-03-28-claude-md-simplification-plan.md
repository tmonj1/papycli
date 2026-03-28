# CLAUDE.md 簡潔化 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CLAUDE.md を約 277 行から約 110 行に削減し、コンテキスト消費を抑える。

**Architecture:** 1 ファイル (`CLAUDE.md`) を書き換えるだけのドキュメント変更。テストコードなし。削除・圧縮の判断基準は `design/2026-03-28-claude-md-simplification.md` に記載。

**Tech Stack:** なし（テキスト編集のみ）

---

### Task 1: CLAUDE.md を簡潔版に書き換える

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: 現在の行数を確認する**

```bash
wc -l CLAUDE.md
```

Expected: `277 CLAUDE.md`

- [ ] **Step 2: CLAUDE.md を以下の内容に全置換する**

```markdown
# CLAUDE.md

## プロジェクト概要

`papycli` は OpenAPI 3.0 仕様を読み込み、REST API エンドポイントをターミナルから直接呼び出せるインタラクティブな CLI を提供する Python 製ツールです。

---

## 開発環境

- Python 3.12 以上 / uv で仮想環境を管理（Linux / macOS のみ）
- テスト: `uv run pytest`
- Lint・フォーマット: `uv run ruff check` / `uv run ruff format`
- 型チェック: `uv run mypy src/`

---

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

---

## 内部データフォーマット

### API 定義ファイル (`apis/<name>.json`)

`{ "<path>": [ { "method", "query_parameters", "post_parameters" } ] }` の形式。

- `method`: `"get"` / `"post"` / `"put"` / `"patch"` / `"delete"`
- `query_parameters` / `post_parameters`: `[{ "name", "type", "required", "enum"(省略可) }]`
- path にはパステンプレート（`/pet/{petId}` 形式）も使用可

### 設定ファイル (`papycli.conf`)

`{ "default": "<api-name>", "<api-name>": { "openapispec", "apidef", "url" } }` の形式。

---

## CLI 仕様

### コマンド構文

\`\`\`
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
\`\`\`

### サポートするメソッド

`get | post | put | patch | delete` をサポートする。

### パステンプレートのマッチング

リソースパスに数値や文字列が含まれる場合（例：`/pet/99`）、API 定義内のテンプレート（`/pet/{petId}`）にマッチさせ、値を埋め込んでリクエストを送信する。

---

## 環境変数

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `PAPYCLI_CONF_DIR` | `~/.papycli` | 設定ディレクトリのパス |
| `PAPYCLI_CUSTOM_HEADER` | （なし） | 全リクエストに付与するカスタムヘッダー（改行区切りで複数指定可） |

---

## テスト方針

- `tests/unittest/` 以下にユニットテストを配置する
- `tests/integration/` 以下に統合テストを配置する
- HTTP リクエストは `responses` ライブラリ等でモックして実テストしない
- OpenAPI spec の変換ロジックは代表的なケースを網羅するテストを書く

---

## コーディング規約

- フォーマッタ・Lint は `ruff` を使用する
- 型ヒントを積極的に使用し、`mypy` でチェックを通す
- 関数・モジュールの公開 API にのみ docstring を書く（内部実装には不要）
- エラーメッセージはユーザーが原因を特定しやすい内容にする

---

## コード調査・編集のワークフロー

- シンボル操作はファイルを直接読む前にできるだけSerenaを使うこと
- ファイル内容の検索には可能なら `grep` ではなく `rg`（ripgrep）を使うこと

---

## Git リポジトリ運用 (GitHub)

### issue 管理

- ソースコードやドキュメントの追加・修正は原則として最初に issue を作成し、それに対応する形で行う
- issue には適切なラベルをつける。使用するラベルは以下のいずれか
- 機能以外のバグの場合、`ci`、`chore` などのラベルも追加する

| ラベル | 用途 |
|---------------|------|
| `feature` | 新機能の追加 |
| `bug` | バグ修正 |
| `refactor` | 機能変更を伴わないリファクタリング |
| `test` | テストコードの追加 |
| `ci` | GitHub ActionsなどContinuous Integrationに関係する変更 |
| `documentation` | ドキュメントのみの変更 |
| `chore` | 上記以外 (ビルド・依存関係・設定等のメンテナンス) |

### ブランチ・コミット・PR

- ソースコード修正は必ず最新の `main` ブランチからピックブランチを作成しておこなう
- ソースコード修正時、異なるタイプの修正 (たとえば機能追加とリファクタリング) は極力コミットを分ける。
- Pythonのソースコードを追加・修正した場合、`ruff` と `mypy` でチェックし、警告がなくなるようにしておく
- コミットメッセージは原則として Conventional Commits に従う
  - ユーザーから見て機能に変更がないときは `feat` は使わない
  - 破壊的変更を伴う場合、`feat!:` や `fix!` のようにコミットメッセージのタイプに**必ず**`!`を付ける
  - `ci` や `chore` のバグ修正の場合、`fix(ci):`、`fix(chore)` のように機能上の不具合修正でないことがわかるように明記する
  - コミットに互換性を損なう破壊的変更が含まれる場合、"BREAKING CHANGE:" フッターを**必ず**追加する
  - 重要: プルリクエスト (PR) のレビュー指摘に対するコード修正のときだけ Conventional Commits で定義されていない `review:` プレフィクスを付ける（CHANGELOG対象から外すため）
- PR でレビュー指摘を受けた場合、必要であればコードを修正し、修正コミットをプッシュする
- PR で `Nit` の指摘に対しては「このままとします」と回答し、コードは修正しなくてよい
- プッシュ後、修正内容を簡潔にまとめてPRに返信する
```

- [ ] **Step 3: 行数を確認する**

```bash
wc -l CLAUDE.md
```

Expected: 110 行前後（100〜120 行の範囲）

- [ ] **Step 4: コミットする**

```bash
git add CLAUDE.md
git commit -m "docs: simplify CLAUDE.md from 277 to ~110 lines"
```
