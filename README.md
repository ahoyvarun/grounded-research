# grounded-research

A single [Claude Skill](https://www.anthropic.com/news/skills) that imposes a
five-stage verification discipline on research writing — catching unsupported
claims, fabricated or mismatched citations, and hidden contradictions before
they reach a reader. **One install, runs the whole pipeline.**

> **On the word "hallucination."** No tool can *guarantee* a text is
> hallucination-free, and any tool that claims to is itself making an unverifiable
> claim. This skill does something honest instead: it breaks a text into atomic
> claims, checks each against the sources and the citation record, then reports —
> transparently — what was verified, what failed, and what couldn't be checked.
> The goal is **auditability**, not a reassuring score.

## What it does

You give it a draft and the sources it's based on, and say "fact-check this."
It runs five stages in sequence, each feeding the next through a shared
Claims Ledger:

```
1. Decompose  → break the text into atomic, individually checkable claims
2. Ground     → is each claim actually supported by the provided sources?
3. Audit cites→ do the cited works exist, match their metadata, and say what they're cited for?
4. Contradict → do the sources (or the text) disagree in ways the narrative hides?
5. Report     → one auditable verdict: a groundedness score and a list of what to fix
```

It's **one skill**, not five — you install a single package and Claude performs
all five roles itself. (You can still ask it to run just one stage, e.g. "audit
these citations.")

## Install

**Claude.ai / Claude Desktop:** download `grounded-research.skill` from this
repo, then go to Settings → Customize → Skills → **+** → Upload, and select the
file. Done — now ask Claude to "fact-check this draft against these sources."

**Claude Code / manual:** copy the `grounded-research/` folder into your skills
directory.

Requires a plan with Skills / code execution enabled. The citation script needs
network access to reach Crossref and arXiv (see note below).

## What's in this repo

```
grounded-research/            ← the skill (this whole folder is what installs)
├── SKILL.md                  ← the five-stage pipeline, all in one file
├── references/
│   └── ledger_schema.md      ← the shared Claims Ledger JSON contract
├── scripts/
│   └── verify_citations.py   ← Crossref + arXiv citation resolver (unit-tested)
└── examples/
    ├── flawed_paragraph.md   ← a paragraph with planted errors
    └── demo/                 ← the verification report the pipeline produces for it
grounded-research.skill       ← the packaged one-click installer
README.md · LICENSE · .gitignore
```

## Proof it works

`grounded-research/examples/` contains a paragraph with four planted flaws — a
fabricated citation, a contradicted statistic, a wrong publication year, and an
overstatement — plus several sound claims. The pipeline catches all four and
passes the sound ones (groundedness 3/9, exactly right for a paragraph built to
fail). The report in `examples/demo/verification_report.md` is the actual output.

## A note on the citation script

`scripts/verify_citations.py` queries two free, no-key scholarly APIs — Crossref
(`api.crossref.org`) and arXiv (`export.arxiv.org`) — to confirm a cited work
exists and that its title/year/authors match. The matching logic is verified
against real Crossref records. With network access it resolves live citations;
in a sandbox without scholarly-API access it reports `NOT_FOUND` for everything
and labels existence `UNVERIFIED` — by design, it never *guesses* a citation is
real.

## Academic grounding

Operationalizes peer-reviewed work on factuality and attribution:

- Min, S., et al. (2023). *FActScore: Fine-grained Atomic Evaluation of Factual
  Precision in Long Form Text Generation.* EMNLP 2023, 12076–12100. arXiv:2305.14251.
- Rashkin, H., et al. (2023). *Measuring Attribution in Natural Language
  Generation Models.* Computational Linguistics 49(4), 777–840. DOI: 10.1162/coli_a_00486.
- Manakul, P., et al. (2023). *SelfCheckGPT: Zero-Resource Black-Box Hallucination
  Detection for Generative Large Language Models.* EMNLP 2023, 9004–9017. arXiv:2303.08896.
- Ji, Z., et al. (2023). *Survey of Hallucination in Natural Language Generation.*
  ACM Computing Surveys 55(12), Article 248. DOI: 10.1145/3571730.
- Es, S., et al. (2024). *RAGAs: Automated Evaluation of Retrieval Augmented
  Generation.* EACL 2024 (System Demonstrations), 150–158. arXiv:2309.15217.

## License

MIT (see `LICENSE`). Cite the papers above, not this repo, for the underlying methods.

## Author

Built by **Varun Chaturvedi** as a research tooling project — feedback and issues
welcome. Connect: [LinkedIn](https://linkedin.com/in/varunchaturvedii) ·
[GitHub](https://github.com/ahoyvarun)
