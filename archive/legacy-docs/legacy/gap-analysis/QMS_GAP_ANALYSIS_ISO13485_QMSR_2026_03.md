# QMS Gap Analysis: ISO 13485:2016 and FDA QMSR (21 CFR Part 820)

**Date:** 2026-03-17 (QMSR-focused revision)  
**Prepared for:** Silq Leadership Team  
**Prepared by:** Internal RA/QA gap analysis support  
**Primary inputs used:**  
- `docs/review/QMS_DOCUMENT_INVENTORY_2026_03.md` (full review completed)  
- `RegulatoryStandards&Approvals/ISO/ISO 13485 2016 Medical devices Practical Guide.pdf`  
- `RegulatoryStandards&Approvals/ISO/ISO_13485_2016.pdf`  
- `RegulatoryStandards&Approvals/ISO/ISO_14971_2019(en).pdf`  
- `RegulatoryStandards&Approvals/ISO/2024-01709. FDAQMSRFinalRule.pdf`

---

## Part 1: Executive Summary

### Overall QMS Maturity Assessment

**Maturity rating: _Substantially Aligned — QMSR Transition Gaps Identified (Moderate Risk)_.**

Silq has a mature QMS base with broad procedural coverage and evidence across design, manufacturing, post-market, supplier controls, and management review. The highest-value transition work is now focused on QMSR-specific record controls, modernized citation architecture, and tighter cross-linking between ISO 13485 processes and retained FDA overlays.

### QMSR Readiness Score (Major ISO Clause Coverage)

| ISO 13485 Major Clause | Status |
|---|---|
| Clause 4 (QMS + documentation) | ⚠️ Partial |
| Clause 5 (management responsibility) | ⚠️ Partial |
| Clause 6 (resources) | ⚠️ Partial |
| Clause 7 (product realization) | ⚠️ Partial |
| Clause 8 (measurement/improvement) | ⚠️ Partial |

**Readiness interpretation:** All major clauses are operationally implemented, with targeted transition gaps rather than foundational system absence.

### Top 5 Priority Gaps (QMSR-focused)

1. **`§820.35(a)` complaint record field compliance** is not yet explicitly embedded in form-level checks and SOP language.  
2. **`§820.45` labeling/packaging supplemental controls** need explicit record evidence for release checks and mix-up prevention.  
3. **Legacy 820 references in core QM documents** need controlled transition to ISO 13485 + revised 820 architecture.  
4. **QMS traceability mapping for `§820.10(b)` overlays** (parts 830/821/803/806) needs explicit clause-to-procedure linkage.  
5. **Clause 7.6 equipment calibration/service evidence consistency** remains uneven across 16 equipment items and impacts QMSR readiness confidence.

### Estimated Remediation Effort

| Gap Area | Effort |
|---|---|
| QMSR supplemental records (`§820.35`, `§820.45`) | Medium |
| Citation/terminology modernization across QM docs | Medium |
| QMSR overlay crosswalk formalization (`§820.10(b)`) | Low to Medium |
| Equipment evidence normalization (calibration/service) | Medium |
| Management review trend integration for transition KPIs | Medium |

### Key Message

Silq is operating from a strong baseline and does not require a system rebuild for QMSR. The transition priority is precision: make retained FDA supplemental controls explicit in procedures and records, then close consistency gaps in objective evidence. This is a focused compliance-hardening effort, not a structural overhaul.

---

## Part 2: QMSR Transition Overview

### What changed on Feb 2, 2026

The FDA QMSR Final Rule made ISO 13485:2016 the baseline by incorporation by reference and retained a small set of FDA-specific supplemental requirements in revised Part 820.

### Practical meaning of incorporation by reference

- ISO 13485 now carries the primary QMS requirement framework for FDA device CGMP expectations.
- Compliance remains dual-context: ISO 13485 requirements plus FDA-specific overlays in revised Part 820 and related regulations.
- Internal procedures should cite both ISO clauses and retained FDA overlays where applicable.

### Revised 820 structure (codified)

Core sections in revised Part 820 include:
- `§820.1` Scope
- `§820.3` Definitions
- `§820.7` Incorporation by reference
- `§820.10` Requirements for a quality management system
- `§820.35` Control of records (supplemental)
- `§820.45` Device labeling and packaging controls (supplemental)

Subparts C through O are reserved in the revised codified structure.

### FDA-specific overlays most relevant to Silq

- `§820.10(b)(1)-(4)` links ISO clauses to UDI, traceability, MDR, and advisory notice obligations.
- `§820.35(a)-(d)` adds explicit record expectations for complaints, servicing, UDI, and confidentiality handling.
- `§820.45(a)-(c)` adds specific labeling/packaging control and documentation expectations.

### Transition implication for existing SOP references

Silq should execute one controlled citation remediation package:
- Replace legacy-only 820 citations with ISO 13485 clause references plus revised 820 overlays where applicable.
- Keep change-history rationale so users can bridge old/new reference structures during training.

---

## Part 3: Clause-by-Clause Gap Analysis

### Gap Rating Scale

| Rating | Meaning |
|---|---|
| ✅ Conforming | Fully addressed by current documentation and practice |
| ⚠️ Minor Gap | Substantially addressed; targeted updates needed |
| 🔶 Moderate Gap | Partially addressed; defined revisions needed |
| 🔴 Major Gap | Not adequately addressed |
| ℹ️ Not Applicable | Requirement not applicable to Silq operations |

### 3.1 — Clause 4.1 General Requirements
**Practical Guide Reference:** pp. 31-42  
**a) Requirement Summary:** QMS processes must be established, controlled, and risk-based across the system.  
**b) Current Silq Coverage:** Quality Manual (`QM.SLQ027` Rev E), 46 QM SOPs/WIs, 40 controlled forms, 14 templates, risk SOPs `QM.SLQ012`/`QM.SLQ013` (Rev B).  
**c) Gap Assessment:** ⚠️ Minor Gap  
**d) Specific Findings:** System exists; QMSR-era process-level risk narrative is distributed across documents rather than consolidated in one map.  
**e) Recommended Actions:** Add QMS process interaction + risk map appendix in `QM.SLQ027`. **Priority: High**

---

### 3.2 — Clauses 4.2.1-4.2.2 Documentation and Quality Manual
**Practical Guide Reference:** pp. 43-50  
**a) Requirement Summary:** Documented QMS and quality manual with scope/process interaction are required.  
**b) Current Silq Coverage:** Documented QMS with 46 QM documents and controlled forms/templates.  
**c) Gap Assessment:** ⚠️ Minor Gap  
**d) Specific Findings:** Mature documentation base; quality manual and key SOP references need QMSR-era citation architecture refresh.  
**e) Recommended Actions:** Revise manual to include ISO-to-QMSR overlay matrix. **Priority: High**

---

### 3.3 — Clause 4.2.3 Medical Device File
**Practical Guide Reference:** pp. 50-53  
**a) Requirement Summary:** Device files must contain specifications and records needed for conformity.  
**b) Current Silq Coverage:** DMRs (3 SKUs), DHRs (13 production lots), specifications, work orders, and risk files are available.  
**c) Gap Assessment:** ⚠️ Minor Gap  
**d) Specific Findings:** Retrieval is substantially improved with ZIP extraction; one labeling archive (`L.SLQ005.zip`) remains isolated and should be normalized.  
**e) Recommended Actions:** Extract and index remaining labeling ZIP content. **Priority: High**

---

### 3.4 — Clauses 4.2.4-4.2.5 Control of Documents and Records
**Practical Guide Reference:** pp. 53-58  
**a) Requirement Summary:** Records/documents must be approved, retrievable, current, and controlled.  
**b) Current Silq Coverage:** Document/record SOPs (`QM.SLQ001`, `QM.SLQ002`, `QM.SLQ014`) and controlled templates are in place.  
**c) Gap Assessment:** 🔶 Moderate Gap  
**d) Specific Findings:** Core control process exists, but root-level misplaced files (~18 files) and duplicate audit records still reduce retrieval confidence; `§820.35` supplemental requirements are not yet fully explicit in control language.  
**e) Recommended Actions:** Add `§820.35` requirements to record-control procedures and complete records housekeeping closure list. **Priority: Critical**

---

### 3.5 — Clauses 5.1-5.4 Management Commitment, Policy, Planning
**Practical Guide Reference:** pp. 59-68  
**a) Requirement Summary:** Leadership must set policy/objectives and ensure QMS planning and customer/regulatory focus.  
**b) Current Silq Coverage:** Policy (`QM.SLQ035`), objectives (`QM.SLQ037`), planning (`QM.SLQ025`), and regular management reviews are present.  
**c) Gap Assessment:** ⚠️ Minor Gap  
**d) Specific Findings:** Process is active; transition KPI linkage to QMSR-specific actions can be sharper.  
**e) Recommended Actions:** Add QMSR transition KPIs to quality objectives dashboard and management review package. **Priority: Medium**

---

### 3.6 — Clause 5.5 Responsibility, Authority, Communication
**Practical Guide Reference:** pp. 68-71  
**a) Requirement Summary:** Roles and communication controls must support QMS effectiveness.  
**b) Current Silq Coverage:** Organizational structure (`QM.SLQ034` Rev F) and SOP ownership are defined.  
**c) Gap Assessment:** ⚠️ Minor Gap  
**d) Specific Findings:** Role framework exists; explicit transition ownership matrix would improve execution clarity.  
**e) Recommended Actions:** Add QMSR transition RACI by role title. **Priority: Medium**

---

### 3.7 — Clause 5.6 Management Review
**Practical Guide Reference:** pp. 71-78  
**a) Requirement Summary:** Management review must include required inputs and actionable outputs.  
**b) Current Silq Coverage:** MR2022–MR2024 are organized with meeting minutes + slides in dedicated folders; MR2025 slides (`MR2025V1.pdf`) exist at root level with no dedicated folder or minutes on file yet.  
**c) Gap Assessment:** 🔶 Moderate Gap  
**d) Specific Findings:** Cadence is established and consistent through 2024; MR2025 record completion and action-tracking consistency should be strengthened. Practical Guide (pp. 71-78) emphasizes complete input set and output actions with follow-through.  
**e) Recommended Actions:** Standardize management review input/output checklist; close MR2025 filing package with minutes and controlled folder. **Priority: High**

---

### 3.8 — Clauses 6.1-6.2 Resources and Human Resources
**Practical Guide Reference:** pp. 79-87  
**a) Requirement Summary:** Organization must ensure competence and adequate resources.  
**b) Current Silq Coverage:** Training system with 7 employee folders, SOP-specific training records, QSR annual training 2022–2025 (all 7 employees have QSR 2025 records), 13 job descriptions.  
**c) Gap Assessment:** ⚠️ Minor Gap  
**d) Specific Findings:** Process is broadly implemented. This revision intentionally excludes isolated pre-2023 record-level detail.  
**e) Recommended Actions:** Focus on process-level training effectiveness metrics tied to critical QMSR-updated SOPs. **Priority: Medium**

---

### 3.9 — Clauses 6.3-6.4 Infrastructure, Work Environment
**Practical Guide Reference:** pp. 87-92  
**a) Requirement Summary:** Infrastructure and work environment must be suitable and controlled.  
**b) Current Silq Coverage:** Infrastructure SOPs (`QM.SLQ049`, `QM.SLQ050`, `QM.SLQ051`), 16 equipment stations (ST-001–ST-016), environmental monitoring logs and water quality reports (2022–2025).  
**c) Gap Assessment:** 🔶 Moderate Gap  
**d) Specific Findings:** System exists, but objective evidence consistency varies significantly — only 6 of 16 equipment items have calibration certificates on file; 5 items lack service logs entirely.  
**e) Recommended Actions:** Integrate environment/infrastructure trend reporting into management review. **Priority: Medium**

---

### 3.10 — Clause 7.1 Product Realization Planning (Risk Integration)
**Practical Guide Reference:** pp. 93-100  
**a) Requirement Summary:** Realization planning must include risk, verification, validation, and controls.  
**b) Current Silq Coverage:** Design SOPs (`QM.SLQ004`–`QM.SLQ010`), risk SOPs, and full Risk Management File (RM-0018 Plan Rev D, RM-0019 HA Rev D, RM-0020 DFMEA Rev D, RM-0021 PFMEA Rev F, RM-0094 Post-Production Review Rev A, RM-0141 RMF Review 2024).  
**c) Gap Assessment:** ⚠️ Minor Gap  
**d) Specific Findings:** Risk records are accessible and substantive; strongest remaining need is formal traceability from risk outputs to realization controls and acceptance criteria.  
**e) Recommended Actions:** Publish risk-to-realization trace matrix (design, production, post-market links). **Priority: High**

---

### 3.11 — Clause 7.2 Customer-Related Processes
**Practical Guide Reference:** pp. 100-106  
**a) Requirement Summary:** Requirements review and customer communication controls are required.  
**b) Current Silq Coverage:** Sales order SOP (`QM.SLQ036`) and advisory notice SOP (`QM.SLQ030`).  
**c) Gap Assessment:** ⚠️ Minor Gap  
**d) Specific Findings:** Process exists; advisory notice workflow should explicitly reference part 806 under `§820.10(b)(4)`. Root-level sales/shipping files indicate records filing needs normalization.  
**e) Recommended Actions:** Create controlled sales/shipping records location; verify advisory notice procedure references QMSR/part 806 language. **Priority: Medium**

---

### 3.12 — Clause 7.3 Design and Development
**Practical Guide Reference:** pp. 106-136  
**a) Requirement Summary:** Design controls must cover planning through file completion and change control.  
**b) Current Silq Coverage:** Design SOP stack (`QM.SLQ004`–`QM.SLQ010`), 29 V&V documents (VV.SLQ001–VV.SLQ029; VV.SLQ018/VV.SLQ027 absent from sequence), accessible risk management files (RM-0018/0019/0020), 3 cleared 510(k)s (K192034, K221625, K222118).  
**c) Gap Assessment:** ⚠️ Minor Gap  
**d) Specific Findings:** Design control is one of Silq's strongest areas. V&V sequence gaps and one IQ protocol without a corresponding report (VV.SLQ026) should be formally dispositioned.  
**e) Recommended Actions:** Add controlled design file completeness checklist and documented sequence dispositions. **Priority: Medium**

---

### 3.13 — Clause 7.4 Purchasing
**Practical Guide Reference:** pp. 136-146  
**a) Requirement Summary:** Supplier qualification, purchasing controls, and incoming verification are required.  
**b) Current Silq Coverage:** Supplier SOPs (`QM.SLQ015`, `QM.SLQ020`), 17 supplier folders, Approved Supplier List (Jun 2025), assessment schedules 2022–2025, 144 PO records, supplier audits (Pathway Audit 22-01, 23-02).  
**c) Gap Assessment:** ⚠️ Minor Gap  
**d) Specific Findings:** Overall framework is active and broad. Ningbo (catheter component supplier — no quality assessment on file, only COAs) and Bentec (catheter-related supplier — POs exist but no dedicated supplier folder) represent assessment gaps for catheter-critical suppliers.  
**e) Recommended Actions:** Close assessment evidence gaps for Ningbo and Bentec; maintain risk-based supplier monitoring cadence. **Priority: High**

---

### 3.14 — Clauses 7.5.1-7.5.4 Production and Service Provision
**Practical Guide Reference:** pp. 146-158  
**a) Requirement Summary:** Production/service activities must be controlled and documented.  
**b) Current Silq Coverage:** Manufacturing procedures, QC procedures, 13 lot DHRs (6 suspension, 7 catheter), 3 approved work orders, BOM/BOR, receiving inspections, 11 supply source control specifications.  
**c) Gap Assessment:** ⚠️ Minor Gap  
**d) Specific Findings:** Production records are substantially complete. QMSR servicing record fields (`§820.35(b)`) should be explicitly addressed if servicing activities occur.  
**e) Recommended Actions:** Add servicing data-field checklist and periodic verification. **Priority: High**

---

### 3.15 — Clauses 7.5.5-7.5.7 Sterile Requirements and Process Validation
**Practical Guide Reference:** pp. 158-162  
**a) Requirement Summary:** Sterile-device and process-validation controls must include outsourced special-process governance.  
**b) Current Silq Coverage:** Sterilization outsourced to Steripax (supplier assessment, re-evaluation 2024, ISO 9001:2015 certificate); process validation SOP (`QM.SLQ047`), IQ package set (VV.SLQ011–VV.SLQ025).  
**c) Gap Assessment:** 🔶 Moderate Gap  
**d) Specific Findings:** Control framework exists; acceptance criteria/change-notification/record linkage for outsourced sterilization should be more explicit. No formal Steripax supplier audit on file for this critical outsourced special process.  
**e) Recommended Actions:** Add outsourced sterilization control appendix and evidence checklist. **Priority: High**

---

### 3.16 — Clauses 7.5.8-7.5.11 Identification, Traceability, Preservation
**Practical Guide Reference:** pp. 162-165  
**a) Requirement Summary:** End-to-end identification, traceability, and preservation controls are required.  
**b) Current Silq Coverage:** Traceability SOP (`QM.SLQ019` Rev C), DHR/lot records across 13 production lots, receiving/shipping SOPs.  
**c) Gap Assessment:** 🔶 Moderate Gap  
**d) Specific Findings:** Operational traceability is present; explicit QMSR mapping to parts 830/821 and documented preservation matrix should be added.  
**e) Recommended Actions:** Update traceability SOP/form architecture for direct `§820.10(b)` alignment. **Priority: Critical**

---

### 3.17 — Clause 7.6 Monitoring and Measuring Equipment
**Practical Guide Reference:** pp. 165-170  
**a) Requirement Summary:** Measurement equipment must be calibrated/maintained where needed and traceably controlled.  
**b) Current Silq Coverage:** Calibration/PM SOP (`QM.SLQ050`), 16 equipment files (ST-001 through ST-016). Calibration certificates on file for 6 items (ST-005, ST-006, ST-007, ST-012, ST-013, ST-015); 10 items lack calibration records; 5 items lack service logs.  
**c) Gap Assessment:** 🔶 Moderate Gap  
**d) Specific Findings:** Evidence consistency remains uneven. Several items without calibration records (e.g., tanks ST-002, pumps ST-003/ST-004/ST-008) may not require calibration — but that distinction is not formally documented. The gap is the absence of a defensible calibration-required vs. non-calibration-required classification.  
**e) Recommended Actions:** Create risk-based equipment classification matrix with calibration/service requirements and due-date tracking. **Priority: High**

---

### 3.18 — Clause 8.1 Measurement, Analysis, Improvement (General)
**Practical Guide Reference:** pp. 170-172  
**a) Requirement Summary:** QMS must define monitoring/measurement/improvement framework.  
**b) Current Silq Coverage:** Core processes (audit, CAPA, complaints, MR) are in place.  
**c) Gap Assessment:** ⚠️ Minor Gap  
**d) Specific Findings:** Framework exists; centralized transition KPI reporting can improve leadership visibility.  
**e) Recommended Actions:** Add QMSR transition dashboard to management review cycle. **Priority: Medium**

---

### 3.19 — Clauses 8.2.1-8.2.3 Feedback, Complaints, Regulatory Reporting
**Practical Guide Reference:** pp. 172-184  
**a) Requirement Summary:** Feedback, complaint handling, and regulatory reporting must be controlled and complete.  
**b) Current Silq Coverage:** Complaint SOP (`QM.SLQ021` Rev D), MDR/eMDR procedures, 11 complaint records (2021–2025), Complaints and Reportable Events Log, 2 eMDR submission packages.  
**c) Gap Assessment:** 🔶 Moderate Gap  
**d) Specific Findings:** QMSR `§820.35(a)` makes complaint record content explicit. Earlier complaints (2022001–2022003) have richer supporting documentation than more recent single-file PCFs (2023004, 2024001/002/004), indicating documentation consistency should be standardized so field-level completeness is demonstrable every time.  
**e) Recommended Actions:** Update complaint SOP/template with mandatory `§820.35(a)` checklist and periodic QA completeness audits. **Priority: Critical**

---

### 3.20 — Clause 8.2.4 Internal Audit
**Practical Guide Reference:** pp. 184-189  
**a) Requirement Summary:** Internal audits must verify conformity/effectiveness and drive closure.  
**b) Current Silq Coverage:** Annual audit cycle (IA2022, IA2023, IA2024), FDA inspection 2025 with Form 483, response, and EIR on file.  
**c) Gap Assessment:** ⚠️ Minor Gap  
**d) Specific Findings:** Audit cadence is strong. IA2024 folder contains 6 duplicated files from IA2023 alongside the actual Jan 2025 audit records, reducing evidence clarity.  
**e) Recommended Actions:** Remove duplicates and enforce one audit package per year/audit ID; add QMSR supplemental audit checklist module. **Priority: Medium**

---

### 3.21 — Clauses 8.2.5-8.2.6 Monitoring and Measurement of Processes/Product
**Practical Guide Reference:** pp. 189-192  
**a) Requirement Summary:** Process/product monitoring must be defined and actionable.  
**b) Current Silq Coverage:** Product-level QC evidence in DHRs; process data across manufacturing and equipment records.  
**c) Gap Assessment:** ⚠️ Minor Gap  
**d) Specific Findings:** Process KPI architecture can be made more explicit and threshold-driven.  
**e) Recommended Actions:** Define KPI thresholds and escalation rules in controlled procedure or MR annex. **Priority: Medium**

---

### 3.22 — Clause 8.3 Control of Nonconforming Product
**Practical Guide Reference:** pp. 192-197  
**a) Requirement Summary:** NC product must be contained, dispositioned, and trended.  
**b) Current Silq Coverage:** NCMR SOP (`QM.SLQ040` Rev B), forms, NCMR Log template. Only NCMR-0001.pdf on file.  
**c) Gap Assessment:** 🔶 Moderate Gap  
**d) Specific Findings:** NC process exists; single visible NCMR against 13 production lots of activity suggests possible under-capture or distributed records. Centralized trend visibility should be strengthened for CAPA/MR linkage.  
**e) Recommended Actions:** Implement controlled NC trend dashboard with closure verification. **Priority: High**

---

### 3.23 — Clause 8.4 Analysis of Data
**Practical Guide Reference:** pp. 197-198  
**a) Requirement Summary:** Data analysis must support suitability/effectiveness and improvement decisions.  
**b) Current Silq Coverage:** Data sources exist across quality subsystems (complaints, CAPA, audits, supplier, QC, equipment).  
**c) Gap Assessment:** 🔶 Moderate Gap  
**d) Specific Findings:** Strong data availability, but formal integrated analysis routine is still diffuse.  
**e) Recommended Actions:** Define minimum required trend set and analysis cadence in controlled workflow. **Priority: High**

---

### 3.24 — Clause 8.5 Improvement, Corrective Action, Preventive Action
**Practical Guide Reference:** pp. 198-208  
**a) Requirement Summary:** Corrective/preventive action must be risk-based and effectiveness-verified.  
**b) Current Silq Coverage:** CAPA SOP (`QM.SLQ016` Rev C), CAPA Log (Excel), CAPA001.pdf on file. CAPAs 2025-002 and 2025-003 pending upload (expected, from FDA 483 response).  
**c) Gap Assessment:** 🔶 Moderate Gap  
**d) Specific Findings:** CAPA process is established; effectiveness verification criteria should be consistently objective and time-bound.  
**e) Recommended Actions:** Standardize CAPA effectiveness metrics and closure-evidence checks. **Priority: High**

---

## Part 4: QMSR-Specific Requirements Crosswalk

| QMSR Provision | Description | Derived From (legacy 820) | Silq Coverage | Gap? |
|---|---|---|---|---|
| `§820.10(a)` | Document QMS meeting ISO 13485 + part 820 | Legacy 820 core CGMP structure | Quality manual and SOP framework present | ⚠️ (citation refresh) |
| `§820.10(b)(1)` | UDI assignment per part 830 for ISO 7.5.8 | Legacy identification framework plus UDI era integration | Traceability SOP exists | ⚠️ |
| `§820.10(b)(2)` | Traceability procedures per part 821 where applicable | Legacy `820.65` traceability concepts | Traceability controls exist | ⚠️ (explicit applicability statement needed) |
| `§820.10(b)(3)` | Regulatory reporting alignment with part 803 | Legacy complaint/MDR integration (`820.198` context) | MDR/eMDR process active | ✅ |
| `§820.10(b)(4)` | Advisory notices handled per part 806 | Legacy correction/removal expectations | Recall/advisory SOP exists | ⚠️ (cross-reference precision) |
| `§820.10(c)` | Design controls applicability | Legacy `820.30` | Design control SOP stack active | ✅ |
| `§820.10(d)` | Additional traceability for life-sustaining/supporting devices under ISO 7.5.9.2 | Legacy implant/life-support traceability concepts | Traceability system exists; applicability to product classes should be documented | ⚠️ |
| `§820.35(a)` | Complaint record minimum content requirements | Legacy `820.198` details modernized | Complaint process exists; field-level completeness not yet hardcoded | 🔶 |
| `§820.35(b)` | Servicing record minimum content requirements | Legacy `820.200` | Servicing controls conditional by applicability | ⚠️ |
| `§820.35(c)` | UDI recorded per device or batch | Legacy identification/traceability regime modernized | Lot records exist; UDI field consistency should be verified | 🔶 |
| `§820.35(d)` | Confidentiality marking provisions | Legacy public-information handling context | Administrative control possible | ℹ️ |
| `§820.45(a)-(c)` | Labeling/packaging controls + documented release/inspection | Legacy `820.120` intent modernized | Labeling and production controls exist; explicit checklists needed | 🔶 |
| `§820.3` + `§820.7` | Definitions and IBR governance | Legacy part 820 definitions framework | Quality manual/procedural glossary can be updated | ⚠️ |

---

## Part 5: Risk Management Integration Assessment

### Reference basis

- ISO 13485 Practical Guide Clause 7.1 (pp. 93-100)  
- ISO 14971:2019 Clauses 4-10  

### Risk Management File Inventory (current state)

| Document ID | Rev | Title | ISO 14971 Clause Alignment |
|---|---|---|---|
| RM-0018 | D | Risk Management Plan, SILQ Foley Catheter | Clause 4.4 (Risk management plan) |
| RM-0019 | D | Hazard Analysis (HA) Risk Management Report, SILQ Foley Catheter | Clauses 5–6 (Risk analysis, evaluation) |
| RM-0020 | D | DFMEA Risk Management Report, HDX Foley Catheter | Clauses 5–7 (Risk analysis, evaluation, control) |
| RM-0021 | F | SILQ PFMEA | Clauses 5–7 (Process risk analysis and control) |
| RM-0094 | A | Production & Post-Production Risk Review, SILQ | Clause 10 (Production and post-production activities) |
| RM-0141 | A | RMF Review, SILQ 2024 (signed 04-16-2025) | Clause 9 (Overall residual risk evaluation / review) |

### Current-state assessment

- **QMS-level risk-based approach (4.1.2):** Partially demonstrated; product-risk files are strong, system-level process-risk narrative is still distributed.  
- **Design integration (7.3):** Substantially implemented through accessible RM plan, hazard analysis, and FMEA set.  
- **Production integration (7.5):** Present; can be strengthened with clearer traceability from risk controls to production acceptance/monitoring records.  
- **Post-market integration (8.2.1):** Present; closed-loop trigger language from complaints/CAPA into RM updates should be formalized.  
- **RM file accessibility:** Resolved — ZIP archives have been extracted.

### Gap rating

**⚠️ Minor Gap (QMSR-focused integration refinement).**

### Targeted actions

1. Build an ISO 14971 Clause 4-10 trace matrix to specific RM records. **Priority: High**  
2. Add formal rule for complaint/CAPA trend triggers to RM update workflow. **Priority: High**  
3. Ensure management review includes risk-file update status as standing input/output. **Priority: Medium**

---

## Part 6: Structural and Housekeeping Issues

### Confirmed issues impacting QMSR readiness

- **Root-level misplaced files** (~18 QMS files): MR2025 slides, manufacturing procedure duplicate, supplier list, equipment list, training matrix, sales order records, packing slips, and miscellaneous records remain at root instead of in controlled folders.
- **Audit record duplication:** 6 IA2023 files duplicated in IA2024 folder alongside actual Jan 2025 audit records.
- **Folder naming:** `PostMarketSurviellance` is misspelled (should be "Surveillance").
- **One remaining isolated ZIP:** `L.SLQ005.zip` in Manufacturing/C.SLQ001/Specifications has no extracted content.
- **Original ZIP files** remain alongside extracted folders (RM-0018/0019/0020, POs) — should be archived.

### Housekeeping actions

1. Extract remaining labeling ZIP (`L.SLQ005.zip`) into controlled structure. **Priority: High**
2. Complete root-level filing normalization.
3. Remove duplicate audit records in IA2024 package.
4. Archive or remove original ZIP files alongside extracted content.
5. Correct `PostMarketSurviellance` folder spelling.
6. Implement annual records architecture audit.

---

## Part 7: Consolidated Action Plan (QMSR Transition Specific)

| # | Gap Area | ISO 13485 Clause | Priority | Effort | Owner (Suggested) | Action Description | Target Date |
|---|---|---|---|---|---|---|---|
| 1 | Implement `§820.35(a)` complaint-record controls | 8.2.2, 4.2.5 | **Critical** | Low | Quality Specialist | Revise `QM.SLQ021` + complaint form to require all seven `§820.35(a)` data elements; add mandatory checklist signoff and monthly completeness audit | 2026-04-15 |
| 2 | Implement `§820.35(c)` UDI record capture | 7.5.8, 7.5.9 | **Critical** | Medium | VP of RA CA | Add mandatory UDI/UPC capture fields to complaint, DHR review, and servicing records with controlled exception criteria | 2026-04-30 |
| 3 | Implement `§820.45(a)-(c)` labeling/packaging controls | 7.5.1, 4.2.5 | **Critical** | Medium | Director or Manager Manufacturing | Add pre-release labeling verification checklist, documented release authorization, and packaging line-clearance evidence workflow | 2026-05-15 |
| 4 | Implement `§820.35(b)` servicing record minimums | 7.5.4, 4.2.5 | **High** | Low | Director or Manager Manufacturing | Update servicing template to include required fields (device ID, date, personnel, work performed, test/inspection data) and applicability statement | 2026-05-31 |
| 5 | Publish `§820.10(b)` overlay matrix | 7.5.8, 7.5.9, 8.2.3 | **High** | Low | VP of RA CA | Release one controlled ISO-to-regulation matrix mapping parts 830/821/803/806 to SOPs, forms, and objective evidence locations | 2026-05-31 |
| 6 | Execute citation modernization package | 4.1, 4.2.2 | **High** | Medium | VP of QA | Update legacy 820-only citations in Quality Manual and affected SOPs; issue one controlled release with redline rationale and training impact list | 2026-06-30 |
| 7 | Add QMSR readiness block to management review | 5.6 | **High** | Low | President/CEO | Add standing KPI block for complaint completeness, UDI capture, labeling release errors, open transition CAPAs, and audit findings; close MR2025 filing | 2026-06-30 |
| 8 | Add QMSR-focused internal audit module | 8.2.4 | **High** | Low | Quality Specialist | Add dedicated checklist for `§820.10`, `§820.35`, `§820.45`; include objective-evidence sampling rules | 2026-06-30 |
| 9 | Harden risk closed-loop integration | 7.1, 8.2.1, 8.5 | **High** | Medium | VP of QA | Formalize trigger logic linking complaints/CAPA/MDR outcomes to RM updates and management review reporting; publish ISO 14971 clause trace matrix | 2026-07-31 |
| 10 | Equipment control defensibility package | 7.6, 6.3 | **High** | Medium | Director or Manager Manufacturing | Classify each of 16 assets as calibration-required/not-required with technical rationale; close service/calibration evidence gaps for required assets | 2026-08-15 |
| 11 | Formalize QMSR transition trend pack | 8.4, 8.1 | **Medium** | Medium | Quality Specialist | Issue quarterly transition trend pack (record completeness, labeling errors, traceability exceptions, CAPA aging, audit results) | 2026-09-15 |
| 12 | Close structural retrieval risks | 4.2.4, 4.2.5 | **Medium** | Low | Director or Manager Manufacturing | Extract `L.SLQ005.zip`; complete root-level re-filing; remove IA2024 duplicates; archive original ZIP files alongside extracted content | 2026-10-15 |

> **Pending CAPA note:** CAPAs 2025-002 and 2025-003 remain expected pending uploads and are not treated as systemic absence.

---

## Part 8: Standards and References Needed

### Confirmed on file

- ISO 13485:2016  
- ISO 13485:2016 Practical Guide  
- ISO 14971:2019  
- FDA QMSR Final Rule  
- ASTM F623-23 and ASTM F623-25  
- ISO 20696:2018

### Additional recommended references

| Standard / Guidance | Rationale |
|---|---|
| **ISO/TR 24971:2020** | Practical implementation guidance for ISO 14971 integration and documentation depth |
| **IEC 62366-1:2015** | Supports design/post-market usability-related risk integration |
| **IEC 62304:2006+A1:2015** | Needed if SilqQMS software tool is confirmed as QMS-impacting and requiring lifecycle rigor |

---

## Final Leadership Takeaway

Silq is close to QMSR-ready in structure and operational maturity. The remaining work is concentrated in explicit FDA supplemental records (`§820.35`, `§820.45`), citation modernization, and objective-evidence consistency. Executing the prioritized 12-item action plan should close transition risk without broad system redesign, moving the organization to demonstrable QMSR readiness within two to three quarters.
