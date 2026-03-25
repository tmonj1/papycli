# 開発

## セットアップ

```bash
git clone https://github.com/tmonj1/papycli.git
cd papycli
pip install -e ".[dev]"
```

## テストの実行

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

## ツール

| ツール | 用途 |
|--------|------|
| `pytest` | テスト実行 |
| `ruff` | Lint + フォーマット |
| `mypy` | 型チェック |

## ドキュメントのビルド

ドキュメントをローカルでビルドするには、`mkdocs-material` をインストールして以下を実行します：

```bash
pip install mkdocs-material
mkdocs serve
```

`http://127.0.0.1:8000/` でライブリロード付きのローカルサーバーが起動します。
