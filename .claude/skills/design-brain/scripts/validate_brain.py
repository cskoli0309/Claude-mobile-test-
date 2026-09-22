#!/usr/bin/env python3
"""Validate a design brain: structure, evidence discipline, and completeness.

Beyond schema checks, this enforces the rule that makes a brain trustworthy:
a rule may only be as strict as its evidence.

    stated   -> may be blocker   (needs a rung 1-4 source, or the arbiter)
    inferred -> max major        (needs count/of >= 0.8 and count >= 8)
    assumed  -> max minor        (needs a matching open_question)

Usage:
    validate_brain.py brain.json
    validate_brain.py brain.json --json
    validate_brain.py brain.json --strict     # warnings become errors

Exit codes: 0 ok (warnings allowed), 1 errors found, 2 could not read the file.
Stdlib only.
"""

import argparse
import datetime as dt
import json
import re
import sys

SEVERITY_RANK = {"note": 0, "minor": 1, "major": 2, "blocker": 3}
CONFIDENCE_CEILING = {"assumed": "minor", "inferred": "major", "stated": "blocker"}
LANES = ("V", "C", "S", "G")
CONFIDENCES = ("stated", "inferred", "assumed")
MODES = ("mechanical", "rubric")
SCOPE_KINDS = ("house", "sub_brand", "campaign", "channel")
RULE_ID_RE = re.compile(r"^[VCSG]-[A-Z]+-\d{3}$")
SLUG_RE = re.compile(r"^[a-z0-9-]+$")

INFERRED_MIN_COUNT = 8
INFERRED_MIN_RATIO = 0.8
AUTHORITATIVE_RUNGS = {1, 2, 3, 4}
EXTERNAL_AUTHORITY_TYPES = {"regulation", "platform_policy"}
CHANNEL_STALE_DAYS = 90


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []

    def error(self, where, msg):
        self.errors.append({"where": where, "message": msg})

    def warn(self, where, msg):
        self.warnings.append({"where": where, "message": msg})

    def note(self, msg):
        self.info.append(msg)


def parse_date(value):
    if not value:
        return None
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


# --------------------------------------------------------------------------- structure

def check_structure(brain, rep):
    for key in ("brain_version", "brand", "scope", "provenance", "rules"):
        if key not in brain:
            rep.error("root", "missing required key '%s'" % key)

    if brain.get("brain_version") not in (None, "1.0"):
        rep.warn("root", "brain_version %r is not 1.0; this validator targets 1.0"
                 % brain["brain_version"])

    brand = brain.get("brand") or {}
    for key in ("name", "slug", "updated"):
        if not brand.get(key):
            rep.error("brand", "missing required field '%s'" % key)
    if brand.get("slug") and not SLUG_RE.match(brand["slug"]):
        rep.error("brand", "slug %r must be lowercase alphanumeric with hyphens" % brand["slug"])
    if brand.get("updated") and not parse_date(brand["updated"]):
        rep.error("brand", "updated %r is not an ISO date (YYYY-MM-DD)" % brand["updated"])

    review_by = parse_date(brand.get("review_by"))
    if not brand.get("review_by"):
        rep.warn("brand", "no review_by date; brains rot — set one ~6 months out")
    elif review_by and review_by < dt.date.today():
        rep.warn("brand", "review_by %s has passed; re-verify inferred rules" % brand["review_by"])

    scope = brain.get("scope") or {}
    if scope.get("kind") not in SCOPE_KINDS:
        rep.error("scope", "kind must be one of %s, got %r" % (", ".join(SCOPE_KINDS), scope.get("kind")))
    if scope.get("kind") in ("campaign", "channel") and not brain.get("extends"):
        rep.warn("scope", "a %s-scoped brain normally 'extends' a house brain and carries deltas only"
                 % scope.get("kind"))

    if not isinstance(brain.get("rules"), list):
        rep.error("rules", "must be a list")


def check_sources(brain, rep):
    sources = ((brain.get("provenance") or {}).get("sources")) or []
    if not sources:
        rep.error("provenance", "no sources; every rule must trace to evidence")
        return {}

    by_id = {}
    for i, src in enumerate(sources):
        where = "provenance.sources[%d]" % i
        sid = src.get("id")
        if not sid:
            rep.error(where, "missing id")
            continue
        if sid in by_id:
            rep.error(where, "duplicate source id %r" % sid)
        rung = src.get("rung")
        if not isinstance(rung, int) or not 1 <= rung <= 8:
            rep.error(where, "rung must be an integer 1-8, got %r" % rung)
        if not src.get("type"):
            rep.error(where, "missing type")
        if not src.get("date"):
            rep.warn(where, "source %r has no date; staleness cannot be judged" % sid)
        if src.get("type") == "asset_corpus" and not src.get("n"):
            rep.warn(where, "asset_corpus %r has no n; inferred support cannot be audited" % sid)
        by_id[sid] = src
    return by_id


# --------------------------------------------------------------------------- rules

def check_rules(brain, sources, rep):
    rules = brain.get("rules") or []
    if not rules:
        rep.error("rules", "brain has no rules; it cannot curate or QC anything")
        return {}

    owner = (brain.get("brand") or {}).get("owner")
    questions = brain.get("open_questions") or []
    question_targets = set()
    for q in questions:
        for rid in q.get("blocks") or []:
            if q.get("status") == "open":
                question_targets.add(rid)

    by_id = {}
    for i, rule in enumerate(rules):
        rid = rule.get("id", "<no id>")
        where = "rules[%d] %s" % (i, rid)

        if not rule.get("id"):
            rep.error(where, "missing id")
        elif not RULE_ID_RE.match(rule["id"]):
            rep.error(where, "id must match <LANE>-<DIM>-<NNN>, e.g. V-COLOR-004")
        elif rule["id"] in by_id:
            rep.error(where, "duplicate rule id %r" % rule["id"])

        lane = rule.get("lane")
        if lane not in LANES:
            rep.error(where, "lane must be one of %s, got %r" % (", ".join(LANES), lane))
        elif rule.get("id") and rule["id"][0] != lane:
            rep.error(where, "id prefix %r disagrees with lane %r" % (rule["id"][0], lane))

        statement = rule.get("statement") or ""
        if len(statement) < 10:
            rep.error(where, "statement is missing or too short to be testable")
        elif not statement.rstrip().endswith((".", "!")):
            rep.warn(where, "statement should read as a complete sentence")

        severity = rule.get("severity")
        confidence = rule.get("confidence")
        if severity not in SEVERITY_RANK:
            rep.error(where, "severity must be one of %s, got %r"
                      % (", ".join(SEVERITY_RANK), severity))
        if confidence not in CONFIDENCES:
            rep.error(where, "confidence must be one of %s, got %r"
                      % (", ".join(CONFIDENCES), confidence))

        check = rule.get("check") or {}
        mode = check.get("mode")
        if mode not in MODES:
            rep.error(where, "check.mode must be 'mechanical' or 'rubric', got %r" % mode)
        if mode == "mechanical" and not check.get("kind"):
            rep.error(where, "mechanical check needs a 'kind' (see 02-brain-schema.md)")
        if mode == "rubric" and not check.get("rubric"):
            rep.warn(where, "rubric check has no 'rubric' text; scoring will not be reproducible")

        if severity in ("blocker", "major") and not rule.get("fix_hint"):
            rep.warn(where, "%s rule has no fix_hint; findings will be hard to action" % severity)

        # --- the evidence ceiling -------------------------------------------------
        if severity in SEVERITY_RANK and confidence in CONFIDENCE_CEILING:
            ceiling = CONFIDENCE_CEILING[confidence]
            if SEVERITY_RANK[severity] > SEVERITY_RANK[ceiling]:
                rep.error(where, "severity '%s' exceeds the '%s' ceiling of '%s'. "
                                 "Confirm the rule and re-tag it, or lower the severity."
                          % (severity, ceiling, confidence))

        support = rule.get("support") or {}
        src_ids = support.get("source_ids") or []
        for sid in src_ids:
            if sid not in sources:
                rep.error(where, "support cites unknown source %r" % sid)

        if confidence == "stated":
            if not src_ids:
                rep.error(where, "'stated' rule cites no source_ids")
            else:
                ok = any(
                    sources.get(s, {}).get("rung") in AUTHORITATIVE_RUNGS
                    or sources.get(s, {}).get("type") in EXTERNAL_AUTHORITY_TYPES
                    for s in src_ids
                )
                if not ok:
                    rep.error(where, "'stated' needs a rung 1-4 source or an external authority "
                                     "(regulation/platform_policy); cited sources are lower-rung")

        elif confidence == "inferred":
            count, of = support.get("count"), support.get("of")
            if count is None or of is None:
                rep.error(where, "'inferred' rule needs support.count and support.of")
            else:
                if of <= 0:
                    rep.error(where, "support.of must be > 0")
                else:
                    ratio = count / of
                    if count < INFERRED_MIN_COUNT:
                        rep.error(where, "'inferred' needs count >= %d, got %d"
                                  % (INFERRED_MIN_COUNT, count))
                    if ratio < INFERRED_MIN_RATIO:
                        rep.error(where, "'inferred' needs consistency >= %.0f%%, got %.0f%% (%d/%d)"
                                  % (INFERRED_MIN_RATIO * 100, ratio * 100, count, of))
                    if count > of:
                        rep.error(where, "support.count (%d) exceeds support.of (%d)" % (count, of))
            if not src_ids:
                rep.error(where, "'inferred' rule cites no source_ids")

        elif confidence == "assumed":
            if rule.get("id") not in question_targets:
                rep.error(where, "'assumed' rule needs an open question in open_questions "
                                 "with this id in its 'blocks' list")

        if rule.get("id"):
            by_id[rule["id"]] = rule

    # Brain-level, not per-rule: one missing arbiter is one problem, not N.
    if not owner:
        blockers = [r.get("id") for r in rules if r.get("severity") == "blocker"]
        if blockers:
            rep.error("brand", "brand.owner (the arbiter) is unset, but %d rule(s) carry "
                               "'blocker' severity: %s. Blockers need someone who can confirm them."
                      % (len(blockers), ", ".join(str(b) for b in blockers[:4])))

    return by_id


def check_exemplars(brain, rules, rep):
    ex = brain.get("exemplars") or {}
    positives = ex.get("positive") or []
    negatives = ex.get("negative") or []
    principle_ids = {p.get("id") for p in (brain.get("principles") or [])}
    known = set(rules) | principle_ids

    for bucket, items, key in (("positive", positives, "illustrates"),
                               ("negative", negatives, "violates")):
        for i, item in enumerate(items):
            where = "exemplars.%s[%d]" % (bucket, i)
            if not item.get("id"):
                rep.error(where, "missing id")
            if not item.get("why"):
                rep.error(where, "missing 'why'; an exemplar without a reason teaches nothing")
            if not item.get("uri"):
                rep.warn(where, "no uri; the exemplar cannot be shown to a reviewer")
            for ref in item.get(key) or []:
                if ref not in known:
                    rep.error(where, "%s references unknown rule/principle %r" % (key, ref))

    rubric_rules = [r for r in rules.values() if (r.get("check") or {}).get("mode") == "rubric"]
    if rubric_rules:
        covered = set()
        for item in positives:
            covered.update(item.get("illustrates") or [])
        uncovered = [r["id"] for r in rubric_rules if r["id"] not in covered]
        if uncovered:
            rep.warn("exemplars", "%d rubric rule(s) have no positive exemplar (%s); "
                                  "scoring them is judgement without a reference"
                     % (len(uncovered), ", ".join(sorted(uncovered)[:5])))
    if not negatives:
        rep.warn("exemplars", "no negative exemplars; counter-examples sharpen rules "
                              "more than positives do")


def check_channels(brain, rep):
    today = dt.date.today()
    for i, ch in enumerate(brain.get("channels") or []):
        where = "channels[%d] %s" % (i, ch.get("id", "<no id>"))
        if not ch.get("id"):
            rep.error(where, "missing id")
        if not ch.get("checks"):
            rep.warn(where, "channel has no checks; it cannot gate anything")
        verified = parse_date(ch.get("verified"))
        if not ch.get("verified"):
            rep.warn(where, "never verified against the platform's current spec; "
                            "its rules must stay 'assumed'")
        elif verified and (today - verified).days > CHANNEL_STALE_DAYS:
            rep.warn(where, "spec last verified %s (%d days ago); platform specs drift"
                     % (ch["verified"], (today - verified).days))


def check_questions(brain, rules, rep):
    for i, q in enumerate(brain.get("open_questions") or []):
        where = "open_questions[%d] %s" % (i, q.get("id", "<no id>"))
        if not q.get("question"):
            rep.error(where, "missing question text")
        if q.get("status") not in ("open", "answered", "wontfix"):
            rep.error(where, "status must be open/answered/wontfix, got %r" % q.get("status"))
        for rid in q.get("blocks") or []:
            if rid not in rules:
                rep.warn(where, "blocks unknown rule %r" % rid)
        if q.get("status") == "open" and not q.get("asked_of"):
            rep.warn(where, "open question has no 'asked_of'; nobody owns the answer")


# --------------------------------------------------------------------------- completeness

def completeness(brain, rules):
    """Score how much of the brain is actually populated. Advisory, not pass/fail."""
    scores = {}

    ident = brain.get("identity") or {}
    filled = sum(1 for k in ("positioning", "personality", "anti_personality",
                             "audience", "competitors_avoided") if ident.get(k))
    scores["identity"] = round(filled / 5 * 100)

    lanes = {lane: 0 for lane in LANES}
    for r in rules.values():
        if r.get("lane") in lanes:
            lanes[r["lane"]] += 1
    for lane in LANES:
        # 8 rules per lane is a usable working brain; more is fine, not required.
        scores["lane_" + lane] = min(100, round(lanes[lane] / 8 * 100))

    total = len(rules) or 1
    mech = sum(1 for r in rules.values() if (r.get("check") or {}).get("mode") == "mechanical")
    scores["mechanical_share"] = round(mech / total * 100)

    by_conf = {c: 0 for c in CONFIDENCES}
    for r in rules.values():
        if r.get("confidence") in by_conf:
            by_conf[r["confidence"]] += 1
    scores["stated_share"] = round(by_conf["stated"] / total * 100)

    ex = brain.get("exemplars") or {}
    n_ex = len(ex.get("positive") or []) + len(ex.get("negative") or [])
    scores["exemplars"] = min(100, round(n_ex / 12 * 100))
    scores["channels"] = min(100, round(len(brain.get("channels") or []) / 4 * 100))

    return scores, lanes, by_conf


def grade(scores):
    core = [scores["identity"], scores["exemplars"],
            max(scores["lane_V"], 1), scores["lane_C"], scores["lane_S"]]
    return round(sum(core) / len(core))


# --------------------------------------------------------------------------- output

def render_text(path, rep, scores, lanes, by_conf, n_rules, ok):
    out = []
    out.append("Design brain validation — %s" % path)
    out.append("=" * 60)

    if rep.errors:
        out.append("")
        out.append("ERRORS (%d) — the brain is not safe to use until these are fixed" % len(rep.errors))
        for e in rep.errors:
            out.append("  x [%s] %s" % (e["where"], e["message"]))
    if rep.warnings:
        out.append("")
        out.append("WARNINGS (%d)" % len(rep.warnings))
        for w in rep.warnings:
            out.append("  ! [%s] %s" % (w["where"], w["message"]))

    out.append("")
    out.append("Rules: %d total  ·  V %d · C %d · S %d · G %d"
               % (n_rules, lanes["V"], lanes["C"], lanes["S"], lanes["G"]))
    out.append("Confidence: stated %d · inferred %d · assumed %d"
               % (by_conf["stated"], by_conf["inferred"], by_conf["assumed"]))
    out.append("")
    out.append("Completeness")
    for key in ("identity", "lane_V", "lane_C", "lane_S", "lane_G",
                "mechanical_share", "stated_share", "exemplars", "channels"):
        val = scores[key]
        bar = "#" * (val // 5) + "." * (20 - val // 5)
        out.append("  %-18s %s %3d%%" % (key, bar, val))
    out.append("")
    out.append("Overall: %d%%" % grade(scores))

    if scores["mechanical_share"] < 25 and n_rules >= 8:
        out.append("")
        out.append("Note: only %d%% of rules are mechanically checkable. A brain that is almost all"
                   % scores["mechanical_share"])
        out.append("      judgement is documentation, not QC. Aim for ~40%.")
    if by_conf["stated"] == 0 and n_rules:
        out.append("")
        out.append("Note: no 'stated' rules, so nothing can block. This brain advises only.")
        out.append("      A 30-minute brand-owner interview is the cheapest way to change that.")

    out.append("")
    out.append("RESULT: %s" % ("PASS" if ok else "FAIL"))
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Validate a design brain.")
    ap.add_argument("brain", help="path to brain.json")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = ap.parse_args()

    try:
        with open(args.brain, "r", encoding="utf-8") as fh:
            brain = json.load(fh)
    except FileNotFoundError:
        print("cannot read %s: no such file" % args.brain, file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print("cannot parse %s: %s" % (args.brain, exc), file=sys.stderr)
        return 2

    if not isinstance(brain, dict):
        print("cannot validate %s: top level must be an object" % args.brain, file=sys.stderr)
        return 2

    rep = Report()
    check_structure(brain, rep)
    sources = check_sources(brain, rep)
    rules = check_rules(brain, sources, rep)
    check_exemplars(brain, rules, rep)
    check_channels(brain, rep)
    check_questions(brain, rules, rep)

    scores, lanes, by_conf = completeness(brain, rules)
    ok = not rep.errors and not (args.strict and rep.warnings)

    if args.json:
        print(json.dumps({
            "ok": ok,
            "brain": args.brain,
            "errors": rep.errors,
            "warnings": rep.warnings,
            "rules": {"total": len(rules), "by_lane": lanes, "by_confidence": by_conf},
            "completeness": scores,
            "overall": grade(scores),
        }, indent=2))
    else:
        print(render_text(args.brain, rep, scores, lanes, by_conf, len(rules), ok))

    return 0 if ok else 1


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
