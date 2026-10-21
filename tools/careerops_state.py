#!/usr/bin/env python3
"""Pack the private career-ops runtime data into ONE text bundle (and back).

Cloud sessions are ephemeral and the repository is public, so the tracker, the
pipeline and recent reports travel through Google Drive as a single plain-text
file: `careerops_state.txt`. Text survives Drive round trips; binaries do not.

Usage (run with `python3 -I`):
  careerops_state.py pack   DATA_ROOT OUT.txt [--report-days 14]
  careerops_state.py unpack IN.txt DATA_ROOT [--unescape]
  careerops_state.py check  IN.txt [--unescape]

`--unescape` undoes the markdown escaping that Drive's read_file_content applies
(`\\#`, `\\_`, `\\-`, trailing double spaces) before the checksum is compared.
Drive's text rendering also collapses every TAB into one space and every run of
spaces (leading indentation included) into one space, which would destroy TSV and
YAML files. So `pack` replaces each tab with `⇥` (U+21E5) and every leading space
or space inside a run of two or more with `␣` (U+2423); `unpack` restores them. A
file that already contains either character is refused.

Bundle format:
  # CAREER-OPS STATE BUNDLE v1
  # packed_at: <UTC ISO>
  # files: <n>
  # checksum: <sha256 of the body with every backslash and whitespace removed>
  ===== FILE: data/applications.md =====
  <content>
  ===== END FILE =====
"""
import argparse
import datetime as dt
import hashlib
import os
import re
import sys

MAGIC = "# CAREER-OPS STATE BUNDLE v1"
TAB = "⇥"  # ⇥ stands in for a tab character inside the bundle
SP = "␣"   # ␣ stands in for a leading space, or a space inside a run of 2+
FILE_OPEN = "===== FILE: "
FILE_CLOSE = "===== END FILE ====="
MAX_FILE_BYTES = 400_000
INCLUDE_DIRS = {"data": (".md", ".tsv", ".log", ".json", ".yml"), "batch/tracker-additions": (".tsv",)}
SKIP_FILES = {"data/applications.db", "data/.gitkeep", "data/offers/.gitkeep", "data/parser-output/.gitkeep"}


def norm_checksum(body):
    return hashlib.sha256(re.sub(r"[\\\s]", "", body).encode("utf-8")).hexdigest()


def collect(root, report_days):
    picked = []
    cutoff = dt.datetime.now().timestamp() - report_days * 86400
    for sub, exts in INCLUDE_DIRS.items():
        base = os.path.join(root, sub)
        if not os.path.isdir(base):
            continue
        for dirpath, _, files in os.walk(base):
            for f in sorted(files):
                full = os.path.join(dirpath, f)
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                if rel in SKIP_FILES or not f.endswith(exts) or f.startswith("."):
                    continue
                if os.path.getsize(full) > MAX_FILE_BYTES:
                    continue
                picked.append(rel)
    reports = os.path.join(root, "reports")
    if os.path.isdir(reports):
        for f in sorted(os.listdir(reports)):
            full = os.path.join(reports, f)
            if f.endswith(".md") and os.path.isfile(full) and os.path.getmtime(full) >= cutoff and os.path.getsize(full) <= MAX_FILE_BYTES:
                picked.append("reports/" + f)
    return picked


def pack(args):
    root = os.path.abspath(args.data_root)
    rels = collect(root, args.report_days)
    chunks = []
    for rel in rels:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        if any(line.startswith("===== ") for line in content.splitlines()):
            sys.exit(f"{rel} contains a line starting with '===== '; cannot bundle it safely")
        if TAB in content or SP in content:
            sys.exit(f"{rel} contains the sentinel {TAB!r} or {SP!r}; cannot bundle it safely")
        content = content.replace("\t", TAB)
        content = re.sub(r"^ +| {2,}", lambda m: SP * len(m.group()), content, flags=re.M)
        if not content.endswith("\n"):
            content += "\n"
        chunks.append(f"{FILE_OPEN}{rel} =====\n{content}{FILE_CLOSE}\n")
    body = "".join(chunks)
    header = (
        f"{MAGIC}\n# packed_at: {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}\n"
        f"# files: {len(rels)}\n# checksum: {norm_checksum(body)}\n"
    )
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(header + body)
    print(f"packed {len(rels)} files, {len(header) + len(body)} chars -> {args.out}")
    for rel in rels:
        print("  " + rel)


def unescape_drive(text):
    text = re.sub(r"\\([\\#_*\[\]()`~>|$&+\-.!{}<=:\"'%@^])", r"\1", text)
    text = re.sub(r"[ ]+$", "", text, flags=re.M)
    return text


def parse(path, unescape):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if unescape:
        text = unescape_drive(text)
    lines = text.split("\n")
    if not lines or lines[0].strip() != MAGIC:
        sys.exit("not a career-ops state bundle (magic line missing)")
    meta, i = {}, 1
    while i < len(lines) and lines[i].startswith("# "):
        k, _, v = lines[i][2:].partition(":")
        meta[k.strip()] = v.strip()
        i += 1
    body = "\n".join(lines[i:])
    files, cur, buf = {}, None, []
    for line in lines[i:]:
        if cur is None:
            if line.startswith(FILE_OPEN) and line.endswith(" ====="):
                cur, buf = line[len(FILE_OPEN):-6].strip(), []
            continue
        if line.strip() == FILE_CLOSE:
            files[cur] = ("\n".join(buf) + "\n").replace(TAB, "\t").replace(SP, " ")
            cur = None
        else:
            buf.append(line)
    if cur is not None:
        sys.exit(f"bundle truncated inside {cur}")
    return meta, body, files


def check(args):
    meta, body, files = parse(args.inp, args.unescape)
    ok = meta.get("checksum") == norm_checksum(body)
    print(f"files: {len(files)} (header says {meta.get('files')}) | checksum {'OK' if ok else 'MISMATCH'}")
    for rel in files:
        print("  " + rel)
    sys.exit(0 if ok and str(len(files)) == meta.get("files") else 2)


def unpack(args):
    meta, body, files = parse(args.inp, args.unescape)
    ok = meta.get("checksum") == norm_checksum(body)
    root = os.path.abspath(args.data_root)
    for rel, content in files.items():
        if ".." in rel.split("/") or rel.startswith("/"):
            sys.exit(f"refusing path {rel}")
        full = os.path.join(root, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
    print(f"unpacked {len(files)} files into {root} | checksum {'OK' if ok else 'MISMATCH'}")
    sys.exit(0 if ok else 2)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("pack"); a.add_argument("data_root"); a.add_argument("out"); a.add_argument("--report-days", type=int, default=14); a.set_defaults(fn=pack)
    b = sub.add_parser("unpack"); b.add_argument("inp"); b.add_argument("data_root"); b.add_argument("--unescape", action="store_true"); b.set_defaults(fn=unpack)
    c = sub.add_parser("check"); c.add_argument("inp"); c.add_argument("--unescape", action="store_true"); c.set_defaults(fn=check)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
