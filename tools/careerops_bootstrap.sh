#!/usr/bin/env bash
# Fetch the pinned career-ops release into ./career-ops (gitignored), install its
# dependencies, copy Punit's seed files (the career-ops "user layer") into it, seed
# an empty tracker, and run career-ops' own doctor.
#
#   bash tools/careerops_bootstrap.sh                 # use the commit in career-ops.lock
#   bash tools/careerops_bootstrap.sh --update        # move the pin to upstream HEAD, then fetch
#   bash tools/careerops_bootstrap.sh --export-seeds  # copy edited seed files back into career-ops-data/
#
# Layout: PROJECT_ROOT and DATA_ROOT are both ./career-ops (career-ops' default
# layout, so every upstream script finds the user layer without an override).
# career-ops-data/ in git is the source of truth for the seed files; the checkout
# holds the private runtime data (data/, reports/, jds/), which the daily routine
# persists to Drive with tools/careerops_state.py.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK="$REPO_DIR/career-ops.lock"
DEST="$REPO_DIR/career-ops"
SEEDS="$REPO_DIR/career-ops-data"
SEED_FILES="cv.md config/profile.yml portals.yml modes/_profile.md modes/_brief.md modes/_custom.md"

lock_get() { python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' "$LOCK" "$1"; }

if [ "${1:-}" = "--export-seeds" ]; then
  for f in $SEED_FILES; do
    if [ -f "$DEST/$f" ]; then
      mkdir -p "$(dirname "$SEEDS/$f")"
      cp "$DEST/$f" "$SEEDS/$f"
      echo "exported $f"
    fi
  done
  exit 0
fi

url="$(lock_get repo)"
sha="$(lock_get commit)"

if [ "${1:-}" = "--update" ]; then
  sha="$(git ls-remote "$url" HEAD | cut -f1)"
  python3 -I - "$LOCK" "$sha" <<'PY'
import json, sys, datetime
p, sha = sys.argv[1], sys.argv[2]
d = json.load(open(p))
d["commit"] = sha
d["pinned_on"] = datetime.date.today().isoformat()
json.dump(d, open(p, "w"), indent=2)
open(p, "a").write("\n")
print("career-ops.lock now pins", sha)
PY
fi

if [ ! -d "$DEST/.git" ]; then
  mkdir -p "$DEST"
  git -C "$DEST" init -q
  git -C "$DEST" remote add origin "$url"
fi

have="$(git -C "$DEST" rev-parse HEAD 2>/dev/null || echo none)"
if [ "$have" != "$sha" ]; then
  git -C "$DEST" fetch -q --depth 1 origin "$sha"
  git -C "$DEST" checkout -q --detach FETCH_HEAD
fi

if [ "${1:-}" = "--update" ]; then
  python3 -I - "$LOCK" "$(cut -d' ' -f1 "$DEST/VERSION")" <<'PY'
import json, sys
p, ver = sys.argv[1], sys.argv[2]
d = json.load(open(p)); d["version"] = ver
json.dump(d, open(p, "w"), indent=2); open(p, "a").write("\n")
PY
fi

if [ ! -d "$DEST/node_modules/js-yaml" ]; then
  (cd "$DEST" && PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install --no-audit --no-fund --loglevel=error)
fi

# Seed files: git is the source of truth, copied into the checkout on every run.
for f in $SEED_FILES; do
  mkdir -p "$(dirname "$DEST/$f")"
  cp "$SEEDS/$f" "$DEST/$f"
done

mkdir -p "$DEST/data" "$DEST/reports" "$DEST/output" "$DEST/jds" \
         "$DEST/batch/tracker-additions" "$DEST/interview-prep"

if [ ! -f "$DEST/data/applications.md" ]; then
  printf '# Applications Tracker\n\n| # | Date | Company | Role | Score | Status | PDF | Report | Notes | URL |\n|---|------|---------|------|-------|--------|-----|--------|-------|-----|\n' \
    > "$DEST/data/applications.md"
  echo "seeded empty data/applications.md"
fi

echo "career-ops $(cut -d' ' -f1 "$DEST/VERSION") at $(git -C "$DEST" rev-parse --short HEAD) in $DEST"
echo "seeds synced from $SEEDS: $SEED_FILES"
(cd "$DEST" && node doctor.mjs --json)
