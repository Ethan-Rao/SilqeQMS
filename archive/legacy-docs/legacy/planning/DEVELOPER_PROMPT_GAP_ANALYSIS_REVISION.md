# Developer Prompt: QMS Gap Analysis — Accuracy Review & Revision

**Date:** 2026-03-17  
**Requested by:** Ethan Rao, Director R&D, QA, Regulatory Affairs  
**Purpose:** Perform a thorough, corrective review of the existing gap analysis document based on a complete, holistic examination of the actual QMS repository contents. All ZIP archives have now been extracted.

---

## Critical Instruction: This Is a Correction Task, Not an Expansion Task

**You are revising an existing document, not writing a new one.**

Your primary job is to make the existing gap analysis **accurate** — correcting errors, adjusting gap ratings where evidence warrants, adding specificity where claims are vague, and removing or correcting statements that are not supported by the actual file system. You should **not** inflate the document with additional findings unless something material was missed. Be surgical, not expansive.

**Golden rule:** Every factual claim in the document should be verifiable against the actual repository contents. If a section says "appears to exist" when you can confirm it does exist, fix the language. If a section flags a gap that the evidence shows is actually addressed, downgrade or remove it. If a section understates a real gap, upgrade it.

---

## Input Artifacts

### Document Under Review

**`docs/review/QMS_GAP_ANALYSIS_ISO13485_QMSR_2026_03.md`** — Read this document in its entirety first. This is what you are revising.

### Reference Documents (read all before starting)

1. **QMS Document Inventory** — `docs/review/QMS_DOCUMENT_INVENTORY_2026_03.md`
2. **ISO 13485:2016 Practical Guide** — `RegulatoryStandards&Approvals/ISO/ISO 13485 2016 Medical devices Practical Guide.pdf`
3. **ISO 13485:2016** — `RegulatoryStandards&Approvals/ISO/ISO_13485_2016.pdf`
4. **ISO 14971:2019** — `RegulatoryStandards&Approvals/ISO/ISO_14971_2019(en).pdf`
5. **FDA QMSR Final Rule** — `RegulatoryStandards&Approvals/ISO/2024-01709. FDAQMSRFinalRule.pdf`

### The Actual Repository

**You MUST explore the file system directly.** The document inventory was created before all ZIPs were extracted and may have inaccuracies. The gap analysis was written primarily from the inventory, not from direct file-system verification. Your job is to ground-truth the gap analysis against the actual files on disk.

---

## What Changed Since the Gap Analysis Was Written

All ZIP archives have been extracted. The repository now has **~1,000 QMS files** across 16 subsystem folders. Here is the current state:

### Previously Zipped, Now Extracted

| Archive | Location | Extracted Contents |
|---|---|---|
| `RM-0018.zip` | `RiskManagement/` | `RM-0018/` — Risk Management Plan Rev D (cover sheet + plan .docx) |
| `RM-0019.zip` | `RiskManagement/` | `RM-0019/` — Hazard Analysis Rev D (cover sheet + HA report .docx) |
| `RM-0020.zip` | `RiskManagement/` | `RM-0020/` — DFMEA Rev D (cover sheet + DFMEA report .docx) |
| `WorkOrders.zip` | `Manufacturing/C.SLQ001/C.SLQ001WorkOrders/` | 3 work orders: WO 2209-01, WO 2302-01, WO 2502-01 (approved PDFs) |
| `S.SLQ002.zip` | `Supplies/` | `S.SLQ002/` — Centrifuge Tube spec + TDS attachment |
| `S.SLQ008.zip` | `Supplies/` | `S.SLQ008/` — Crystal Violet spec + SDS |
| `S.SLQ009.zip` | `Supplies/` | `S.SLQ009/` — Acetic Acid spec + SDS |
| `S.SLQ011.zip` | `Supplies/` | `S.SLQ011/` — UV Cuvette spec + data sheet |
| `SLQ007.zip` | `Supplies/` | `SLQ007/` — Bleach spec + SDS |
| `Copied from FileHold...zip` (Supplies) | `Supplies/` | Extracted (contents merged into Supplies) |
| `Copied from FileHold...zip` (ST-006) | `Equipment/ST-006/` | Extracted (ERF, service log, cal certs now directly in ST-006 folder) |
| `Copied from FileHold...zip` (ST-016) | `Equipment/ST-016/` | Extracted subfolder with ERF, service log, maintenance record |
| `POs.zip` | `Purchasing/` | `POs/` — 144 purchase order PDFs (PO 0000001 through PO 0000175, some gaps in numbering) |
| `FDARegistration.zip` | `RegulatoryStandards&Approvals/FDARegistration/` | `FDARegistration/` subfolder with 2024 registration confirmation email and 2022 listings update |

### Still Remaining as ZIP (not extractable or original kept alongside)

| File | Status |
|---|---|
| `RiskManagement/RM-0018.zip`, `RM-0019.zip`, `RM-0020.zip` | Original ZIPs remain alongside extracted folders |
| `Purchasing/POs.zip` | Original ZIP remains alongside extracted `POs/` folder |
| `Manufacturing/C.SLQ001/Specifications/L.SLQ005.zip` | **Still zipped — no extracted content visible.** This appears to be a labeling specification. Flag this. |

---

## Verified Repository Facts

Use these verified facts to correct inaccuracies in the gap analysis. Every number below was confirmed by direct file-system enumeration on 2026-03-17.

### File Counts by QMS Folder

| Folder | File Count | Notes |
|---|---|---|
| `QM Documents/` | 46 | QM SOPs and WIs (QM.SLQ001 through QM.SLQ051, with gaps in numbering) |
| `Forms, Templates, and Travelers/` | 65 | 40 forms, 14 templates, 1 traveler, in 3 subfolders |
| `EmployeeTraining/` | 186 | 7 employee folders + JobDescriptions (13 JDs) + Training Matrix |
| `Equipment/` | 119 | 16 equipment stations (ST-001 through ST-016) + Equipment Master List |
| `Manufacturing/` | 109 | C.SLQ001 (Suspension) + ClearTract Foley Catheters |
| `Suppliers/` | 89 | 17 supplier folders + Approved Supplier List + Assessment Schedules |
| `Purchasing/` | 146 | PO Log + 144 individual POs in `POs/` folder |
| `DHF/` | 60 | V&V documents VV.SLQ001 through VV.SLQ029 (with attachments) |
| `PostMarketSurviellance/` | 54 | ProductComplaints, eMDRs, STC001 clinical study |
| `Audits/` | 31 | IA2022, IA2023, IA2024, FDA2025 |
| `RiskManagement/` | 12 | 6 RM documents + 3 ZIP originals + 3 extracted folders with cover sheets |
| `ManagementReviewMeetings/` | 6 | MR2022, MR2023, MR2024 (each with minutes + slides) |
| `RegulatoryStandards&Approvals/` | 38 | 510(k)s, ASTM, FDA Registration, ISO standards |
| `CAPAs/` | 2 | CAPA Log + CAPA001.pdf |
| `Supplies/` | 18 | 11 source control specs (some with SDS/TDS attachments) |
| `NCMR/` | 1 | NCMR-0001.pdf only |
| **Root-level QMS files** | ~18 | Misplaced files (see below) |

### Risk Management File — Now Fully Accessible

| Document ID | Rev | Title | Format |
|---|---|---|---|
| RM-0018 | D | Risk Management Plan, SILQ Foley Catheter | .docx (extracted from ZIP) |
| RM-0019 | D | Hazard Analysis (HA) Risk Management Report, SILQ Foley Catheter | .docx (extracted from ZIP) |
| RM-0020 | D | DFMEA Risk Management Report, HDX Foley Catheter | .docx (extracted from ZIP) |
| RM-0021 | F | SILQ PFMEA | .pdf |
| RM-0094 | A | Production & Post-Production Risk Review, SILQ | .pdf |
| RM-0141 | A | RMF Review, SILQ 2024 (signed 04-16-2025) | .pdf |

**Important:** The risk management .docx files (RM-0018, 0019, 0020) can now be opened and their content reviewed. If you can read them, check whether RM-0018 includes risk acceptability criteria, an overall residual risk evaluation, and a completeness declaration. This was flagged as unknown in the current gap analysis.

### Production Lots — Verified Count

**Suspension (C.SLQ001):** 6 lots with DHRs — Lot2209-01-1, Lot2209-01-2, Lot2302-01-1, Lot2302-01-2, Lot2502-01-1, Lot2502-01-2. Each has COA, DHR Review Form, QC Report, and Traveler. 3 approved Work Orders on file (WO 2209-01, WO 2302-01, WO 2502-01).

**ClearTract Foley Catheters:** 3 SKUs × multiple lots:
- SLQ-211410SPT: 1 lot (LotSLQ-1192024)
- SLQ-211610SPT: 2 lots (LotSLQ-05012025, LotSLQ-11202024)
- SLQ-211810SPT: 4 lots (LotSLQ-01242025, LotSLQ-05022025, LotSLQ-11182024, LotSLQ-81020515241)

**Total production lot DHRs: 13** (6 suspension + 7 catheter)

### Equipment Documentation Completeness

| Station | ERF | Service Log | Cal Certs | Total Files | Key Gap |
|---|---|---|---|---|---|
| ST-001 | ✅ | ❌ | ❌ | 3 | No service log or calibration |
| ST-002 | ✅ | ❌ | ❌ | 4 | No service log or calibration |
| ST-003 | ✅ | ❌ | ❌ | 4 | No service log or calibration |
| ST-004 | ✅ | ✅ | ❌ | 6 | No calibration |
| ST-005 | ✅ | ✅ | ✅ (5) | 39 | Best documented — transfer docs, datasheets, certs |
| ST-006 | ✅ | ✅ | ✅ (2) | 8 | Good — Microprecision certs 2022 + 2024 |
| ST-007 | ✅ | ✅ | ✅ (2) | 7 | Good — Microprecision certs 2022 + 2024 |
| ST-008 | ✅ | ✅ | ❌ | 4 | No calibration records |
| ST-009 | ✅ | ✅ | ❌ | 3 | No calibration records |
| ST-010 | ✅ | ❌ | ❌ | 3 | No service log or calibration |
| ST-011 | ✅ | ✅ | ❌ | 6 | Fume hood — has HVAC survey but no cal |
| ST-012 | ✅ | ✅ | ✅ (5) | 10 | Good — 2 cal cycles (2022, 2024) |
| ST-013 | ✅ | ✅ | ✅ (1) | 6 | Temperature/humidity — has 2022 cal cert |
| ST-014 | ✅ | ❌ | ❌ | 4 | Spectrophotometer — no service log or cal |
| ST-015 | ✅ | ✅ | ✅ (3) | 6 | VIS cal standard — factory cal on file |
| ST-016 | ✅ | ✅ | ❌ | 5 | Freeze dryer — has maintenance but no cal |

**Summary:** Of 16 equipment items, only 6 have calibration certificates on file. 5 have no service log. This is a significant finding for ISO 13485 Clause 7.6 and should be rated accordingly.

### Supplier Assessment Completeness

| Supplier | Role | Initial Assessment | Re-Evaluations | Audits | Concern |
|---|---|---|---|---|---|
| Pathway | Contract manufacturer | ✅ Survey | ✅ 2021, 2024 | ✅ Audit 22-01, 23-02 | Best documented |
| Steripax | Contract sterilizer | ✅ Survey | ✅ 2024 | ❌ | No formal supplier audit for a critical outsourced special process |
| Ningbo | Catheter component supplier | ❌ No assessment | ❌ | ❌ | **Only COAs and a receiving record on file — no initial assessment or quality agreement for a direct catheter supplier** |
| BioMDg | Cat II consultants | ✅ | ❌ | ❌ | Cat II — lower risk |
| TCI (Tokyo Chemical) | Raw material | ✅ Survey | ✅ 2021–2024 | ❌ | Well managed |
| Repligen | Equipment | ✅ Survey | ✅ 2024 | ❌ | Adequate |
| Bentec | Catheter-related | ❌ No folder | ❌ | ❌ | **POs to Bentec exist (PO 0000034, 0000130, 0000132, 0000136, etc.) but no dedicated supplier folder** |
| Richman Chemical | Chemical | ✅ | ✅ 2023, 2024 | ❌ | Adequate |

**Key supplier gaps to verify:** Ningbo (critical catheter supplier with no assessment) and Bentec (catheter-related supplier with POs but no supplier folder). These should be checked against the Approved Supplier List to determine if they are controlled through a different mechanism.

### Complaint File Detail

11 complaint records spanning 2021–2025:
- **2021001:** PCF + response letter (single complaint)
- **2022001–2022003:** Each has PCF + supporting DHR + inspection record + test method. 2022002 also has clinical study device deficiency report.
- **2023001–2023002:** Each has PCF + supporting DHR
- **2023003:** PCF + email (UTI AE)
- **2023004, 2024001, 2024002, 2024004:** Single-file PCFs (no separate supporting docs folder)
- **2024003:** PCF + Ningbo acknowledgment letter
- **2025001:** Single PCF

Plus: Complaints and Reportable Events Log (Excel), 2 eMDR submission packages (SilqeMDR001, SilqeMDR002), 2 additional eMDR confirmation files (HTML/XML).

**Observation for the agent:** The earlier complaints (2022001-2022003) have richer supporting documentation than later ones (2023004, 2024001/002/004 are single-file PDFs). Check whether the gap analysis addresses this as a potential documentation consistency concern under §820.35(a).

### Employee Training — QSR Annual Coverage

| Employee | QSR 2021 | QSR 2022 | QSR 2023 | QSR 2024 | QSR 2025 | Total Records |
|---|---|---|---|---|---|---|
| Brian McVerry | ❌ | ✅ | ✅ | ✅ | ✅ | 30 |
| Chris Turner | ❌ | ✅ | ✅ | ✅ | ✅ | 28 |
| Chuck Greiner | ❌ | ✅ | ✅ | ✅ | ✅ | 23 |
| Ethan Rao | ❌ | ✅ | ✅ | ✅ | ✅ | 33 |
| Na He | ❌ | ❌ | ✅ | ✅ | ✅ | 20 |
| Tom Downey | ❌ | ✅ | ✅ | ✅ | ✅ | 19 |
| Verne Sharma | ✅ | ✅ | ✅ | ✅ | ✅ | 19 |

Na He is missing QSR 2022 training record. All employees have QSR 2025 training on file. Check whether the gap analysis accurately reflects this.

### Audit Record Duplication Issue

`Audits/IA2024/` contains **13 files** — 7 are the actual IA2024 audit (conducted Jan 2025: agenda, attendance, plan, report SIL IAR-2025-01, certificate 24-01, two checklists for Jan 2025) and **6 are exact duplicates from IA2023** (Nov 2023 agenda, audit plan, report IAR-2023-01, certificate 23-01, both Nov 2023 checklists). Verify the gap analysis flags this correctly.

### Root-Level Misplaced Files

The following QMS-relevant files sit at the repository root instead of in controlled folders:

| File | Should Be In |
|---|---|
| `MR2025V1.pdf` | `ManagementReviewMeetings/MR2025/` |
| `MP-C.SLQ001 B Manufacturing Procedure. Suspension Processing.docx` | `Manufacturing/C.SLQ001/ManufacturingProcedures/` (duplicate) |
| `SILQ Approved Supplier List Feb 2025.docx` | `Suppliers/` (older version — Jun 2025 list is in Suppliers/) |
| `Silq Equipment Master List.xlsx` | `Equipment/` (duplicate — also in Equipment/) |
| `SILQ Training Matrix.xlsx` | `EmployeeTraining/` (duplicate) |
| `Equipment Requirements Form, Equip ID ST-012 - Weighing Scale.pdf` | `Equipment/ST-012/` |
| `SAS TCI.pdf` | `Suppliers/TokyoChemicalIndustry/` |
| `0000145.pdf`, `0000290.pdf` | Unknown — possibly POs or receiving records |
| `2025 Sales Orders.pdf`, `SO_*.pdf` (6 files), `Packing Slips.pdf` | Sales/shipping records — no controlled folder exists |

### Remaining ZIP File

`Manufacturing/C.SLQ001/Specifications/L.SLQ005.zip` — **This is the only ZIP that still has no extracted content alongside it.** It is likely a labeling specification. The gap analysis should note this specifically.

---

## Specific Corrections to Investigate

The following are areas where the current gap analysis may need correction based on the verified facts above. **For each, check the current text and correct if warranted.**

### 1. Risk Management Gap Rating

The current document was initially written when RM ZIPs were inaccessible and has been partially updated. Now that the RM .docx files can actually be opened and read:
- **Read RM-0018 (Risk Management Plan)** and check if it includes: risk acceptability criteria/matrix, risk management process description, scope, and whether it references ISO 14971.
- **Read RM-0019 (Hazard Analysis)** and check if it provides systematic hazard identification with severity/probability ratings and risk control measures.
- **Read RM-0020 (DFMEA)** and check the structure against ISO 14971 expectations.
- Based on what you find, determine if the Part 5 gap rating (currently "Minor-to-Moderate") is accurate. It may need to go up (if the documents are thin) or down (if they are comprehensive).

### 2. Equipment Calibration Gap Rating

Section 3.17 rates this as "Moderate Gap." Given that **10 of 16 equipment items lack calibration records** and **5 lack service logs**, verify whether "Moderate" is appropriate or whether this should be upgraded. Some of those items (ST-001 water deionizer, ST-002 tank, ST-003 waste pump) may not require calibration — verify whether the gap analysis distinguishes between items that require calibration vs. items that don't.

### 3. Supplier Assessment Gaps — Ningbo and Bentec

The current document mentions Bentec and Ningbo as gaps. Verify:
- Is Ningbo on the Approved Supplier List (the .xlsx at `Suppliers/SILQ Approved Supplier List 04 Jun 2025.pdf`)?
- Are there quality agreements or assessments for either supplier stored elsewhere?
- Is the severity of the Ningbo gap (a direct catheter component supplier with no quality assessment) adequately captured?

### 4. QMSR Crosswalk Accuracy (Part 4)

The QMSR provisions table in Part 4 was derived from general knowledge of the Final Rule. Now that you have the actual `2024-01709. FDAQMSRFinalRule.pdf`:
- Verify that every §820 section number cited is correct per the actual rule text.
- Verify the "Derived From (legacy 820)" column is accurate.
- Check if any QMSR provisions are missing from the table.
- Ensure the Silq Coverage column reflects actual repository evidence.

### 5. Complaint Documentation Consistency

The current gap analysis does not distinguish between well-documented complaints (2022001-2022003 with full supporting evidence) and later complaints that are single-file PCFs. Under §820.35(a), complaint record completeness requirements are now explicit. Check whether this observation warrants a specific finding.

### 6. Work Order Coverage

Work Orders are now visible: WO 2209-01, WO 2302-01, WO 2502-01. These correspond to the suspension lots. Verify whether the gap analysis acknowledges this production documentation or whether it's still flagged as inaccessible.

### 7. Supplies Specifications

The Supplies folder now shows 11 source control specifications (S.SLQ001 through S.SLQ011, plus SP-TF.SLQ001) with SDS/TDS attachments where applicable. This is DMR-supporting documentation. Check whether the gap analysis adequately accounts for the completeness of material specifications.

### 8. FDA Registration Evidence

The FDARegistration subfolder now shows a 2024 registration confirmation email and 2022 listings update alongside the existing registration info and small business qualification. Verify this is reflected.

### 9. Management Review — MR2025 Status

MR2025V1.pdf sits at root level. There is NO MR2025 folder in ManagementReviewMeetings/ and no MR2025 meeting minutes. The MR2022-2024 folders each have both minutes and slides. Verify the gap analysis accurately describes this asymmetry.

### 10. PostMarketSurviellance Folder Spelling

The folder is misspelled as "PostMarketSurviellance" (extra 'i', wrong 'e'). This is a minor housekeeping item but should be noted under structural issues if not already.

---

## How to Perform the Review

### Phase 1: Read and Understand (do not edit yet)

1. Read the existing gap analysis document (`docs/review/QMS_GAP_ANALYSIS_ISO13485_QMSR_2026_03.md`) in full.
2. Read the QMS Document Inventory (`docs/review/QMS_DOCUMENT_INVENTORY_2026_03.md`).
3. Read the relevant sections of the Practical Guide, ISO 13485, ISO 14971, and the QMSR Final Rule as needed.
4. Explore the actual file system to verify claims made in the gap analysis. Do NOT rely solely on the inventory — look at the actual folders.

### Phase 2: Build a Corrections List

Before editing, compile a mental list of every correction, rating adjustment, and factual fix needed. Categorize them:
- **Factual errors** (wrong file counts, wrong document names, wrong revision levels)
- **Rating adjustments** (gap ratings that should go up or down based on evidence)
- **Missing context** (areas where the extracted ZIPs provide new information)
- **Overstated gaps** (things flagged as gaps that are actually addressed)
- **Understated gaps** (things rated as minor that are actually more significant)

### Phase 3: Edit the Document

Apply corrections directly to `docs/review/QMS_GAP_ANALYSIS_ISO13485_QMSR_2026_03.md`. For each edit:
- Preserve the existing document structure (Parts 1-8)
- Maintain the consultative, constructive tone
- Update the revision date in the header
- Keep Practical Guide page references accurate
- Ensure the Action Plan (Part 7) is consistent with any rating changes you make

### Phase 4: Verify Consistency

After editing, read the document end-to-end one more time to ensure:
- The Executive Summary (Part 1) accurately reflects the clause-by-clause findings (Part 3)
- The Top 5 Priority Gaps are still the right 5 based on your corrections
- The Action Plan priorities and descriptions match the findings
- The Risk Management Assessment (Part 5) is consistent with the Section 3.10 findings
- No section references "ZIP accessibility" as a current problem (all ZIPs are extracted except L.SLQ005.zip)
- The total file counts and document references are accurate

---

## Important Constraints

1. **Do not add new sections or restructure the document.** Work within the existing 8-part structure.
2. **Do not remove the QMSR crosswalk (Part 4) or restructure Part 2.** Correct them in place.
3. **Preserve Practical Guide page references.** Only change them if they are wrong.
4. **If you cannot read a .docx file** (e.g., RM-0018), note this explicitly rather than guessing at the content.
5. **Maintain the consultative tone.** This is for the leadership team.
6. **Do not expand the document significantly.** Target the same ~25-40 page range. If you add specificity in one area, consider whether another area can be tightened.
7. **Note CAPAs 2025-002 and 2025-003 as pending.** Do not treat their absence as a gap.
8. **Update the revision date** to reflect your review date.
9. **The only file you should modify is** `docs/review/QMS_GAP_ANALYSIS_ISO13485_QMSR_2026_03.md`.

---

## Output

A corrected, accuracy-verified version of `docs/review/QMS_GAP_ANALYSIS_ISO13485_QMSR_2026_03.md` that:

1. Has every factual claim verified against the actual repository
2. Has gap ratings calibrated to the evidence (not inflated, not deflated)
3. Reflects the full extracted state of all ZIP archives
4. Has a consistent, internally-coherent narrative from Executive Summary through Action Plan
5. Is ready for the Silq leadership team to read and act on
