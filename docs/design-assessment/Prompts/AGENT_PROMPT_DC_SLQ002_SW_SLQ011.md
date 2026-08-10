# Agent Prompt: SW.SLQ011 A Software Validation Report, SilqQMS

## Naming note

The controlled document ID is **SW.SLQ011** (*Software* validation report). If you see **SQ.SLQ011** in informal notes, treat it as this same deliverable.

## Project context

You are working on **DC.SLQ002 -- SilqQMS EDMS Transition**, a design control project at Silq Technologies Corporation. This project covers software verification and validation of **SilqQMS** (a custom web-based EDMS) and the controlled transition of SILQ QMS document operations from FileHold to SilqQMS.

The runnable system lives in this workspace under `app/eqms/` (Flask/Python). It is deployed on **DigitalOcean App Platform** with PostgreSQL and S3-compatible object storage. Regulatory records are authored and approved outside SilqQMS (paper-based approvals per QM.SLQ001) and published into SilqQMS for controlled storage, revision control, and retrieval.

Validation is conducted per **QM.SLQ032 A** (Software Validation SOP) and is documented in the **SW.SLQ007--012** deliverable series for SilqQMS.

## Assumption for this assignment

**SW.SLQ010 A Software Verification Test Procedure, SilqQMS** has been **executed and closed without issues**: all manual test cases passed, supplementary automated ( pytest ) evidence was collected as planned, and the executed procedure is available to cite as an attachment in the validation report.

Do **not** re-open SW.SLQ010 findings unless you are documenting something explicitly supplied by the user (e.g., a deviation memo). Default narrative: verification results support a **PASS** validation conclusion for the configured SilqQMS build.

## Current status of SW.SLQ007--012 (readable texts)

The following are available as Markdown readable text under `docs/QMS-Readable-Texts/12-DHF-Software/` (refresh from `QMSInProcess/DC.SLQ002/` using `python scripts/refresh_dc_slq002_readable_texts.py` if a source document is newer):

| Document | Title | Status (for this prompt) | Readable text path |
|---|---|---|---|
| SW.SLQ007 A | Software Validation Plan, SilqQMS | Complete | `docs/QMS-Readable-Texts/12-DHF-Software/SW.SLQ007 A Software Validation Plan, SilqQMS.md` |
| SW.SLQ008 A | Product Requirements Specification, SilqQMS | Complete | `docs/QMS-Readable-Texts/12-DHF-Software/SW.SLQ008 A Product Requirements Specification, SilqQMS.md` |
| SW.SLQ009 A | Software Verification Test Plan, SilqQMS | Complete | `docs/QMS-Readable-Texts/12-DHF-Software/SW.SLQ009 A Software Verification Test Plan, SIlqQMS.md` |
| SW.SLQ010 A | Software Verification Test Procedure, SilqQMS | **Complete (no issues)** | `docs/QMS-Readable-Texts/12-DHF-Software/SW.SLQ010 A Software Verification Test Procedure, SilqQMS.md` |
| SW.SLQ011 A | Software Validation Report, SilqQMS | Complete (readable text) | `docs/QMS-Readable-Texts/12-DHF-Software/SW.SLQ011 A Software Validation Report, SilqQMS.md` |
| SW.SLQ012 A | Requirements Traceability Matrix, SilqQMS | Complete (readable text) | `docs/QMS-Readable-Texts/12-DHF-Software/SW.SLQ012 A Requirements Traceability Matrix, SilqQMS.md` |

**Prior EDMS structural model (FileHold):** `docs/QMS-Readable-Texts/12-DHF-Software/SW.SLQ005 A Software Validation Report, FileHold.md` -- use for section flow and attachment pattern; replace FileHold IDs with SilqQMS SW.SLQ007--010 IDs.

## Your task

Draft an **editing guide** for **SW.SLQ011 A Software Validation Report, SilqQMS**.

Save it to:

`docs/design-assessment/Output/SW_SLQ011_SOFTWARE_VALIDATION_REPORT_EDITING_GUIDE.md`

The guide must tell a document owner exactly **what sections to add or change**, **what evidence to attach**, and **how to phrase conclusions** so that SW.SLQ011 is consistent with:

- SW.SLQ007 (plan: verification + known-issues analysis + conclusions),
- SW.SLQ008/009 (requirements and test coverage),
- SW.SLQ010 (executed procedure and per-test-case outcomes),
- QM.SLQ032 (software validation expectations).

## What SW.SLQ011 should cover (minimum expectations)

Follow SW.SLQ007 and mirror SW.SLQ005-style structure unless the team’s approved template differs:

1. **Executive summary** -- One-paragraph statement of scope, system version tested, and overall validation outcome (**PASS**, assuming SW.SLQ010 clean closure unless user states otherwise).

2. **System under validation** -- SilqQMS identity, deployment environment (production vs validation), and **configuration item** identity (release tag, Git commit SHA, and/or build identifier recorded on the SW.SLQ010 cover page).

3. **Reference documents** -- SW.SLQ007, SW.SLQ008, SW.SLQ009, SW.SLQ010 (executed), SW.SLQ012 when available, QM.SLQ032, QM.SLQ001 as applicable.

4. **Deviations** -- Explicit statement of none, or table of deviation ID / description / impact / disposition (default: none).

5. **Verification results summary** -- Summarize verification test case outcomes from SW.SLQ009/SW.SLQ010; map to SRS clauses in SW.SLQ008 at a high level. Mention **supplementary automated test evidence** (pytest outputs, CI logs, or archived HTML reports) only as *supporting* evidence, consistent with SW.SLQ009 language.

6. **Known issues / risk analysis of residual software anomalies** -- Per SW.SLQ007: review release notes, issue trackers, or dependency advisories relevant to the pinned stack. If none apply, document the negative search and conclusion (mirroring SW.SLQ005’s “known issues” subsection).

7. **Conclusion** -- Formal statement that SilqQMS **Version / configuration [X]** is validated for **intended use** described in SW.SLQ008/SW.SLQ007, subject to any documented deviations (default: unconditional PASS).

8. **Attachments** -- Numbered list matching executed records: e.g. Attachment 1 = verification summary table; Attachment 2 = executed SW.SLQ010; Attachment 3 = pytest (or supplementary) evidence package; Attachment 4 = known-issues technical review (if performed).

## Codebase touchpoints (for accurate language)

You do **not** need to re-validate code, but the guide should name the correct modules so document editors link evidence to the right behavior:

- Document Control: `app/eqms/modules/document_control/`
- Admin Docs libraries: `app/eqms/modules/admin_docs/`
- Authentication / session / rate limits: `app/eqms/auth.py`
- CSRF / headers: `app/eqms/security.py`
- Audit trail model and UI: `app/eqms/models.py` (AuditEvent), `app/eqms/templates/admin/audit/`

Point reviewers to automated tests under `tests/` that are already cited from SW.SLQ009/SW.SLQ010 guidance (e.g., `tests/test_document_control.py`, `tests/test_edms_improvements.py`) so SW.SLQ011 references are consistent.

## Output quality bar

- Use complete sentences; avoid ambiguous “update as needed” without naming the field or section.
- Call out **exact filenames** in `docs/QMS-Readable-Texts/12-DHF-Software/` to pull quoted language from.
- Keep the editing guide **shorter than a full procedure** but **specific enough** that a new technical writer could revise a blank SW.SLQ011 docx in one pass.

## Do not

- Do not fabricate test failures or CAPAs.
- Do not treat automated tests as replacing manual SW.SLQ010 execution.
- Do not change application code unless asked in a separate task; this assignment is documentation strategy only.

---

When finished, print the absolute path of the editing guide you created and a one-line summary of the recommended attachment list for SW.SLQ011.
