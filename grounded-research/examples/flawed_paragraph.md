# Example input: a research paragraph with planted flaws

This is a deliberately flawed paragraph used to demonstrate the grounded-research
pipeline. It contains (a) a fabricated citation, (b) a numeric drift from the
real source, (c) an overstated claim, and (d) several sound claims.

---

> Retrieval-Augmented Generation (RAG) has become the dominant approach to
> reducing hallucination in large language models. RAGAS, introduced by Es et
> al. in 2022, provides reference-free evaluation of RAG pipelines and has become
> the de facto industry standard for the task. Its faithfulness metric
> decomposes an answer into statements and checks each against the retrieved
> context. More recently, Schmidt and Vogel (2024) demonstrated that quantum
> grounding networks eliminate hallucination entirely, achieving a 100%
> faithfulness score on the WikiEval benchmark. Independent evaluation by Min et
> al. (2023) using the FActScore framework found that ChatGPT achieved only a 12%
> factual precision score on biography generation, underscoring how far
> general-purpose models remain from reliability.

---

## Planted flaws (what the pipeline should catch)

1. **Citation year mismatch** — RAGAS (Es et al.) is cited as **2022**; the work
   is **2023** (arXiv:2309.15217, Sep 2023; EACL 2024 demo track).
   → citation-auditor: METADATA_MISMATCH.

2. **Fabricated citation** — "Schmidt and Vogel (2024), quantum grounding
   networks, 100% faithfulness" does not exist.
   → citation-auditor: NOT_FOUND; confidence-reporter: FAILED.

3. **Implausible/unsupported claim** — "eliminate hallucination entirely / 100%"
   contradicts the entire literature and has no real source.
   → grounding: UNSUPPORTED; contradiction-surfacer flags it.

4. **Numeric drift** — FActScore reports ChatGPT at **58%** factual precision on
   biographies, not **12%**.
   → grounding: CONTRADICTED (intrinsic) against the real FActScore paper.

5. **Overstatement** — "de facto industry standard" is stronger than any source
   supports.
   → grounding: UNSUPPORTED / PARTIALLY; contradiction-surfacer: overstatement.

6. **Sound claims** — RAG reduces hallucination risk; RAGAS is reference-free;
   the faithfulness metric decomposes answers into statements checked against
   context. → VERIFIED against the RAGAS and survey sources.

## Expected bottom line from confidence-reporter

> This paragraph is **not yet trustworthy**. It contains a fabricated citation
> (Schmidt & Vogel 2024) and a contradicted statistic (FActScore for ChatGPT is
> 58%, not 12%), plus an unsupported "eliminates hallucination entirely" claim
> and a citation year error for RAGAS (2023, not 2022). The core description of
> RAG and RAGAS is sound. Fix the fabricated citation and the two false claims
> before any use.

This file doubles as a regression check: running the pipeline over this
paragraph should reproduce findings 1–6.
