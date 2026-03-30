# papycli

**papycli** は OpenAPI 3.0 仕様を読み込み、REST API エンドポイントをターミナルから直接呼び出せるインタラクティブな CLI を提供します。

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

## 制限事項

- リクエストボディは `application/json` のみ対応
- 配列パラメータはスカラー型（string、integer 等）のみ対応（オブジェクトの配列は非対応）
- 認証ヘッダーは `-H "Authorization: Bearer token"` または `PAPYCLI_CUSTOM_HEADER` 環境変数で渡す
