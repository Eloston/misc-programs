#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: borg_to_kopia.sh <borg_repo> <kopia_repo> [--mount-dir DIR]

Converts a BorgBackup 1.x repository into a Kopia filesystem repository by
creating one Kopia snapshot per Borg archive, preserving snapshot time.

Requirements:
  - borg (1.x), kopia, jq, mountpoint
  - For encrypted Borg repos: set BORG_PASSPHRASE or BORG_PASSCOMMAND
  - For Kopia: set KOPIA_PASSWORD (or use existing repository config)

Example:
  BORG_PASSPHRASE=secret KOPIA_PASSWORD=secret \
    ./borg_to_kopia.sh /path/to/borg-repo /path/to/kopia-repo
EOF
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 2 ]]; then
  usage
  exit 1
fi

BORG_REPO=$1
KOPIA_REPO=$2
SNAPSHOT_PATH="eloston@elframework:/home/eloston/box"
shift 2

MOUNT_BASE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mount-dir)
      MOUNT_BASE=$2
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

require_cmd borg
require_cmd kopia
require_cmd jq
require_cmd mountpoint

if [[ -z "$MOUNT_BASE" ]]; then
  MOUNT_BASE=$(mktemp -d)
else
  mkdir -p "$MOUNT_BASE"
fi

cleanup_mounts=()
cleanup() {
  for m in "${cleanup_mounts[@]:-}"; do
    if mountpoint -q "$m"; then
      borg umount "$m" >/dev/null 2>&1 || true
    fi
  done
  if [[ -z ${MOUNT_BASE:-} || ${MOUNT_BASE} == /tmp/* ]]; then
    rm -rf "$MOUNT_BASE" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

# Connect or create Kopia filesystem repository
if ! kopia repository status >/dev/null 2>&1; then
  if ! kopia repository connect filesystem --path "$KOPIA_REPO" >/dev/null 2>&1; then
    kopia repository create filesystem --path "$KOPIA_REPO" >/dev/null
  fi
fi

printf "Listing Borg archives...\n" >&2
borg list --json "$BORG_REPO" | jq -r '.archives[] | [.name, .time] | @tsv' | \
while IFS=$'\t' read -r archive_name archive_time; do
  if [[ -z "$archive_name" ]]; then
    continue
  fi

  mount_dir="$MOUNT_BASE/$archive_name"
  mkdir -p "$mount_dir"
  cleanup_mounts+=("$mount_dir")

  printf "Mounting %s...\n" "$archive_name" >&2
  borg mount "$BORG_REPO::$archive_name" "$mount_dir" &
  mount_pid=$!

  # Wait for mount to become available
  for _ in {1..300}; do
    if mountpoint -q "$mount_dir"; then
      break
    fi
    sleep 0.1
  done

  if ! mountpoint -q "$mount_dir"; then
    echo "Failed to mount archive: $archive_name" >&2
    kill "$mount_pid" >/dev/null 2>&1 || true
    exit 1
  fi

  # Convert Borg ISO-8601 time to Kopia-accepted format
  start_time="$(date -d "$archive_time" +"%Y-%m-%d %H:%M:%S %Z")"

  printf "Creating Kopia snapshot for %s...\n" "$archive_name" >&2
  kopia snapshot create "$mount_dir" \
    --override-source="$SNAPSHOT_PATH" \
    --start-time="$start_time" \
    --description="Borg archive $archive_name" \
    --tags="borg-archive:$archive_name" \
    --tags="borg-repo:$BORG_REPO"

  printf "Unmounting %s...\n" "$archive_name" >&2
  borg umount "$mount_dir"
  wait "$mount_pid" >/dev/null 2>&1 || true

  # Clear mount from cleanup list after success
  cleanup_mounts=(${cleanup_mounts[@]/$mount_dir})
  rmdir "$mount_dir" >/dev/null 2>&1 || true

done

printf "Done.\n" >&2
