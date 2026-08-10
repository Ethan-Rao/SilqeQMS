# Phase 3 — Prompt 22: Quality Planning Page Redesign + Design & Development Records Accordion

## Context

Three independent work streams:
- Task A (code): add Design & Development Records to the accordion library set
- Task B (code): redesign the Quality Planning page with 4 objectives, Q3 scorecard, and a reports archive section
- Tasks C/D/E (coordinator-run scripts, not committed): folder restructure and PDF upload

---

## Task A — Accordion for Design & Development Records

In `app/eqms/modules/admin_docs/admin.py`, add `"dhfs"` to `ACCORDION_LIBRARIES`:

```python
ACCORDION_LIBRARIES: frozenset[str] = frozenset({
    "management_reviews",
    "post_market_surveillance",
    "risk_management",
    "dhfs",  # Design & Development Records
})
```

No template changes needed — the `accordion.html` template is already in place.
Add one test: `GET /admin/dhfs` returns 200 and contains `<details` for admin and staff.

---

## Task B — Quality Planning page redesign

The current page at `GET /admin/quality-objectives` (`admin.quality_objectives`)
shows 5 quality objectives with a manual entry form. This prompt replaces it with a
three-section page.

### B1 — Quality Objectives (4 objectives, remove Employee Training)

Remove Objective 4 (Employee Training Program: ≥ 10 activities/year). The
auto-compute of `training_acknowledged_this_year` is no longer needed and can be
removed. The remaining objectives — renumbered 1–4 — are:

1. **Incoming Material Quality** — lot acceptance rate ≥ 90%
2. **Finished Product Complaint Rate** — < 1% of distributed product
3. **Active Post-Market Surveillance Activities** — ≥ 12 per year
4. **Quarterly Quality Plan Execution** — ≥ 80% of action items on-schedule, min 5 tracked

For each objective, store the current-period value and a brief notes field in
`system_settings` (key: `quality_objectives`, same JSON blob as before but with 4 items).

**Q2 2026 default values** — pre-populate these as defaults when system_settings is
empty (i.e., never saved yet). Display a `data-period="Q2 2026"` attribute or a
"Last recorded: Q2 2026" note next to each value:

| # | Current Value | Period | Notes |
|---|---|---|---|
| 1 | N/A — no lots received | Q2 2026 | Tracking resumes at next material receipt |
| 2 | 0% (0 complaints) | Q2 2026 | Target: <1% — on track |
| 3 | 3 of 12 activities YTD | Q2 2026 | On pace for annual target (3/qtr) |
| 4 | 92% (12/13 items) | Q2 2026 | Q2 execution rate — exceeds 80% target |

Admin users can save updated values at any time. Staff see a read-only view.

### B2 — Q3 2026 Quality Plan Scorecard section

Add a new collapsible section below the objectives titled
**"Q3 2026 Quality Plan Scorecard"** (uses `<details open>` so it starts expanded).

Store the scorecard as a JSON list under `system_settings` key `quality_plan_scorecard`.
If this key is absent, pre-populate it with the Q3 2026 action items below.

Admin-only: an "Edit Scorecard" button leads to a simple textarea where the JSON can
be updated (or a table-editor if straightforward — textarea fallback is fine).

**Pre-populate with the following Q3 2026 action items** (columns: item, owner, target,
status, notes). Status values: `Complete`, `In Progress`, `Deferred`, `Not Yet Due`,
`Needs Follow-Up`. Render status as a coloured badge:
- `Complete` → success/green
- `In Progress` → info/blue
- `Deferred` → warning/yellow
- `Not Yet Due` → neutral/grey
- `Needs Follow-Up` → danger/red

Action items (from Q2 2026 Quality Report, Section 6 scorecard):

| Item | Owner | Target | Status | Notes |
|---|---|---|---|---|
| QMSR Supplementary Provision Mapping | Ethan Rao | Q2 2026 | Complete | Completed via DCO094 (QM.SLQ027 Rev F) |
| Medical Device File Framework | Ethan Rao | Q2 2026 | Complete | Completed via DCO094 (QM.SLQ027 and QM.SLQ048) |
| QMS Platform Transition DC.SLQ002 | Ethan Rao | Per schedule | In Progress | Procedure revisions complete (DCO091-095); file migration underway |
| Systemic Legacy Part 820 References | Ethan Rao | Q3 2026 | Not Yet Due | Substantially addressed through DCO091-095; final confirmation at Q3 |
| Quality Objectives — Revise Existing | Ethan Rao | Q2 2026 | Complete | Completed via DCO094 (QM.SLQ037 Rev B); thresholds tightened |
| Quality Objectives — Add Three New | Ethan Rao | Q2 2026 | Complete | Completed via DCO094; PMS, training, and QP-execution objectives added |
| New Hire Training — Haley Shomo | Ethan Rao | Q3 2026 | Deferred | All training activities moved to Q3 per management direction |
| QMSR Transition Training | Ethan Rao | Q3 2026 | Deferred | All training activities moved to Q3 per management direction |
| Regulatory Reference Materials (AAMI/ISO 13485 Guide) | Verne Sharma | Q2 2026 | Complete | AAMI/ISO 13485:2016 Practical Guide and regulatory standards purchased |
| Design Control Retraining (CAPA 2025-003 effectiveness confirmation) | Ethan Rao | Q3 2026 | Deferred | Training execution moved to Q3; this is the effectiveness confirmation for CAPA 2025-003 |
| Complaint and MDR Escalation Pathway | Ethan Rao | Q2 2026 | Complete | Completed via DCO093 (QM.SLQ021 cross-reference section) |
| Valve Modification Design Assessment (DC.SLQ001) | Ethan Rao | Q2 2026 | Complete | Design review signed; Letter to File finalized; project closed |
| Design Control Procedure Revisions (CAPA 2025-003) | Ethan Rao | Q2 2026 | Complete | Completed via DCO095 (QM.SLQ052 Pathway C mandatory supplier trigger) |
| Supplier Audit — Pathway MedTech | Ethan Rao | Q4 2026 | Not Yet Due | On-site audit scheduled for Q4 |
| Feedback Governance Procedure | Ethan Rao | Q2 2026 | Complete | Completed via DCO094 (QM.SLQ033 feedback governance section) |
| Active Post-Market Surveillance Program (formal establishment) | Ethan Rao | Q3 2026 | Needs Follow-Up | Formal program establishment not completed in Q2; active surveillance activities underway (3 YTD); carried to Q3 |
| Complaint Non-Investigation Rationale | Ethan Rao | Q2 2026 | Complete | Completed via DCO093 (QM.SLQ021) |
| Regulatory Reporting QMSR Framing | Ethan Rao | Q2 2026 | Complete | Completed via DCO093 (QM.SLQ022 and QM.SLQ030) |
| CAPA 2025-001 Effectiveness Confirmation | Ethan Rao | Nov 2026 | Not Yet Due | Monitoring complaints through November 2026 |
| CAPA 2025-002 Effectiveness Confirmation | Ethan Rao | Dec 2026 | Not Yet Due | Evaluating complaints through December 2026 |
| CAPA 2025-003 Corrective Action Completion | Ethan Rao | Q3 2026 | In Progress | Procedure revisions and DC.SLQ001 complete; retraining deferred to Q3 |
| Post-Production Risk File Update Triggers | Ethan Rao | Q3 2026 | Not Yet Due | Decision framework added to QM.SLQ012 via DCO093; Q3 review |
| Failure Mode and Probability Rating Review | Ethan Rao | Q2 2026 | Complete | RM-0018 through RM-0021 and related files reviewed against complaint history |
| ASTM F623-25 Risk Management Alignment | Ethan Rao | Q3 2026 | Not Yet Due | Risk management policy evaluation and update |
| Packaging Inspection for ASTM F1886 | Ethan Rao | Q2 2026 | Complete | Visual inspection of existing finished goods completed; compliance confirmed |
| Gage R&R Study (UV and Rinse Test) | Ethan Rao | Upon next production | Not Yet Due | Timing dependent on next C.SLQ001 production run |
| UV Spectroscopy Test Protocol Development | Na He | Q3 2026 | Not Yet Due | Protocol development for incoming and finished catheter analysis |
| Dynamic Employee Training Program | Ethan Rao | Q3 2026 | Not Yet Due | Comprehension-based training assessment program |

### B3 — Quality Plans & Reports section

Add a third section at the bottom of the page titled **"Quality Plans & Reports"**,
visible to all `admin.view` users (staff + admin).

This section queries `AdminDocFile` records from the `management_reviews` library
where the file belongs to a folder named `"Quality Planning"` (match by folder name,
not hardcoded ID). Render as a simple list of files with view and download links,
ordered by `uploaded_at` descending (most recent first). Empty-state: "No quality
plan documents uploaded yet."

This is a read-only query (1–2 extra queries). No new routes needed — use the
existing `admin_docs.admin_docs_document_view` and
`admin_docs.admin_docs_document_download` endpoints.

### B4 — Page layout summary

The redesigned page at `/admin/quality-objectives` renders three sections:

1. **Quality Objectives** — 4 objectives with progress values and a save form (admin)
   or read-only view (staff). Breadcrumb: Dashboard / Quality Planning.
2. **Q3 2026 Quality Plan Scorecard** — full action item table with status badges.
   Admin sees an "Edit Scorecard" button. Staff sees read-only.
3. **Quality Plans & Reports** — links to PDFs/documents from the management_reviews
   Quality Planning folder. Viewable inline for PDFs.

---

## Tasks C, D, E — Coordinator-run scripts (gitignored, not committed)

### Task C — `scripts/_restructure_ddr_folders.py`

Two folder changes in the `dhfs` library (DB only, no S3 operations):

1. Find the top-level folder named `"DHF"` in `dhfs`. Rename it to
   `"Design History File"`.
2. Find the top-level folder named `"SLQ-DHF"` in `dhfs`. Rename it to
   `"Pathway MedTech DHF Documents"` AND set its `parent_id` to the id of the
   `"Design History File"` folder (making it a child of that folder).

Include the standard `DRY_RUN = True` guard with `--execute` flag.

### Task D — `scripts/_delete_rm_subfolders.py`

Delete the 5 empty product subfolders created in the Risk Management library during the
earlier folder-setup script. Find them by name under the `risk_management` library:
`"C.SLQ001 Pathway Catheter"`, `"SLQ-211410SPT"`, `"SLQ-211610SPT"`,
`"SLQ-211810SPT"`, `"General"`.

Before deleting each folder: verify it has zero files and zero child folders.
If any folder is non-empty, skip it and print a warning — do not delete.
Include the standard `DRY_RUN = True` guard.

### Task E — `scripts/_upload_quality_pdfs.py`

Upload the two PDF files at the workspace root into the `management_reviews` library,
inside the folder named `"Quality Planning"` (look up by name, not hardcoded ID).

Files to upload:
- `2026 Silq Quality Plan.pdf`
- `Silq Q2 2026 Quality Report.pdf`

Use the existing `upload_document` service with the S3-backed storage. Include the
standard env-var setup pattern used in previous upload scripts
(`S3_ACCESS_KEY_ID=[REDACTED_SPACES_KEY]`, `S3_SECRET_ACCESS_KEY=[REDACTED_SPACES_SECRET]
Skip any file that already exists by filename in the target folder (idempotent).
Include the standard `DRY_RUN = True` guard.

---

## Deploy Discipline

- Tasks A and B: code only, no migration.
- Tasks C, D, E: coordinator-run scripts, not committed.
- Full test suite must pass. Single migration head unchanged. Import guard passes.

Tests to add (`tests/test_p22_quality_planning.py`):
- `GET /admin/dhfs` contains `<details` (accordion active).
- `GET /admin/quality-objectives` returns 200 for admin and staff.
- Response does NOT contain "Employee Training Program" (Obj 4 removed).
- Response contains "Incoming Material Quality" and "Active Post-Market Surveillance".
- Response contains "Needs Follow-Up" (scorecard badge present).
- Staff user gets 200 on the page (read-only access confirmed).
- Admin POST to save objectives updates system_settings (200 + redirect).

---

## Deliverables

1. Design & Development Records uses accordion view (Task A deployed).
2. Quality Planning page shows 4 objectives (Q2 defaults), Q3 scorecard table, and
   reports archive (Task B deployed).
3. DHF → "Design History File"; SLQ-DHF → "Pathway MedTech DHF Documents" inside it
   (coordinator runs Task C).
4. 5 empty RM subfolders deleted (coordinator runs Task D).
5. Both quality PDFs uploaded to management_reviews / Quality Planning folder
   (coordinator runs Task E).
6. Full suite green; coordinator confirms Quality Planning page and DHF accordion on
   the live site before Prompt 23.
