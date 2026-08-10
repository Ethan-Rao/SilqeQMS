# Developer Prompt: QMSR / ISO 13485 Gap Analysis

**Date:** 2026-03-24  
**Requested by:** Ethan Rao, Director R&D, QA, Regulatory Affairs  
**Purpose:** Produce a structured gap analysis identifying where Silq's existing QMS procedures need to be updated to align with the FDA QMSR and ISO 13485:2016.

---

## Your Task

Write a gap analysis report and save it at:

**`docs/gap-analysis/Output/QMS_GAP_ANALYSIS_QMSR_ISO13485_2026_03.md`**

This document will be shared with the Silq leadership team. It should clearly explain what the QMSR regulatory change means for our company, walk through our existing QMS clause by clause, identify gaps, and provide actionable recommendations — all in language that a management team can follow without being regulatory specialists.

---

## Audience and Tone

- **Primary audience:** CEO, VP of QA, VP of RA, Director of Manufacturing, Quality Specialist
- **Tone:** Professional, clear, and direct. Explain regulatory concepts when you introduce them. Avoid jargon without context.
- **Length:** Aim for a thorough but readable document. Each clause section should be concise — a few paragraphs, not pages. Use tables and bullet points for clarity.
- **Critical rule:** You are identifying gaps and making observations. You are NOT rewriting procedures or making operational decisions. Leadership will decide how to address each gap.

---

## Key Assumptions

1. **Silq's QMS was previously adequate against the old 21 CFR Part 820.** The existing procedures were written to comply with the legacy QS regulation. This gap analysis is about identifying what *additional or different* requirements arise from the QMSR's incorporation of ISO 13485:2016 by reference, plus the FDA's supplementary provisions. It is not a from-scratch compliance audit.

2. **Do not deep-dive into ASTM testing specifics.** ASTM F623 (catheter testing) is a product-specific test standard. Note it exists and move on — this analysis is about QMS structure, not test method content.

3. **Do not deep-dive into individual employee training records.** The training *system* (SOP, forms, matrix approach) is in scope. Whether specific individuals have completed specific courses is not.

4. **Do not deep-dive into individual lot records, complaint files, or CAPA records.** You may reference them for evidence of process maturity, but the analysis is at the *procedural* level (does the SOP address the requirement?), not the *record* level (has every record been filled out correctly?).

5. **A separate transition plan covers the FileHold-to-SilqQMS platform migration.** That project is documented at `docs/transition-plan/`. Do NOT analyze or comment on FileHold references in procedures — that is handled elsewhere. If you encounter "FileHold" while reading documents, ignore it for purposes of this analysis.

---

## What You Must Read Before Writing

### Mandatory resources (read these first — they are pre-built reference materials):

1. **QM Document Register with ISO 13485 clause mapping:**  
   `docs/gap-analysis/Resources/REFERENCE_QM_DOCUMENT_REGISTER.md`  
   This is your master reference. It maps all 46 QM documents to their ISO 13485 clauses, lists legacy 820 citations, and provides file paths to the readable text of every document.

2. **Legacy 820 Citation Analysis:**  
   `docs/gap-analysis/Resources/REFERENCE_LEGACY_820_CITATIONS.md`  
   Shows which 19 documents contain explicit 820.xx section references and where those citations appear.

3. **Regulatory Standards Index:**  
   `docs/gap-analysis/Resources/REFERENCE_REGULATORY_STANDARDS_INDEX.md`  
   Index of all available regulatory documents with file paths.

### Mandatory regulatory standards (read in full — these are the standards you are analyzing against):

4. **ISO 13485:2016 standard text:**  
   `docs/QMS-Readable-Texts/11-RegulatoryStandards/ISO -- ISO_13485_2016.md`  
   Read the full standard. You need to understand every clause at the requirement level (the "shall" statements).

5. **FDA QMSR Final Rule:**  
   `docs/QMS-Readable-Texts/11-RegulatoryStandards/ISO -- 2024-01709. FDAQMSRFinalRule.md`  
   Focus on: Summary of Major Provisions, Supplementary Provisions (§820.35, §820.45, §820.10(b)), Conforming Amendments, and Effective Date / Implementation Strategy.

6. **ISO 14971:2019 (Risk Management):**  
   `docs/QMS-Readable-Texts/11-RegulatoryStandards/ISO -- ISO_14971_2019(en).md`  
   Read at least the clause structure and key requirements. ISO 13485 references risk management throughout, and the QMSR emphasizes risk-based approaches.

7. **ISO 13485 Practical Guide:**  
   `docs/QMS-Readable-Texts/11-RegulatoryStandards/ISO -- ISO 13485 2016 Medical devices Practical Guide.md`  
   Use this as interpretive guidance. When you identify a gap, reference the relevant Practical Guide page(s) so leadership can look up the context.

### Mandatory QM documents (read in full):

8. **Quality Manual:** `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ027 E Quality Manual.md`  
   This is the foundation — it maps the entire QMS structure and declares clause exclusions.

9. **Document Control SOP:** `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ001 A Document Control SOP.md`  
   Core procedure for clause 4.2.

10. **Risk Management SOP + Risk Analysis SOP:**  
    `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ012 B Risk Management SOP.md`  
    `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ013 B Risk Analysis SOP.md`  
    Critical for assessing ISO 14971 alignment.

11. **CAPA SOP:** `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ016 C CAPA SOP.md`  
    Key for clause 8.5 and §820.45.

12. **Management Review SOP:** `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ018 A Management Review SOP.md`  
    Key for clause 5.6.

13. **Product Complaint System SOP:** `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ021 D Product Complaint System SOP.md`  
    Key for clause 8.2.2 and §820.35.

### Additional QM documents (read as needed for specific clauses):

Use the document register to identify which QM documents cover the clause you are analyzing, then read those documents. The full text of all 46 QM procedures is available at `docs/QMS-Readable-Texts/01-QM-Documents/`.

You may also browse the subsystem evidence folders listed in the document register (Audits, CAPAs, DHF, Equipment, Manufacturing, NCMR, Post-Market Surveillance, Risk Management, Suppliers, Purchasing, Employee Training) for evidence of process maturity. These are at `docs/QMS-Readable-Texts/02-*` through `docs/QMS-Readable-Texts/16-*`.

---

## Context: What Changed and Why This Analysis Is Needed

### The Regulatory Change

On February 2, 2024, the FDA published the Quality Management System Regulation (QMSR) final rule, which fundamentally restructures 21 CFR Part 820. The key change: instead of prescribing quality system requirements directly in the regulation text (as the old Part 820 did), the QMSR incorporates ISO 13485:2016 by reference. This means that compliance with ISO 13485 — the international consensus standard for medical device QMS — now *is* the FDA requirement.

However, the QMSR is not a pure adoption of ISO 13485. The FDA retained certain supplementary provisions that go beyond ISO 13485, primarily in the areas of:
- **§820.10(b):** Lists specific FDA regulatory requirements (UDI under 21 CFR 830, MDR under 21 CFR 803, corrections/removals under 21 CFR 806, reports under 21 CFR 4) that must be addressed by the QMS.
- **§820.35:** Supplementary requirements for complaint handling, including specific record-keeping expectations and connections to MDR reporting.
- **§820.45:** Supplementary requirements for corrective and preventive action procedures.

### What This Means for Silq

Silq's QMS was built to comply with the old 21 CFR Part 820. Many requirements overlap with ISO 13485 — the old 820 was already "substantially similar." But ISO 13485 introduces some concepts and requirements that the old 820 did not explicitly require, and the QMSR's supplementary provisions add FDA-specific layers on top of ISO 13485.

This gap analysis answers the question: **Where does our existing QMS fall short of ISO 13485 + QMSR requirements, and what needs to change?**

### Quality Manual Exclusions

Per QM.SLQ027 Rev E, Silq has formally excluded the following ISO 13485 clauses with documented justification:
- 7.5.3 (Installation activities) — products ship ready to use
- 7.5.4 (Servicing activities) — no servicing required
- 7.5.9.2 (Implantable device requirements) — not an implantable device manufacturer
- 7.5.10 (Customer property) — no physical customer property

Verify that these exclusions are adequately documented and still justified, but do not treat them as gaps.

---

## Document Structure

Write the gap analysis with the following sections:

### 1. Executive Summary

One page maximum. Answer these questions:
- What is the QMSR and when did it take effect?
- What is Silq's overall readiness posture? (e.g., "generally well-positioned with targeted gaps in X, Y, and Z areas")
- How many gaps were identified and at what severity level?
- What are the top 3-5 priority items leadership should focus on first?

### 2. Background: The QMSR Regulatory Change

Two pages maximum. Explain:
- What changed (old 820 → QMSR incorporating ISO 13485)
- Why the FDA made this change (harmonization with international framework)
- The effective date and compliance timeline
- What "supplementary provisions" means — where the FDA goes beyond ISO 13485
- What this analysis covers and what it does not (scope boundaries)

### 3. Methodology

Brief section explaining:
- How this analysis was conducted (clause-by-clause review of ISO 13485 against existing QM procedures)
- What documents were reviewed
- How gaps are categorized (see Gap Classification below)

### 4. Clause-by-Clause Analysis

This is the core of the report. Walk through each major ISO 13485:2016 clause section and assess Silq's current procedural coverage.

**For each clause (4 through 8 and their subclauses):**

1. **State the requirement** — one or two sentences summarizing what ISO 13485 requires. Use the "shall" language from the standard.
2. **Identify the current Silq procedure(s)** — which QM document(s) address this clause (use the document register cross-reference).
3. **Assess the gap** — Does the current procedure adequately address the ISO 13485 requirement?
   - If yes: state that briefly and move on.
   - If there is a gap: describe it specifically (what's missing or insufficient).
4. **Note the Practical Guide reference** — include the relevant page number(s) from the ISO 13485 Practical Guide so leadership can look up additional context.
5. **Assign a gap classification** (see below).

**Gap Classification:**

| Level | Meaning |
|---|---|
| **Adequate** | Current procedure substantially addresses the requirement. No action needed beyond minor citation updates. |
| **Minor Gap** | Requirement is partially addressed but the procedure lacks specific language, a required element, or explicit documentation of a practice that likely exists informally. |
| **Significant Gap** | The requirement is not adequately addressed by any current procedure. A revision or new procedure is needed. |
| **Not Applicable** | The clause has been formally excluded per the Quality Manual, with documented justification. |

You do not need to analyze every single sub-sub-clause in exhaustive detail. Group related subclauses where appropriate (e.g., 7.3.2 through 7.3.10 can be covered as a "Design and Development" section if the assessment is similar across subclauses). But do break out any subclause where you identify a gap — leadership needs to know exactly which requirement is not met.

**Clauses to give particular attention to:**
- **4.2.3 (Medical device file)** — This is an ISO 13485 concept that the old 820 did not use. Silq may or may not have an equivalent.
- **7.1 (Planning of product realization)** — ISO 13485 requires explicit risk management integration per ISO 14971.
- **7.5.6 (Validation of processes)** — Check alignment with ISO 13485's specific validation requirements.
- **8.2.1 (Feedback)** — ISO 13485 requires a documented procedure for feedback, including early warning of quality problems. This is broader than the old 820's complaint handling focus.
- **8.2.2 (Complaint handling)** — Compare against §820.35 supplementary requirements.
- **8.5.2/8.5.3 (Corrective/Preventive action)** — Compare against §820.45 supplementary requirements.

### 5. QMSR Supplementary Provisions Analysis

Separate section specifically addressing the FDA's supplementary provisions that go beyond ISO 13485:

- **§820.10(b)** — Does Silq's QMS adequately address UDI (21 CFR 830), MDR (21 CFR 803), corrections/removals (21 CFR 806), and combination product requirements (21 CFR 4)?
- **§820.35** — Complaint handling supplementary requirements. Compare against QM.SLQ021 and QM.SLQ022.
- **§820.45** — CAPA supplementary requirements. Compare against QM.SLQ016.

### 6. Risk Management Alignment (ISO 14971)

A focused section on how well Silq's risk management procedures (QM.SLQ012, QM.SLQ013) and risk management files align with ISO 14971:2019. This is important because ISO 13485 references risk management throughout, and the QMSR emphasizes risk-based approaches.

Assess:
- Does the risk management SOP reference ISO 14971:2019 (or an earlier version)?
- Are the key ISO 14971 process steps (risk analysis, risk evaluation, risk control, residual risk evaluation, risk management review, production/post-production monitoring) addressed procedurally?
- Is there evidence of risk management files for Silq's products? (Check `docs/QMS-Readable-Texts/12-RiskManagement/`)

### 7. Legacy 820 Citation Update Requirements

Brief section noting that 19 QM documents contain explicit references to legacy 820 section numbers (e.g., "820.40", "820.198") that correspond to the old Part 820 structure. These citations need to be updated to reference either the QMSR section numbers or the corresponding ISO 13485 clauses.

Use the data from `docs/gap-analysis/Resources/REFERENCE_LEGACY_820_CITATIONS.md`. Present a summary table showing each document's legacy citation and what the updated reference should be (QMSR section or ISO 13485 clause).

This is a bounded, mechanical task — it does not represent a procedural gap, just an editorial update to bring citations current.

### 8. Summary of Gaps and Recommended Priorities

Closing section that:
1. Lists all identified gaps in a summary table: Document ID, ISO 13485 clause, gap description, classification level.
2. Groups them by priority (significant gaps first, then minor gaps).
3. Provides 3-5 recommended priority actions for leadership to consider.

Do NOT assign owners, dates, or resource estimates. Those are management decisions.

---

## Important Constraints

1. **Do not fabricate findings.** You have the actual procedure texts and the actual standard texts. If you describe what a procedure says, base it on what you read. If you haven't read a specific document, say so rather than guessing.

2. **Do not rewrite procedures.** Identify what's missing or insufficient. Do not draft replacement language.

3. **Do not make operational decisions.** If a gap exists, describe it and explain why it matters. Do not prescribe how to fix it.

4. **Do not analyze FileHold references.** The platform migration from FileHold to SilqQMS is a separate project. Ignore FileHold references entirely.

5. **Reference the Practical Guide.** When identifying a gap or assessing a clause, include the relevant page number(s) from the ISO 13485 Practical Guide. This gives leadership an easy way to look up the context behind your finding.

6. **Keep it at the procedural level.** You are analyzing whether the *SOPs* address the *requirements*. You are not auditing whether individual records comply with SOPs.

7. **Be balanced.** Where Silq's procedures are adequate, say so clearly. Do not inflate findings. A gap analysis that says everything is broken is not useful. Neither is one that says everything is fine. Be honest and specific.

8. **The only file you should create is** `docs/gap-analysis/Output/QMS_GAP_ANALYSIS_QMSR_ISO13485_2026_03.md`.
