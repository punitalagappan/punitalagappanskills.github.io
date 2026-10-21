# punitalagappanskills.github.io

Portfolio site (`index.html`, `script.js`, the case files) plus Punit's Claude Code skills.

## career-ops (job-search agent)

[career-ops](https://github.com/career-ops-hq/career-ops) is an open-source AI job-search
agent (MIT): it scores a job posting into an A-F report with a 1-5 score, triages batches,
tracks applications and follow-ups, and prepares interviews. It is wired in here as a
pinned dependency plus Punit's own data layer, and runs every weekday as a scheduled task.

| Piece | Where |
|-------|-------|
| Pinned upstream commit | `career-ops.lock` (fetched at run time into `./career-ops/`, gitignored) |
| Bootstrap (fetch, `npm install`, doctor) | `tools/careerops_bootstrap.sh` |
| Punit's seed files (CV, profile, portals, triage brief, house rules) | `career-ops-data/`, copied into the checkout by the bootstrap |
| Private runtime data (tracker, reports, saved JDs) | inside the gitignored checkout; persisted to Drive `Job_Search_Master/career-ops/careerops_state.txt` by `tools/careerops_state.py` |
| Connector-fed pipeline helper | `tools/careerops_pipeline.py` |
| Interactive skill (`/career-ops`) | `.claude/skills/career-ops/SKILL.md` |
| Unattended weekday routine (`/career-ops-daily`) | `.claude/skills/career-ops-daily/SKILL.md` |
| Proposed hook into the 9:41 AM Career OS digest | `.claude/skills/career-ops-daily/PROPOSED_hook.md` |

### Daily routine

The scheduled task **"career-ops daily pre-run"** fires at 8:41 AM America/Chicago, Monday to
Friday, in a fresh cloud session of this repository. It bootstraps career-ops, restores the
state bundle from Drive, discovers fresh US finance-analyst postings through the JobDataLake,
Indeed and JobsPipe connectors (career-ops' own scanner is blocked by the cloud network
policy), triages up to 15, runs full A-F evaluations on the top 3, lists follow-ups due, and
writes `careerops_brief_<date>.md` plus the new `careerops_state.txt` to Drive. Its final
message is a phone-sized summary. The 9:41 AM Career OS digest can read the brief's `FEED`
section once the proposed hook is approved.

### Run it yourself

```bash
bash tools/careerops_bootstrap.sh      # fetch the pinned release, install, copy the seed files
cd career-ops
node scan.mjs --since 2                # needs normal internet (blocked in the cloud sandbox)
node stats.mjs --summary
node followup-cadence.mjs --summary
```

Or open Claude Code in this repository and say "evaluate this job <url>" (the `career-ops`
skill), or "run the career-ops daily" (the `career-ops-daily` skill).

To update career-ops: `bash tools/careerops_bootstrap.sh --update`, then commit `career-ops.lock`.
