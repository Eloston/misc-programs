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

# Query backports upgrades with versions for display, and names for install
readarray -t LINES < <(
  aptitude search -t "${CODENAME}-backports" '?upgradable ?archive(backports)' -F '%p %v -> %V' | awk 'NF'
)
if [[ ${#LINES[@]} -eq 0 ]]; then
  echo "No backports upgrades available."
  exit 0
fi

# Prepare editable list (git-commit style)
TMPFILE="$(mktemp)"
{
  echo "# Edit the list of packages to upgrade from ${CODENAME}-backports."
  echo "# Keep one entry per line. Lines starting with '#' are ignored."
  echo "# Format: <package> <current> -> <backports>"
  echo "# Delete lines to skip packages. Save and close to proceed."
  printf "%s\n" "${LINES[@]}"
} > "$TMPFILE"

"${EDITOR:-nvim}" "$TMPFILE"

# Read back selected package names (ignore comments/blank lines), take first field as package
readarray -t SELECTED < <(grep -v '^\s*#' "$TMPFILE" | awk 'NF' | awk '{print $1}' | sort -u)
rm -f "$TMPFILE"

if [[ ${#SELECTED[@]} -eq 0 ]]; then
  echo "No packages selected; nothing to do."
  exit 0
fi

# Upgrade only already-installed packages to their backports versions
sudo apt install -y --only-upgrade -t "${CODENAME}-backports" "${SELECTED[@]}"

