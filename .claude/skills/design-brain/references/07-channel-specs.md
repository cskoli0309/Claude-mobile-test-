# Lane S — channel & spec compliance

Mechanical, cheap, and the lane most often skipped until a delivery bounces.

> **Read this first.** The table below is a **starting point, not an authority.** Platform specs
> change without notice and vary by placement, market, and objective. Verify against the platform's
> current documentation before any rule sourced from here carries `blocker` severity. Rules built
> from this table start at `assumed` until verified — `validate_brain.py` will hold you to that.
>
> To verify: pull current specs from the platform's own docs, or for Meta placements read the
> rendered result via `ads_get_ad_preview`. Then re-tag the rule `stated` with a
> `type: "platform_policy"` source and the date you checked.

## What lane S checks

| Check | `check.kind` | Script support |
|---|---|---|
| Aspect ratio | `aspect_ratio` | `check_specs.py` |
| Pixel dimensions / min resolution | `dimensions` | `check_specs.py` |
| File size | `file_size` | `check_specs.py` |
| Duration | `duration` | `check_specs.py` (needs ffprobe) |
| Safe zones | `safe_zone` | visual pass against overlay |
| Colour profile | — | visual/metadata pass |
| Text-in-image ratio | — | visual pass |
| Platform policy | — | judgement, cite the policy |

## Starter channel table — VERIFY BEFORE USE

Common digital placements. Ratios and rough dimensions only; treat every number as needing
confirmation.

| Channel | Placement | Ratio | Typical px | Notes |
|---|---|---|---|---|
| Meta | Feed image | 1:1 or 4:5 | 1080×1080 / 1080×1350 | 4:5 maximises feed real estate |
| Meta | Stories / Reels | 9:16 | 1080×1920 | Reserve top and bottom for UI chrome |
| Meta | Right column | 1.91:1 | 1200×628 | Small render — check legibility at size |
| Instagram | Feed | 1:1, 4:5 | 1080×1350 | |
| Instagram | Reels | 9:16 | 1080×1920 | Caption/UI zones at bottom |
| TikTok | In-feed | 9:16 | 1080×1920 | Heavy UI overlay — safe zone is generous |
| YouTube | In-stream | 16:9 | 1920×1080 | |
| YouTube | Shorts | 9:16 | 1080×1920 | |
| LinkedIn | Feed image | 1.91:1, 1:1 | 1200×627 | |
| Display | Standard IAB | various | 300×250, 728×90, 300×600, 160×600 | Size caps are strict |
| Email | Header | — | 600–700 wide | Retina: export 2× |
| Web | Hero | varies | ≥1920 wide | Provide 1×/2×; art-direct the mobile crop |
| OOH | varies | varies | vendor spec | Always vendor-supplied; never assume |
| Print | varies | varies | 300dpi at size | CMYK, bleed, crop marks per printer |

**Safe zones are placement-specific and shift with UI redesigns.** Where a platform publishes an
overlay template, use it. Where it does not, measure from a current screenshot of the real placement
rather than from a remembered percentage.

## Defining channels in the brain

```json
{
  "id": "meta-reels",
  "label": "Meta / Instagram Reels",
  "checks": [
    { "kind": "aspect_ratio", "params": { "allowed": ["9:16"], "tolerance": 0.01 } },
    { "kind": "dimensions",   "params": { "min_w": 1080, "min_h": 1920 } },
    { "kind": "file_size",    "params": { "max_bytes": 4194304 } },
    { "kind": "duration",     "params": { "min_s": 3, "max_s": 90 } },
    { "kind": "safe_zone",    "params": { "top_pct": 12, "bottom_pct": 20, "left_pct": 6, "right_pct": 6 } }
  ],
  "verified": "2026-09-22",
  "source_ids": ["s9"]
}
```

`verified` is not decoration — `validate_brain.py` warns on any channel unverified for 90+ days, and
caps its rules at `assumed` if it has never been verified at all.

## Running the checks

Single asset against a channel:

```bash
python3 scripts/check_specs.py delivery/reel-01.mp4 \
    --brain brains/acme/brain.json --channel meta-reels
```

Survey a delivery folder before checking anything:

```bash
python3 scripts/check_specs.py delivery/*.png --summarize
```

`--summarize` reports what is actually in the folder — dimensions, ratios, sizes — with no pass/fail.
Run it first on any new corpus or delivery: it usually surfaces the wrong-format file immediately,
and on an intake corpus it tells you what formats the brand really ships.

## Platform policy

Beyond file specs, the content rules. These are `blocker` and externally `stated`:

- Prohibited content categories for the vertical.
- Claim restrictions (health, finance, and similar regulated categories).
- Before/after imagery restrictions.
- Personal-attribute targeting implications in the creative itself.
- Required AI-content disclosure.
- Political/social-issue ad requirements.

Cite the specific policy in the rule's source. "Against platform policy" without a citation is not
an actionable finding, and it is the kind of finding that gets a QC report argued with rather than
acted on.

## Print and OOH

Different discipline, same structure:

- Bleed, trim, safety per the printer's spec sheet — never a generic assumption.
- CMYK conversion checked, not assumed. Brand colours need named CMYK/Pantone equivalents in the
  brain, or every print job re-derives them differently.
- Resolution at **final size**, including any viewing-distance allowance for large format.
- Overprint, spot colours, and varnish per the production spec.
- Fonts embedded or outlined per the printer's requirement.

For OOH, viewing distance drives minimum type size. That belongs in the channel definition as a
`type_scale` check, not in someone's head.
