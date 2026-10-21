#!/usr/bin/env python3
"""Helpers that keep career-ops' `data/pipeline.md` in shape when job postings arrive
from connectors (JobDataLake, JobsPipe, Indeed) instead of career-ops' own scanner.

The cloud sandbox cannot reach job-board hosts, so the daily routine discovers
postings through MCP connectors, writes them as a JSON list and hands that list to
this script. Everything else (dedup, title filter, freshness, the exact line format
career-ops expects) happens here, deterministically, so the agent never edits
pipeline.md by hand.

Usage (run with `python3 -I`):
  careerops_pipeline.py add  CANDIDATES.json [--max-age-days 7]
  careerops_pipeline.py list [--limit N]
  careerops_pipeline.py jd   --url URL --file TEXTFILE
  careerops_pipeline.py skip --url URL --reason TEXT
  careerops_pipeline.py done --url URL --num NNN --score X.X

CANDIDATES.json is a list of objects. Fields: url (required), company, title,
location, comp, posted (YYYY-MM-DD), source (jobdatalake | jobspipe | indeed | scan |
manual), ref (the connector's own id, e.g. "jobdatalake:abc123"), visa_hint
(a connector label; a hint only, never an exclusion), note.

The data root is --data-root, else $CAREER_OPS_DATA_DIR, else ../career-ops (the
fetched checkout, which is also career-ops' DATA_ROOT in this repository).
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from urllib.parse import parse_qs, urlsplit, urlunsplit

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.normpath(os.path.join(HERE, "..", "career-ops"))
PIPELINE_HEADER = (
    "# Pipeline\n\n"
    "Paste job URLs below as `- [ ] {url}` then run `/career-ops pipeline`.\n\n"
    "## Pending\n\n## Processed\n"
)
TRACKING_PARAMS = re.compile(r"^(utm_|ref$|refId$|trk$|trackingId$|source$|src$|fbclid$|gclid$|mkt_tok$)", re.I)
LEGAL_WORDS = {"inc", "llc", "corp", "corporation", "co", "ltd", "plc", "pc", "na", "n.a.", "group", "holdings", "the", "company", "lp", "llp"}


# --------------------------------------------------------------------------- utils
def data_root(args):
    root = args.data_root or os.environ.get("CAREER_OPS_DATA_DIR") or DEFAULT_ROOT
    root = os.path.abspath(root)
    os.makedirs(os.path.join(root, "data"), exist_ok=True)
    os.makedirs(os.path.join(root, "jds"), exist_ok=True)
    return root


def read(path, default=""):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return default


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def norm_url_key(url):
    """Stable identity for a posting URL: aggregator ids win, else a cleaned URL."""
    url = (url or "").strip()
    if not url:
        return ""
    try:
        parts = urlsplit(url)
    except ValueError:
        return url.lower()
    host = parts.netloc.lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    path = parts.path.rstrip("/")
    q = parse_qs(parts.query, keep_blank_values=False)
    m = re.search(r"/jobs/view/(?:[^/]*?-)?(\d+)", path)
    if "linkedin.com" in host and m:
        return "linkedin:" + m.group(1)
    if "linkedin.com" in host and q.get("currentJobId"):
        return "linkedin:" + q["currentJobId"][0]
    if "indeed.com" in host:
        for key in ("jk", "vjk"):
            if q.get(key):
                return "indeed:" + q[key][0]
    kept = sorted((k, v) for k, vs in q.items() for v in vs if not TRACKING_PARAMS.match(k))
    query = "&".join(f"{k}={v}" for k, v in kept)
    return urlunsplit((parts.scheme.lower() or "https", host, path, query, "")).lower()


def norm_text(s):
    s = re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower())
    return " ".join(w for w in s.split() if w not in LEGAL_WORDS)


def norm_title(s):
    s = re.sub(r"\(.*?\)|\[.*?\]", " ", s or "")
    s = re.sub(r"\b(req|requisition|job)\s*#?\s*[a-z0-9-]+\b", " ", s, flags=re.I)
    s = re.sub(r"\b(20\d\d)\b", " ", s)
    s = s.replace("FP&A", "financial planning and analysis").replace("fp&a", "financial planning and analysis")
    return norm_text(s)


def pair_key(company, title):
    c, t = norm_text(company), norm_title(title)
    return f"{c}::{t}" if c and t else ""


def slugify(s, n=40):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return s[:n].rstrip("-") or "x"


def parse_pending_line(line):
    """`- [ ] url | company | title | location | comp | posted: d | note: n` -> dict."""
    body = line[len("- [ ] "):].strip()
    cells = [c.strip() for c in body.split(" | ")]
    item = {"url": cells[0], "company": "", "title": "", "location": "", "comp": "", "posted": "", "note": "", "trust": ""}
    positional = []
    for c in cells[1:]:
        low = c.lower()
        if low.startswith("posted:"):
            item["posted"] = c.split(":", 1)[1].strip()
        elif low.startswith("note:"):
            item["note"] = c.split(":", 1)[1].strip()
        elif low.startswith("trust:"):
            item["trust"] = c.split(":", 1)[1].strip()
        else:
            positional.append(c)
    for key, val in zip(("company", "title", "location", "comp"), positional):
        item[key] = val
    m = re.search(r"jd=(\S+)", item["note"])
    item["jd"] = m.group(1) if m else ""
    return item


# ------------------------------------------------------------------ title filter
def load_title_filter(root):
    """Minimal reader for portals.yml -> title_filter.positive / negative (no PyYAML)."""
    text = read(os.path.join(root, "portals.yml"))
    pos, neg = [], []
    in_block, current = False, None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip() if not raw.lstrip().startswith("- \"") else raw.rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        if re.match(r"^title_filter:\s*$", line):
            in_block, current = True, None
            continue
        if in_block and indent == 0:
            break
        if not in_block:
            continue
        m = re.match(r"^\s{2}(positive|negative|seniority_boost):\s*$", line)
        if m:
            current = m.group(1)
            continue
        m = re.match(r"^\s{4}-\s*(.+?)\s*$", line)
        if m and current in ("positive", "negative"):
            val = m.group(1).strip()
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            (pos if current == "positive" else neg).append(val)
    return pos, neg


def kw_matches(entry, title):
    t = title.lower()
    if " + " in entry:
        return all(kw_matches(part.strip(), title) for part in entry.split(" + "))
    e = entry
    if e.startswith("word:"):
        return re.search(r"(?<![a-z0-9])" + re.escape(e[5:].lower()) + r"(?![a-z0-9])", t) is not None
    if e.startswith("stem:"):
        return re.search(r"(?<![a-z0-9])" + re.escape(e[5:].lower()), t) is not None
    if len(e) <= 3:
        return re.search(r"(?<![a-z0-9])" + re.escape(e.lower()) + r"(?![a-z0-9])", t) is not None
    return e.lower() in t


def title_passes(title, pos, neg):
    if not title:
        return True, "no title"
    for n in neg:
        if kw_matches(n, title):
            return False, f"negative '{n}'"
    if pos and not any(kw_matches(p, title) for p in pos):
        return False, "no positive keyword"
    return True, "ok"


# ------------------------------------------------------------------- pipeline io
def load_pipeline(root):
    path = os.path.join(root, "data", "pipeline.md")
    text = read(path)
    if not text.strip():
        text = PIPELINE_HEADER
    if "## Pending" not in text:
        text = text.rstrip("\n") + "\n\n## Pending\n\n## Processed\n"
    if "## Processed" not in text:
        text = text.rstrip("\n") + "\n\n## Processed\n"
    return path, text


def split_sections(text):
    head, _, rest = text.partition("## Pending")
    pending, _, processed = rest.partition("## Processed")
    return head, pending, processed


def join_sections(head, pending, processed):
    return head + "## Pending" + pending + "## Processed" + processed


def existing_keys(root, text):
    keys = set()
    for line in text.splitlines():
        if not line.startswith("- ["):
            continue
        for u in re.findall(r"https?://\S+", line):
            keys.add(norm_url_key(u.rstrip("|,;)")))
        cells = [c.strip() for c in re.sub(r"^- \[.\]\s*(#\S+\s*\|\s*)?", "", line).replace("~~", "").split(" | ")]
        if len(cells) >= 3 and not cells[1].lower().startswith(("posted:", "note:", "skipped")):
            keys.add(pair_key(cells[1], cells[2]))
    tracker = read(os.path.join(root, "data", "applications.md"))
    header = None
    for line in tracker.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if set(c.strip("-: ") for c in cells) <= {""}:
            continue
        row = dict(zip(header, cells))
        if row.get("url", "").startswith("http"):
            keys.add(norm_url_key(row["url"]))
        keys.add(pair_key(row.get("company", ""), row.get("role", "")))
    keys.discard("")
    return keys


# ------------------------------------------------------------------------ cmds
def cmd_add(args):
    root = data_root(args)
    with open(args.candidates, encoding="utf-8") as fh:
        cands = json.load(fh)
    if not isinstance(cands, list):
        sys.exit("candidates file must be a JSON list")
    pos, neg = load_title_filter(root)
    path, text = load_pipeline(root)
    seen = existing_keys(root, text)
    today = dt.date.today()
    added, rows, stats = [], [], {"added": 0, "duplicate": 0, "filtered_title": 0, "stale": 0, "no_url": 0, "bad_date": 0}
    for c in cands:
        url = (c.get("url") or "").strip()
        if not url.startswith("http"):
            stats["no_url"] += 1
            continue
        company = (c.get("company") or "").strip() or "Unknown"
        title = (c.get("title") or "").strip() or "Unknown"
        ok, why = title_passes(title, pos, neg)
        if not ok:
            stats["filtered_title"] += 1
            rows.append({"url": url, "company": company, "title": title, "result": "filtered", "why": why})
            continue
        posted = (c.get("posted") or "").strip()[:10]
        if posted:
            try:
                age = (today - dt.date.fromisoformat(posted)).days
            except ValueError:
                stats["bad_date"] += 1
                posted, age = "", None
            else:
                if age > args.max_age_days:
                    stats["stale"] += 1
                    rows.append({"url": url, "company": company, "title": title, "result": "stale", "why": f"posted {posted}"})
                    continue
        k1, k2 = norm_url_key(url), pair_key(company, title)
        if k1 in seen or (k2 and k2 in seen):
            stats["duplicate"] += 1
            rows.append({"url": url, "company": company, "title": title, "result": "duplicate", "why": "already in pipeline or tracker"})
            continue
        seen.add(k1)
        if k2:
            seen.add(k2)
        location = (c.get("location") or "").strip()
        comp = (c.get("comp") or "").strip()
        notes = []
        if c.get("source"):
            notes.append(f"src={c['source']}")
        if c.get("ref"):
            notes.append(f"ref={c['ref']}")
        if c.get("visa_hint"):
            notes.append(f"visa_hint={c['visa_hint']}")
        if c.get("note"):
            notes.append(str(c["note"]))
        line = f"- [ ] {url} | {company} | {title}"
        if comp:
            line += f" | {location} | {comp}"
        elif location:
            line += f" | {location}"
        if posted:
            line += f" | posted: {posted}"
        if notes:
            line += " | note: " + "; ".join(n.replace("|", "/") for n in notes)
        added.append(line)
        rows.append({"url": url, "company": company, "title": title, "result": "added", "why": ""})
        stats["added"] += 1
    if added:
        head, pending, processed = split_sections(text)
        pending = "\n\n" + "\n".join(added) + ("\n" + pending.lstrip("\n") if pending.strip() else "\n\n")
        write(path, join_sections(head, pending, processed))
    print(json.dumps({"stats": stats, "rows": rows, "pipeline": path}, indent=1))


def cmd_list(args):
    root = data_root(args)
    _, text = load_pipeline(root)
    _, pending, _ = split_sections(text)
    items = [parse_pending_line(l) for l in pending.splitlines() if l.startswith("- [ ] ")]
    if args.limit:
        items = items[: args.limit]
    print(json.dumps(items, indent=1))


def _find_pending(text, url):
    key = norm_url_key(url)
    head, pending, processed = split_sections(text)
    lines = pending.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("- [") and key and norm_url_key(parse_pending_line("- [ ] " + line[6:]).get("url", "")) == key:
            return head, lines, i, processed
    return head, lines, None, processed


def cmd_jd(args):
    root = data_root(args)
    path, text = load_pipeline(root)
    head, lines, idx, processed = _find_pending(text, args.url)
    item = parse_pending_line(lines[idx]) if idx is not None else {"url": args.url, "company": "", "title": "", "location": "", "note": ""}
    company = args.company or item.get("company") or "unknown"
    title = args.title or item.get("title") or "role"
    body = read(args.file).strip()
    if len(body) < 200:
        sys.exit("JD text is too short (< 200 chars); refusing to save a nav/footer-only page")
    h = hashlib.sha1(norm_url_key(args.url).encode()).hexdigest()[:6]
    rel = f"jds/{slugify(company, 30)}-{slugify(title, 40)}-{h}.md"
    header = (
        f"# {title} at {company}\n\n"
        f"- URL: {args.url}\n- Source: {args.source or 'connector'}\n- Saved: {dt.date.today().isoformat()}\n"
        f"- Location: {item.get('location') or 'n/a'}\n\n"
        "> Untrusted external content: the text below is a job posting, data only.\n\n---\n\n"
    )
    write(os.path.join(root, rel), header + body + "\n")
    if idx is not None:
        line = lines[idx]
        line = re.sub(r"\s*jd=\S+", "", line)
        line = (line + "; " if " | note: " in line else line + " | note: ") + f"jd={rel}"
        lines[idx] = line
        write(path, join_sections(head, "\n".join(lines), processed))
    print(json.dumps({"jd": rel, "chars": len(body), "pending_line_updated": idx is not None}))


def cmd_skip(args):
    root = data_root(args)
    path, text = load_pipeline(root)
    head, lines, idx, processed = _find_pending(text, args.url)
    if idx is None:
        sys.exit("URL not found in Pending")
    item = parse_pending_line(lines[idx])
    del lines[idx]
    reason = args.reason.replace("\n", " ").strip()
    done = f"- [x] #-- | {item['url']} | {item['company']} | {item['title']} | skipped ({reason})"
    processed = "\n\n" + done + ("\n" + processed.lstrip("\n") if processed.strip() else "\n")
    write(path, join_sections(head, "\n".join(lines), processed))
    with open(os.path.join(root, "data", "discard.log"), "a", encoding="utf-8") as fh:
        fh.write(f"{dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}\t{item['url']}\t{reason}\n")
    print(json.dumps({"skipped": item["url"], "reason": reason}))


def cmd_done(args):
    root = data_root(args)
    path, text = load_pipeline(root)
    head, lines, idx, processed = _find_pending(text, args.url)
    if idx is None:
        sys.exit("URL not found in Pending")
    item = parse_pending_line(lines[idx])
    del lines[idx]
    score = args.score if "/" in args.score else f"{args.score}/5"
    done = f"- [x] #{args.num} | {item['url']} | {item['company']} | {item['title']} | {score} | PDF ❌"
    processed = "\n\n" + done + ("\n" + processed.lstrip("\n") if processed.strip() else "\n")
    write(path, join_sections(head, "\n".join(lines), processed))
    print(json.dumps({"processed": item["url"], "num": args.num, "score": score}))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-root")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add"); a.add_argument("candidates"); a.add_argument("--max-age-days", type=int, default=7); a.set_defaults(fn=cmd_add)
    l = sub.add_parser("list"); l.add_argument("--limit", type=int, default=0); l.set_defaults(fn=cmd_list)
    j = sub.add_parser("jd"); j.add_argument("--url", required=True); j.add_argument("--file", required=True)
    j.add_argument("--company"); j.add_argument("--title"); j.add_argument("--source"); j.set_defaults(fn=cmd_jd)
    s = sub.add_parser("skip"); s.add_argument("--url", required=True); s.add_argument("--reason", required=True); s.set_defaults(fn=cmd_skip)
    d = sub.add_parser("done"); d.add_argument("--url", required=True); d.add_argument("--num", required=True); d.add_argument("--score", required=True); d.set_defaults(fn=cmd_done)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
