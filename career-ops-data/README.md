# career-ops-data: Punit's seed files for career-ops

These are the committed "user layer" files for
[career-ops](https://github.com/career-ops-hq/career-ops) (pinned in `../career-ops.lock`).
`tools/careerops_bootstrap.sh` fetches the pinned upstream into `../career-ops/`
(gitignored) and copies these files into it on every run, so career-ops runs in its
default layout (PROJECT_ROOT = DATA_ROOT = `../career-ops`) and every upstream script
finds them:

```bash
bash tools/careerops_bootstrap.sh          # fetch, npm install, copy seeds, seed tracker, doctor
cd career-ops
node doctor.mjs --json
node scan.mjs --since 2 --quiet            # needs normal internet (blocked in the cloud sandbox)
node stats.mjs --summary
```

| File | Purpose |
|------|---------|
| `cv.md` | Master CV in career-ops' markdown shape, from the verified facts file |
| `config/profile.yml` | Identity, target archetypes, comp, dealbreakers, run settings |
| `portals.yml` | Title and location filters plus tracked US finance employers for the scanner |
| `modes/_brief.md` | Compact triage brief (first-pass go/no-go) |
| `modes/_profile.md` | Archetypes, framing, narrative, comp, location and work-authorization policy |
| `modes/_custom.md` | House rules: no dashes, no visa wording, no documents from career-ops, unattended-run rules |

Edit them here and re-run the bootstrap, or edit the copies inside `../career-ops/` and
pull them back with `bash tools/careerops_bootstrap.sh --export-seeds`.

The private runtime data (`data/` tracker and pipeline, `reports/`, `jds/`, `output/`)
lives only in the gitignored checkout. In the cloud, the daily routine persists it to
Google Drive as one text bundle, `Job_Search_Master/career-ops/careerops_state.txt`,
with `tools/careerops_state.py pack|unpack`, and restores it at the start of every run.
