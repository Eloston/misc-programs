#!/bin/bash

set -euo pipefail

# Assumes: backports repo is enabled and apt lists are already up to date.

# Detect codename
if [[ -r /etc/os-release ]]; then
  . /etc/os-release
  CODENAME="${VERSION_CODENAME}"
else
  CODENAME="$(lsb_release -sc)"
fi

# Gather (tab-separated): PACKAGE<TAB>CURRENT<TAB>-><TAB>BACKPORTS
readarray -t TSV < <(
  aptitude search -t "${CODENAME}-backports" '?upgradable ?archive(backports)' \
    -F '%p\t%v\t->\t%V' | awk 'NF'
)

if [[ ${#TSV[@]} -eq 0 ]]; then
  echo "No backports upgrades available."
  exit 0
fi

TMPFILE="$(mktemp)"

# Header with nvim modelines:
# - nowrap: avoid wrapping long version strings.
# - noexpandtab: keep tabs, so columns align visually.
# - tabstop=24: tune visual width of tabs; adjust to taste.
# - colorcolumn=, list, listchars to gently show tabs without clutter.
{
  echo "# Edit the list of packages to upgrade from ${CODENAME}-backports."
  echo "# Delete lines to skip packages. Lines starting with '#' are ignored."
  echo "# Columns (tab-separated): PACKAGE<TAB>CURRENT<TAB>-><TAB>BACKPORTS"
  echo "# vim: set nowrap noexpandtab tabstop=24 list listchars=tab:\ \ ,trail:· colorcolumn=:"
  printf "%s\t%s\t%s\t%s\n" "PACKAGE" "CURRENT" "->" "BACKPORTS"
  printf "%s\n" "${TSV[@]}"
} > "$TMPFILE"

# Comment the header row so it won't be selected
sed -i 's/^PACKAGE/# PACKAGE/' "$TMPFILE"

"${EDITOR:-nvim}" "$TMPFILE"

# Read back selected package names (ignore comments/blank lines).
# Because we kept hard tabs and first field is the package name,
# we can safely split on tabs and take field 1.
readarray -t SELECTED < <(
  grep -v '^\s*#' "$TMPFILE" | awk -F'\t' 'NF {print $1}' | sort -u
)

rm -f "$TMPFILE"

if [[ ${#SELECTED[@]} -eq 0 ]]; then
  echo "No packages selected; nothing to do."
  exit 0
fi

sudo apt install -y --only-upgrade -t "${CODENAME}-backports" "${SELECTED[@]}"

