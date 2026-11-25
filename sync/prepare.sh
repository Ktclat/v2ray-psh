#!/usr/bin/env bash
# Usage: bash sync/prepare.sh <exact upstream SHA> <new checkout directory>
set -euo pipefail
[[ $# -eq 2 && "$1" =~ ^[0-9a-f]{40}$ ]] || { echo "Expected a full upstream commit SHA" >&2; exit 2; }
base="$1"
target="$2"
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
[[ ! -e "$target" ]] || { echo "Checkout directory already exists" >&2; exit 2; }
git init --quiet "$target"
cd "$target"
git config core.autocrlf false
git fetch --no-tags https://github.com/2dust/v2rayN.git "$base"
[[ "$(git rev-parse FETCH_HEAD)" == "$base" ]]
git -c advice.detachedHead=false checkout --quiet --detach "$base"
# The desktop build uses one upstream-pinned submodule. No recursive downloads.
[[ "$(git ls-files --stage | awk '$1 == "160000" {print $4}')" == v2rayN/GlobalHotKeys ]]
[[ "$(git config -f .gitmodules --get submodule.v2rayN/GlobalHotKeys.url)" == https://github.com/2dust/GlobalHotKeys ]]
git submodule update --init -- v2rayN/GlobalHotKeys >&2
# v2rayN 7.x uses the original WPF project name; 8.x renamed it.
# Select the known layout first. Never fall through to other patches after a conflict.
if [[ -f v2rayN/v2rayN.Windows/v2rayN.Windows.csproj && ! -f v2rayN/v2rayN/v2rayN.csproj ]]; then
    patch=patches/terminal-commands.patch
elif [[ -f v2rayN/v2rayN/v2rayN.csproj && ! -f v2rayN/v2rayN.Windows/v2rayN.Windows.csproj ]]; then
    patch=patches/terminal-commands-legacy-wpf.patch
else
    echo "Unrecognized WPF project layout" >&2
    exit 1
fi
git -C "$here" show "HEAD:$patch" | git apply --check --index -
git -C "$here" show "HEAD:$patch" | git apply --index -
git diff --cached --check "$base" -- v2rayN
# Keep upstream build files and source, but do not install somebody else's Actions in this repository.
git rm -rq -- .github/workflows
git write-tree
