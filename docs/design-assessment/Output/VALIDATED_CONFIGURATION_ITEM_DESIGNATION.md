# Validated SilqQMS configuration item (Git)

**Use the following as a single block in SW.SLQ010 / SW.SLQ011 / SW.SLQ012 (and DC.SLQ002 narrative where applicable):**

> SilqQMS validated software configuration: Git **annotated tag** `validated/silqqms-2026-05-08` → commit **`79aaa9ade016e0e19b6983d1e05a04518243126c`** (`79aaa9a`), branch **`main`**, repository **https://github.com/Ethan-Rao/SilqeQMS**.

**Status:** **Frozen** — annotated tag `validated/silqqms-2026-05-08` points at **`main`** commit `79aaa9a` (full SHA above) and has been **pushed to `origin`**. This matches the DigitalOcean App Platform deployment snapshot discussed for SW.SLQ010 execution.

**Verify anytime:**

```bash
git fetch --tags && git rev-parse validated/silqqms-2026-05-08^{}
```

Expected output (single line, 40 hex chars):

`79aaa9ade016e0e19b6983d1e05a04518243126c`

PowerShell (repository root):

```powershell
.\scripts\git_show_validation_designation.ps1
```

**Deployment:** DigitalOcean App Platform deploys from branch **`main`**. After each deploy, confirm the **Deployments** tab commit SHA still matches this designation before citing it on controlled records; if **`main`** advances and production moves, create a **new** tag (do not move this one).

**Internal docs branch:** Active QMS/documentation work may continue on branch **`internal`** and does not change this designation until a new validation tag is created on a new **`main`** commit.

---

## Future validation cycles

When `main` advances and a **new** configuration item must be recorded:

1. Confirm DigitalOcean **live deployment** commit SHA matches the intended **`main`** commit.
2. Create a **new** annotated tag (new date or version suffix); never force-move `validated/silqqms-2026-05-08`.
3. Update this file’s blockquote or add a dated subsection per QM.SLQ001 / project practice.

```bash
git checkout main
git pull origin main
git tag -a validated/silqqms-YYYY-MM-DD -m "SilqQMS DC.SLQ002 configuration item; SW.SLQ010/SW.SLQ011 scope."
git push origin validated/silqqms-YYYY-MM-DD
```

Ceremony details: [`../Resources/GIT_BRANCH_RUNBOOK.md`](../Resources/GIT_BRANCH_RUNBOOK.md).
