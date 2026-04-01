# Design: `config add --upgrade` オプション

## 概要

`papycli config add` コマンドに `--upgrade` オプションを追加する。
このオプションは既存の登録済み OpenAPI spec を新しいバージョンに更新するために使用する。

## 要件

- `config add <spec>` は新規登録専用とする。既存の API 名が登録済みの場合はエラーにする。
- `config add --upgrade <spec>` は既存 API の spec・apidef ファイルおよび base URL を更新する。
- `--upgrade` で対象 API が未登録の場合は通常の新規登録として処理する。
- 更新時の base URL は新しい spec から取得した値で上書きする。

## 変更ファイル

`src/papycli/main.py` の `cmd_config_add` のみ変更する。`init_cmd.py` は変更しない。

## 設計詳細

### フラグ追加

```python
@click.option(
    "--upgrade", "upgrade", is_flag=True,
    help=h(
        "Update an existing registered API with a new spec.",
        "既存の登録済み API を新しい spec で更新する。",
    ),
)
def cmd_config_add(spec_file: str, upgrade: bool) -> None:
```

### 分岐ロジック

```
conf をロード
if not upgrade and api_name が既に登録済み:
    → Error: API '{name}' is already registered. Use --upgrade to update it.
    → exit 1
else:
    → init_api(...) で spec・apidef ファイルを（上書き）保存
    → register_initialized_api(...) で conf を更新・保存
    → 成功メッセージ出力
```

### 出力メッセージ

| ケース | メッセージ |
|---|---|
| 新規登録（従来通り） | `Registered API 'petstore'` |
| `--upgrade` で更新 | `Updated API 'petstore'` |
| 既存 API に `--upgrade` なしで `add` | `Error: API 'petstore' is already registered. Use --upgrade to update it.` |

## テスト

`tests/unittest/` に以下を追加する。

1. `config add` で既存 API → エラー終了（exit code 1）
2. `config add --upgrade` で既存 API → 正常更新・"Updated API" メッセージ
3. `config add --upgrade` で未登録 API → 新規登録・"Registered API" メッセージ
