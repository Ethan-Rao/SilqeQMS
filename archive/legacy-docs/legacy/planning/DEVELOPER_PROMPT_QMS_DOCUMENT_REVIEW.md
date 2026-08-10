# Developer Prompt: Systematic QMS Document Review & Structure Catalog

**Date:** 2026-03-16  
**Requested by:** Ethan Rao, Director R&D, QA, Regulatory Affairs  
**Purpose:** Produce a comprehensive QMS Document Inventory & Structure Report that will serve as the input artifact for a subsequent Gap Analysis against ISO 13485:2016, 21 CFR Part 820 (QMSR), and other applicable regulatory standards.

---

## Objective

Perform a systematic, folder-by-folder review of every QMS-related document and content file uploaded to the `SilqQMS` project root. Catalog every document, classify it by QMS subsystem and document type, and produce a single structured output document (`docs/review/QMS_DOCUMENT_INVENTORY_2026_03.md`) that contains:

1. A complete **file-tree breakdown** of every QMS content folder  
2. A **document inventory table** for each subsystem  
3. A **cross-reference map** linking each document to relevant ISO 13485:2016 clauses and 21 CFR 820 subparts  
4. An **observations section** noting completeness, gaps in coverage, naming inconsistencies, or structural issues  
5. A **summary statistics** section  

This document will be consumed by a subsequent AI-assisted gap analysis — it must be machine-readable, thorough, and precise.

---

## Scope — Folders to Review

Review the following top-level folders in the `SilqQMS` project root. Each folder represents a QMS subsystem. You must enumerate every file (including those inside .zip archives where the contents are visible or inferable from naming conventions).

| # | Folder Path | QMS Subsystem |
|---|-------------|---------------|
| 1 | `Audits/` | Internal & External Audits |
| 2 | `CAPAs/` | Corrective and Preventive Actions |
| 3 | `DHF/` | Design History File (Verification & Validation) |
| 4 | `EmployeeTraining/` | Training Records, Job Descriptions, Training Matrix |
| 5 | `Equipment/` | Equipment Master List, Equipment Files (ST-001 through ST-016) |
| 6 | `Forms, Templates, and Travelers/` | Controlled Forms, Document Templates, Manufacturing Travelers |
| 7 | `ManagementReviewMeetings/` | Management Review Records (MR2022–MR2024) |
| 8 | `Manufacturing/` | Manufacturing Procedures, DHRs, BOMs, Specifications, QC, Environmental Monitoring — for both C.SLQ001 (Suspension) and ClearTract Foley Catheters (3 SKUs) |
| 9 | `NCMR/` | Nonconforming Material Reports |
| 10 | `PostMarketSurviellance/` | Product Complaints, eMDRs, Clinical Study (STC-001) |
| 11 | `Purchasing/` | Purchase Orders, PO Log |
| 12 | `QM Documents/` | Quality System SOPs, Work Instructions, Quality Manual, Quality Policy, Org Chart |
| 13 | `RegulatoryStandards&Approvals/` | 510(k) clearances, ASTM standards, FDA registration, ISO standards |
| 14 | `RiskManagement/` | Risk Management Files (RM-0018 through RM-0141), PFMEA |
| 15 | `Suppliers/` | Supplier Assessment Files, Approved Supplier List |
| 16 | `Supplies/` | Supply/Material Source Control Specifications |

Additionally, review these **standalone root-level files** that are QMS-relevant:

- `MR2025V1.pdf` — 2025 Management Review presentation (not yet filed into ManagementReviewMeetings/)
- `SILQ Approved Supplier List Feb 2025.docx`
- `Silq Equipment Master List.xlsx`
- `SILQ Training Matrix.xlsx`
- `MP-C.SLQ001 B Manufacturing Procedure. Suspension Processing.docx`
- `SAS TCI.pdf` (Supplier Assessment)
- `Equipment Requirements Form, Equip ID ST-012 - Weighing Scale.pdf`

---

## Output Document Structure

Create `docs/review/QMS_DOCUMENT_INVENTORY_2026_03.md` with the following sections:

### Section 1: Executive Summary
- Total document count across all subsystems
- Breakdown by document type (SOP, Form, Template, Record, Specification, Report, etc.)
- Breakdown by file format (PDF, DOCX, XLSX, PPTX, ZIP, etc.)
- Date range of documents (earliest to most recent based on filenames/content)
- Key observations (3–5 bullet points)

### Section 2: Complete File Tree
- Render the full directory tree for all 16 folders listed above
- Include file counts per folder
- Flag any files that appear to be duplicates or misplaced (e.g., `MR2025V1.pdf` in root instead of `ManagementReviewMeetings/`)

### Section 3: Document Inventory by Subsystem

For EACH of the 16 subsystems, create a subsection with:

#### 3.X [Subsystem Name]

**a) Document Inventory Table:**

| Document ID | Title/Filename | Rev | Type | Format | ISO 13485 Clause(s) | 21 CFR 820 Section(s) | Notes |
|-------------|----------------|-----|------|--------|---------------------|----------------------|-------|

Where:
- **Document ID** = Silq document number if identifiable (e.g., QM.SLQ001, VV.SLQ029, FM1-QM.SLQ016), or "N/A" if unnumbered
- **Rev** = Revision letter if visible in filename (e.g., A, B, C, D, E, F)
- **Type** = SOP | WI | Form | Template | Record | Report | Specification | Drawing | Certificate | Correspondence | Other
- **Format** = PDF | DOCX | XLSX | PPTX | ZIP | Other
- **ISO 13485 Clause(s)** = The primary ISO 13485:2016 clause(s) the document addresses
- **21 CFR 820 Section(s)** = The primary 21 CFR 820 section(s) the document addresses

**b) Observations:**
- Are document revision levels consistent within the subsystem?
- Are there obvious gaps (e.g., missing training records for employees, missing DHR components)?
- Are naming conventions followed consistently?
- Are any documents potentially outdated based on revision history?
- Are there files that appear to be duplicated across folders?

### Section 4: QMS Procedure (SOP) Cross-Reference Matrix

Create a dedicated mapping of all QM Documents (SOPs/WIs) to regulatory clauses:

| QM Doc # | Title | Rev | ISO 13485:2016 Clause | 21 CFR 820 Subpart/Section | QMSR Status |
|----------|-------|-----|-----------------------|---------------------------|-------------|

Where **QMSR Status** = assessment of whether the SOP likely needs updating for the new QMSR (effective Feb 2, 2026) that incorporates ISO 13485 by reference into 21 CFR 820.

### Section 5: Employee & Training Coverage Matrix

For each employee folder found in `EmployeeTraining/`:

| Employee | Job Description Present? | Training Program Present? | E-Sig Acknowledgment? | Resume? | # Training Records | QSR Annual Training (2022–2025) | SOP-Specific Training Gaps |
|----------|------------------------|--------------------------|----------------------|---------|--------------------|---------------------------------|---------------------------|

Cross-reference against the SOPs in `QM Documents/` — for each SOP, note which employees have documented training and which do not (based on filename patterns).

### Section 6: Manufacturing & Product Coverage

Summarize the manufacturing documentation coverage:

**Suspension (C.SLQ001):**
- Manufacturing Procedure: Present? Rev?
- BOM: Present? Rev?
- QC Procedure: Present? Rev?
- Specifications: List all
- DHRs: List all lots with completeness check (Traveler + QC Report + CoA + DHR Approval)
- Receiving Inspections: List all incoming material lots
- Environmental Monitoring: Present?

**ClearTract Foley Catheters (3 SKUs):**
For each SKU (SLQ-211410SPT, SLQ-211610SPT, SLQ-211810SPT):
- DMR: Present?
- DHRs: List all lots with completeness check
- QC Results: Crystal Violet + Coating Adherence per lot
- Labeling Specifications: List all
- Operating Procedures: List all

### Section 7: Risk Management File Inventory

| RM Document | Title/Description (from filename) | Format | Status |
|-------------|-----------------------------------|--------|--------|
| RM-0018 | (from zip — infer if possible) | ZIP | |
| RM-0019 | (from zip — infer if possible) | ZIP | |
| RM-0020 | (from zip — infer if possible) | ZIP | |
| RM-0021 Rev F | SILQ PFMEA | PDF | |
| RM-0094 Rev A | Risk Management, Production & Post-Production Review | PDF | |
| RM-0141 Rev A | RMF Review, SILQ 2024 | PDF | Signed 04-16-2025 |

Note any gaps relative to ISO 14971 requirements (Risk Management Plan, PHA, dFMEA/pFMEA, Risk/Benefit Analysis, Production & Post-Production Review).

### Section 8: Regulatory Clearances & Standards Inventory

List all 510(k) clearances with status, all standards on file, FDA registration documents.

### Section 9: Post-Market Surveillance Coverage

- Product Complaints: List all complaint files (2021–2025) with PCF numbers
- eMDRs: List all filed MDRs
- Clinical Study STC-001: List all CRFs and study documents
- Complaints Log: Present?

### Section 10: Supplier Management Coverage

- Approved Supplier List: Present? Date?
- For each supplier folder: List assessment documents, re-evaluation forms, certificates
- Supplier Assessment Schedule: Present?
- Supplier CAPA forms: Available in Forms?

### Section 11: Audit History Summary

| Year | Audit Type | Audit # | Scope | Findings | CAPA Ref |
|------|-----------|---------|-------|----------|----------|

Include both internal audits (IA2022, IA2023, IA2024) and external (FDA 2025).

### Section 12: Identified Structural Issues

Flag any issues found during the review:
- Misplaced files (documents in wrong folders or at root level)
- Duplicate documents across folders
- Missing documents referenced by other documents (e.g., SOPs that reference forms not found)
- Naming convention violations
- Zip files that should be extracted for accessibility
- Incomplete DHR packages
- Employees without complete training coverage

### Section 13: Summary Statistics Table

| Metric | Count |
|--------|-------|
| Total QMS Documents | |
| SOPs/WIs | |
| Forms/Templates | |
| Records (DHRs, Training, Inspections) | |
| Specifications | |
| Reports (VV, QC, Audit) | |
| Regulatory Submissions | |
| Risk Management Documents | |
| Employees with Training Folders | |
| Product SKUs with DMRs | |
| Suspension Lots with DHRs | |
| Catheter Lots with DHRs | |
| Product Complaints on File | |
| Purchase Orders on File | |
| Suppliers with Assessment Files | |

---

## Important Instructions

1. **Read every folder recursively.** Do not skip subfolders or zip files. If a zip file's contents can be inferred from the filename, note them. If not, note it as "ZIP — contents not inspected."

2. **Do not modify any QMS files.** This is a read-only review. The only file you create is the output document.

3. **Be precise with document IDs and revision levels.** These are critical for the subsequent gap analysis. Extract them from filenames using the Silq naming convention: `[TYPE]-[SYSTEM].[NUMBER] [REV] [Title]` (e.g., `QM.SLQ001 A` = QM Document #001, Revision A).

4. **Cross-reference the QM Documents SOPs against ISO 13485:2016 clauses.** Use the following primary mapping as a starting guide, but verify and expand based on actual SOP content/titles:
   - QM.SLQ001 → Document Control → ISO 4.2.4 / 820.40
   - QM.SLQ003 → Training → ISO 6.2 / 820.25
   - QM.SLQ004–010 → Design Controls → ISO 7.3 / 820.30
   - QM.SLQ012–013 → Risk Management → ISO 7.1 (ISO 14971) / 820.30(g)
   - QM.SLQ015 → Supplier QA → ISO 7.4 / 820.50
   - QM.SLQ016 → CAPA → ISO 8.5.2–8.5.3 / 820.90
   - QM.SLQ017 → Internal Audits → ISO 8.2.4 / 820.22
   - QM.SLQ018 → Management Review → ISO 5.6 / 820.20
   - QM.SLQ019 → Identification & Traceability → ISO 7.5.8–7.5.9 / 820.60–820.65
   - QM.SLQ020 → Purchasing Controls → ISO 7.4 / 820.50
   - QM.SLQ021 → Product Complaints → ISO 8.2.2 / 820.198
   - QM.SLQ022–023 → MDR / eMDR → ISO 8.2.3 / 21 CFR 803
   - QM.SLQ025 → Quality Planning → ISO 5.4.2 / 820.20
   - QM.SLQ027 → Quality Manual → ISO 4.2.2
   - QM.SLQ029 → DHR Review → ISO 7.5.1 / 820.184
   - QM.SLQ030 → Advisory Notices/Recalls → ISO 8.2.3 / 21 CFR 806
   - QM.SLQ033 → Post-Market Surveillance → ISO 8.2.1
   - QM.SLQ036 → Sales Order → ISO 7.2 / 820.80
   - QM.SLQ039 → Receiving Inspection → ISO 7.4.3 / 820.80
   - QM.SLQ040 → Nonconforming Materials → ISO 8.3 / 820.90
   - QM.SLQ046 → Shipping → ISO 7.5.1 / 820.80–820.160
   - QM.SLQ047 → Process Validation → ISO 7.5.6 / 820.75
   - QM.SLQ048 → DMR → ISO 4.2.3 / 820.181
   - QM.SLQ050 → Calibration/PM → ISO 7.6 / 820.72

5. **Note the QMSR transition.** The FDA QMSR became effective February 2, 2026, incorporating ISO 13485:2016 by reference into 21 CFR 820. Flag any SOPs that reference "21 CFR 820" clauses that have been restructured under QMSR. This will be critical for the gap analysis.

6. **Note the 2025 Management Review content.** The `MR2025V1.pdf` file at root contains the 2025 Management Review presentation (meeting date: March 16, 2026). It references several action items, CAPAs (2025-002, 2025-003), and regulatory changes. Cross-reference these against the documents on file.

7. **Note the FDA 483 and response.** In `Audits/FDA2025/`, there is an FDA Form 483 with 2 observations and a Silq 483 Response. These generated CAPAs 2025-002 and 2025-003. Verify these CAPAs are documented in the `CAPAs/` folder.

8. **Flag the MR2025 filing issue.** The 2025 Management Review file (`MR2025V1.pdf`) is at the project root, not in `ManagementReviewMeetings/`. Additionally, there is no `MR2025/` subfolder yet. Note this as a structural issue.

9. **Pay attention to the clinical study.** `PostMarketSurviellance/STC001/` contains a clinical study protocol and CRFs. Note its completeness for the gap analysis.

10. **The output document should be self-contained.** Someone reading it with no access to the file system should be able to fully understand the QMS document landscape, coverage, and potential gaps.

---

## Context for Subsequent Gap Analysis

After this document is produced, it will be used as input for a formal gap analysis comparing the documented QMS against:

- **ISO 13485:2016** (all clauses)
- **21 CFR Part 820 / QMSR** (all subparts, as amended Feb 2, 2026)
- **21 CFR Part 803** (Medical Device Reporting)
- **21 CFR Part 806** (Reports of Corrections and Removals)
- **ISO 14971:2019** (Risk Management)
- **ASTM F623** (Foley Catheter Performance Specification)

The regulatory standards documents are located in `RegulatoryStandards&Approvals/` for reference.

The gap analysis will identify:
- Required procedures/records that are missing entirely
- Procedures that exist but may not fully address regulatory requirements
- Records that should exist but are not on file
- Areas where the QMSR transition requires updates

**This document inventory is the essential first step. Be thorough.**
