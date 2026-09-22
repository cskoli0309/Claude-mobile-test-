# Lane G — generative integrity

Applies **only** to AI-generated or AI-edited assets. Skip it for hand-made work and say you skipped
it, so nobody assumes it passed.

Lane G exists because generative assets fail in ways brand QC was never built to catch. An image can
be perfectly on-palette, on-type, correctly cropped — and have six fingers. Lanes V/C/S will pass it.

## G1 — Structural artifacts

| Check | Look for | Typical severity |
|---|---|---|
| Anatomy | Hand/finger count, joint direction, limb count, teeth, ear/eye asymmetry | `blocker` |
| Object coherence | Objects merging, floating, or intersecting impossibly | `blocker` |
| Repetition | Cloned faces in crowds, tiled textures, duplicated background elements | `major` |
| Edge quality | Halos, smeared boundaries, melted contours at subject edges | `major` |
| Depth logic | Shadows without sources, multiple contradictory light directions, wrong scale | `major` |
| Reflection logic | Mirrors/glass showing the wrong scene, or nothing | `major` |

**Inspect at 100% and at delivery size.** Most defects are invisible at thumbnail and glaring at
full size — and the ones that survive thumbnail viewing are the ones that ship. Check hands, eyes,
text, and any hard product edge specifically: those are where current models fail most.

## G2 — Text rendering

Generated text is the single most common defect and the easiest to miss on a quick pass.

- Any text in the image: is it real, correctly spelled, correct brand wording?
- Gibberish or near-miss text in the **background** — signage, packaging, screens, labels. This is
  the one people miss, because the eye reads intent rather than glyphs.
- Logo reproduction: a generated logo is **always** a `blocker`. Models approximate logos; brand logos
  must be composited from the real asset, never generated.
- Product packaging: generated packaging copy is almost always wrong. Treat as `blocker` for any
  hero product shot.

Rule of thumb: **if text is legible in frame, it must be real or removed.** There is no acceptable
middle.

## G3 — Product accuracy

For any asset featuring a real product:

- Correct model and generation — not a plausible-looking hybrid of two.
- Correct colourway, materials, finish.
- Correct proportions. Models routinely subtly restyle products, and "subtly wrong" is worse than
  obviously wrong because it ships.
- Current packaging, current branding.
- Control details — buttons, ports, seams, logos placed where they actually are.

`blocker` throughout. Compare against a real product photograph, not memory. If no reference is
available, say the check could not be performed.

## G4 — Brief fidelity

Does it depict what was asked for?

- Subject, action, setting, mood as briefed.
- Required elements present; prohibited elements absent.
- Cast/casting direction honoured (age, representation, wardrobe).
- The *implied* requirements met — "in use" means a person actually using it, not a hand hovering
  near it.

Findings here often trace back to the prompt, not the model. Say which, because the fix differs:
reprompt versus regenerate versus retouch.

## G5 — Model signature & drift

The tells that mark an asset as AI-made to a trained viewer:

- Over-smooth skin, plastic sheen, uncanny symmetry.
- Default model aesthetic overriding brand grade — the "Midjourney look", the over-lit studio default.
- Excessive bokeh, HDR-ish local contrast, over-saturated rim lighting.
- Generic stock-photo composition where the brand has a specific convention.

These are usually `major`: individually defensible, collectively they make the work look generic and
not-of-the-brand.

**Batch drift** — across a set, check that:
- Subject, lighting and grade stay consistent between frames intended as a set.
- Characters keep identity across a sequence (face, wardrobe, build).
- The set does not converge on the model's default look as brand specificity washes out over
  successive rounds.

Drift is a **systemic** finding. Report it once about the batch, with the prompt or seed fix — never
as N per-asset findings.

## G6 — Provenance & disclosure

- Rights cleared for any reference image, likeness or style used.
- Generated likenesses do not resemble identifiable real people.
- Market-required AI disclosure present (varies by market and platform — check every market in
  `brand.markets`).
- Generation metadata retained for audit: model, prompt, seed, settings.
- No style transfer from a living named artist's work where the brand's policy or the market
  prohibits it.

`blocker` throughout. These are `stated` by external authority, not by the brand.

## Video-specific

| Check | Notes |
|---|---|
| Temporal coherence | Morphing faces/objects between frames; flicker on static elements |
| Motion plausibility | Physics, gait, cloth, hair, liquid behaviour |
| Cut continuity | Wardrobe, lighting, product state across cuts |
| Lip sync | Phoneme match for any speaking subject |
| Audio/visual sync | Action lands on the beat it should |
| First frame | Thumbnail-quality — it is the still most viewers see |
| Loop point | Clean if the placement loops |

## Workflow

1. **Screen mechanically first.** Run G1–G3 across the batch before any judgement. On a typical batch
   this removes a third of candidates and saves the expensive attention for real contenders.
2. **Then brief fidelity (G4)** on survivors.
3. **Then signature/drift (G5)** across the survivor set as a whole.
4. **Then the brand lanes V/C/S** on what is left.

Screening in that order is the whole efficiency gain: never spend rubric judgement on an asset with
a broken hand.

## Feeding findings back

Lane G findings are prompt intelligence. When a defect recurs across a batch:

- Add a negative constraint to the prompt, or a positive specification that crowds it out.
- Record it as a lane-G rule in the brain so the next QC pass checks it by default.
- If the `higgsfield-prompt-architect` skill is in play, feed it back into the brand block so future
  generations start from the corrected prompt rather than repeating the round.

A QC process that only rejects is half a process. The loop back into generation is where the defect
rate actually drops.
