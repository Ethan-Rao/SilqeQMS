# Developer Prompt: Review and Revise Transition Plan and Gap Analysis

**Date:** 2026-03-24  
**Requested by:** Ethan Rao, Director R&D, QA, Regulatory Affairs  
**Purpose:** Perform a thorough review and targeted revision of two management-facing QMS deliverables to ensure accuracy, clarity, scope discipline, and readiness for leadership distribution.

---

## Your Task

You are reviewing and revising two documents that will be distributed to the Silq leadership team (CEO, VP QA, VP RA, Director of Manufacturing, Quality Specialist). Both documents must be accurate, clearly written in plain English, and strictly scoped to their intended purpose.

**Documents to revise (edit these files in place):**

1. `docs/transition-plan/Output/QMS_TRANSITION_PLAN_FILEHOLD_TO_SILQQMS.md`
2. `docs/gap-analysis/Output/QMS_GAP_ANALYSIS_QMSR_ISO13485_2026_03.md`

---

## Context: What These Documents Are

### Transition Plan
Explains what needs to change in Silq's 46 QM procedures to move from the FileHold document management system to the new SilqQMS platform. It is a purely internal platform migration document — it categorizes every QM document by how deeply FileHold is embedded (complete rewrite, targeted revision, simple text update, or no change needed) and recommends a sequencing strategy.

**Scope:** FileHold references in procedures, what to revise, and in what order.  
**Not in scope:** Regulatory alignment, QMSR, ISO 13485 clauses, 820 citations, or any regulatory content whatsoever.

### Gap Analysis
Identifies where Silq's current QMS procedures fall short of ISO 13485:2016 and the FDA QMSR's supplementary provisions. It walks through each ISO 13485 clause, assesses Silq's current procedural coverage, identifies gaps at Adequate/Minor/Significant levels, and provides Practical Guide page references.

**Scope:** Regulatory alignment — ISO 13485 clauses, QMSR supplementary provisions (§820.10(b), §820.35, §820.45), ISO 14971 risk management alignment, and legacy 820 citation updates.  
**Not in scope:** FileHold references, platform migration, or SilqQMS system features.

---

## What You Must Read Before Revising

### Mandatory — read in full:

1. Both output documents listed above.
2. **Reference: FileHold Integration Analysis** — `docs/transition-plan/Prompts/REFERENCE_FILEHOLD_AND_820_ANALYSIS.md`
3. **Reference: QM Document Register with ISO 13485 Clause Mapping** — `docs/gap-analysis/Resources/REFERENCE_QM_DOCUMENT_REGISTER.md`
4. **Reference: Legacy 820 Citations** — `docs/gap-analysis/Resources/REFERENCE_LEGACY_820_CITATIONS.md`
5. **Reference: Regulatory Standards Index** — `docs/gap-analysis/Resources/REFERENCE_REGULATORY_STANDARDS_INDEX.md`
6. **Quality Manual** — `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ027 E Quality Manual.md`

### Read as needed to verify specific claims:

7. Any QM document text referenced in either deliverable. All 46 are at `docs/QMS-Readable-Texts/01-QM-Documents/`.
8. **ISO 13485:2016** — `docs/QMS-Readable-Texts/11-RegulatoryStandards/ISO -- ISO_13485_2016.md`
9. **ISO 13485 Practical Guide** — `docs/QMS-Readable-Texts/11-RegulatoryStandards/ISO -- ISO 13485 2016 Medical devices Practical Guide.md`
10. **FDA QMSR Final Rule** — `docs/QMS-Readable-Texts/11-RegulatoryStandards/ISO -- 2024-01709. FDAQMSRFinalRule.md`
11. **ISO 14971:2019** — `docs/QMS-Readable-Texts/11-RegulatoryStandards/ISO -- ISO_14971_2019(en).md`
12. **SilqQMS README** — `README.md`
13. **Admin Docs library definitions** — `app/eqms/modules/admin_docs/admin.py`

---

## Review Criteria

Apply each of the following review passes to **both documents**. For each issue found, fix it directly in the document. Do not produce a separate review report — edit the files in place.

### Pass 1: Factual Accuracy

Verify claims against actual source data. Spot-check at minimum:

**For the Transition Plan:**
- Do the FileHold reference counts match reality? The reference analysis says QM.SLQ014 has 80 and QM.SLQ001 has 76. Confirm the Category A/B/C/D groupings account for all 46 documents (2 + 6 + 25 + 13 = 46).
- Are the associated forms/templates listed for Group 1 and Group 2 documents correct? Read QM.SLQ001, QM.SLQ014, and at least two Category B documents to verify the form IDs mentioned.
- Does the 11-library list in Section 3 match what's actually defined in `app/eqms/modules/admin_docs/admin.py`? Read the file and compare.

**For the Gap Analysis:**
- Do the ISO 13485 clause-to-document mappings match the Quality Manual's Appendix 1? Cross-check at least 5 clause rows against the document register.
- Is the ISO 14971 version claim correct? The report says QM.SLQ012 references ISO 14971:2019. Read the document to confirm.
- Are the Practical Guide page references plausible? The guide is organized by clause, so page 49 should be near clause 4.2.3, page 171 near 8.2.1, etc. Spot-check at least 3 references by reading the Practical Guide at those page markers.
- Does the legacy 820 citation table in Section 7 match the data in `REFERENCE_LEGACY_820_CITATIONS.md`? Verify all 19 rows.
- Is the gap count in the Executive Summary consistent with the clause-by-clause tables? Count the classifications and confirm.

### Pass 2: Scope Discipline

Ensure each document stays strictly in its lane:

**Transition Plan must NOT contain:**
- Any mention of ISO 13485 clauses, QMSR, §820.xx supplementary provisions, or regulatory gap analysis
- Any analysis of whether procedures meet regulatory requirements
- Any recommendation about regulatory citation updates

**Gap Analysis must NOT contain:**
- Any mention of FileHold, SilqQMS platform features, or the platform migration
- Any analysis of system reference updates (that's the transition plan's domain)
- Any discussion of which documents need FileHold text replaced

**Section 7 (Out of Scope) in both documents** should clearly reference the other project by name so leadership understands how the two relate, without actually doing the other project's work.

### Pass 3: Completeness

**Transition Plan:**
- Are all 46 documents accounted for across Groups 1-4? Verify the total.
- Is every Category B document accompanied by a "why" explanation and associated forms list?
- Does Section 6 (Recommended Sequence) provide a clear, logical rationale for Wave 1 → Wave 2 → Wave 3?

**Gap Analysis:**
- Are all major ISO 13485 clauses (4.1 through 8.5.3) represented in the clause-by-clause table? Identify any that are missing.
- Are all 4 formal Quality Manual exclusions (7.5.3, 7.5.4, 7.5.9.2, 7.5.10) listed as "Not Applicable"?
- Does the consolidated gap table in Section 8 include every gap identified in Section 4? Cross-check.
- Does Section 5 (QMSR Supplementary Provisions) cover all three provisions: §820.10(b), §820.35, §820.45?
- Does Section 6 (Risk Management) confirm the ISO 14971 version and address all key process elements?

### Pass 4: Tone and Readability

Both documents will be read by executives who may not be regulatory specialists. Apply these standards:

- **Plain English.** If a sentence requires QMS jargon to understand, add brief context. The first mention of any acronym or regulatory term should include a plain-language explanation.
- **No walls of text.** Sections should use headers, short paragraphs, bullet points, and tables. A busy executive should be able to skim headers and tables and understand the scope of work.
- **No filler.** Remove any sentence that restates what the previous sentence just said. Every sentence should add information.
- **Consistent terminology.** If the transition plan calls the new system "SilqQMS," don't also call it "the eQMS application" elsewhere. Pick one name and use it.
- **Active voice preferred.** "The procedure addresses this requirement" is better than "This requirement is addressed by the procedure."
- **Table formatting.** Ensure all tables render correctly in markdown — consistent column counts, no broken rows, alignment markers match column count.

### Pass 5: Internal Consistency

Check that the two documents are consistent with each other where they reference overlapping territory:

- Both documents reference the same 46 QM documents. Confirm document IDs and revision letters are consistent between the two.
- The Transition Plan's Section 7 mentions the gap analysis as a separate project. The Gap Analysis's background section mentions the platform migration as separate. Ensure these cross-references are accurate and symmetrical.
- Documents that appear in both reports (e.g., QM.SLQ016 appears in Transition Plan Group 3 for FileHold text update and in Gap Analysis for CAPA citation updates) should not have conflicting information between the two documents.

---

## Important Constraints

1. **Edit the files in place.** Do not create new files. Revise the two existing output documents directly.
2. **Do not change the overall structure** of either document. The section numbering and organization are intentional. Fix content within the existing structure.
3. **Do not inflate findings.** If a claim in the document is accurate, leave it. Do not add gaps that aren't supported by evidence in the source documents. Do not upgrade Minor Gaps to Significant Gaps without reading the actual procedure and standard text.
4. **Do not deflate findings.** If a legitimate gap is identified, do not downgrade or remove it.
5. **Do not add agent metadata.** Do not add sections listing which files you read, what tools you used, or timestamps of your review. The documents are for leadership, not for documenting your process.
6. **Preserve page reference accuracy.** If you change or verify a Practical Guide page reference, confirm it by reading the guide at the cited page marker. The guide uses `--- Page N ---` markers in the extracted text.
7. **Do not make operational decisions.** Both documents identify what needs attention. Neither document should prescribe how to fix things, assign owners, or set dates. If you find language that does this, remove it.
