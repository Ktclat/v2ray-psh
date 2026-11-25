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
# If upstream changes the affected integration points, stop rather than guess or ship unpatched code.
git apply --check --index "$here/patches/terminal-commands.patch"
git apply --index "$here/patches/terminal-commands.patch"
git diff --cached --check "$base" -- v2rayN
# Keep upstream build files and source, but do not install somebody else's Actions in this repository.
git rm -rq -- .github/workflows
git write-tree
