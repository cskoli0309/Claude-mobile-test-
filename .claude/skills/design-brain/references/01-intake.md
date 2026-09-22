# Intake: gathering evidence for any brand

The goal of intake is not "collect everything". It is **collect enough evidence that the rules you
induce can carry the severity you need them to carry.** Work backwards from that.

## Step 1 — scope the brain

Ask, before gathering anything:

- **What is this brain for?** A single campaign, one channel, a product line, or the whole brand?
- **What will it gate?** Advisory notes, or a hard ship/no-ship decision? Gating demands `stated`
  rules, which demands an authoritative source or a brand-owner confirmation pass.
- **Who arbitrates?** Name the person who can promote an `inferred` rule to `stated`. Put them in
  `brand.owner`. A brain with no arbiter can never gain blockers.

Record the answers in `brand` and in `scope`. A campaign-scoped brain that `extends` a house brain is
almost always better than a second full brain.

## Step 2 — work the source ladder

Sources are not equal. Higher rungs yield higher confidence, so climb as far as the brand allows and
stop when the scope is covered.

| Rung | Source | Yields | Notes |
|---|---|---|---|
| 1 | Design tokens / Figma variables / theme config | `stated`, mechanical | The gold standard. Exact values, no inference. |
| 2 | Official brand guideline (PDF, Figma, Notion) | `stated` | Cite page/frame. Watch for staleness — check the date against live work. |
| 3 | Brand-owner interview / written answers | `stated` | The only way to get `stated` rules for a brand with no docs. Cheap, high yield. |
| 4 | Component library / design system file | `stated` for structure, `inferred` for usage | Components tell you what exists, not what is chosen. |
| 5 | Approved asset corpus (shipped, signed-off work) | `inferred` | The workhorse. Needs volume — see minimums below. |
| 6 | Live site / app in production | `inferred` | Extractable mechanically. Beware legacy pages predating the current system. |
| 7 | Rejected / killed work | `inferred`, negative | Underrated. Counter-exemplars sharpen rules more than positives do. |
| 8 | Competitor set | context only | Never a rule source. Feeds `identity.competitors_avoided`. |

**Rungs 3 and 7 are the ones teams skip and shouldn't.** A 30-minute interview converts a pile of
`inferred` rules into `stated` ones, which is the difference between a brain that advises and a brain
that gates. And a folder of killed work tells you where the real edges are.

## Step 3 — hit the minimum viable corpus

Per lane, the smallest evidence base that supports `inferred` rules (≥80% consistency, n≥8):

| Lane | Minimum | Comfortable | What to sample for |
|---|---|---|---|
| V Visual | 12 assets | 30–40 | Spread across format, channel, and at least 2 campaigns |
| C Copy | 15 pieces | 40+ | Headlines, body, CTAs, and error/edge copy |
| S Channel | 3 per channel | 8 per channel | The actual delivered files, not mockups |
| G Generative | 20 generations | 60+, with verdicts | Must include rejects, or you learn nothing |

**Sampling rule:** spread across time and campaign, never one campaign deep. Fifteen assets from a
single campaign teach you that campaign's rules, not the brand's. If you only have one campaign, say
so — cap every rule at `assumed` and note it in `open_questions`.

**When the corpus is too small:** do not pad it with guesses. Build the brain from what exists, tag
honestly, and list what a follow-up pass needs. A thin brain that says it is thin is usable. A thin
brain wearing a confident face causes bad ship decisions.

## Step 4 — handle the missing-source cases

| Situation | Move |
|---|---|
| No guideline at all | Rungs 3, 5, 6, 7. Interview is now mandatory, not optional. |
| Guideline exists but live work contradicts it | Both go in. Record the conflict in `open_questions` and ask the arbiter which wins. Never silently pick. |
| Brand new brand, no shipped work | Brain is `assumed` throughout. Build from the concept deck + a named reference set. Advisory only — state this loudly. |
| Only the logo and a colour or two | Legitimate fast brain. 4–6 mechanical rules, everything else `open_questions`. |
| Multiple sub-brands | One house brain + one thin `extends` brain per sub-brand. Do not merge them. |
| Brand mid-rebrand | Scope to one system and date it. Put the other in `provenance` as `superseded`. |

## Step 5 — log provenance as you go

Every source gets an entry in `provenance.sources` **at the moment you use it**, not afterwards from
memory:

```json
{
  "id": "s3",
  "type": "asset_corpus",
  "uri": "drive://Acme/Approved 2025 Q3",
  "rung": 5,
  "date": "2026-09-14",
  "weight": 1.0,
  "n": 34,
  "notes": "Q3 retail campaign + always-on social. No OOH."
}
```

Rules reference these ids in `support.source_ids`. Without that chain, nobody can audit why a rule
exists, and the brain rots the first time someone disagrees with it.

Store the actual artefacts under `brains/<slug>/evidence/` where licensing permits, or record
resolvable URIs where it does not. A rule whose evidence has vanished is an `assumed` rule, whatever
it was tagged when written — downgrade it on the next review.

## Step 6 — set a review date

Brains rot. Put `brand.review_by` about 6 months out, or at the next campaign boundary, whichever is
sooner. On review: re-check `inferred` rules against new work, downgrade rules whose evidence is
gone, and clear `open_questions`.
