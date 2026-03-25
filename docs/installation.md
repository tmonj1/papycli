# Installation

## Install papycli

```bash
pip install papycli
```

## Enable Shell Completion

### bash

```bash
# Add to ~/.bashrc or ~/.bash_profile
eval "$(papycli config completion-script bash)"
```

Restart your shell or run `source ~/.bashrc` to apply.

### zsh

```bash
# Add to ~/.zshrc
eval "$(papycli config completion-script zsh)"
```

Restart your shell or run `source ~/.zshrc` to apply.

### Git Bash (Windows)

Git Bash uses MSYS path conversion, which can mangle the output of `$()` command substitution.
Disable it before running the `eval` command:

```bash
# Add to ~/.bashrc or ~/.bash_profile
export MSYS_NO_PATHCONV=1
eval "$(papycli config completion-script bash)"
```
