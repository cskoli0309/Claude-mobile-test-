# Mode: QC

QC audits one asset (or a batch) against a brain and returns a verdict that survives an argument.

## Before you start

1. **Load the brain.** No brain → no QC. Offer a fast brain instead of improvising.
2. **Identify the asset.** Type, channel, placement, whether it is AI-generated, what stage it is at.
   Stage matters: a concept round gets lanes V+C; a delivery file gets all four with S weighted hard.
3. **Select the rules in play.** Filter by lane and by `channels`. Running 80 rules against a
   favicon wastes everyone's time and produces noise findings that get the whole report ignored.
4. **State what you cannot check.** If you have a JPEG and no source file, you cannot verify font
   family or layer structure. Say so up front, in the report, under "Not checked". A QC report that
   silently omits what it could not see is worse than one that admits the gap.

## The four lanes

Run each independently. **Never average them into a single number** — a 78/100 with a legal blocker
is a FAIL, and averaging is exactly how that ships.

| Lane | Scope | Detail |
|---|---|---|
| **V** Visual system | colour, type, spacing/grid, logo, imagery, composition | below |
| **C** Copy & tone | voice, claims, terminology, CTA, legal | below |
| **S** Channel & spec | ratio, safe zones, file specs, platform policy | `07-channel-specs.md` |
| **G** Generative integrity | artifacts, anatomy, text, brief fidelity, drift | `06-generative-qc.md` |

---

## Lane V — visual system

### V1 Colour
- Every significant fill/text colour maps to a palette entry within tolerance (`color_presence`).
- Accent colours stay within their share limits (`palette_share`) — an accent used at 40% coverage is
  no longer an accent, and this is one of the most common real defects.
- Text contrast meets the brand's floor, or WCAG AA (4.5:1 body, 3:1 large) where the brand has none.
  Accessibility failures are `blocker` by external authority even when the brand never stated them.
- Gradients, overlays and image tints respect the brand's colour strategy.

Run: `python3 scripts/extract_palette.py <asset> --brain brains/<slug>/brain.json`

### V2 Typography
- Families are brand families. Watch for fallback rendering — a JPEG cannot tell you it fell back,
  so flag as unverifiable rather than passing it.
- Sizes sit on the type scale (`type_scale`); no arbitrary intermediate sizes.
- Weights are used as the system defines them (semibold for subheads ≠ bold for subheads).
- Line length, leading, tracking within convention. Optical tracking on display sizes.
- Hierarchy is unambiguous — one clear entry point per composition.

### V3 Spacing & grid
- Spacing values come from the spacing scale; no off-scale nudges.
- Margins and gutters match the grid for the format.
- Optical alignment where mathematical alignment reads wrong (this is a judgement call — rubric).
- Density matches the brand's convention. Brands have a characteristic breathing room; a
  correctly-tokened but too-tight layout is still off-brand.

### V4 Logo
- Correct lockup for the context (primary / stacked / mark-only).
- Clear space respected (`clear_space`) — measure it, don't eyeball it.
- Minimum size respected.
- No distortion, recolouring, rotation, effects, or unapproved backgrounds.
- Placement follows convention.

Logo rules are the most common legitimate `blocker`s in a brand brain, and usually `stated`.

### V5 Imagery & treatment
- Subject treatment matches convention (in use vs. still-life, cropping, angle).
- Lighting and colour grade consistent with the corpus.
- Post-treatment (duotone, grain, vignette) applied as the system specifies.
- Product accuracy: correct model, colourway, current packaging. **Check this explicitly** — an
  obsolete SKU or a discontinued colourway is a real blocker that pure design QC misses every time.

### V6 Composition
Rubric-scored against exemplars. Balance, focal hierarchy, the relationship of copy to image, use of
negative space, crop convention. Always cite the exemplar you scored against.

---

## Lane C — copy & tone

### C1 Voice
Rubric, scored against headline exemplars. Check against `anti_personality` as well as
`personality` — "this reads playful and we are not playful" is a stronger, more actionable finding
than "this doesn't feel quite right".

### C2 Claims & substantiation
- Every performance, comparative or superlative claim is on the approved claims list.
- Required substantiation or asterisk is present and legible.
- No absolute claims ("the best", "only") without backing.

`blocker` when unsubstantiated. This lane is where QC earns its keep commercially — an unsubstantiated
claim is a legal exposure, not a style note.

### C3 Terminology
- Product names exact, including capitalisation and spacing (`terminology`).
- Preferred terms over banned synonyms.
- Feature names as the brand writes them, not as the writer remembers them.

Mechanically checkable and consistently violated — always worth running.

### C4 CTA
- Verb and phrasing from the approved set.
- Placement and prominence per convention.
- Destination matches the promise.

### C5 Legal & disclaimers
- Required disclaimers present, complete, current version.
- Legible at delivered size — a disclaimer set at 6px on a mobile placement is legally present and
  practically absent. Check the rendered size, not the source size.
- Trademark and ® / ™ marks correct on first use.
- Market-specific requirements for every market in `brand.markets`.

`blocker` throughout.

---

## Severity assignment

| Severity | Use when | Effect |
|---|---|---|
| `blocker` | Violates a `stated` rule, a legal/policy requirement, or an accessibility floor | FAIL |
| `major` | Violates a high-confidence `inferred` rule; clearly off-brand to a trained eye | PASS WITH FIXES |
| `minor` | Deviates from convention; defensible but not how the brand usually does it | Advisory |
| `note` | Observation, question, or a suggestion beyond the rules | No action |

**A finding may not exceed the severity ceiling of the rule it cites.** If a rule is `inferred`, its
findings cap at `major`, however strongly you feel. Wanting a stronger finding is a signal to go get
the rule confirmed and re-tagged — not to override the ceiling.

## The verdict gate

```
any blocker   → FAIL
else any major → PASS WITH FIXES
else           → PASS
```

Report per-lane scores alongside the verdict for trending, but the gate alone decides. Lane scores
answer "is this getting better"; the gate answers "can this ship".

## Finding format

Every finding carries:

```json
{
  "id": "f-03",
  "lane": "V",
  "rule_id": "V-LOGO-001",
  "severity": "blocker",
  "observed": "Wordmark is 18px from the right edge; clear space requires 34px (1x cap-height).",
  "location": "top-right, all three sizes",
  "fix": "Increase right margin to 34px minimum, or drop to the mark-only lockup for this width.",
  "confidence": "certain"
}
```

- **`rule_id` is mandatory.** A finding with no rule is an opinion. Opinions are welcome — they go
  in `observations`, and they never affect the verdict. This one discipline is what keeps QC reports
  trusted, because it means nobody can be failed by a rule that was invented while reviewing them.
- **`observed`** states what is, with a measurement wherever one exists. "Too close to the edge" is
  not reviewable; "18px, requires 34px" is.
- **`fix`** is an instruction, not a restatement. Give the number, or give the option.
- **`confidence`** is `certain` | `likely` | `unverifiable`. Use `unverifiable` freely — flagging
  "this looks like a fallback font but I can't confirm from a JPEG" is genuinely useful, and
  pretending certainty you lack is what gets a QC process distrusted.

## Batch QC

For 5+ assets:

1. Mechanical passes across the whole set first (`check_specs.py --summarize`, `extract_palette.py`).
2. **Look for systemic findings** — the same defect across the set is one finding about the source
   (a broken template, a stale master, a bad prompt), not N findings about N assets. Report it once,
   at the top, as systemic.
3. Then per-asset findings for what remains.
4. Verdict per asset, plus a set-level verdict: the set ships only when every asset ships.

The systemic/per-asset split matters more than it looks. Twelve copies of the same finding reads as
a disaster and buries the three real per-asset defects; one systemic finding plus three specifics is
an actionable report.

## Running the gate

```bash
python3 scripts/qc_score.py findings.json --brain brains/acme/brain.json --format markdown
```

Exits 1 on FAIL, 0 otherwise — drops straight into a delivery pipeline.
