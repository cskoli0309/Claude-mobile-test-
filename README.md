# Design Brain

A workflow for building a **design brain** — a portable, evidence-backed model of any brand's design
system — and using it to **curate** work and **QC** it.

Packaged as a Claude Code skill. Invoke it in any session with `/design-brain`, or just describe the
job ("is this on-brand?", "QC these before delivery", "codify this client's system") and it triggers.

## The problem it solves

Brand QC usually runs on one of two things: a PDF nobody opens, or the taste of whoever is senior
enough to say no. The first cannot be checked; the second cannot be delegated, audited, or scaled.

A design brain is the missing middle — a model that is **specific enough to check mechanically** and
**honest enough to admit what it does not know**.

## The idea

> **A rule may only be as strict as its evidence.**

Every rule in a brain carries a confidence level, and that caps how hard it can fail an asset:

| confidence | meaning | max severity |
|---|---|---|
| `stated` | in an official guideline, or confirmed by the brand owner | `blocker` |
| `inferred` | observed in ≥80% of the approved corpus (n≥8) | `major` |
| `assumed` | analogy, category convention, or a thin sample | `minor` |

This is why the workflow works for **any brand**. A brand with a 200-page guideline and a brand with
nothing but a folder of approved ads both produce a valid brain — they differ in confidence, not in
structure. And nothing can be failed by a rule that was invented while reviewing it.

## Three modes

| Mode | What it does |
|---|---|
| **build** | Induce a brain from whatever evidence exists — tokens, guidelines, shipped work, killed work, a 30-minute interview |
| **curate** | Rank candidates (references, AI generations, concept routes) with a hard gate, a weighted fit score, a diversity pass, and a tension check |
| **qc** | Audit an asset across four lanes and return a verdict that survives an argument |

### The four QC lanes

| Lane | Covers |
|---|---|
| **V** Visual system | colour, type, spacing, grid, logo, imagery, composition |
| **C** Copy & tone | voice, claims, terminology, CTA, legal |
| **S** Channel & spec | ratio, safe zones, file specs, platform policy |
| **G** Generative integrity | artifacts, anatomy, text rendering, brief fidelity, batch drift |

Lanes are scored independently and **never averaged** — a 78/100 with a legal blocker is a FAIL, and
averaging is exactly how that ships. Severity decides:

```
any blocker    → FAIL
else any major → PASS WITH FIXES
else           → PASS
```

## Layout

```
.claude/skills/design-brain/
  SKILL.md                     the router — read this first
  references/
    01-intake.md               source ladder, minimum corpus sizes, missing-source cases
    02-brain-schema.md         the brain format and how to write good rules
    03-extraction-recipes.md   per-source recipes (Figma, PDF, corpus, site, Higgsfield, Meta)
    04-curation.md             gate → score → diversity → tension
    05-qc-rubric.md            lanes V and C, severity, findings, batch QC
    06-generative-qc.md        lane G — AI-specific defects
    07-channel-specs.md        lane S — specs, safe zones, platform policy
    08-reporting.md            report formats and what to trend
  assets/
    brain.schema.json          JSON Schema for brain.json
    brain.template.json        empty scaffold
    qc-report.template.md      report layout
    findings.example.json      worked findings file
  scripts/                     stdlib-only Python 3.8+, no install step
examples/
  acme-brain.json              a complete worked brain
```

## Scripts

No dependencies. Pillow and ffprobe are used automatically **if present** and are never required —
the scripts narrow what they can check and say so, rather than failing.

| Script | Does |
|---|---|
| `validate_brain.py` | Schema + evidence discipline; flags any rule stricter than its evidence |
| `extract_palette.py` | Palette, brand-colour mapping, WCAG contrast; `--aggregate` induces a palette from a corpus |
| `check_specs.py` | Real dimensions, ratio, size, duration vs a channel spec |
| `qc_score.py` | Applies the severity gate, detects systemic batch defects, renders the report |

`validate_brain.py` and `qc_score.py` exit non-zero on failure, so they drop straight into CI.

PNG, JPEG, GIF, WEBP, BMP and MP4 headers are parsed in pure Python — including a full PNG decoder
(all five filter types) so palette extraction works on a bare interpreter.

## Try it

```bash
# Validate the worked example
python3 .claude/skills/design-brain/scripts/validate_brain.py examples/acme-brain.json

# Run the gate on the example findings
python3 .claude/skills/design-brain/scripts/qc_score.py \
    .claude/skills/design-brain/assets/findings.example.json \
    --brain examples/acme-brain.json

# Survey a delivery folder before checking anything
python3 .claude/skills/design-brain/scripts/check_specs.py delivery/*.png --summarize

# Induce a core palette from an approved corpus
python3 .claude/skills/design-brain/scripts/extract_palette.py evidence/approved/*.png --aggregate
```

## Fast brain

When QC is needed today: 10–15 approved assets, the live site, and the logo files, in 30–60 minutes.
Every rule lands at `inferred` or `assumed`, so nothing can block — the brain advises rather than
gates. That limitation is stated on delivery, not buried.

The cheapest upgrade from there is a 30-minute conversation with whoever signs work off. It converts
guesses into `stated` rules, which is the whole difference between a brain that advises and a brain
that gates.

## Working with other tools

- **Figma MCP** — `get_variable_defs` is the highest-confidence source available; it yields `stated`
  mechanical rules directly.
- **Higgsfield** — generation history doubles as a pre-labelled corpus (used vs. discarded); lane G
  QCs what comes back, and findings feed back into the prompt.
- **Meta MCP** — ad library for the competitor set; ad preview for rendered spec checks.
