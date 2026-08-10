# Reference: FileHold Integration Analysis

**Date:** 2026-03-24  
**Purpose:** Ground-truth analysis of every QM document's actual references to FileHold, extracted directly from the `.docx` file contents. Use this to determine which documents need revision for the platform transition and what kind of revision is required.

---

## FileHold Reference Summary

**33 of 46 QM documents reference FileHold. 13 do not.**

### Category A: Deep FileHold Integration (procedures built around FileHold workflows)

| Document ID | Rev | Title | FileHold Refs | Nature of References |
|---|---|---|---|---|
| QM.SLQ014 | B | Electronic Doc System WI | 80 | Entire document describes FileHold — login, navigation, check-in/check-out, review workflows, folder structure, version control. **Complete rewrite required.** |
| QM.SLQ001 | A | Document Control SOP | 76 | FileHold is integral to every procedure step: DCO routing, approval workflows, filing, archiving, obsoleting, external document control, and the full quality records retention table (39 record types listing "FileHold" as storage location). |

### Category B: Multiple Procedural FileHold References

| Document ID | Rev | Title | FileHold Refs | Nature of References |
|---|---|---|---|---|
| QM.SLQ003 | B | Employee Training SOP | 14 | Training records filing, training program storage, matrix maintenance in FileHold |
| QM.SLQ017 | A | Internal Audits SOP | 6 | Audit records filing, schedule maintenance, report storage in FileHold |
| QM.SLQ020 | D | Purchasing Controls SOP | 6 | PO filing, PO log check-in/check-out, closure records in FileHold |
| QM.SLQ036 | E | Sales Order SOP | 5 | Sales order log, approved order storage, glossary definition |
| QM.SLQ015 | B | Supplier QA SOP | 4 | Supplier assessment records, approved supplier list maintenance |
| QM.SLQ004 | A | Design Control Program SOP | 3 | Design file storage references |

### Category C: Light FileHold References (1-2 mentions — typically a glossary definition and/or a records-filing instruction)

| Document ID | Rev | Title | FileHold Refs |
|---|---|---|---|
| QM.SLQ005 | B | Design Project Planning SOP | 2 |
| QM.SLQ006 | A | Design Input SOP | 2 |
| QM.SLQ007 | A | Design Output SOP | 2 |
| QM.SLQ008 | A | Design Review SOP | 2 |
| QM.SLQ009 | A | Design VV SOP | 2 |
| QM.SLQ010 | A | Design Transfer SOP | 2 |
| QM.SLQ012 | B | Risk Management SOP | 2 |
| QM.SLQ013 | B | Risk Analysis SOP | 2 |
| QM.SLQ016 | C | CAPA SOP | 2 |
| QM.SLQ018 | A | Management Review SOP | 2 |
| QM.SLQ021 | D | Product Complaint System SOP | 2 |
| QM.SLQ023 | A | eMDR Submission Work Instruction | 2 |
| QM.SLQ028 | A | Protection of Confidential Patient Info | 2 |
| QM.SLQ029 | A | DHR Review and Approval SOP | 2 |
| QM.SLQ030 | A | Advisory Notices and Recalls SOP | 2 |
| QM.SLQ038 | B | Managing Regulatory Inspections | 2 |
| QM.SLQ043 | A | Work Order SOP | 2 |
| QM.SLQ046 | A | Shipping SOP | 2 |
| QM.SLQ048 | A | Device Master Record SOP | 2 |
| QM.SLQ051 | A | Environmental Monitoring | 2 |
| QM.SLQ027 | E | Quality Manual | 1 |
| QM.SLQ039 | B | Receiving Inspection SOP | 1 |
| QM.SLQ045 | A | Receiving SOP | 1 |
| QM.SLQ049 | A | Workstation Practices SOP | 1 |
| QM.SLQ050 | A | Calibration and Preventive Maintenance SOP | 1 |

### Category D: No FileHold References

| Document ID | Rev | Title |
|---|---|---|
| QM.SLQ002 | B | Good Documentation Practices SOP |
| QM.SLQ011 | A | Statistical Techniques WI |
| QM.SLQ019 | C | Identification and Traceability SOP |
| QM.SLQ022 | A | Medical Device Reporting |
| QM.SLQ025 | A | Quality Planning SOP |
| QM.SLQ026 | C | Part Number Assignment WI |
| QM.SLQ032 | A | Software Validation SOP |
| QM.SLQ033 | A | Post-Market Surveillance SOP |
| QM.SLQ034 | F | Organization Chart |
| QM.SLQ035 | D | Quality Policy |
| QM.SLQ037 | A | Quality Objectives |
| QM.SLQ040 | B | Nonconforming Materials SOP |
| QM.SLQ047 | A | Process Validation SOP |

---

## Note on Legacy 820 Citations

19 of 46 QM documents also contain references to legacy 21 CFR Part 820 section numbers. These are **not relevant to the FileHold platform transition** and will be addressed in a separate regulatory gap analysis project. Do not analyze or include them in the transition plan.

---

## Typical FileHold Reference Patterns

The most common patterns found across the 25 "Category C" documents are:

1. **Glossary definition:** "FileHold: Software based document management system used to electronically store controlled documents."
2. **Records filing instruction:** "Records are to be scanned and imported into FileHold and filed within appropriate [folder name] folder."

These are straightforward text replacements — "FileHold" becomes "SilqQMS" (or whatever the team decides to call the system in procedures), and procedural language about scanning/importing is updated to reflect the new upload workflow.
