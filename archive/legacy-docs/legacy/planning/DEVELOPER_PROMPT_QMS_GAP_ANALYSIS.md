# Developer Prompt: QMS Gap Analysis — ISO 13485:2016 & QMSR Alignment

**Date:** 2026-03-16  
**Requested by:** Ethan Rao, Director R&D, QA, Regulatory Affairs  
**Purpose:** Perform a structured gap analysis of the Silq Technologies QMS against ISO 13485:2016 and the FDA QMSR (effective Feb 2, 2026), producing a team-ready report with prioritized action items.

---

## Background & Context

Silq Technologies is a medical device manufacturer with two product families:
1. **C.SLQ001 Suspension** — a proprietary antimicrobial surface treatment
2. **ClearTract Foley Catheters** — 3 SKUs (14 Fr, 16 Fr, 18 Fr) with the Silq surface treatment

The company holds three 510(k) clearances (K192034, K221625, K222118) and is FDA-registered.

### Regulatory Landscape

- **FDA QMSR** became effective **February 2, 2026**. This rule fundamentally restructures 21 CFR Part 820 by incorporating ISO 13485:2016 by reference, rather than maintaining the legacy FDA-specific QSR clauses. The practical effect is that FDA-regulated manufacturers must now demonstrate conformity to ISO 13485:2016 as the baseline, with a small number of FDA-specific additions retained.
- Silq's QMS was **previously adequate against the legacy 21 CFR Part 820** (pre-QMSR). The gap analysis should therefore focus on identifying **what changes are required to align with ISO 13485:2016 requirements that were not explicitly required under the old 820**, as well as any new QMSR-specific additions.
- The company recently underwent an **FDA inspection (Oct 2025)** resulting in a Form 483 with 2 observations, which generated CAPAs 2025-002 and 2025-003. These CAPAs will be uploaded in the future and should be noted but not analyzed in depth.

### Input Artifacts

You have the following critical input documents — **read all of them before starting**:

1. **QMS Document Inventory** — `docs/review/QMS_DOCUMENT_INVENTORY_2026_03.md`  
   This is a comprehensive, section-by-section catalog of every QMS document in the repository. It contains document inventory tables, SOP cross-reference matrices, manufacturing coverage, employee training summaries, audit history, supplier management, risk management file inventory, and identified structural issues. **Read this document in its entirety before starting.**

2. **ISO 13485:2016 — Medical Devices — A Practical Guide** — `RegulatoryStandards&Approvals/ISO/ISO 13485 2016 Medical devices Practical Guide.pdf`  
   This is a 220-page handbook published by ISO/TC 210 that provides clause-by-clause guidance on ISO 13485:2016. For each clause, it reproduces the standard text, explains the intent, and provides practical guidance. **Use this as your primary reference for interpreting requirements.** When citing guidance, reference the Practical Guide page number so the team can look it up.

3. **ISO 13485:2016** — `RegulatoryStandards&Approvals/ISO/ISO_13485_2016.pdf`  
   The actual standard (46 pages). Use this for the precise requirement text when needed.

4. **ISO 14971:2019** — `RegulatoryStandards&Approvals/ISO/ISO_14971_2019(en).pdf`  
   The international standard for risk management of medical devices. This is referenced throughout ISO 13485:2016 and is central to the QMSR's risk-based approach. Use this to assess whether Silq's risk management SOPs (QM.SLQ012, QM.SLQ013) and risk management files (RM-0018 through RM-0141) align with ISO 14971 requirements. When relevant, cite specific ISO 14971 clause numbers in your gap findings.

5. **FDA QMSR Final Rule** — `RegulatoryStandards&Approvals/ISO/2024-01709. FDAQMSRFinalRule.pdf`  
   The Federal Register publication (87 FR 68905) of the Quality Management System Regulation final rule. This is the authoritative source for understanding which legacy 21 CFR 820 provisions were replaced by ISO 13485 incorporation, which were retained as FDA-specific additions, and any new requirements. **Use this document for Part 2 (QMSR Transition Overview) and Part 4 (QMSR-Specific Requirements Crosswalk).** Cite specific sections/pages of the final rule when identifying FDA-specific requirements that go beyond ISO 13485.

---

## Objective

Produce a single output document: **`docs/review/QMS_GAP_ANALYSIS_ISO13485_QMSR_2026_03.md`**

This document will be **shared with the Silq leadership team** and must be:
- **Comprehensive** — covering every ISO 13485:2016 clause
- **Digestible** — starting high-level with executive summaries before drilling into detail
- **Actionable** — every gap must have a clear remediation recommendation
- **Prioritized** — gaps ranked by regulatory risk and effort
- **Referenced** — citing Practical Guide pages so the team can self-educate

---

## Scope & Focus Areas

### IN SCOPE — Focus Here

1. **ISO 13485:2016 clause-by-clause gap assessment** against the documented QMS
2. **QMSR transition gaps** — requirements that are new or materially different under QMSR vs. legacy 820
3. **QMS documentation structure** — Quality Manual (QM.SLQ027 Rev E), Quality Policy (QM.SLQ035 Rev D), quality objectives, and organizational structure
4. **Document control and record control** processes (Clause 4.2)
5. **Management responsibility** — management review completeness, quality planning (Clause 5)
6. **Risk management integration** — ISO 14971 alignment, risk-based approach at QMS level (Clause 7.1, and throughout)
7. **Design controls** — completeness of the DHF and design control SOPs (Clause 7.3)
8. **Purchasing and supplier management** — supplier qualification, purchasing controls (Clause 7.4)
9. **Production and service provision** — process validation, identification & traceability, product preservation (Clause 7.5)
10. **CAPA system** — process adequacy, open CAPAs, effectiveness verification (Clause 8.5)
11. **Post-market surveillance and complaint handling** — feedback, complaints, MDR reporting (Clause 8.2)
12. **Internal audit program** — adequacy and coverage (Clause 8.2.4)
13. **Monitoring, measurement, and data analysis** (Clauses 8.2.5, 8.2.6, 8.4)
14. **Infrastructure and work environment** (Clauses 6.3, 6.4)

### OUT OF SCOPE — Acknowledge but Don't Deep-Dive

1. **ASTM F623 testing specifics** — Note that ASTM F623-23 and F623-25 are on file but do not perform a clause-by-clause analysis of test method compliance. Simply confirm the standard is available and referenced in relevant DMRs.
2. **Individual employee training record completeness** — The inventory already identifies training gaps. Acknowledge the training system exists and note any systemic issues, but do not build per-employee, per-SOP training matrices. Focus instead on whether the training *process* (QM.SLQ003) meets ISO 13485 Clause 6.2 requirements.
3. **Content review of individual DHRs** — DHR completeness is already cataloged in the inventory. Reference those findings but don't re-analyze individual lot records.
4. **CAPAs 2025-002 and 2025-003** — Note that these are pending upload. Do not treat their absence as a gap; they are expected.

---

## Output Document Structure

### Part 1: Executive Summary (1–2 pages)

Write this section for a busy executive who needs to understand the overall posture in 5 minutes.

- **Overall QMS Maturity Assessment** — A qualitative rating (e.g., "Substantially Aligned," "Gaps Identified — Moderate Risk," etc.)
- **QMSR Readiness Score** — A simple visual: how many of the ISO 13485 major clauses are covered vs. have gaps
- **Top 5 Priority Gaps** — The 5 most important items to address, with brief descriptions
- **Estimated Remediation Effort** — High-level estimate (Low/Medium/High per gap area)
- **Key Message** — A 2–3 sentence summary the team can internalize: "Our QMS is [X]. The QMSR transition requires [Y]. The highest-priority actions are [Z]."

### Part 2: QMSR Transition Overview (1–2 pages)

Using the **QMSR Final Rule** (`RegulatoryStandards&Approvals/ISO/2024-01709. FDAQMSRFinalRule.pdf`) as your authoritative source, explain what the QMSR changes in plain language for the team:
- What changed on Feb 2, 2026
- What "incorporation by reference" means practically
- Which legacy 820 subparts were retired vs. retained (cite specific sections from the Final Rule)
- What the FDA-specific additions are that supplement ISO 13485 (e.g., complaint files, DHR requirements, records — cite the specific new §820 sections from the Final Rule)
- What this means for Silq's existing SOPs that reference "21 CFR 820.XX" clauses
- Any transition period or enforcement discretion provisions noted in the Final Rule

### Part 3: Clause-by-Clause Gap Analysis

For **each major clause** of ISO 13485:2016 (Clauses 4 through 8), produce a subsection with:

#### 3.X — Clause [Number]: [Clause Title]

**Practical Guide Reference:** Page(s) [XX–YY] of the ISO 13485:2016 Practical Guide

**a) Requirement Summary**  
A plain-language summary of what the clause requires (2–4 sentences). Do not reproduce the full standard text.

**b) Current Silq QMS Coverage**  
Map the existing Silq documents/processes to this clause, referencing the QMS Document Inventory. For example:
- "Addressed by QM.SLQ001 Rev A (Document Control SOP), with Forms FM1-QM.SLQ001 and FM2-QM.SLQ001"
- "Management reviews conducted annually (MR2022–MR2025) with minutes and slides on file"

**c) Gap Assessment**  
Rate the gap using this scale:

| Rating | Meaning |
|--------|---------|
| ✅ **Conforming** | Requirement is fully addressed by existing documentation and practice |
| ⚠️ **Minor Gap** | Requirement is substantially addressed but may need updates (e.g., terminology changes, minor procedural additions) |
| 🔶 **Moderate Gap** | Requirement is partially addressed; specific additions or revisions are needed |
| 🔴 **Major Gap** | Requirement is not adequately addressed; new procedures, records, or processes may be needed |
| ℹ️ **Not Applicable** | Requirement does not apply to Silq's operations |

**d) Specific Findings**  
Bullet-pointed list of specific observations. For each finding:
- State what is missing or inadequate
- Reference the specific Practical Guide page(s) for context
- Note if this is a QMSR-specific change vs. an existing ISO 13485 requirement

**e) Recommended Actions**  
Specific, actionable remediation steps. For each:
- What needs to be done
- Which existing SOP(s) or document(s) need revision
- Priority: **Critical** (address within 30 days), **High** (within 90 days), **Medium** (within 6 months), **Low** (within 12 months)

#### Clauses to Cover

Use the following sub-clause breakdown. You don't need a separate section for every sub-sub-clause, but group them logically:

| Section | Clauses | Practical Guide Pages |
|---------|---------|----------------------|
| 3.1 | 4.1 General Requirements (QMS processes, risk-based approach) | pp. 31–42 |
| 3.2 | 4.2.1–4.2.2 Documentation Requirements, Quality Manual | pp. 43–50 |
| 3.3 | 4.2.3 Medical Device File | pp. 50–53 |
| 3.4 | 4.2.4–4.2.5 Control of Documents, Control of Records | pp. 53–58 |
| 3.5 | 5.1–5.4 Management Commitment, Customer Focus, Quality Policy, Planning | pp. 59–68 |
| 3.6 | 5.5 Responsibility, Authority, Communication | pp. 68–71 |
| 3.7 | 5.6 Management Review | pp. 71–78 |
| 3.8 | 6.1–6.2 Resource Management, Human Resources (Competence, Training) | pp. 79–87 |
| 3.9 | 6.3–6.4 Infrastructure, Work Environment, Contamination Control | pp. 87–92 |
| 3.10 | 7.1 Planning of Product Realization (including risk management) | pp. 93–100 |
| 3.11 | 7.2 Customer-Related Processes | pp. 100–106 |
| 3.12 | 7.3 Design and Development (all sub-clauses) | pp. 106–136 |
| 3.13 | 7.4 Purchasing | pp. 136–146 |
| 3.14 | 7.5.1–7.5.4 Production Controls, Cleanliness, Installation, Servicing | pp. 146–158 |
| 3.15 | 7.5.5–7.5.7 Sterile device requirements, Process Validation | pp. 158–162 |
| 3.16 | 7.5.8–7.5.11 Identification, Traceability, Customer Property, Preservation | pp. 162–165 |
| 3.17 | 7.6 Control of Monitoring and Measuring Equipment | pp. 165–170 |
| 3.18 | 8.1 General (Measurement, Analysis, Improvement) | pp. 170–172 |
| 3.19 | 8.2.1–8.2.3 Feedback, Complaint Handling, Reporting to Regulatory Authorities | pp. 172–184 |
| 3.20 | 8.2.4 Internal Audit | pp. 184–189 |
| 3.21 | 8.2.5–8.2.6 Monitoring and Measurement of Processes and Product | pp. 189–192 |
| 3.22 | 8.3 Control of Nonconforming Product | pp. 192–197 |
| 3.23 | 8.4 Analysis of Data | pp. 197–198 |
| 3.24 | 8.5 Improvement, Corrective Action, Preventive Action | pp. 198–208 |

### Part 4: QMSR-Specific Requirements Crosswalk

Using the **QMSR Final Rule** (`RegulatoryStandards&Approvals/ISO/2024-01709. FDAQMSRFinalRule.pdf`), create a focused table showing **every FDA-specific addition** that remains under the revised 21 CFR Part 820 and is NOT covered by ISO 13485 alone:

| QMSR Provision (new §820.XX) | Description | Derived From (legacy 820) | Silq Coverage | Gap? |
|-------------------------------|-------------|--------------------------|---------------|------|

Derive this table directly from the Final Rule text. Include items such as (but verify and complete from the actual rule):
- Complaint file requirements
- Device History Record requirements
- Device Master Record requirements
- Record retention periods
- Unique Device Identification (UDI) requirements
- Reports of corrections and removals
- Any other FDA-specific additions enumerated in the Final Rule

For each provision, cite the specific new §820 section number from the QMSR and note the corresponding legacy 820 section it derives from.

### Part 5: Risk Management Integration Assessment

Given that ISO 14971 integration is a central theme under QMSR, provide a focused assessment using **ISO 14971:2019** (`RegulatoryStandards&Approvals/ISO/ISO_14971_2019(en).pdf`) as the reference standard:

- Does the QMS demonstrate a risk-based approach at the QMS process level (ISO 13485 Clause 4.1.2)?
- Is risk management integrated into design controls (Clause 7.3)?
- Is risk management integrated into production controls (Clause 7.5)?
- Is risk management integrated into post-market surveillance (Clause 8.2.1)?
- Are the RM ZIP files (RM-0018, RM-0019, RM-0020) a concern for accessibility?
- Is the PFMEA (RM-0021 Rev F) current?
- Is the Production & Post-Production Review (RM-0094) adequate?
- Do the risk management SOPs (QM.SLQ012, QM.SLQ013) align with the ISO 14971:2019 process requirements (Clauses 4–10 of ISO 14971)?
- Is there evidence of a complete Risk Management File per ISO 14971 Clause 4.5?

Reference Practical Guide pp. 93–100 (Clause 7.1) for the ISO 13485 risk management requirements, and cross-reference against ISO 14971:2019 clause structure for completeness.

### Part 6: Structural & Housekeeping Issues

Summarize the structural issues identified in the QMS Document Inventory (Section 12) and add any new issues discovered during the gap analysis:
- Misplaced files and duplicates
- ZIP files that need extraction for regulatory accessibility
- Naming convention issues
- Filing actions needed

### Part 7: Consolidated Action Plan

Create a single, prioritized remediation table:

| # | Gap Area | ISO 13485 Clause | Priority | Effort | Owner (Suggested) | Action Description | Target Date |
|---|----------|-----------------|----------|--------|-------------------|-------------------|-------------|

Sort by priority (Critical → High → Medium → Low), then by effort (Low → High within each priority).

For "Owner (Suggested)," use role titles from the Org Chart (QM.SLQ034), not individual names.

### Part 8: Standards & References Needed

List any standards that the team should procure or have available to support the remediation work. Check against what is already in `RegulatoryStandards&Approvals/` and note what's missing.

---

## Important Instructions

1. **Read the QMS Document Inventory (`docs/review/QMS_DOCUMENT_INVENTORY_2026_03.md`) in full before starting.** This is your primary source of truth for what exists in the QMS. Do not re-explore the file system — rely on the inventory.

2. **Read the Practical Guide (`RegulatoryStandards&Approvals/ISO/ISO 13485 2016 Medical devices Practical Guide.pdf`) clause by clause** as you work through each section of Part 3. Reference specific page numbers from this guide so the team can follow along.

3. **Read the ISO 13485:2016 standard (`RegulatoryStandards&Approvals/ISO/ISO_13485_2016.pdf`)** for precise requirement language when needed.

4. **Read the ISO 14971:2019 standard (`RegulatoryStandards&Approvals/ISO/ISO_14971_2019(en).pdf`)** for risk management requirements. Cross-reference against Silq's risk management SOPs and files when assessing Clause 7.1 and Part 5.

5. **Read the QMSR Final Rule (`RegulatoryStandards&Approvals/ISO/2024-01709. FDAQMSRFinalRule.pdf`)** to identify the specific FDA-specific additions that supplement ISO 13485. Use this for Part 2 and Part 4. You do not need to read every page of preamble discussion — focus on the actual regulatory text (the amended §820 sections) and the summary of changes.

6. **Assume the QMS was previously adequate against legacy 21 CFR Part 820.** Do not flag items that were already required under the old 820 unless there is evidence from the inventory that they are actually missing. Focus your "QMSR transition" findings on genuinely new or changed requirements.

7. **Keep the tone constructive and team-appropriate.** This is an internal working document, not an audit report. Use language like "Opportunity to strengthen..." or "Recommend updating..." rather than "Failure to comply with..."

8. **Be specific about what the Practical Guide says.** When you cite a Practical Guide page, briefly summarize the relevant guidance so the reader gets value without having to immediately open the book. For example: "The Practical Guide (p. 72) notes that management review should include analysis of data trends, not just a presentation of metrics."

9. **Do not modify any QMS files.** The only file you create is the output document.

10. **The document should be self-contained.** A reader with access to the Practical Guide, the standard, ISO 14971, and the QMSR Final Rule should be able to understand every gap, why it matters, and what to do about it — without needing to consult additional sources.

11. **Note CAPA 2025-002 and CAPA 2025-003 as pending.** They are expected to be uploaded in the future and should not be flagged as a systemic gap. Acknowledge their absence and move on.

12. **For sterile device requirements (7.5.5, 7.5.7):** Silq does not perform sterilization in-house. ClearTract catheters are sterilized by a contract sterilizer (Steripax). Note this but assess whether the QMS adequately controls the outsourced sterilization process.

13. **For software validation (QM.SLQ032):** Note that the SilqQMS application exists in the repository as a software tool. If it is used in quality system processes, it would need to be validated per Clause 4.1.6. Flag this as a question for the team.

---

## Practical Guide Page-to-Clause Quick Reference

Use this mapping when citing the Practical Guide (page numbers refer to the PDF page numbers printed at the bottom of each page):

| Clause | Topic | Practical Guide Pages |
|--------|-------|----------------------|
| Foreword | QMS overview, purpose of handbook | pp. 6–9 |
| 0.1–0.4 | Introduction, process approach, compatibility | pp. 10–22 |
| 1 | Scope | pp. 23–26 |
| 4.1 | General QMS requirements, risk-based approach | pp. 31–42 |
| 4.2.1 | Documentation general | pp. 43–46 |
| 4.2.2 | Quality manual | pp. 46–50 |
| 4.2.3 | Medical device file | pp. 50–53 |
| 4.2.4 | Control of documents | pp. 53–56 |
| 4.2.5 | Control of records | pp. 56–58 |
| 5.1 | Management commitment | pp. 59–61 |
| 5.2 | Customer focus | pp. 62–63 |
| 5.3 | Quality policy | pp. 63–65 |
| 5.4 | Planning, quality objectives | pp. 65–68 |
| 5.5 | Responsibility, authority, communication | pp. 68–71 |
| 5.6 | Management review (input, output) | pp. 71–78 |
| 6.1 | Provision of resources | pp. 79–80 |
| 6.2 | Human resources, competence, training | pp. 80–87 |
| 6.3 | Infrastructure | pp. 87–89 |
| 6.4 | Work environment, contamination control | pp. 89–92 |
| 7.1 | Planning of product realization, risk management | pp. 93–100 |
| 7.2 | Customer-related processes | pp. 100–106 |
| 7.3.1–7.3.2 | Design and development general, planning | pp. 106–110 |
| 7.3.3 | Design and development inputs | pp. 110–112 |
| 7.3.4 | Design and development outputs | pp. 112–114 |
| 7.3.5 | Design and development review | pp. 114–117 |
| 7.3.6 | Design and development verification | pp. 117–120 |
| 7.3.7 | Design and development validation | pp. 120–123 |
| 7.3.8 | Design and development transfer | pp. 123–126 |
| 7.3.9 | Design and development changes | pp. 126–129 |
| 7.3.10 | Design and development files | pp. 129–132 |
| 7.4.1 | Purchasing process | pp. 136–140 |
| 7.4.2 | Purchasing information | pp. 140–142 |
| 7.4.3 | Verification of purchased product | pp. 142–146 |
| 7.5.1 | Control of production and service provision | pp. 146–150 |
| 7.5.2 | Cleanliness of product | pp. 150–151 |
| 7.5.3–7.5.4 | Installation, servicing activities | pp. 151–153 |
| 7.5.5 | Sterile medical device requirements | pp. 153–154 |
| 7.5.6 | Validation of processes | pp. 154–158 |
| 7.5.7 | Sterilization validation | pp. 158–159 |
| 7.5.8 | Identification | pp. 159–160 |
| 7.5.9 | Traceability | pp. 160–162 |
| 7.5.10 | Customer property | pp. 162–163 |
| 7.5.11 | Preservation of product | pp. 163–165 |
| 7.6 | Monitoring and measuring equipment | pp. 165–170 |
| 8.1 | General (measurement framework) | pp. 170–172 |
| 8.2.1 | Feedback (post-market surveillance) | pp. 172–176 |
| 8.2.2 | Complaint handling | pp. 176–180 |
| 8.2.3 | Reporting to regulatory authorities | pp. 180–184 |
| 8.2.4 | Internal audit | pp. 184–189 |
| 8.2.5 | Monitoring and measurement of processes | pp. 189–191 |
| 8.2.6 | Monitoring and measurement of product | pp. 191–192 |
| 8.3 | Control of nonconforming product | pp. 192–197 |
| 8.4 | Analysis of data | pp. 197–198 |
| 8.5.1 | Improvement — general | pp. 198–199 |
| 8.5.2 | Corrective action | pp. 199–205 |
| 8.5.3 | Preventive action | pp. 205–208 |
| Annex A | Guidance for small organizations | pp. 209–214 |

---

## Tone & Style

- **Audience:** Silq leadership team — a mix of technical and business roles. Assume they understand QMS fundamentals but may not know ISO 13485 clause-by-clause.
- **Voice:** Consultative, constructive, professional. Think "experienced RA/QA consultant presenting to a client" — not "auditor issuing findings."
- **Length:** Target 25–40 pages. Enough to be thorough, short enough to be read.
- **Formatting:** Use tables, bullet points, and color-coded gap ratings liberally. Minimize wall-of-text paragraphs.

---

## Additional Standards Recommendation

The following standards are now available in `RegulatoryStandards&Approvals/ISO/`:

- ✅ **ISO 13485:2016** — On file
- ✅ **ISO 13485:2016 Practical Guide** — On file
- ✅ **ISO 14971:2019** — On file (`ISO_14971_2019(en).pdf`)
- ✅ **FDA QMSR Final Rule** — On file (`2024-01709. FDAQMSRFinalRule.pdf`)
- ✅ **ASTM F623-23 and F623-25** — On file
- ✅ **ISO 20696:2018** — On file

In Part 8 of the output, note any *additional* standards the team should consider procuring based on gaps identified during the analysis. Candidates may include:

- **ISO/TR 24971:2020** — Guidance on the application of ISO 14971. Helpful companion document.
- **IEC 62366-1:2015** — Usability Engineering for Medical Devices. Referenced by the Practical Guide in the design controls section.
- **IEC 62304:2006+A1:2015** — Medical device software lifecycle processes. Relevant if the SilqQMS application requires validation.
- Any others identified during the analysis.

Confirm these recommendations and add any others you identify during the analysis.
