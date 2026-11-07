#!/usr/bin/env bash
# Move the data hidden by hide_past_runs.sh back into the project, MERGING it with whatever the
# new run produced (new harness_runs/<run_id>/, solutions/, output_figs/ are kept).
# A file that exists in both places is never overwritten: it stays in the archive and is listed.
set -euo pipefail
cd "$(dirname "$0")"
ARCHIVE="${CAD_ARCHIVE:-$HOME/CAD_prj_archive}"
[ -d "$ARCHIVE" ] || { echo "No archive at $ARCHIVE: nothing to restore."; exit 0; }

rsync -a --ignore-existing --remove-source-files "$ARCHIVE/" ./
find "$ARCHIVE" -depth -type d -empty -delete

if [ -d "$ARCHIVE" ]; then
  echo "These files exist both in the project and in the archive and were NOT restored:" >&2
  find "$ARCHIVE" -type f >&2
  exit 1
fi
echo "Restored everything from $ARCHIVE"
git status --short | head -20
