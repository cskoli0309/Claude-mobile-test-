# The brain schema

`brain.json` is the whole model. One file per brand-scope, validated by
`assets/brain.schema.json`, checked by `scripts/validate_brain.py`.

Design intent: **every rule must be traceable to evidence and actionable by a checker.** If a rule
cannot name its evidence, it cannot carry severity. If it cannot describe its check, it belongs in
`principles`, not `rules`.

## Top-level shape

```json
{
  "brain_version": "1.0",
  "extends": null,
  "brand": { },
  "scope": { },
  "provenance": { "sources": [] },
  "identity": { },
  "principles": [],
  "rules": [],
  "exemplars": { "positive": [], "negative": [] },
  "channels": [],
  "open_questions": []
}
```

### `brand`

```json
{
  "name": "Acme",
  "slug": "acme",
  "aliases": ["ACME Corp"],
  "category": "consumer electronics",
  "markets": ["US", "DE"],
  "owner": "priya@acme.com",
  "updated": "2026-09-22",
  "review_by": "2027-03-22"
}
```

`owner` is the arbiter who can promote rules to `stated`. Required for any brain with blockers.

### `scope`

```json
{ "kind": "house", "applies_to": ["all"], "excludes": ["legacy-2019-system"] }
```

`kind` is `house` | `sub_brand` | `campaign` | `channel`. Campaign and channel brains should set
`extends` to the house brain's path and carry only their deltas.

### `identity`

The judgement context. Not directly checkable, but it is what rubric rules are argued from.

```json
{
  "positioning": "Precision tools for people who take the work seriously.",
  "personality": ["understated", "exact", "warm at the edges"],
  "anti_personality": ["playful", "disruptive", "loud"],
  "audience": "Professional makers, 28-45, buy once and keep it.",
  "competitors_avoided": [
    { "name": "Rival Co", "why": "their high-saturation gradient language reads as consumer-cheap" }
  ]
}
```

`anti_personality` earns its keep — "not playful" catches more bad work than "understated" does.

### `principles`

Directional, un-checkable statements. They inform rubric scoring and brief-writing; they never
produce findings on their own.

```json
[{ "id": "P-01", "statement": "Product is always shown in use, never floating.", "source_ids": ["s2"] }]
```

If you find yourself wanting a principle to fail an asset, it is a rule — write a check for it.

### `rules` — the core

```json
{
  "id": "V-COLOR-004",
  "lane": "V",
  "dimension": "color",
  "statement": "Body copy on light surfaces is Ink #101418. Pure black #000000 is never used.",
  "check": {
    "mode": "mechanical",
    "kind": "color_presence",
    "params": { "forbidden": ["#000000"], "tolerance_deltaE": 3 }
  },
  "severity": "major",
  "confidence": "inferred",
  "support": { "count": 31, "of": 34, "source_ids": ["s3", "s6"] },
  "exceptions": ["Print CMYK builds where registration black is a production requirement"],
  "fix_hint": "Replace #000000 fills with Ink #101418.",
  "added": "2026-09-22"
}
```

Field notes:

- **`id`** — `<LANE>-<DIMENSION>-<NNN>`. Stable forever; findings cite it, so never renumber.
- **`lane`** — `V` visual, `C` copy, `S` channel/spec, `G` generative. Drives which QC pass sees it.
- **`statement`** — one sentence, testable, in the positive where possible. State the rule, then the
  prohibition. Bad: "Don't use weird colours." Good: the example above.
- **`check.mode`** — `mechanical` (a script or a deterministic look can decide) or `rubric` (needs
  judgement against exemplars). Roughly 40% mechanical is a healthy brain; 100% rubric means you have
  written documentation, not QC.
- **`check.kind`** — for mechanical rules, the checker to use. See the catalogue below.
- **`severity`** — `blocker` | `major` | `minor` | `note`. **Capped by `confidence`** (see below).
- **`confidence`** — `stated` | `inferred` | `assumed`.
- **`support`** — `count` of corpus items exhibiting it, `of` the number examined, plus `source_ids`.
  Required for `inferred`. `stated` rules use `source_ids` alone and may omit counts.
- **`exceptions`** — known-legitimate violations. A rule with no exceptions after six months of use
  is either perfect or unexamined; check which.
- **`fix_hint`** — what to actually do. Findings inherit it. Write it as an instruction, not a
  restatement of the problem.

### The severity ceiling

Enforced by `validate_brain.py`; do not bypass it.

| confidence | max severity | requirement |
|---|---|---|
| `stated` | `blocker` | ≥1 `source_ids` at ladder rung 1–4, or arbiter confirmation |
| `inferred` | `major` | `count/of ≥ 0.8` and `count ≥ 8` |
| `assumed` | `minor` | must have a matching entry in `open_questions` |

Legal, accessibility and platform-policy rules are the standard exception path to `blocker` — they
are `stated` by an external authority. Cite the authority as the source (`type: "regulation"` or
`"platform_policy"`), not the brand.

### Mechanical check kinds

What `scripts/` and a careful visual pass can decide deterministically:

| `kind` | Params | Checked by |
|---|---|---|
| `color_presence` | `allowed[]` / `forbidden[]`, `tolerance_deltaE` | `extract_palette.py` |
| `color_contrast` | `min_ratio`, `context` (`text`/`large_text`/`ui`) | `extract_palette.py` |
| `palette_share` | `color`, `max_pct` / `min_pct` | `extract_palette.py` |
| `aspect_ratio` | `allowed[]`, `tolerance` | `check_specs.py` |
| `dimensions` | `min_w`, `min_h`, `max_w`, `max_h` | `check_specs.py` |
| `file_size` | `max_bytes` | `check_specs.py` |
| `duration` | `min_s`, `max_s` | `check_specs.py` (needs ffprobe) |
| `safe_zone` | `top_pct`, `bottom_pct`, `left_pct`, `right_pct` | visual pass against overlay |
| `type_scale` | `allowed_px[]`, `min_px` | Figma/CSS extraction, or visual |
| `font_family` | `allowed[]` | Figma/CSS extraction, or visual |
| `clear_space` | `multiple_of`, `reference` | visual pass |
| `text_presence` | `required[]` / `forbidden[]`, `match` (`exact`/`regex`/`semantic`) | text extraction |
| `terminology` | `preferred{}`, `banned[]` | text extraction |

Anything not on this list is `rubric`. Extend the list rather than stretching a kind to fit.

### `exemplars`

The training set for rubric rules. Without these, rubric scoring is vibes with extra steps.

```json
{
  "positive": [
    { "id": "ex-p-04", "uri": "evidence/approved/aw24-hero-03.jpg",
      "why": "Canonical: product in use, off-centre, single light source, copy in the negative space.",
      "illustrates": ["V-COMP-002", "P-01"] }
  ],
  "negative": [
    { "id": "ex-n-02", "uri": "evidence/killed/aw24-hero-alt-07.jpg",
      "why": "Killed in review: floating product on a gradient — reads as Rival Co.",
      "violates": ["P-01", "V-COLOR-009"] }
  ]
}
```

Target 3–5 positives and 2–3 negatives per rubric rule. **Negatives near the boundary are worth more
than obvious ones** — a killed asset that was almost right teaches the edge; a random off-brand image
teaches nothing.

### `channels`

Per-channel delivery specs. Feeds lane S and `check_specs.py`. See `07-channel-specs.md` for the
starter table and how to override it.

### `open_questions`

```json
[{ "id": "q-03", "question": "Does the #000000 ban apply to print CMYK builds?",
   "blocks": ["V-COLOR-004"], "asked_of": "priya@acme.com", "status": "open" }]
```

Every `assumed` rule needs one. Every guideline-vs-live conflict needs one. Clearing these is the
cheapest way to upgrade a brain.

## Writing good rules — worked contrast

| Weak | Why it fails | Strong |
|---|---|---|
| "Use brand colours." | No check, no values, no severity possible | "Fills outside the 6-colour core palette cover ≤10% of the canvas. `palette_share`, max_pct 10." |
| "Logo should have breathing room." | Unmeasurable | "Logo clear space ≥ 1× cap-height of the wordmark on all sides. `clear_space`, multiple_of 1.0." |
| "Copy should feel confident." | Judgement with no exemplars | Principle P-07, plus rubric rule C-VOICE-002 with 4 positive + 3 negative headline exemplars. |
| "Never use black." | Overreaches its evidence | Scope it and note the exception — see V-COLOR-004 above. |

## Layering with `extends`

A campaign brain sets `extends: "../house/brain.json"` and carries only deltas. Merge semantics,
applied by the loader:

- `rules` — merged by `id`. A child rule with an existing id **replaces** the parent's entirely.
  To relax a parent rule, restate it at lower severity with a new `source_ids` justification.
- `principles`, `exemplars`, `open_questions` — appended.
- `identity`, `brand`, `scope` — shallow-merged, child wins per key.
- `channels` — merged by channel `id`.

Never copy the parent's rules into the child. The whole point is that the house brain stays the
single source of truth, and you can read a campaign brain and see exactly what the campaign changed.
