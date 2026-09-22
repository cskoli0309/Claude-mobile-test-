# Mode: curate

Curation ranks a candidate set against the brain. Same machinery whether the candidates are mood
references, AI generations, concept routes, or stock options.

The failure mode curation exists to prevent is **regression to the safest option**. A pure fit score
rewards the most generic candidate, because generic things violate nothing. The diversity and tension
passes below are what stop that.

## The pipeline

```
candidates → [1 hard gate] → [2 fit score] → [3 diversity pass] → [4 tension check] → ranked output
```

### 1. Hard gate — binary, no scoring

Drop any candidate that violates a `blocker` rule. Do not score it, do not rank it low, do not
include it "for reference". Report the drops separately with the rule id, so the user sees what was
removed and why.

Typical gate hits: banned colour systems, legal/claim violations, competitor-owned visual devices,
wrong aspect ratio for the stated channel, unusable resolution.

If the gate removes everything, stop and say so. That is a finding about the candidate set, not a
reason to relax the gate.

### 2. Fit score — weighted, per job

Score survivors 0–100 across the lanes that matter for **this** job. Weights are not fixed; set them
from the job and state them in the output.

| Job | V | C | S | G | Note |
|---|---|---|---|---|---|
| Mood / reference curation | 70 | 10 | 0 | 0 | +20 "conceptual fit to brief" |
| Shortlisting AI generations | 45 | 5 | 15 | 35 | G matters — a beautiful broken hand is unusable |
| Concept route selection | 40 | 30 | 0 | 0 | +30 "brief fit" |
| Final asset selection | 35 | 20 | 30 | 15 | S weight rises near delivery |

Within a lane, score against that lane's rules:

- **Mechanical rules** — pass (full marks) or fail (zero for that rule's share).
- **Rubric rules** — score 0–4 against the exemplars:

  | Score | Meaning |
  |---|---|
  | 4 | Indistinguishable from a positive exemplar |
  | 3 | Clearly on-brand, minor deviation |
  | 2 | Neutral — neither expresses nor violates the rule |
  | 1 | Leans toward a negative exemplar |
  | 0 | Matches a negative exemplar |

Weight each rule by its severity: `blocker` 3× (in curation these are already gated, so this applies
to gated-by-context rules only), `major` 2×, `minor` 1×, `note` 0×.

**Always cite the exemplar you scored against.** "3 — close to ex-p-04 but the product is centred"
is reviewable. "3 — good fit" is not, and it is how curation quietly becomes taste.

### 3. Diversity pass — the anti-sameness step

Top-N by score alone returns near-duplicates, because similar candidates score similarly. After
ranking:

1. Take the top scorer.
2. Walk down the list, skipping any candidate that is *materially similar* to one already selected —
   same composition, same colour strategy, same subject treatment.
3. Continue until N is filled.
4. If that empties the list before N, say so: "only 3 materially distinct routes exist in this set."

The output should span the brand's range, not one corner of it. A 5-pick that is five versions of the
same idea is a 1-pick with padding.

### 4. Tension check — the anti-blandness step

For any selection of 3+, flag whether the set is **entirely safe**. If every pick scores 3–4 on every
rule and nothing sits near an edge, the set is probably boring and the brief is probably underserved.

Include one **stretch candidate** where it exists: a route that scores lower on conformity but strong
on brief fit, sitting deliberately at the edge of a rule. Label it as such and name the rule it
strains. That label is what makes it a proposal rather than a mistake — the brand owner can now
choose to bend the rule knowingly.

Do not invent a stretch candidate if the set genuinely has none. Say the set has none.

## Output format

```markdown
## Curation: <job> — <n> candidates, <n> after gate

**Weights:** V 45 · C 5 · S 15 · G 35   **Brain:** acme@2026-09-22 (house)

| # | Candidate | Fit | V | C | S | G | Why |
|---|---|---|---|---|---|---|---|
| 1 | gen-041 | 87 | 38/45 | 4/5 | 15/15 | 30/35 | Closest to ex-p-04; off-centre product, single source light. Minor hand artifact at 200%. |
| 2 | gen-017 | 79 | 35/45 | 5/5 | 15/15 | 24/35 | Different route — interior, warmer. Text in background needs a patch. |
| 3 | gen-008 | 71 | 40/45 | 3/5 | 12/15 | 16/35 | **Stretch.** Strongest composition in the set; strains V-COLOR-004 (near-black). Worth a rule conversation. |

**Gated out (3):** gen-022, gen-031 — V-LOGO-001, wordmark distorted. gen-039 — S-RATIO-002, 1:1 for a 9:16 placement.

**Not covered by this set:** no candidate shows the product in use at all (P-01). The whole set is still-life.
```

That last line is the most valuable one in the output and the one most often omitted. Curation is not
only about ranking what you were given — it is about naming what you were not given.

## Batch curation of generations

When shortlisting 20+ AI generations:

1. Run lane G mechanically first (`06-generative-qc.md`) — defect screening is cheap and removes a
   third of most batches before any judgement is spent.
2. Gate on brand blockers.
3. Score survivors. Full rubric scoring on 60 candidates is not a good use of anyone's attention —
   coarse-pass to a top 10, then score those properly.
4. Check for **batch drift**: if the whole batch shares a defect or an off-brand tendency, that is a
   prompt problem, not a selection problem. Say so and fix the prompt rather than picking the least
   bad output. Feed the finding back into the brand block of the generation prompt.
