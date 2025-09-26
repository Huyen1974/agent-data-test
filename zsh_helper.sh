#!/bin/bash
# Zsh Helper Script - Load additional tools when needed
# This script can be sourced when you need full functionality

echo "🔧 Loading full Zsh environment..."

# ----- Homebrew -----
eval "$(/opt/homebrew/bin/brew shellenv)"

# ----- Google Cloud SDK -----
if [ -f '/Users/nmhuyen/google-cloud-sdk/path.zsh.inc' ]; then
    source '/Users/nmhuyen/google-cloud-sdk/path.zsh.inc'
    source '/Users/nmhuyen/google-cloud-sdk/completion.zsh.inc'
fi

# ----- Python Environments -----
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# Conda
__conda_setup="$('/Users/nmhuyen/miniconda/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/Users/nmhuyen/miniconda/etc/profile.d/conda.sh" ]; then
        source "/Users/nmhuyen/miniconda/etc/profile.d/conda.sh"
    else
        export PATH="/Users/nmhuyen/miniconda/bin:$PATH"
    fi
fi

# ----- Other Tools -----
export JAVA_HOME="/Library/Java/JavaVirtualMachines/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
export PATH="/opt/homebrew/opt/mysql-client/bin:$PATH"
export PATH="$PATH:/Users/nmhuyen/.local/bin"
fpath=(/Users/nmhuyen/.docker/completions $fpath)
autoload -Uz compinit && compinit

echo "✅ Full environment loaded!"
echo "💡 You can now use: gcloud, terraform, python, conda, docker, etc."
