# Agent Prompt: Git workflow — segregate internal/QMS work from production code commits

## Audience

You are a **developer agent** (or human dev) implementing a **durable Git workflow** for the **SilqeQMS** repository (`Ethan-Rao/SilqeQMS` on GitHub). The product owner needs:

1. **Separated history and pushes** — internal QMS work (editing guides, readable-text extractions, design-assessment prompts, auditor CSVs, `QMSInProcess/` mirror docs, etc.) must not be mixed on the same integration path as **application changes** (`app/`, migrations, tests that gate deploy) unless intentionally merged.
2. **A stable “configuration item” designation for validation reports** — SW.SLQ010 / SW.SLQ011 / SW.SLQ012 and similar records must cite **one unambiguous Git reference** (SHA and/or tag) for the **validated SilqQMS build**, which may differ from the tip of branches used for day-to-day internal documentation work.
3. **Compatibility with Cursor agents** — humans and agents continue to work in clones of the same repo; the workflow must be **documented**, **scriptable**, and **hard to do wrong** (branch names, push targets, when to tag).

This prompt is the **implementation charter**. When you finish, you must hand the owner a **single, copy-paste-ready “designation line”** (format below) and any **branch/tag names** you instituted.

---

## Current baseline (verify, do not assume)

Before changing anything:

1. Record **which Git branch** DigitalOcean App Platform deploys from (almost certainly `main`).
2. Confirm `origin` remote URL and that **GitHub branch protection** (if any) applies to `main`.
3. List recent commits that are **docs-only** vs **code** to illustrate the problem for the owner in your final report.

---

## Design goals (required)

| Goal | Success criterion |
|------|-------------------|
| **G1 — Deploy safety** | Pushes that **only** add or change internal paths **do not** trigger a production deploy **unless** the owner intentionally merges them into the deploy branch. |
| **G2 — Traceability** | Validation documents cite a **tag or SHA** that **points to the exact commit** that was tested in production (or in the formal validation environment), not “whatever is latest on an internal branch.” |
| **G3 — Low ceremony for agents** | A short **runbook** (≤ 1 page) tells humans/agents: “create branch X from Y, push here, open PR there.” |
| **G4 — Single owner-facing designation** | Owner can paste **one line** into Word/PDF reports without interpreting Git internals. |

---

## Recommended strategy (implement unless you document a better alternative)

Use **two long-lived integration lines** plus **annotated validation tags**:

### A. Branch: `main` (deploy / product code)

- **Purpose:** Application code, tests, deployment config, and any documentation that **must** ship with the runtime (e.g. `README`, operational runbooks linked from deploy).
- **Rule:** DigitalOcean (or CI) **only** auto-deploys from **`main`** (keep `main` as production branch unless the owner explicitly chooses another name—if you rename, update DO and this doc).

### B. Branch: `internal` (default for QMS / design-assessment / extractions)

- **Purpose:** Commits touching paths such as:

  - `docs/design-assessment/**`
  - `docs/QMS-Readable-Texts/**` (where used only for human-readable mirrors, not runtime)
  - `QMSInProcess/**` (if tracked)
  - Large static QMS extracts, auditor lists, prompts, editing guides **not required** to run the app

- **Rule:** All **internal-only** agent work **lands here first** via PR or direct push (per team preference). **`internal` is never connected to the DO deploy trigger.**

- **Creation (one-time):**

  ```bash
  git fetch origin
  git checkout main
  git pull origin main
  git checkout -b internal
  git push -u origin internal
  ```

- **Ongoing:** Periodically merge **`main` → `internal`** (fast-forward or merge commit) so internal docs stay aligned with the current codebase **without** pushing internal commits to `main`.

### C. Validation tags (immutable configuration item)

When the owner **freezes** a build for SW.SLQ010 execution (or after successful run), create an **annotated tag** on the **`main` commit** that was deployed and tested—not on `internal`.

**Naming convention (propose defaults; adjust with owner):**

- `validated/silqqms-YYYY-MM-DD`  
  or  
- `validated/silqqms-vMAJOR.MINOR.PATCH`

**Example:**

```bash
git checkout main
git pull origin main
git tag -a validated/silqqms-2026-05-08 -m "SilqQMS configuration item for DC.SLQ002 SW.SLQ010--012; deployed production build."
git push origin validated/silqqms-2026-05-08
```

**Rule:** Tags are **immutable**. If a build is retested after a code fix, create a **new** tag (new date or patch), never move the old tag.

### D. Optional: selective promotion `internal` → `main`

If the owner wants **some** internal artifacts versioned on `main` (e.g. `scripts/refresh_dc_slq002_readable_texts.py`), use **small, reviewed PRs** from `internal` to `main` that touch **only** agreed paths—or maintain those scripts on `main` and keep bulky docs only on `internal`. **Document the chosen rule** in the runbook.

---

## “Designation for reports” (mandatory deliverable)

When implementation is complete, produce a short artifact the owner can file next to the editing guides, for example:

`docs/design-assessment/Output/VALIDATED_CONFIGURATION_ITEM_DESIGNATION.md`

It must contain **exactly this structure** (fill in real values):

```markdown
# Validated SilqQMS configuration item (Git)

**Use the following as a single block in SW.SLQ010 / SW.SLQ011 / SW.SLQ012 (and DC.SLQ002 narrative where applicable):**

> SilqQMS validated software configuration: Git **annotated tag** `validated/silqqms-YYYY-MM-DD` → commit **`<full-40-char-sha>`** (`<short-7>`), branch **`main`**, repository **https://github.com/Ethan-Rao/SilqeQMS**.

**Verify anytime:**

`git fetch --tags && git rev-parse validated/silqqms-YYYY-MM-DD^{}`

**Deployment:** DigitalOcean App Platform deploys from branch **`main`** at commit `<short-7>` matching this tag at time of validation.

**Internal docs branch:** Active QMS/documentation work may continue on branch **`internal`** and does not change this designation until a new validation tag is created on a new `main` commit.
```

**You must** compute and paste the **real** tag name and **full SHA** that existed at the end of your work (or the tag the owner asked you to record). If validation has **not** run yet, create the file with **TBD** for tag/SHA but **fully specify** the **exact format** and the **commands** the owner will run to fill it in.

---

## DigitalOcean checklist

- [ ] Confirm deploy source branch (**`main`** only).
- [ ] Confirm **`internal`** is **not** listed as a deploy branch.
- [ ] If “Deploy on push” is enabled for all branches, **restrict** to `main` (DO UI: component → settings → sources / branch).
- [ ] Document for the owner where to see **which commit** is live in production (DO runtime **App** → **Deployments** → commit SHA if GitHub-linked).

---

## GitHub settings checklist

- [ ] Branch protection on `main` (optional but recommended): require PR, require passing checks.
- [ ] `internal` may remain unprotected for speed, or use loose protection—**document choice**.
- [ ] Add a **short repo README section** or `docs/design-assessment/Resources/GIT_BRANCH_RUNBOOK.md` linked from the main README **only if** the owner approves touching root README (otherwise put runbook under `docs/design-assessment/` only).

---

## Agent / human collaboration rules (document in runbook)

1. **Code change or test change** → branch from **`main`**, PR to **`main`**, deploy as today.
2. **Editing guides, prompts, QMS readable extracts, auditor CSV refresh** → branch from **`internal`** (or from `main` then merge target `internal`), push to **`internal`**.
3. **Never** cite the tip of **`internal`** as the validated build in a regulatory document.
4. **Always** cite the **annotated tag** (plus expanded SHA) for the **`main`** commit that was under test.
5. After merging code to `main` and deploying, **update `internal`** with `git merge main` on `internal` so agents see latest code.

---

## Implementation tasks (your checklist)

- [ ] Verify DO + GitHub baseline; note deploy branch.
- [ ] Create **`internal`** from current `main`, push to `origin`.
- [ ] Add **`VALIDATED_CONFIGURATION_ITEM_DESIGNATION.md`** (or update if tag pre-exists) with the canonical report wording.
- [ ] Add **`GIT_BRANCH_RUNBOOK.md`** (≤ 1 page) under `docs/design-assessment/Resources/` with branch diagram + commands.
- [ ] If helpful, add a tiny script `scripts/git_show_validation_designation.sh` or `.ps1` that prints the tag → SHA line for the latest `validated/silqqms-*` tag (**optional**).
- [ ] Open a brief summary for the owner listing: branch names, DO change(s), tag naming rule, and the **exact designation string** to paste into reports.

---

## Constraints

- Do **not** force-push to **`main`** or **rewrite** public history unless the owner explicitly authorizes it.
- Do **not** move **annotated validation tags** after publication to stakeholders.
- Prefer **minimal** file churn outside `docs/` and Git configuration; do **not** refactor application code in this task.

---

## Final handoff to the product owner (required)

Close your work with a message that includes:

1. **Branches:** roles of `main` and `internal`.
2. **Deploy:** confirmation that only `main` triggers production.
3. **Report designation:** the **single formatted block** from `VALIDATED_CONFIGURATION_ITEM_DESIGNATION.md` (or TBD + fill-in steps).
4. **Next action for the owner:** create the first real **`validated/silqqms-…`** tag immediately after the next production deploy they intend to test under SW.SLQ010.

That designation block is the **“correct designation to use on the reports”** the owner requested.
