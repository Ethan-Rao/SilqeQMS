# DCO091 — Document package (editing guides)

This folder holds editing guides for the controlled Word revisions released together on DCO091 in `QMSInProcess\DCO091`. The DCO combines:

1. Silq eQMS transition edits for QM.SLQ001, QM.SLQ014, and FM1-QM.SLQ014 (per the design-assessment guides referenced below).
2. NC #15 closure — effective date model (per-row calendar dates, release versus effective, originator attestation, no automatic three-day default) per `MASTER_EFFECTIVE_DATE_NC15_EDITING_GUIDE.md`.

## Reviewer package before FM1 layout is approved

To send **DCO091** to approvers while the change order form is still **FM1-QM.SLQ001 Rev A**, use the paste-ready narrative and checklist in:

`docs/DCO091/DCO091_REVIEW_PACKAGE_FM1_REV_A.md`

That document explains how to attach draft QM/FM1 revisions and how to record per-document calendar effective intent on the legacy form fields.

## Critical note on your working files

FIND strings in these guides come from repository markdown mirrors. If your Word already removed a FIND block, apply the REPLACE intent only. For **clean finals**, regenerate readable text with `python scripts/refresh_dco091_readable_texts.py` and read `docs/QMS-Readable-Texts/20-QMSInProcess/DCO091/DCO091_EXTRACTION_REVIEW.md` for the latest gap analysis.

## Guide index (open in this order)

| Order | File | Document |
| --- | --- | --- |
| 0 | `EDITOR_COMBINED_QM001B_QM014C_FM1_DCO091.md` | **Single guide:** QM.SLQ001 B, QM.SLQ014 C, and FM1-QM.SLQ001 (form when created) |
| 1 | `MASTER_EFFECTIVE_DATE_NC15_EDITING_GUIDE.md` | NC #15 master; FIND/REPLACE detail and section H verification |
| 2 | `EDITOR_QM_SLQ001_DCO091.md` | QM.SLQ001 only (short index to upstream guides) |
| 3 | `EDITOR_QM_SLQ014_DCO091.md` | QM.SLQ014 only (short index) |
| 4 | `EDITOR_FM1_SLQ001_FROM_REV_A_DCO091.md` | **FM1-QM.SLQ001:** concise Rev A → next (NC15 + Silq) |
| 5 | `EDITOR_FM1_SLQ001_DCO091.md` | FM1-QM.SLQ001 only (short index to MASTER) |
| 6 | `EDITOR_FM1_SLQ014_DCO091.md` | FM1-QM.SLQ014 Electronic Signature Acknowledgement |

DCO091 does not include **TMP1-QM.SLQ001**. The file `EDITOR_TMP1_SLQ001_DCO091.md` is retained only for a possible future DCO.

Markdown extractions from clean Word: run `python scripts/refresh_dco091_readable_texts.py` (see `docs/QMS-Readable-Texts/20-QMSInProcess/DCO091/README.md`).

## Upstream design-assessment guides (Silq transition)

- `docs/design-assessment/Output/QM_SLQ001_REV_A_DOCUMENT_CONTROL_SOP_EDITING_GUIDE.md`
- `docs/design-assessment/Output/QM_SLQ014_REV_B_ELECTRONIC_DOC_SYSTEM_WI_EDITING_GUIDE.md`

NC #15 acceptance text: `docs/IA 2025 Questions, Responses/Response to NC list -- Editing Guide.md` (NC #15).

## After all edits

Run the verification tables in `MASTER_EFFECTIVE_DATE_NC15_EDITING_GUIDE.md` section H plus each EDITOR file checklist. Update Section cross-references and TOC in every Word file after final numbering.

## Readable text mirrors in this repo

In-process extractions and the repo-side review checklist live under:

`docs/QMS-Readable-Texts/20-QMSInProcess/DCO091/`

The primary QM and form mirrors under `docs/QMS-Readable-Texts/01-QM-Documents/` and `02-Forms-Templates-Travelers/` are updated when you run `scripts/refresh_dco091_readable_texts.py` (see folder README). See `DCO091_EXTRACTION_REVIEW.md` in that folder for review findings against NC15 and Silq guides.
