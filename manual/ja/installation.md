# インストール

## papycli のインストール

```bash
pip install papycli
```

## シェル補完の有効化

### bash の場合

```bash
# ~/.bashrc または ~/.bash_profile に追加
eval "$(papycli config completion-script bash)"
```

設定を反映するためにシェルを再起動するか `source ~/.bashrc` を実行してください。

### zsh の場合

```bash
# ~/.zshrc に追加
eval "$(papycli config completion-script zsh)"
```

設定を反映するためにシェルを再起動するか `source ~/.zshrc` を実行してください。

### Git Bash（Windows）の場合

Git Bash は MSYS のパス変換機能を持つため、`$()` コマンド置換の出力が変換されて `eval` が正しく動作しないことがあります。
`eval` を実行する前にパス変換を無効にしてください：

```bash
# ~/.bashrc または ~/.bash_profile に追加
export MSYS_NO_PATHCONV=1
eval "$(papycli config completion-script bash)"
```
