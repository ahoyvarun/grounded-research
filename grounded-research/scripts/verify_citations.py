#!/usr/bin/env python3
"""
verify_citations.py — existence + metadata verification for citations.

Queries two free, no-key scholarly APIs:
  - Crossref  (https://api.crossref.org)  — DOIs, journals, conferences, books
  - arXiv     (https://export.arxiv.org)  — preprints

It verifies that a cited work EXISTS and that supplied metadata (title, year,
authors) MATCHES the canonical record. It does NOT judge whether the source
supports a claim — that is a reading task the skill performs separately.

Usage:
    python verify_citations.py --input citations.json --output audit.json
    python verify_citations.py --bibliography refs.txt --output audit.json

Input JSON: list of {id, raw, title?, doi?, arxiv?, year?, authors?}
Exit code is always 0; per-citation status lives in the output JSON.

Author: part of the grounded-research skill pack.
"""

import argparse
import datetime
import difflib
import json
import re
import sys
import time
import urllib.parse
import urllib.request

CROSSREF = "https://api.crossref.org/works"
ARXIV = "http://export.arxiv.org/api/query"
UA = "grounded-research-citation-auditor/1.0 (https://github.com/ahoyvarun/grounded-research)"
TIMEOUT = 20


# ----------------------------------------------------------------- helpers ---

def _get(url: str) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read()
    except Exception as e:
        print(f"  ! request failed: {e}", file=sys.stderr)
        return None


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()


def _title_sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio()


# --------------------------------------------------------------- resolvers ---

def resolve_doi(doi: str) -> dict | None:
    doi = doi.strip().replace("https://doi.org/", "")
    data = _get(f"{CROSSREF}/{urllib.parse.quote(doi)}")
    if not data:
        return None
    try:
        msg = json.loads(data)["message"]
    except Exception:
        return None
    return _crossref_record(msg)


def search_crossref_by_title(title: str) -> dict | None:
    q = urllib.parse.urlencode({"query.bibliographic": title, "rows": 3})
    data = _get(f"{CROSSREF}?{q}")
    if not data:
        return None
    try:
        items = json.loads(data)["message"].get("items", [])
    except Exception:
        return None
    best, best_sim = None, 0.0
    for it in items:
        cand = " ".join(it.get("title", []) or [])
        sim = _title_sim(title, cand)
        if sim > best_sim:
            best, best_sim = it, sim
    if best and best_sim >= 0.75:
        rec = _crossref_record(best)
        rec["title_similarity"] = round(best_sim, 3)
        return rec
    return None


def _crossref_record(msg: dict) -> dict:
    year = None
    for k in ("published-print", "published-online", "issued", "created"):
        parts = msg.get(k, {}).get("date-parts", [[None]])
        if parts and parts[0] and parts[0][0]:
            year = parts[0][0]
            break
    authors = [f"{a.get('family','')}" for a in msg.get("author", []) if a.get("family")]
    return {
        "source": "crossref",
        "title": " ".join(msg.get("title", []) or []),
        "year": year,
        "authors": authors,
        "venue": (msg.get("container-title", [None]) or [None])[0],
        "doi": msg.get("DOI"),
        "type": msg.get("type"),
    }


def resolve_arxiv(arxiv_id: str) -> dict | None:
    arxiv_id = arxiv_id.strip().replace("arXiv:", "").replace("arxiv:", "")
    q = urllib.parse.urlencode({"id_list": arxiv_id, "max_results": 1})
    data = _get(f"{ARXIV}?{q}")
    if not data:
        return None
    text = data.decode("utf-8", "replace")
    if "<entry>" not in text:
        return None
    def tag(t):
        m = re.search(rf"<{t}>(.*?)</{t}>", text, re.S)
        return re.sub(r"\s+", " ", m.group(1)).strip() if m else None
    title = tag("title")
    published = tag("published")
    year = int(published[:4]) if published else None
    authors = re.findall(r"<name>(.*?)</name>", text, re.S)
    authors = [a.strip().split()[-1] for a in authors if a.strip()]
    return {"source": "arxiv", "title": title, "year": year,
            "authors": authors, "venue": "arXiv preprint",
            "doi": None, "arxiv": arxiv_id}


def search_arxiv_by_title(title: str) -> dict | None:
    q = urllib.parse.urlencode({"search_query": f'ti:"{title}"', "max_results": 1})
    data = _get(f"{ARXIV}?{q}")
    if not data:
        return None
    text = data.decode("utf-8", "replace")
    if "<entry>" not in text:
        return None
    m = re.search(r"<title>(.*?)</title>", text, re.S)
    cand = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    # first <title> is the feed title; grab the entry title instead
    titles = re.findall(r"<title>(.*?)</title>", text, re.S)
    cand = re.sub(r"\s+", " ", titles[1]).strip() if len(titles) > 1 else cand
    if _title_sim(title, cand) >= 0.75:
        idm = re.search(r"<id>http://arxiv.org/abs/(.*?)</id>", text)
        return resolve_arxiv(idm.group(1)) if idm else None
    return None


# ------------------------------------------------------------------ audit ---

def audit_one(c: dict) -> dict:
    supplied_title = c.get("title") or c.get("raw", "")
    rec = None
    if c.get("doi"):
        rec = resolve_doi(c["doi"])
    if not rec and c.get("arxiv"):
        rec = resolve_arxiv(c["arxiv"])
    if not rec and supplied_title:
        rec = search_crossref_by_title(supplied_title) or search_arxiv_by_title(supplied_title)

    if not rec:
        return {"id": c.get("id"), "status": "NOT_FOUND", "raw": c.get("raw"),
                "resolved": None, "mismatches": [],
                "note": "No match in Crossref or arXiv. May be fabricated, or "
                        "published in a non-indexed venue. Verify manually."}

    mismatches = []
    if c.get("year") and rec.get("year") and int(c["year"]) != int(rec["year"]):
        mismatches.append(f"year: cited {c['year']}, found {rec['year']}")
    if c.get("title") and rec.get("title"):
        sim = _title_sim(c["title"], rec["title"])
        if sim < 0.9:
            mismatches.append(f"title similarity {sim:.2f} (found: \"{rec['title']}\")")
    if c.get("authors") and rec.get("authors"):
        cited = {_norm(a).split()[-1] for a in c["authors"] if a}
        found = {_norm(a) for a in rec["authors"] if a}
        if cited and found and not (cited & found):
            mismatches.append(f"authors: cited {sorted(cited)} vs found {sorted(found)[:3]}")

    status = "VERIFIED" if not mismatches else "METADATA_MISMATCH"
    return {"id": c.get("id"), "status": status, "raw": c.get("raw"),
            "resolved": rec, "mismatches": mismatches,
            "note": "Existence and metadata confirmed. Claim-support must still "
                    "be checked by reading the source." if status == "VERIFIED"
                    else "Work exists but metadata differs from the citation."}


def parse_bibliography(text: str) -> list[dict]:
    out, idx = [], 1
    for line in text.splitlines():
        line = line.strip()
        if len(line) < 10:
            continue
        doi = (re.search(r"10\.\d{4,9}/[^\s]+", line) or [None])
        doi = doi.group(0) if hasattr(doi, "group") else None
        ax = re.search(r"arXiv:\s*(\d{4}\.\d{4,5})", line, re.I)
        yr = re.search(r"(19|20)\d{2}", line)
        out.append({"id": f"B{idx}", "raw": line,
                    "title": line, "doi": doi,
                    "arxiv": ax.group(1) if ax else None,
                    "year": int(yr.group(0)) if yr else None})
        idx += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="citations JSON")
    ap.add_argument("--bibliography", help="plain-text reference list")
    ap.add_argument("--output", default="audit.json")
    args = ap.parse_args()

    if args.input:
        citations = json.load(open(args.input, encoding="utf-8"))
    elif args.bibliography:
        citations = parse_bibliography(open(args.bibliography, encoding="utf-8").read())
    else:
        sys.exit("Provide --input or --bibliography")

    results = []
    for c in citations:
        print(f"Checking {c.get('id')}: {(c.get('title') or c.get('raw',''))[:70]}...")
        results.append(audit_one(c))
        time.sleep(1)  # be polite to the public APIs

    summary = {"checked": len(results),
               "verified": sum(r["status"] == "VERIFIED" for r in results),
               "metadata_mismatch": sum(r["status"] == "METADATA_MISMATCH" for r in results),
               "not_found": sum(r["status"] == "NOT_FOUND" for r in results),
               "generated": datetime.datetime.now().isoformat(timespec="seconds")}
    json.dump({"summary": summary, "results": results},
              open(args.output, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\nSummary: {summary}")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
