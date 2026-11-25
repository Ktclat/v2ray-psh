#!/usr/bin/env bash
# GitHub's latest endpoint excludes drafts and prereleases. Check the response as well.
set -euo pipefail
: "${GH_TOKEN:?Missing the GitHub Actions read token}"
curl --fail --silent --show-error --max-time 30 --retry 2 \
  -H "Authorization: Bearer $GH_TOKEN" \
  -H 'Accept: application/vnd.github+json' \
  https://api.github.com/repos/2dust/v2rayN/releases/latest |
  jq -er 'select(.draft == false and .prerelease == false and (.published_at | type == "string")) |
    .tag_name | strings | select(length <= 32 and test("\\Av?[0-9]+(\\.[0-9]+){1,3}\\z"))'
