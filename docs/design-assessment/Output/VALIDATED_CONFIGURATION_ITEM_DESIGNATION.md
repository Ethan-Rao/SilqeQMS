# Validated SilqQMS configuration item (Git)

**Use the following as a single block in SW.SLQ010 / SW.SLQ011 / SW.SLQ012 (and DC.SLQ002 narrative where applicable):**

> SilqQMS validated software configuration: Git **annotated tag** `validated/silqqms-TBD` → commit **`<full-40-char-sha-TBD>`** (`<short-7-TBD>`), branch **`main`**, repository **https://github.com/Ethan-Rao/SilqeQMS**.

**Status:** No validation freeze tag has been recorded yet. Replace **TBD** values after the next deployment intended for SW.SLQ010 execution using the ceremony in [`GIT_BRANCH_RUNBOOK.md`](../Resources/GIT_BRANCH_RUNBOOK.md) (tagging section).

**Verify anytime (after tag exists):**

```bash
git fetch --tags && git rev-parse validated/silqqms-YYYY-MM-DD^{}
```

Use the actual tag name you created (for example `validated/silqqms-2026-05-08`). The command prints the full commit SHA the tag points to.

**Deployment:** DigitalOcean App Platform is expected to deploy from branch **`main`** at the commit matching this tag at time of validation. Confirm in the App Platform UI that **only `main`** triggers production builds and compare the **Deployments** tab commit SHA to `git rev-parse validated/silqqms-YYYY-MM-DD^{}` after tagging.

**Internal docs branch:** Active QMS/documentation work may continue on branch **`internal`** and does not change this designation until a new validation tag is created on a new `main` commit.

---

## Owner fill-in after freeze

When SW.SLQ010 execution references a specific deployed build:

1. Confirm DigitalOcean **live deployment** commit SHA matches the intended **`main`** commit.
2. On a clean **`main`** checkout at that commit:

   ```bash
   git checkout main
   git pull origin main
   git tag -a validated/silqqms-YYYY-MM-DD -m "SilqQMS DC.SLQ002 configuration item; SW.SLQ010/SW.SLQ011 scope."
   git push origin validated/silqqms-YYYY-MM-DD
   ```

3. Replace the blockquote above with real values, for example:

> SilqQMS validated software configuration: Git **annotated tag** `validated/silqqms-2026-05-08` → commit **`a37faac…`** (`a37faac`), branch **`main`**, repository **https://github.com/Ethan-Rao/SilqeQMS**.

(Use the **full 40-character SHA** from `git rev-parse`; shorten only for display where the procedure allows.)
