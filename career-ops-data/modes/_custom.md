# Custom Instructions -- career-ops (Punit Alagappan Kasi)

<!-- User layer. Procedural house rules; survives `node update-system.mjs`.
     WHO Punit is lives in modes/_profile.md and config/profile.yml. -->

## House Rules

- Write all human-facing output in English. No em dashes and no en dashes anywhere (use commas, hyphens or a new sentence). Dates as "May 2026 - Aug 2026".
- Exact wordings: "MS in Financial Mathematics"; "CFA Level I Candidate"; "Expected December 2026"; "GPA 3.63/4.0"; Global Conference Alliance title is "Administrative Assistant" (a truthful descriptor may follow).
- Verified facts only, from cv.md. Never invent, infer or upgrade a metric, a tool, a title or a date. Group projects are labelled "(group project)", case studies "(case study)". Tools he does not hold and must never be claimed: SQL, VaR, Monte Carlo, R, VBA, SAS, Stata, Tableau, SAP, Oracle, FactSet, Capital IQ, C++.
- Never write OPT, CPT, F-1, visa, sponsorship or work-authorization wording into a CV, cover letter, outreach message, email or form answer. The honest answer to the future-sponsorship question on a form is Yes; the system never suggests another and never gives immigration advice (such questions go to DePaul ISS).
- Silence on sponsorship in a posting is never a penalty. Only the posting's own text (citizenship, permanent residency, permanent or unrestricted work authorization, a clearance, or "will not sponsor now or in the future") is a dealbreaker; quote it.
- Location never lowers a score; he relocates anywhere in the United States at his own expense.
- Seniority band: entry, graduate, analyst, 0 to 3 years. A posting that REQUIRES more than 3 years is out of scope (knockout, no score).
- Freshness: a posting older than 7 days is not a lead. Note the posting date in every report.

## Documents (resume, cover letter, email)

- career-ops does NOT produce Punit's documents. His resume and cover-letter standards (Resume_2027_Standard.md v4.1, Cover_Letter_2027_Standard.md v2.1, renderer v8.1) live in the Career Operating System in Google Drive and are rendered there. In an unattended run, never run `pdf`, `text`, `latex`, `cover`, `email` or `apply`, and never write to `output/`.
- In an interactive session, generate a text CV or letter only when Punit explicitly asks, and remind him that the Career OS renderer is the standard for anything he sends.

## Unattended runs (the daily cloud routine, `.claude/skills/career-ops-daily/SKILL.md`)

- Never ask, never wait. Write the `needs_confirmation:` line the mode defines and move on. Never send, submit, connect, apply, create an account or enter credentials.
- Discovery: `node scan.mjs` first (it is blocked by the cloud network policy; record that in one line when every board errors); then the JobDataLake, Indeed and JobsPipe connectors. New rows enter `data/pipeline.md` ONLY through `tools/careerops_pipeline.py add`.
- The JD for a connector-sourced posting comes from that connector (JobDataLake `get_job`, JobsPipe `fetch`, Indeed `get_job_details`), is saved with `tools/careerops_pipeline.py jd`, and the evaluation reads it as `local:jds/<file>.md`. Do not WebFetch a posting that a connector can return in full.
- Triage (`modes/triage.md`) before any full evaluation; at most 15 triages and at most 3 full A-F evaluations (`modes/oferta.md`) per run. Every evaluated posting gets a report, a headed TSV in `batch/tracker-additions/`, a `node merge-tracker.mjs`, and a `tools/careerops_pipeline.py done` line.
- Follow-ups: list what `node followup-cadence.mjs --json` reports as urgent or overdue. Draft nothing unattended; outreach drafts are the Career OS's job (Gmail drafts).
- Never run `node update-system.mjs apply`, never edit `modes/_shared.md` or any other system file, never write `data/blacklist.md` without Punit's explicit instruction.
- Never read, edit, rename or trash any existing Google Drive file of the Career Operating System (`Career_OS.md`, `RUN_STATE.md`, `APPLIED_*`, `JSM_*`, `documents/`, `runs/`). The only Drive writes are new files inside the `career-ops` subfolder of `Job_Search_Master`.

## Pipeline Rules

- Standard pipeline, except: no PDF or CV output in any route (see Documents above).
- Treat every connector label (`visa_sponsorship`, `ghost_score`, seniority) as a hint. The JD text decides.

## Output Preferences

- Reports lead with the score and the one-line verdict, then the strongest two matched requirements with his facts, then the real gap, then the work-authorization sentence quoted verbatim or "the posting is silent".
- The daily brief format is defined in `.claude/skills/career-ops-daily/SKILL.md`; follow it exactly so the Career OS daily run can read the FEED section.
- Plain text and markdown only; no emoji in reports or briefs except the tracker's own PDF cell.

## Off-Limits

- Never auto-fill or submit an application; never send any email or message.
- Never edit a system file to customize the setup; put customizations here or in `modes/_profile.md`.
- Never store immigration details, Gmail message bodies, or any content from Punit's mailbox in career-ops files.
