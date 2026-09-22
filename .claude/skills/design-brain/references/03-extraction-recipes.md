# Extraction recipes

One recipe per source type. Each states what it yields, the confidence ceiling it supports, and the
failure mode to watch for.

---

## Figma (via Figma MCP) — highest yield available

**Yields:** exact tokens, type scale, spacing system, component inventory. `stated`, mechanical.

1. `get_variable_defs` on the design-system file → colour, type, spacing, radius tokens. This is the
   single best source in the ladder: exact values with names, no inference. Map straight to
   `color_presence`, `type_scale`, `font_family` rules at `stated`.
2. `get_metadata` on key frames → layout structure, frame sizes, naming conventions.
3. `get_design_context` on representative components → how tokens are actually composed.
4. `get_screenshot` on canonical frames → exemplar images. Save into `evidence/`.
5. `search_design_system` / `get_libraries` → the published component surface; tells you what the
   system offers versus what teams actually reach for.

**Failure mode:** the file is a graveyard of detached layers and abandoned explorations. Confirm
which file/page is canonical *before* extracting, or you will codify someone's scratch pad. Ask for
the published library, not the working file.

**Confidence call:** published library variables → `stated`. Values found only on loose layers →
`inferred` at best.

---

## Brand guideline PDF

**Yields:** stated rules across every lane. `stated`, but verify freshness.

1. Extract text and page images (the `pdf` skill handles this).
2. Pull the hard values first — hex codes, type scale, clear-space diagrams, minimum sizes, ratios.
   These become mechanical rules directly.
3. Capture the do/don't spreads as exemplars. Guideline don'ts are pre-labelled negative exemplars —
   the cheapest counter-exemplars you will ever get.
4. Record page numbers in `source_ids` notes so findings can cite chapter and verse.
5. **Then check it against live work.** Sample 10 recent assets against the guideline's hard rules.
   Where they disagree, file an `open_question` — do not assume the document wins. Guidelines
   describe intent; shipped work describes practice, and the arbiter decides which is the rule.

**Failure mode:** a stale 2019 guideline codified at `stated` severity, blocking work that reflects
how the brand actually looks now. Always compare dates.

---

## Approved asset corpus (the workhorse)

**Yields:** everything, at `inferred`. This is how you build a brain for a brand with no docs.

1. Assemble per the minimums in `01-intake.md`. Spread across campaign and time.
2. Run `extract_palette.py` over the image set:
   ```bash
   python3 scripts/extract_palette.py evidence/approved/*.png --json > evidence/palettes.json
   ```
   Aggregate the results — colours appearing in ≥80% of assets are core palette candidates; colours
   appearing once are noise, not accents.
3. Run `check_specs.py --summarize` over the set to learn the real delivered formats.
4. Pass over the set visually for the things no script sees: composition, crop convention, product
   placement, lighting, subject treatment, how copy sits in the frame.
5. **Count everything.** Every rule needs its `count/of`. "Most of them" is not a support value.
   If you cannot count it, you cannot claim `inferred`.
6. Look for the *absences* too. If 34 assets contain no centred compositions, "product is never
   centred" is a real inferred rule — and absences are frequently stronger signals than presences.

**Failure mode:** inducing a campaign's rules as the brand's. Check your sample spread before you
write a single rule.

---

## Rejected / killed work

**Yields:** negative exemplars and rule boundaries. `inferred`, disproportionately valuable.

Ask for the killed rounds and, where you can get it, the reason each died. Each becomes a negative
exemplar with `why` set to the actual review note. A rule with a real killed asset attached to it
survives arguments that a rule with only positives does not.

**The near-misses matter most.** An asset killed for being 10% too far in one direction defines the
boundary; an obviously off-brand one defines nothing.

---

## Live site / app

**Yields:** computed colour, type, spacing, contrast. `inferred`, mechanical.

1. Pull the stylesheet or computed styles. A CSS custom-property block is effectively a token export
   — treat it near Figma-grade, though usage drift means it stays `inferred` unless confirmed.
2. Screenshot key templates at mobile and desktop widths → `extract_palette.py` + contrast checks.
3. Note what recurs across templates versus what is page-specific.

**Failure mode:** legacy pages predating the current system. Sample recently-shipped templates and
ask which pages are current.

---

## Higgsfield generation history

**Yields:** a labelled corpus for lane G, plus real brand signal. `inferred`.

1. `show_generations` / `show_marketing_studio_generations` for the history.
2. Split by outcome — what got used versus what got discarded. The used set is an approved corpus;
   the discarded set is negative exemplars, already labelled by the act of discarding.
3. Mine the prompts of the winners for the brand language that actually works. These become the
   brand block that `higgsfield-prompt-architect` uses, and they belong in the brain as principles.
4. Record recurring defect patterns per model → lane G rules (see `06-generative-qc.md`).

If the `higgsfield-corpus-intel` skill is available, run it first and build on its output rather than
re-deriving the analysis.

---

## Meta Ad Library (competitors + own history)

**Yields:** competitive context; own delivered-ad corpus. Context only, never a rule source.

1. `ads_library_search` on the brand → what actually ran, with dates.
2. Same on 3–5 competitors → fills `identity.competitors_avoided`. Write the `why` as a *visual*
   observation ("their gradient language"), not a business one ("they're cheaper") — the brain uses
   it for design judgement.
3. `ads_get_ad_preview` renders a live ad for lane S spec checks.

**Failure mode:** treating a competitor convention as a category requirement. The brain's job is
often the opposite — to keep the brand *out* of the category default.

---

## Brand-owner interview (30 minutes, highest ROI per minute)

**Yields:** `stated` rules for a brand with no documentation. Nothing else does this.

Ask these, in this order:

1. "Show me three assets you're proud of, and three that made it out but shouldn't have." — instant
   positive and negative exemplars, pre-labelled by the only opinion that counts.
2. "What gets kicked back in review most often?" — these are your blockers, straight from practice.
3. "What would make you say *that isn't us*?" — fills `anti_personality`, which catches more bad work
   than the positive personality list.
4. "Which competitor do we never want to look like, and what specifically about them?" — fills
   `competitors_avoided` with a usable visual observation.
5. "What's non-negotiable — legal, accessibility, trademark?" — these are legitimately `blocker` and
   externally sourced.
6. "What in the guideline do you ignore in practice?" — resolves guideline-versus-live conflicts
   before they become QC false positives.

Record verbatim answers in `evidence/interview-<date>.md` and cite it as a rung-3 source. Rules
sourced here are `stated` — the arbiter said so, on the record.

---

## Cross-source conflict resolution

When two sources disagree, do **not** average them or silently pick.

1. Prefer the higher ladder rung, but only when it is also current. A rung-1 token export from 2023
   loses to a rung-5 corpus from this quarter.
2. If rungs are close or dates conflict, file an `open_question` naming both sources and the
   discrepancy, tag the rule `assumed`, and route it to the arbiter.
3. Once the arbiter rules, promote to `stated`, cite the ruling, and close the question.

Conflicts are not noise to be smoothed away — they are usually the most informative thing intake
turns up, because they mark where the brand's intent and its practice have drifted apart.
