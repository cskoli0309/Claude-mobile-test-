#!/usr/bin/env python3
"""Apply the QC severity gate to a findings file and render the report.

The gate, and only the gate, decides the verdict:

    any blocker    -> FAIL
    else any major -> PASS WITH FIXES
    else           -> PASS

Lane scores are reported for trending. They never override the gate — averaging
a legal blocker into a 78/100 is exactly how bad work ships.

Usage:
    qc_score.py findings.json
    qc_score.py findings.json --brain brains/acme/brain.json
    qc_score.py findings.json --format json
    qc_score.py findings.json --format block          # short status-channel summary
    qc_score.py f1.json f2.json --format markdown     # batch, with systemic detection

Exit codes: 0 PASS or PASS WITH FIXES, 1 FAIL, 2 could not read input.
Stdlib only.
"""

import argparse
import datetime as dt
import json
import os
import sys

SEVERITIES = ("blocker", "major", "minor", "note")
SEVERITY_WEIGHT = {"blocker": 40, "major": 15, "minor": 4, "note": 0}
LANE_NAMES = {"V": "Visual", "C": "Copy", "S": "Spec", "G": "Generative"}
VERDICT_FAIL = "FAIL"
VERDICT_FIXES = "PASS WITH FIXES"
VERDICT_PASS = "PASS"


def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def verdict_for(findings):
    if any(f.get("severity") == "blocker" for f in findings):
        return VERDICT_FAIL
    if any(f.get("severity") == "major" for f in findings):
        return VERDICT_FIXES
    return VERDICT_PASS


def counts_for(findings):
    counts = {s: 0 for s in SEVERITIES}
    for f in findings:
        sev = f.get("severity")
        if sev in counts:
            counts[sev] += 1
    return counts


def lane_scores(findings, lanes_run):
    """100 minus weighted deductions, floored at 0. Trending only."""
    scores = {}
    for lane in LANE_NAMES:
        if lane not in lanes_run:
            scores[lane] = None
            continue
        deduction = sum(SEVERITY_WEIGHT.get(f.get("severity"), 0)
                        for f in findings if f.get("lane") == lane)
        scores[lane] = max(0, 100 - deduction)
    return scores


def validate_findings(doc, brain_rules, path, problems):
    """A finding without a rule id is an opinion. Opinions go in observations."""
    for f in doc.get("findings") or []:
        fid = f.get("id", "<no id>")
        if not f.get("rule_id"):
            problems.append("%s: finding %s cites no rule_id — move it to 'observations' "
                            "or add the rule to the brain first" % (path, fid))
        elif brain_rules is not None and f["rule_id"] not in brain_rules:
            problems.append("%s: finding %s cites rule %s, which is not in the brain"
                            % (path, fid, f["rule_id"]))
        if f.get("severity") not in SEVERITIES:
            problems.append("%s: finding %s has invalid severity %r"
                            % (path, fid, f.get("severity")))
        if not f.get("fix") and f.get("severity") in ("blocker", "major"):
            problems.append("%s: finding %s is a %s with no fix"
                            % (path, fid, f.get("severity")))
        if brain_rules:
            rule = brain_rules.get(f.get("rule_id"))
            if rule and f.get("severity") in SEVERITIES and rule.get("severity") in SEVERITIES:
                order = {s: i for i, s in enumerate(reversed(SEVERITIES))}
                if order[f["severity"]] > order[rule["severity"]]:
                    problems.append(
                        "%s: finding %s is '%s' but rule %s is only '%s' — a finding may not "
                        "exceed its rule's severity" % (path, fid, f["severity"],
                                                        f["rule_id"], rule["severity"]))


def find_systemic(docs, threshold=0.6):
    """A defect across most of a batch is one finding about the source, not N about the assets."""
    if len(docs) < 3:
        return []
    tally = {}
    for _, doc in docs:
        for rid in {f.get("rule_id") for f in (doc.get("findings") or []) if f.get("rule_id")}:
            tally[rid] = tally.get(rid, 0) + 1
    systemic = []
    for rid, n in sorted(tally.items(), key=lambda kv: -kv[1]):
        if n / len(docs) >= threshold:
            systemic.append({"rule_id": rid, "assets": n, "of": len(docs),
                             "pct": round(n / len(docs) * 100)})
    return systemic


def render_markdown(path, doc, brain_meta, problems):
    findings = doc.get("findings") or []
    verdict = verdict_for(findings)
    counts = counts_for(findings)
    lanes_run = doc.get("lanes_run") or sorted({f.get("lane") for f in findings if f.get("lane")})
    scores = lane_scores(findings, lanes_run)

    out = []
    out.append("# QC Report — %s" % doc.get("asset", os.path.basename(path)))
    out.append("")
    out.append("**Verdict: %s**  ·  %d blockers, %d majors, %d minors"
               % (verdict, counts["blocker"], counts["major"], counts["minor"]))
    if brain_meta:
        out.append("Brain: `%s` v%s (%s, scope: %s)"
                   % (brain_meta.get("slug", "?"), brain_meta.get("version", "?"),
                      brain_meta.get("updated", "?"), brain_meta.get("scope", "?")))
    bits = [b for b in (doc.get("asset_type"), doc.get("channel"), doc.get("stage")) if b]
    if doc.get("generated"):
        bits.append("AI-generated")
    if bits:
        out.append("Asset: " + " · ".join(bits))
    out.append("Checked: %s · Lanes run: %s"
               % (dt.date.today().isoformat(), ", ".join(lanes_run) or "none"))

    for sev, title, note in (
        ("blocker", "Blockers", "must fix before ship"),
        ("major", "Majors", "fix before ship"),
    ):
        items = [f for f in findings if f.get("severity") == sev]
        if not items:
            continue
        out.append("")
        out.append("---")
        out.append("")
        out.append("## %s — %s" % (title, note))
        for n, f in enumerate(items, 1):
            out.append("")
            out.append("### %d. %s" % (n, f.get("rule_id", "—")))
            out.append("**Observed.** %s" % f.get("observed", "—"))
            if f.get("location"):
                out.append("**Where.** %s" % f["location"])
            out.append("**Fix.** %s" % f.get("fix", "—"))
            if f.get("confidence") == "unverifiable":
                out.append("**Note.** Could not be verified from the supplied file.")

    minors = [f for f in findings if f.get("severity") == "minor"]
    if minors:
        out.append("")
        out.append("---")
        out.append("")
        out.append("## Minors — advisory")
        out.append("")
        for f in minors:
            out.append("- **%s** %s → %s"
                       % (f.get("rule_id", "—"), f.get("observed", "—"), f.get("fix", "—")))

    notes = [f for f in findings if f.get("severity") == "note"]
    observations = doc.get("observations") or []
    if notes or observations:
        out.append("")
        out.append("---")
        out.append("")
        out.append("## Observations")
        out.append("")
        out.append("No rule covers these. They do not affect the verdict.")
        out.append("")
        for f in notes:
            out.append("- **%s** %s" % (f.get("rule_id", "—"), f.get("observed", "—")))
        for o in observations:
            suffix = "  _(candidate rule)_" if o.get("suggest_rule") else ""
            out.append("- %s%s" % (o.get("note", "—"), suffix))

    not_checked = doc.get("not_checked") or []
    if not_checked:
        out.append("")
        out.append("---")
        out.append("")
        out.append("## Not checked")
        out.append("")
        for nc in not_checked:
            out.append("- **%s** — %s" % (nc.get("what", "—"), nc.get("why", "—")))

    out.append("")
    out.append("---")
    out.append("")
    out.append("## Lane scores")
    out.append("")
    out.append("| Lane | Score | Findings |")
    out.append("|---|---|---|")
    for lane, name in LANE_NAMES.items():
        score = scores[lane]
        n = sum(1 for f in findings if f.get("lane") == lane)
        out.append("| %s %s | %s | %s |"
                   % (lane, name, "n/a" if score is None else "%d" % score,
                      "—" if score is None else n))
    out.append("")
    out.append("Scores are for trending. The verdict is set by the severity gate, not the scores.")

    if problems:
        out.append("")
        out.append("---")
        out.append("")
        out.append("## Report hygiene")
        out.append("")
        for p in problems:
            out.append("- %s" % p)

    return "\n".join(out)


def render_block(path, doc):
    findings = doc.get("findings") or []
    verdict = verdict_for(findings)
    counts = counts_for(findings)
    lines = ["%s — %s" % (doc.get("asset", os.path.basename(path)), verdict)]
    lines.append("%d blockers, %d majors." % (counts["blocker"], counts["major"]))
    for f in findings:
        if f.get("severity") == "blocker":
            lines.append("· %s (%s)" % (f.get("observed", "—"), f.get("rule_id", "—")))
    return "\n".join(lines)


def render_json(path, doc, brain_meta, problems):
    findings = doc.get("findings") or []
    lanes_run = doc.get("lanes_run") or sorted({f.get("lane") for f in findings if f.get("lane")})
    return {
        "verdict": verdict_for(findings),
        "counts": counts_for(findings),
        "lane_scores": lane_scores(findings, lanes_run),
        "blocking": [f.get("rule_id") for f in findings if f.get("severity") == "blocker"],
        "brain": brain_meta,
        "asset": doc.get("asset", os.path.basename(path)),
        "checked": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "hygiene_problems": problems,
    }


def main():
    ap = argparse.ArgumentParser(description="Apply the QC severity gate and render a report.")
    ap.add_argument("findings", nargs="+", help="one or more findings JSON files")
    ap.add_argument("--brain", help="brain.json, to validate rule references")
    ap.add_argument("--format", choices=("markdown", "json", "block"), default="markdown")
    args = ap.parse_args()

    brain_rules, brain_meta = None, None
    if args.brain:
        try:
            brain = load(args.brain)
        except (OSError, json.JSONDecodeError) as exc:
            print("cannot read brain %s: %s" % (args.brain, exc), file=sys.stderr)
            return 2
        brain_rules = {r["id"]: r for r in (brain.get("rules") or []) if r.get("id")}
        brand = brain.get("brand") or {}
        brain_meta = {
            "slug": brand.get("slug"),
            "version": brain.get("brain_version"),
            "updated": brand.get("updated"),
            "scope": (brain.get("scope") or {}).get("kind"),
        }

    docs, problems = [], []
    for path in args.findings:
        try:
            doc = load(path)
        except (OSError, json.JSONDecodeError) as exc:
            print("cannot read %s: %s" % (path, exc), file=sys.stderr)
            return 2
        validate_findings(doc, brain_rules, path, problems)
        docs.append((path, doc))

    systemic = find_systemic(docs)
    worst = VERDICT_PASS
    for _, doc in docs:
        v = verdict_for(doc.get("findings") or [])
        if v == VERDICT_FAIL:
            worst = VERDICT_FAIL
        elif v == VERDICT_FIXES and worst != VERDICT_FAIL:
            worst = VERDICT_FIXES

    if args.format == "json":
        payload = {
            "set_verdict": worst,
            "systemic": systemic,
            "assets": [render_json(p, d, brain_meta, problems) for p, d in docs],
        }
        print(json.dumps(payload if len(docs) > 1 else payload["assets"][0], indent=2))
    elif args.format == "block":
        for path, doc in docs:
            print(render_block(path, doc))
            print()
        if len(docs) > 1:
            print("SET VERDICT: %s (%d assets)" % (worst, len(docs)))
    else:
        if systemic:
            print("# Systemic findings")
            print()
            print("These appear across most of the batch. They are one problem with the source —")
            print("a template, a master file, or a prompt — not N problems with N assets. Fix the source.")
            print()
            for s in systemic:
                print("- **%s** — %d of %d assets (%d%%)"
                      % (s["rule_id"], s["assets"], s["of"], s["pct"]))
            print()
            print("---")
            print()
        for i, (path, doc) in enumerate(docs):
            if i:
                print()
                print("---")
                print()
            print(render_markdown(path, doc, brain_meta, problems))
        if len(docs) > 1:
            print()
            print("---")
            print()
            print("**Set verdict: %s** — %d assets. The set ships only when every asset ships."
                  % (worst, len(docs)))

    return 1 if worst == VERDICT_FAIL else 0


if __name__ == "__main__":
    # Piping into head/less closes stdout early; exit quietly instead of tracebacking.
    try:
        import signal
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (AttributeError, ValueError, OSError):
        pass
    try:
        sys.exit(main())
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except Exception:
            pass
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(130)
