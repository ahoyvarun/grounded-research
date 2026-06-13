---
name: grounded-research
description: >-
  Fact-check and verify any research text, report draft, literature review, or
  AI-generated answer by running it through a five-stage grounding pipeline:
  decompose into atomic claims, check each against provided sources, audit every
  citation for existence and accuracy, surface contradictions between sources,
  and produce one auditable verification report with a groundedness score. Use
  this skill whenever the user wants to check accuracy, verify claims, audit
  citations or a bibliography, confirm a text is supported by its sources, detect
  fabricated references, find contradictions across sources, or "check for
  hallucinations" in research writing. Trigger on "fact-check this", "verify
  this", "is this accurate?", "are these citations real?", "do these sources
  agree?", "audit this draft", or any request to confirm that claims trace back
  to real, correctly-cited evidence. Runs the whole pipeline end to end from a
  single instruction.
---

# Grounded Research

A five-stage discipline for verifying research writing. You ask your friend who
tells confident stories whether each part is actually true — and this skill is
the careful checker that goes line by line so confidence never gets mistaken for
correctness.

> **On the word "hallucination."** No process can *guarantee* a text is
> hallucination-free, and claiming so would itself be an unverifiable claim. This
> skill does something honest instead: it breaks a text into checkable pieces,
> tests each against the sources and the citation record, and reports — clearly —
> what was verified, what failed, and what could not be checked. The goal is
> **auditability**, not a reassuring number.

Run all five stages in order. Each stage updates a shared **Claims Ledger**
(`claims_ledger.json`) — a running JSON record that carries results from one
stage to the next. Stages can also be run individually if the user asks for just
a citation check or just a grounding check, but the default for "fact-check
this" is the full pipeline.

```
Stage 1 Decompose  → break text into atomic, checkable claims
Stage 2 Ground     → is each claim supported by the provided sources?
Stage 3 Audit cites→ do cited works exist, match metadata, and support the claim?
Stage 4 Contradict → do sources (or the text) disagree in hidden ways?
Stage 5 Report     → one auditable verdict: groundedness score + what to fix
```

## What you need from the user

- **The text** to check (pasted, or a file).
- **The sources** it should be based on (files in `/mnt/user-data/uploads`,
  pasted text, or — only if the user explicitly authorizes web use — fetched
  pages). For Stage 2 you cannot proceed without sources; if they're missing,
  ask. Never substitute your own parametric knowledge for the provided corpus —
  "I happen to know this is true" is the exact failure this skill exists to catch.
- For Stage 3, web access lets the citation script confirm a reference exists.
  Without it, mark existence UNVERIFIED rather than guessing.

The Claims Ledger schema is defined in `references/ledger_schema.md`. Read it
before Stage 1 so the JSON you produce is consistent across stages.

---

## Stage 1 — Decompose into atomic claims

Hallucinations hide in compound sentences. "Smith et al. (2021) showed in a study
of 4,000 patients that the treatment cut mortality 30%" looks like one statement
but contains five independently checkable assertions. A fabrication in any one of
them survives review if the sentence is checked as a unit. This mirrors FActScore
(Min et al., EMNLP 2023), which defines an atomic fact as a short sentence
conveying one piece of information and checks each one independently.

1. **Read the whole text first** for context (so pronouns resolve correctly).
2. **Split every sentence** into atomic claims. Each claim must assert exactly
   one thing, be self-contained (replace "it"/"they" with the actual referent),
   and preserve the original meaning — never strengthen or weaken a hedge
   ("may reduce" stays "may reduce").
3. **Classify each** by `type`: `factual`, `numeric` (always isolate numbers,
   dates, percentages — highest hallucination risk), `causal`, `attributed`
   (credits a source → routed to Stage 3), `definitional`, or `normative`
   (opinion → exempt from grounding, labeled OPINION at the end).
4. **Record citation strings verbatim** in `cites` — including any errors; Stage
   3 needs the original to detect mismatches.
5. **Do not verify yet.** Judging while extracting causes silent "fixing" instead
   of flagging. Every claim leaves Stage 1 as UNCHECKED.

Create `claims_ledger.json` and show a markdown table: `| ID | Claim | Type | Cites |`.

---

## Stage 2 — Check grounding against the sources

Operationalizes the AIS framework (Rashkin et al., Computational Linguistics
2023): output about the external world must be verifiable against an identified
source, via the test *"According to [source], [claim]"* — is that faithful? The
hallucination survey (Ji et al., ACM Computing Surveys 2023) distinguishes
**intrinsic** hallucination (contradicts the source) from **extrinsic**
(the source can't verify it) — they get different labels because they need
different fixes.

Read every source in full, then label each claim's `grounding.status`:

- **SUPPORTED** — a specific passage entails it. Record the verbatim span
  (≤25 words) and its location. Quoting forces real grounding; paraphrase can
  drift toward the claim and manufacture false support.
- **PARTIALLY_SUPPORTED** — part holds, part doesn't. A numeric claim whose exact
  number isn't in the source goes here, with the discrepancy named.
- **UNSUPPORTED** — sources neither confirm nor contradict (extrinsic). May still
  be true in the world; it just isn't grounded here. Say so; do not rescue it
  with outside knowledge.
- **CONTRADICTED** — a passage asserts the opposite (intrinsic). Most serious;
  record the contradicting span.
- **NOT_APPLICABLE** — opinion/definitional claims the corpus isn't expected to
  adjudicate.

Be adversarial about numbers, names, and dates. "30%" is not SUPPORTED by "about
a third." A 2021 claim is not supported by a 2019 source.

---

## Stage 3 — Audit the citations

Fabricated citations are the signature research hallucination: fluent,
authoritative, pointing at a paper that was never written — or a real paper that
says something else. Check three things per citation, in order of severity:
**existence** → **metadata** (authors, year, title, venue, DOI) → **claim
support** (does the work actually say what it's cited for?).

Use the bundled script for existence + metadata when web access is authorized:

```bash
python scripts/verify_citations.py --input citations.json --output audit.json
# or parse a bibliography directly:
python scripts/verify_citations.py --bibliography refs.txt --output audit.json
```

It queries Crossref and arXiv (both free, no key) and returns, per citation,
whether it resolved and a field-by-field metadata match. Read the script's header
for the exact I/O schema. **It checks existence and metadata only** — claim
support (check 3) is a reading task: open the real source and compare it to the
claim, as in Stage 2.

Without web access, DO NOT guess whether a citation is real. Audit what's
checkable offline (internal consistency, DOI/arXiv-ID syntax, match against any
provided PDFs) and mark existence `UNVERIFIED — no web access`.

Label each in `citation.status`: VERIFIED · METADATA_MISMATCH · MISATTRIBUTED
(real paper, wrong claim) · NOT_FOUND (likely fabricated) · UNVERIFIED. Never
upgrade to VERIFIED from familiarity — recognizing a title is not resolving it.
Never invent a DOI or URL to "complete" a citation.

---

## Stage 4 — Surface contradictions

The subtle failure isn't the invented fact (earlier stages catch those) — it's
**false consensus**: a smooth synthesis that reconciles sources which actually
disagree, silently picking a side or averaging incompatible numbers. The
consistency principle behind SelfCheckGPT (Manakul et al., EMNLP 2023) applies:
divergence is a signal to surface, not smooth.

Find three kinds: **text-vs-source** (collect the CONTRADICTED claims from Stage
2), **source-vs-source** (two relied-on sources disagree — highest value), and
**internal** (the text contradicts itself; two ledger claims are incompatible).

Rules: flag every disagreement, never adjudicate it away. Report numeric
conflicts side by side with sources ("A: 30%, B: 18%") — never a blended "around
20–30%". Distinguish real contradiction from apparent (different scope, period,
or population can make two true statements look incompatible — note the
reconciling dimension if one genuinely exists; otherwise mark UNRESOLVED). Record
in `cross_source`.

---

## Stage 5 — Write the verification report

Produce a verdict the reader can act on, plus an honest account of the check's
own limits. Embodies the FActScore principle: precision as the proportion of
atomic units supported — made transparent per claim, not collapsed into one
opaque figure.

Combine the three checks into each claim's `final_label`:
**VERIFIED** (supported, no citation failure, no conflict) · **PARTIALLY
VERIFIED** (partial support or minor citation mismatch) · **UNVERIFIED** (not
grounded) · **DISPUTED** (in an unresolved contradiction) · **FAILED**
(contradicted, or citation not found/misattributed) · **OPINION** (normative;
reported separately, not scored).

Compute **Groundedness = VERIFIED ÷ (all claims except OPINION)** and ALWAYS show
the full breakdown table and coverage caveats beside it — never the score alone.
Save `verification_report.md` using this structure:

```markdown
# Verification Report — <document>
## Bottom line
<2–3 sentences; lead with the most serious finding>
## Groundedness score
**X/N verified (P%)** — <what this covers and doesn't>
| Verdict | Count |  (Verified / Partial / Unverified / Disputed / Failed / Opinion)
## 🔴 Must fix (failures)
## 🔵 Resolve before publishing (disputes)
## ⚪ Needs a citation (unverified)
## 🟡 Tighten (partial)
## ✅ Verified
## Method & limits  (stages run · web access y/n · sources · what was NOT checked)
```

**Honesty rules — the whole point:** never inflate the score by excluding
inconvenient claims (only OPINION is excluded, and its count is shown); never
report VERIFIED for a check that didn't run; the bottom line is governed by the
**worst** finding, not the average (one fabricated citation outweighs fifty
verified claims for trust); never claim the text is "hallucination-free" — claim
only "no unsupported or contradicted claims were found among the N examined,
using the sources provided."

---

## Worked example

`examples/flawed_paragraph.md` is a paragraph with four planted flaws (a
fabricated citation, a contradicted statistic, a wrong year, an overstatement)
plus sound claims. `examples/demo/verification_report.md` is the report this
pipeline produces for it — it catches all four and passes the sound claims
(groundedness 3/9, correct for a paragraph built to fail). Use it as a sanity
check that the skill is working.

## References (all verified to exist with correct venue/year)

- Min et al. 2023. *FActScore.* EMNLP 2023, 12076–12100. arXiv:2305.14251.
- Rashkin et al. 2023. *Measuring Attribution in NLG Models.* Computational
  Linguistics 49(4), 777–840. DOI: 10.1162/coli_a_00486.
- Manakul et al. 2023. *SelfCheckGPT.* EMNLP 2023, 9004–9017. arXiv:2303.08896.
- Ji et al. 2023. *Survey of Hallucination in NLG.* ACM Computing Surveys 55(12),
  Article 248. DOI: 10.1145/3571730.
- Es et al. 2024. *RAGAs.* EACL 2024 (System Demonstrations), 150–158.
  arXiv:2309.15217.
