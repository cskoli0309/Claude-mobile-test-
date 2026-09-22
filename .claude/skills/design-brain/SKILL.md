---
name: design-brain
description: Build a portable, evidence-backed model of any brand's design system (a "design brain"), then use it to curate references/candidates and run QC on any asset. Use when someone asks to codify a brand's design rules, audit or QC a design, creative, ad, deck or generated asset for on-brand-ness, shortlist or rank references and AI generations, onboard a new brand or client, or check a batch of outputs before delivery. Works with or without an existing brand guideline — it induces rules from approved work when no documentation exists. Triggers on "is this on-brand", "QC these", "build a brand brain", "brand audit", "which of these should we ship", "check this against the guidelines".
---

# Design Brain

A **design brain** is a portable, machine-readable model of a brand's design system that is good
enough to do two jobs a PDF guideline cannot:

1. **Curate** — rank any set of candidates (references, AI generations, concepts) by how well they fit.
2. **QC** — audit a specific asset and return blocking defects, fixes, and a defensible verdict.

The brain works across any brand because it is **induced from evidence**, not transcribed from a
document. A brand with a 200-page guideline and a brand with nothing but a Dropbox of approved ads
both produce a valid brain — they differ in *confidence*, not in structure.

## The one rule that makes this work

> **A rule may only be as strict as its evidence.**

Every rule carries a `confidence` and a `support` count, and that caps the `severity` it can fail an
asset on:

| confidence | meaning | max severity | evidence bar |
|---|---|---|---|
| `stated` | written in an official guideline, or confirmed by the brand owner | `blocker` | cite the source |
| `inferred` | observed consistently across the approved corpus | `major` | holds in ≥80% of cases, n≥8 |
| `assumed` | analogy, category convention, or a thin sample | `minor` | must also be logged in `open_questions` |

This is what stops a brain from inventing hard rules and failing good work. Never promote a rule's
severity above its confidence ceiling. If you want to promote one, get it confirmed and re-tag it
`stated`.

## Three modes

Figure out which the user wants, then read the matching reference file. Do not read all of them.

| Mode | Ask sounds like | Read |
|---|---|---|
| **build** | "codify this brand", "onboard this client", "we have no guidelines" | `references/01-intake.md` → `references/02-brain-schema.md` → `references/03-extraction-recipes.md` |
| **curate** | "which of these fit", "rank these", "pick the best 5", "find references" | `references/04-curation.md` |
| **qc** | "is this on-brand", "audit this", "check before we ship" | `references/05-qc-rubric.md` (+ `06`, `07` as the asset demands) |

`build` is a prerequisite for the other two. If asked to curate or QC with no brain on disk, say so
and offer a **fast brain** (see below) rather than QC-ing against vibes.

## Mode: build

Produces `brains/<brand-slug>/brain.json` plus an `evidence/` folder.

1. **Scope it.** Ask what the brain is *for* — a single campaign, a channel, or the whole brand.
   Scope determines how much intake is enough. Do not gold-plate a brain for one banner.
2. **Intake.** Gather sources — guidelines, Figma libraries, live site, approved asset corpus,
   competitor set, ad library. `references/01-intake.md` has the source checklist, the minimum
   viable corpus sizes, and what to do when a source type is missing.
3. **Extract.** Run the per-source recipes in `references/03-extraction-recipes.md`. Figma, images,
   PDFs, live sites and ad libraries each have a different recipe and a different confidence yield.
4. **Induce rules.** Turn observations into rules using the schema in `references/02-brain-schema.md`.
   Tag every rule with confidence, support count, and source ids. Mechanical rules get a `check`
   expression; judgement rules get a rubric and exemplars.
5. **Validate.** `python3 scripts/validate_brain.py brains/<slug>/brain.json` — checks the schema,
   scores section completeness, and flags any rule whose severity exceeds its evidence.
6. **Report the gaps.** Hand back the completeness report and the `open_questions` list. A brain that
   admits what it does not know is more useful than one that pretends.

**Fast brain** (30–60 min, when the user needs to QC *today*): 10–15 approved assets, the live site,
and the logo files. Every rule lands at `inferred` or `assumed`, so nothing can block — the brain
advises rather than gates. Say this explicitly when you hand it over.

## Mode: curate

Ranks candidates against the brain. Read `references/04-curation.md`.

Shape of it: a **hard gate** first (anything violating a `blocker` rule is out, no score), then a
weighted fit score across the lanes that matter for the job, then a **diversity pass** so you do not
return five near-identical winners. Output is a ranked table with a one-line reason per candidate and
an explicit "here is what none of these cover" note.

## Mode: qc

Audits one asset, or a batch. Read `references/05-qc-rubric.md`.

Four lanes, scored independently — never averaged into one number, because averaging hides blockers:

| Lane | Covers | Reference |
|---|---|---|
| **V** Visual system | colour, type, spacing, grid, logo, imagery, composition | `05-qc-rubric.md` |
| **C** Copy & tone | voice, claims, terminology, CTA, legal/disclaimer | `05-qc-rubric.md` |
| **S** Channel & spec | ratio, safe zones, file specs, platform policy | `07-channel-specs.md` |
| **G** Generative integrity | artifacts, anatomy, text rendering, brief fidelity, batch drift | `06-generative-qc.md` |

Lane **G** applies only to AI-generated assets. Skip it for hand-made work and say so.

**Verdict gate** — severity decides, not score:

- any `blocker` finding → **FAIL**
- else any `major` finding → **PASS WITH FIXES**
- else → **PASS**

Every finding needs: lane, severity, the rule id it violates, what was observed, and a concrete fix.
A finding that cannot name a rule id is an *opinion* — log it under `observations`, never as a defect.

Run `python3 scripts/qc_score.py findings.json` to apply the gate and render the report. See
`references/08-reporting.md` for output formats.

## Scripts

All stdlib-only Python 3.8+. They degrade gracefully when Pillow or ffprobe are absent — they
narrow what they can check and say so, rather than failing.

| Script | Does |
|---|---|
| `scripts/validate_brain.py` | Schema-validates a brain, scores completeness, flags over-strict rules |
| `scripts/extract_palette.py` | Pulls a palette from an image, maps to brain colours, checks WCAG contrast |
| `scripts/check_specs.py` | Reads real dimensions/ratio/size, checks against a channel spec |
| `scripts/qc_score.py` | Applies the severity gate to findings, renders the QC report |

Run any with `--help`. `validate_brain.py` and `qc_score.py` exit non-zero on failure, so they drop
straight into CI.

## Working with the rest of this environment

- **Figma MCP** — `get_variable_defs` is the highest-confidence colour/type source available; it
  yields `stated` rules. `get_design_context` and `get_screenshot` cover components and layout.
  See `references/03-extraction-recipes.md`.
- **Higgsfield** — `show_generations` is a ready-made approved/rejected corpus for inducing a brain,
  and lane G exists to QC its outputs. Pairs with the `higgsfield-prompt-architect` skill: the brain
  supplies the brand block of the prompt, QC lane G checks what came back.
- **Meta MCP** — `ads_library_search` gives a competitor corpus for the `competitors_avoided` set;
  `ads_get_ad_preview` renders an ad for lane S checks.

## Anti-patterns

- **Averaging lanes into one score.** A 78/100 with a legal blocker is a FAIL, not a B+.
- **QC against an unwritten brain.** If the rule is not in `brain.json`, it cannot fail an asset.
  Add it as a rule first — with its evidence — or file it as an observation.
- **Guideline transcription.** Copying a PDF into JSON is not a brain. A brain needs checks,
  exemplars, and counter-exemplars. Rules nobody can check are documentation, not QC.
- **One global brain per brand.** Sub-brands, campaigns and channels legitimately diverge. Use
  `extends` to layer a campaign brain over the house brain rather than forking it.
- **Silent assumptions.** Anything you could not verify goes in `open_questions`. Every time.
