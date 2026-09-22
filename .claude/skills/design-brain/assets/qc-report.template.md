# QC Report — {{asset}}

**Verdict: {{VERDICT}}**  ·  {{n}} blockers, {{n}} majors, {{n}} minors
Brain: `{{brand_slug}}` v{{brain_version}} ({{brain_updated}}, scope: {{scope}})
Asset: {{asset_type}} · {{channel}} · {{stage}} · {{generated ? "AI-generated" : "not generated"}}
Checked: {{date}} · Lanes run: {{lanes}}

---

## Blockers — must fix before ship

### 1. {{rule_id}} — {{short}}
**Observed.** {{observed}}
**Where.** {{location}}
**Fix.** {{fix}}

---

## Majors — fix before ship

### 1. {{rule_id}} — {{short}}
**Observed.** {{observed}}
**Where.** {{location}}
**Fix.** {{fix}}

---

## Minors — advisory

- **{{rule_id}}** {{observed}} → {{fix}}

---

## Observations

Not defects. No rule covers these; they do not affect the verdict.

- {{note}}

---

## Not checked

- **{{what}}** — {{why}}

---

## Lane scores

| Lane | Score | Rules run | Findings |
|---|---|---|---|
| V Visual | {{score}} | {{n}} | {{n}} |
| C Copy | {{score}} | {{n}} | {{n}} |
| S Spec | {{score}} | {{n}} | {{n}} |
| G Generative | n/a | — | — |

Scores are for trending only. The verdict is set by the severity gate, not by the scores.

---

<sub>Brain `{{brand_slug}}` v{{brain_version}} · {{n_rules}} rules · arbiter {{owner}}</sub>
