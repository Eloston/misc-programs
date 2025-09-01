#!/bin/bash
set -euo pipefail

# Assumes: backports repo is enabled and apt lists are already up to date.

# Detect codename
if [[ -r /etc/os-release ]]; then
  # shellcheck source=/dev/null
  source /etc/os-release
  CODENAME="${VERSION_CODENAME}"
else
  CODENAME="$(lsb_release -sc)"
fi

readarray -t UPGRADABLE < <(
  aptitude search -t "${CODENAME}-backports" '?upgradable ?archive(backports)' \
    -F '%p|%v|%V' | awk 'NF'
)

if [[ ${#UPGRADABLE[@]} -eq 0 ]]; then
  echo "No backports upgrades available."
  exit 0
fi

TMPFILE="$(mktemp)"
{
  echo "# Edit the list of packages to upgrade from ${CODENAME}-backports."
  echo "# Delete lines to skip packages. Lines starting with '#' are ignored."
  echo "# Columns: PACKAGE | CURRENT | -> | BACKPORTS"
  printf "%s\n" "${UPGRADABLE[@]}" \
    | awk -F'|' '{printf "%s|%s|->|%s\n",$1,$2,$3}' \
    | column -t -s '|'
} > "$TMPFILE"

"${EDITOR:-nvim}" "$TMPFILE"

# Parse package names (first token), ignore comments/blank lines
readarray -t SELECTED < <(grep -v '^\s*#' "$TMPFILE" | awk 'NF {print $1}' | sort -u)
rm -f "$TMPFILE"

if [[ ${#SELECTED[@]} -eq 0 ]]; then
  echo "No packages selected; nothing to do."
  exit 0
fi

sudo apt install -y --only-upgrade -t "${CODENAME}-backports" "${SELECTED[@]}"

