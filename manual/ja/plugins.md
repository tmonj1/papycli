# フィルタープラグイン

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

### `RequestContext` のフィールド

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

### `ResponseContext` のフィールド

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
