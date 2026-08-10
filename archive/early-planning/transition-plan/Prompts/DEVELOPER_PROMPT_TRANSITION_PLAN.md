# Developer Prompt: QMS Transition Plan — FileHold to SilqQMS

**Date:** 2026-03-24  
**Requested by:** Ethan Rao, Director R&D, QA, Regulatory Affairs  
**Purpose:** Create a clear, management-friendly transition plan document explaining what needs to change in our QMS procedures to move from FileHold to SilqQMS.

---

## Your Task

Write a transition plan document and save it at:

**`docs/transition-plan/Output/QMS_TRANSITION_PLAN_FILEHOLD_TO_SILQQMS.md`**

This document will be read by the Silq leadership team, some of whom may not be deeply familiar with the QMS. It should be written in plain English, be well-organized, and clearly explain what we have today, what we're moving to, and what document-by-document work is needed to get there.

---

## Audience and Tone

- **Primary audience:** CEO, VP of QA, VP of RA, Director of Manufacturing, Quality Specialist
- **Tone:** Professional but approachable. Explain things clearly without jargon dumps. When regulatory terms are necessary, give brief context.
- **Length:** Aim for 20-30 pages — thorough but not exhausting
- **Critical rule:** Do NOT make decisions about future operating procedures. Your job is to document what exists, what needs to change, and why. The leadership team will make decisions about how to implement changes.

---

## What You Must Read Before Writing

### Required reading (read all of these in full):

1. **Reference analysis** — `docs/transition-plan/Prompts/REFERENCE_FILEHOLD_AND_820_ANALYSIS.md`  
   This tells you exactly which documents reference FileHold, how many times, and in what context. This was generated from actual document content, not guesswork.

2. **The two most impacted QM documents** — Read these in full to understand the depth of FileHold integration:
   - `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ014 B Electronic Doc System WI.md`
   - `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ001 A Document Control SOP.md`

3. **The Quality Manual** — `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ027 E Quality Manual.md`  
   This gives you the overall QMS structure and context.

4. **A sample of Category B documents** (multiple FileHold references) — read at least 3 of these to understand the pattern:
   - `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ003 B Employee Training SOP.md`
   - `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ020 D Purchasing Controls SOP.md`
   - `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ017 A Internal Audits SOP.md`

5. **A sample of Category C documents** (light FileHold references) — read at least 2 to see the typical boilerplate pattern:
   - `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ016 C CAPA SOP.md`
   - `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ012 B Risk Management SOP.md`

You may also browse other documents in `docs/QMS-Readable-Texts/01-QM-Documents/` as needed. The full text of all 46 QM procedures is available there.

### Background context (skim for understanding, don't need to read line-by-line):

6. **Application README** — `README.md` — describes what SilqQMS is
7. **Admin Docs library definitions** — `app/eqms/modules/admin_docs/admin.py` (lines 18-30) — the 11 document libraries in SilqQMS

---

## Context: What Is Happening and Why

### FileHold (the old system)
FileHold is a commercial document management system that Silq has used to store, version, and route controlled QMS documents. It provides folder-based organization, version tracking, check-in/check-out, and review/approval workflows. Most QM procedures reference FileHold by name as the place where records are stored, filed, and controlled.

### SilqQMS (the new system)
SilqQMS is a purpose-built eQMS web application that replaces FileHold. It provides:
- **Document libraries** organized by QMS subsystem (11 libraries: QM Documents, Employee Training, Management Reviews, CAPAs, NCRs, Post-Market Surveillance, Regulatory Standards, Work Orders, Risk Management, DHFs, Forms/Templates/Travelers)
- **Document control** with formal revision tracking, release workflow, and file integrity verification
- **Entity-linked records** where documents can be associated with specific equipment, suppliers, manufacturing lots, etc.

### What needs to change in QMS procedures
Every QM document that references "FileHold" needs to be updated to reference SilqQMS instead. The scope of revision varies dramatically by document — from a simple text replacement in documents with 1-2 boilerplate mentions, to a complete rewrite for QM.SLQ014 which is entirely about FileHold.

### What this plan does NOT cover
Some QM documents also reference legacy 21 CFR Part 820 section numbers. Whether those citations need updating for the FDA's QMSR regulatory transition is a separate project (a gap analysis) that will be conducted independently. **This transition plan is strictly about the internal platform change from FileHold to SilqQMS. Do not analyze, catalog, or comment on regulatory citation accuracy.** If you encounter 820 references while reading documents, ignore them — they are not in scope.

---

## Document Structure

Write the transition plan with the following sections:

### 1. Introduction
- What this document is and who it's for
- Why we're making this transition (1-2 paragraphs, plain language)
- How to read this document

### 2. Current State: How Our QMS Works Today
- Brief overview of Silq's QMS (46 procedures, forms/templates, quality records)
- How FileHold fits in — what role it plays in day-to-day quality operations
- What works well and what's driving the change
- Keep this to 1-2 pages. The audience knows the company; they need context on why the system is changing.

### 3. Target State: How Things Will Work in SilqQMS
- What SilqQMS provides (plain language — no database field names or technical implementation details)
- How document libraries are organized
- What changes for users in daily work
- Keep this to 1-2 pages.

### 4. Document-by-Document Disposition

This is the core of the plan. Present all 46 QM documents grouped by the level of revision work needed:

**Group 1: Complete Rewrite**
Documents where FileHold is so deeply embedded that the procedure needs to be substantially rewritten. Based on the reference analysis, this is QM.SLQ014 (80 FileHold references — the entire document describes FileHold) and QM.SLQ001 (76 references — FileHold is woven into every procedure step and the full records retention table).

For each document in this group, provide:
- Document ID, current revision, title
- A plain-English explanation of why it needs a rewrite (what does the document currently describe, and why can't we just find-and-replace "FileHold" with "SilqQMS"?)
- Key sections that will need attention
- Any forms or templates associated with this document that will also need review

**Group 2: Targeted Revision**
Documents with multiple FileHold references embedded in procedural steps (Category B: 3-14 references). These need more than a simple text swap — someone needs to review how FileHold is referenced in the procedure steps and update the workflow descriptions.

For each, provide:
- Document ID, current revision, title
- Number of FileHold references
- Brief description of what needs to change (e.g., "Training record filing steps reference FileHold check-in/check-out; needs update to SilqQMS upload workflow")
- Associated forms/templates to review

**Group 3: Simple Text Update**
Documents with 1-2 FileHold references that follow a standard boilerplate pattern (glossary definition and/or a records-filing instruction). These can likely be handled as a batch — update the glossary definition and the records-filing sentence.

Present these as a summary table, not individual write-ups. Include document ID, title, and number of references.

**Group 4: No FileHold Changes Needed**
The 13 documents with zero FileHold references. List them in a table and note that these require no changes for the platform transition.

### 5. Forms, Templates, and Travelers Impact

Briefly explain that when a parent SOP is revised, its associated forms and templates should be reviewed for compatibility. Note:
- QM.SLQ001 has 3 associated controlled artifacts (FM1, FM2, TMP1)
- QM.SLQ014 has 1 associated form (FM1 — Electronic Signature Acknowledgement)
- Category B documents collectively have associated forms/templates that should be reviewed with their parent SOPs

Do NOT list every single form with a speculative disposition. Simply note which parent SOPs have associated forms and that those forms should be reviewed when the parent is revised.

### 6. Recommended Sequence

Suggest a logical order for the revision work:
- QM.SLQ014 should be done first (it's the system description — everything else references it)
- QM.SLQ001 next (it's the master document control procedure)
- Category B documents in a second wave
- Category C documents as a batch in a third wave

Explain the rationale briefly. Do not assign specific dates or owners — that's a leadership decision.

### 7. What This Plan Does Not Cover

Clearly state what is out of scope:
- **Regulatory gap analysis** — A separate project will assess whether our QMS procedures meet the requirements of the new QMSR (which incorporates ISO 13485:2016 by reference). That project will analyze regulatory citation accuracy, procedural gaps against ISO clauses, and QMSR-specific FDA overlays. It is entirely separate from this platform transition and has its own deliverable. Do not discuss, preview, or overlap with it.
- **Software validation of SilqQMS** — separate technical activity
- **Training plan details** — will follow once revision scope is confirmed
- **Specific procedure content decisions** — this plan identifies what needs to change, not how to change it

---

## Important Constraints

1. **Do not fabricate or assume procedure content.** You have the actual document texts. If you describe what a document contains, base it on what you read. If you haven't read a specific document, say so.

2. **Do not prescribe how procedures should be rewritten.** Your job is to identify what needs to change and why, not to draft new procedure language. The leadership team and document owners will decide on the content of revisions.

3. **Do not assign owners, dates, or resource estimates.** Those are management decisions.

4. **Do not touch regulatory/QMSR topics.** Do not analyze, catalog, or recommend changes related to 21 CFR 820 citations, ISO 13485 clause alignment, or QMSR compliance. Those topics belong to a separate gap analysis project. This plan is exclusively about the internal platform change from FileHold to SilqQMS.

5. **Keep it readable.** Use headers, short paragraphs, and tables. Avoid walls of text. A busy executive should be able to skim the headers and tables and understand the scope of work.

6. **The only file you should create is** `docs/transition-plan/Output/QMS_TRANSITION_PLAN_FILEHOLD_TO_SILQQMS.md`.
