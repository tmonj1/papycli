---
paths:
  - "src/main.py"
---

# CLI 仕様

## コマンド構文

```
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
```

## サポートするメソッド

`get | post | put | patch | delete` をサポートする。

## パステンプレートのマッチング

リソースパスに数値や文字列が含まれる場合（例：`/pet/99`）、API 定義内のテンプレート（`/pet/{petId}`）にマッチさせ、値を埋め込んでリクエストを送信する。
