# Reporting

Three audiences, three formats. Pick by who is reading, not by habit.

| Audience | Format | What they need |
|---|---|---|
| Designer fixing it | Full markdown report | Every finding, located, with a fix |
| Producer / account | Verdict block | Ship or not, and what is blocking |
| Pipeline / CI | JSON + exit code | Machine-readable gate |

## Full report

Render with `python3 scripts/qc_score.py findings.json --format markdown`, or follow
`assets/qc-report.template.md`.

Order matters, and it is verdict-first. Anyone can stop reading after the first block and still act
correctly:

1. **Verdict** — PASS / PASS WITH FIXES / FAIL, with the blocking count.
2. **Blockers** — numbered, each with location and fix.
3. **Majors** — same.
4. **Minors** — grouped, terse.
5. **Observations** — opinions with no rule behind them, clearly separated.
6. **Not checked** — what you could not verify and why.
7. **Lane scores** — for trending.
8. **Provenance** — brain version, date, who ran it.

Section 6 is the one people cut, and it is the one that keeps the process honest. A report that does
not say what it could not see implies it saw everything.

## Verdict block

For a status channel or an email:

```
Acme AW26 hero — FAIL
2 blockers, 3 majors.
· Logo clear space 18px, requires 34px (V-LOGO-001)
· Unsubstantiated "longest-lasting" claim, no asterisk (C-CLAIM-002)
Full report: qc/aw26-hero-2026-09-22.md
```

Verdict, count, the blockers by name, link. Nothing else.

## JSON

```bash
python3 scripts/qc_score.py findings.json --format json
```

```json
{
  "verdict": "FAIL",
  "counts": { "blocker": 2, "major": 3, "minor": 4, "note": 1 },
  "lane_scores": { "V": 72, "C": 58, "S": 100, "G": null },
  "blocking": ["V-LOGO-001", "C-CLAIM-002"],
  "brain": { "slug": "acme", "version": "1.0", "updated": "2026-09-22" },
  "asset": "aw26-hero.png",
  "checked": "2026-09-22T14:02:00Z"
}
```

Exit code 1 on FAIL, 0 otherwise. `lane_scores` is `null` for any lane not run — never `0`, which
would read as a catastrophic failure rather than "not applicable".

## Writing findings people act on

**Locate it.** "Top-right, all three sizes" beats "the logo". For video, timecode. For long-form,
section or frame.

**Measure it.** "18px, requires 34px" beats "too close to the edge". A number turns an argument into
a task.

**Make the fix an instruction.** "Increase right margin to 34px, or switch to the mark-only lockup at
this width" beats "fix clear space". Where there is a trade-off, name both options — the designer
knows the layout constraints and you do not.

**Separate opinion from defect.** Anything without a rule id goes under Observations. This is the
single discipline that determines whether a QC report gets acted on or argued with, because it means
no one is ever failed by a rule invented while reviewing them.

**Do not pad.** Ten findings where three matter trains people to skim. If the minors are noise this
round, group them into one line and move on.

## Trending

Log every run as a JSON line in `brains/<slug>/qc-log.jsonl`. Over a few months it answers the
questions that improve the system rather than the asset:

- Which rules fire most? High-frequency rules signal a gap in the brief, the template, or the brain —
  not a lazy designer. Fix the source.
- Which rules never fire? Either well-internalised, or unenforceable. Check which; retire the latter.
- Are lane scores improving per channel, per vendor, per campaign?
- What is the block rate at first submission? That is the real health metric for the whole pipeline.

A rule firing on 60% of submissions is a broken template, and QC finding it twelve times is twelve
findings about the same broken template. Fix the template.
