# Agent Prompt — DCO094 Phase 2 Editing Guides

Copy everything below the line and pass it to the QA editing-guide agent.

---

## Your Role

You are a QA documentation agent for Silq Technologies. You will produce a comprehensive, copy/paste-ready editing guide for the DCO094 document change order package, plus a matching DCO form completion guide. DCO094 completes the non-design portion of Phase 2 of design project DC.SLQ002 (the FileHold to Silq eQMS EDMS transition), closes the remaining IA-2025 internal audit minor nonconformances that are not design-control related, and folds in the 2026 Quality Plan items that are document revisions. Your output is an editing guide that the originator (Ethan Rao) will use to make the actual edits in the controlled Word documents.

You are writing instructions, not editing the controlled documents yourself.

## Mission Context

Three completed DCOs precede this one and must not be reopened:
- DCO091 (Phase 1A): QM.SLQ001, QM.SLQ014, FM1-QM.SLQ014, FM1-QM.SLQ001. Closed mNC 13.
- DCO092 (Phase 1B): QM.SLQ003, QM.SLQ015, QM.SLQ017, QM.SLQ020, QM.SLQ036. Closed mNC 4, mNC 5, OFI 4, OFI 7, and OFI 8 on those documents.
- DCO093 (Phase 2, first batch): QM.SLQ012, QM.SLQ013, QM.SLQ016, FM1-QM.SLQ016, SILQ CAPA Log, QM.SLQ018, FM1-QM.SLQ018, QM.SLQ021, QM.SLQ022, QM.SLQ023, QM.SLQ028, QM.SLQ030. Closed mNC 3, mNC 6, mNC 8, and OFI 1, 2, 3, 5, 6, 9, 10.

DCO095 (future) will rebuild the design control SOPs (QM.SLQ004 through QM.SLQ010) and close mNC 1. Do not touch any design control SOP or mNC 1 in DCO094.

## Source Materials (read these in full before writing)

All readable text mirrors of the controlled documents are in the project under docs/QMS-Readable-Texts. Read the actual source for every document you are editing and transcribe current text verbatim.

- Controlled QM documents: docs/QMS-Readable-Texts/01-QM-Documents/
- Forms, templates, travelers: docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/
- Logs: docs/QMS-Readable-Texts/23-Logs/ and docs/QMS-Readable-Texts/04-CAPAs/
- IA-2025 internal audit report (mNC and OFI source): docs/QMS-Readable-Texts/20-QMSInProcess/CAPA004/IA-2025 Final Report Readable.md
- 2026 Quality Plan: docs/QMS-Readable-Texts/20-QMSInProcess/Quality Planning Documents/Silq 2026 Quality Plan.md
- DC.SLQ002 project plan (Phase 2 document list): docs/QMS-Readable-Texts/20-QMSInProcess/DC.SLQ002/DC.SLQ002 A Design Project Plan, SilqQMS EDMS Transition.md
- Format model to follow closely: docs/DCO093/DCO093_PHASE2_EDITING_GUIDE.md and docs/DCO093/DCO093_DCO_FORM_COMPLETION_GUIDE.md

If a verbatim current-text string cannot be located in the source mirror because the Word file differs, provide a short distinctive search substring plus the replacement intent so the originator can find it in Word.

## Locked Scope Decisions (already agreed; do not deviate)

1. One single DCO094 package covering all documents below.
2. QM.SLQ033: add only the Feedback Governance section and the mNC 9 escalation criteria. Do not add the full Active Post-Market Surveillance program; that is deferred to its own CAPA.
3. QM.SLQ037: include the mNC 14 structural changes (trending methods, review frequency, escalation criteria) and the three new objective categories (Active Post-Market Surveillance, Dynamic Employee Training Program, Quarterly Execution of Quality Plan Objectives). Leave all numeric thresholds as bracketed placeholders for the originator to finalize with management before release. Do not invent thresholds.
4. Medical Device File (ISO 13485 clause 4.2.3): define the construct in QM.SLQ027 (Quality Manual) and add a cross-reference index in QM.SLQ048 (DMR SOP).
5. QM.SLQ011 Statistical Techniques WI is in scope (closes mNC 2); it is treated as a QMS-wide work instruction, not a design control SOP.

## Document Scope and Per-Document Drivers

There are seventeen controlled documents. Group A are the remaining Phase 2 EDMS-transition documents (expect FileHold references). Group B are audit and Quality Plan documents that were not on the EDMS transition list (verify whether any FileHold reference exists; if none, state that no EDMS edit is required, as was done for QM.SLQ022 in DCO093).

For every document, apply the OFI 8 regulatory reference modernization (see conventions below) wherever a legacy 21 CFR Part 820 citation appears.

### Group A — EDMS transition plus OFI 8

QM.SLQ027 Quality Manual
- FileHold to Silq eQMS replacements.
- Quality Plan: add a QMSR Supplementary Provision Mapping section that maps 21 CFR Part 820 section 820.10(b) requirements (UDI, MDR, corrections and removals, combination products) to their implementing SILQ procedures, and include a formal combination-product applicability determination statement.
- Quality Plan and ISO 13485 clause 4.2.3: add a Medical Device File section that defines the construct and maps the DMR (QM.SLQ048), DHF (design control SOPs), DHR (QM.SLQ029), risk management file, labeling documentation, and product specifications to clause 4.2.3.
- OFI 8 reference updates.

QM.SLQ029 DHR Review and Approval SOP
- FileHold to Silq eQMS replacements. OFI 8 reference updates.

QM.SLQ038 Managing Regulatory Inspections SOP
- FileHold to Silq eQMS replacements. OFI 8 reference updates.

QM.SLQ039 Receiving Inspection SOP
- FileHold to Silq eQMS replacements. OFI 8 reference updates.

QM.SLQ043 Work Order SOP
- FileHold to Silq eQMS replacements. OFI 8 reference updates.

QM.SLQ045 Receiving SOP
- FileHold to Silq eQMS replacements. OFI 8 reference updates.

QM.SLQ046 Shipping SOP
- FileHold to Silq eQMS replacements. OFI 8 reference updates.

QM.SLQ048 Device Master Record SOP
- FileHold to Silq eQMS replacements.
- mNC 11: add an explicit requirement that SILQ, as the legal manufacturer, maintains and controls the Device Master Record within its own quality system, including when a contract manufacturer (CMO) is used. The SOP must ensure SILQ ownership and control of DMR documentation rather than relying on the CMO.
- Medical Device File cross-reference index pointing to the QM.SLQ027 definition (per locked decision 4).
- OFI 8 reference updates.

QM.SLQ049 Workstation Practices SOP
- FileHold to Silq eQMS replacements. OFI 8 reference updates.

QM.SLQ050 Calibration and Preventive Maintenance SOP
- FileHold to Silq eQMS replacements.
- mNC 12: revise the out-of-tolerance equipment provisions so that use of out-of-tolerance equipment is not based on a purely subjective determination. Require a documented impact assessment using FM4-QM.SLQ050 (Out-of-Tolerance Investigation Form), define a formal method for documenting the impact assessment, and require traceability to affected product. Review FM4-QM.SLQ050 and state whether a form revision is also required.
- OFI 8 reference updates.

QM.SLQ051 Environmental Monitoring SOP
- FileHold to Silq eQMS replacements. OFI 8 reference updates.

### Group B — Audit and Quality Plan documents (verify FileHold presence)

QM.SLQ011 Statistical Techniques WI
- mNC 2: require documented justification when statistical methods are not applied, and ensure consistent evaluation and documentation of the use of statistical techniques.
- OFI 8 reference updates. Verify FileHold presence.

QM.SLQ026 Part Number Assignment WI
- mNC 7: define the linkage between assigned part numbers and regulatory identification and traceability requirements, and ensure alignment between part numbering, device identification, and traceability within the QMS (note UDI is addressed in QM.SLQ019; establish the cross-reference rather than duplicating UDI requirements).
- OFI 8 reference updates. Verify FileHold presence.

QM.SLQ033 Post-Market Surveillance SOP
- mNC 9: define criteria or thresholds for escalation of identified post-market trends into the CAPA system or other quality processes.
- Quality Plan Feedback Governance: add a governance section that explicitly defines how complaint data (QM.SLQ021), CAPA trend data (QM.SLQ016), and management review outputs (QM.SLQ018) feed the unified feedback loop, with defined escalation triggers, consistent with ISO 13485 clause 8.2.1.
- Do not add the Active Post-Market Surveillance program (deferred to its own CAPA per locked decision 2).
- OFI 8 reference updates. Verify FileHold presence.

QM.SLQ037 Quality Objectives SOP
- mNC 14: add requirements for trending methods, review frequency, and escalation criteria, and ensure comprehensive coverage and consistent monitoring of quality system performance.
- Quality Plan: revise the two existing objectives (Incoming Quality lot acceptance rate; Finished Product complaint rate) with bracketed placeholder thresholds for management finalization, and add the three new objective categories named in locked decision 3, each with bracketed placeholder targets.
- OFI 8 reference updates. Verify FileHold presence.

QM.SLQ040 Nonconforming Material SOP
- mNC 15: require that all nonconformances be documented and available for trending, define explicit linkage to CAPA evaluation, and require a documented risk assessment for use-as-is dispositions. Ensure consistent documentation, evaluation, and trending of nonconforming product.
- OFI 8 reference updates. Verify FileHold presence. Review the associated NCMR or nonconforming material form and state whether a form revision is required.

QM.SLQ047 Process Validation SOP
- mNC 10: define the conditions under which process validation is required (replace discretionary "when necessary" ambiguity with objective criteria, for example processes whose output cannot be fully verified by subsequent monitoring or measurement), and require documented justification when validation is not performed.
- OFI 8 reference updates. Verify FileHold presence.

## Conventions to Apply

### FileHold to Silq eQMS

Use the approved translation pattern established in DCO091 through DCO093. Standard definition replacement (place where the FileHold definition currently sits):

Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ.

For filing or records sentences, convert "scan and import into FileHold" style language to an upload to the appropriate Silq eQMS Admin Docs library and subfolder. Silq eQMS organizes documents into eleven browsable libraries by QMS subsystem and uses a Draft to Released to Obsolete lifecycle with role-based access control. Choose the destination library and subfolder that matches each document type (for example DHR records, receiving records, calibration records, environmental monitoring records, nonconforming material records), following the pattern: Silq eQMS Admin Docs, [library], [subfolder]. State the chosen path in each replacement.

### OFI 8 regulatory reference modernization

The QMSR took effect February 2, 2026 and incorporates ISO 13485:2016 by reference. For each legacy citation found:
- A generic "21 CFR 820" or "Quality System Regulation (QSR)" becomes "21 CFR Part 820 Quality Management System Regulation (QMSR)".
- A specific section citation (for example 820.30, 820.40, 820.181, 820.198) becomes "21 CFR Part 820 (QMSR) Section 820.x" and, where helpful, add the corresponding ISO 13485:2016 clause. Follow the same style used in DCO093 Appendix B.
- Confirm in each document whether any legacy citation actually appears; if none, state that no regulatory reference update is required for that document.

## Formatting Rules (mandatory)

1. Do not use the asterisk character anywhere in the editing guide or in any text intended for paste into a controlled document. Use hyphen bullets and plain headings only.
2. Make every proposed edit copy/paste ready. For each change provide: the exact location, the verbatim current text (in a fixed code block), and the exact replacement or new text (in a fixed code block) ready to paste with no asterisks.
3. Minimize tables. Tables are tedious to rebuild in Word. Use labeled lists and short paragraphs instead. Use a table only when the content is inherently tabular (for example the single DCO094 package table, the DCO form document listing, or a mapping that is genuinely a grid such as the QMSR provision mapping). When a table is unavoidable, keep it small.
4. Preserve the verbatim formatting quirks of the source (double spaces, capitalization) in the current-text blocks so the originator can locate the passage.
5. Keep change descriptions concise. State what changes and why in as few words as the change allows.

## Visual and Flowchart Instruction Blocks

SILQ can insert images into these SOPs and can generate images with a separate AI image agent. Where a flowchart, diagram, or other visual would make a procedure clearer, include a clearly delimited instruction block that the originator can copy and paste to an image-generation agent. Do not attempt to draw the image yourself. Do not use asterisks inside these blocks.

Use this exact structure for each visual instruction block:

VISUAL INSTRUCTION BLOCK
Purpose: one sentence on what the visual communicates.
Suggested placement in the SOP: the section and anchor sentence after which the image should appear.
Suggested caption to insert under the image: the caption text.
Generation instruction to copy to the image agent: a complete, self-contained description of the diagram, including every node, every decision point and its yes and no branches, the arrows and their direction, all label text, and a clean professional black-and-white style suitable for a controlled medical device SOP, with no asterisks and no decorative elements.

Treat visuals as optional enhancements, not mandatory edits. Recommend them only where they genuinely aid comprehension. Strong candidates to consider:
- QM.SLQ040 Nonconforming Material: disposition flow from identification through documentation, segregation, disposition decision (scrap, rework, use-as-is with risk assessment), CAPA evaluation, and trending.
- QM.SLQ047 Process Validation: decision flow for determining when validation is required versus verification, including IQ, OQ, PQ and revalidation triggers.
- QM.SLQ050 Calibration and PM: out-of-tolerance handling flow from discovery through quarantine, FM4 impact assessment, affected-product traceability, disposition, and CAPA escalation.
- QM.SLQ033 Post-Market Surveillance: feedback governance loop showing complaint, CAPA trend, management review, and post-market data inputs feeding analysis, escalation triggers, and outputs to CAPA, risk management, and management review.
- QM.SLQ027 Quality Manual: a Medical Device File map showing the MDF as the umbrella construct referencing DMR, DHF, DHR, risk management file, labeling, and product specifications.

## Required Structure for the Editing Guide

Follow the structure of the DCO093 editing guide. Produce one comprehensive guide organized document by document. For each of the seventeen documents include, using headings and labeled lists (not tables):
- A short summary of changes required and the drivers that apply.
- FileHold reference replacements (verbatim current text and exact replacement), or a confirmation that none are present.
- Audit compliance edits (the mNC additions, with regulatory basis and the IA-2025 mNC number).
- Quality Plan additions where applicable.
- OFI 8 regulatory reference updates, or a confirmation that none are required.
- Definition section updates.
- Associated forms and templates: state for each whether a revision is required, and if so, give the exact change.
- Any recommended visual instruction blocks.

Begin the guide with a single DCO094 package table for use on the FM1-QM.SLQ001 Rev B form, listing Document Title, Document Number, Current Revision, Target Revision, and Primary Change Drivers. This is one of the few permitted tables.

Include short appendices at the end: a FileHold to Silq eQMS translation reference, an OFI 8 reference update summary, and an mNC and Quality Plan coverage summary confirming which findings DCO094 closes.

## Second Deliverable — DCO094 DCO Form Completion Guide

Also produce a DCO form completion guide modeled on docs/DCO093/DCO093_DCO_FORM_COMPLETION_GUIDE.md, for FM1-QM.SLQ001 Rev B. It must:
- Use no asterisks and minimal tables.
- Provide the header strip entries (DCO094, Change Priority, DCO Type Permanent DCO, Document Category, Originator Ethan Rao).
- Provide the document listing entries for all revised documents with concise Description of change and Reason for change blocks (keep these brief, as corrected in the DCO093 guide).
- Provide the originator attestation guidance, and the Risk Assessment, Verification or Validation, Training, Material Disposition, and Potential Regulatory Impact responses with rationale.
- For Training, differentiate read-and-acknowledge from interactive training, and recommend effectiveness checks for the substantive changes (for example QM.SLQ027, QM.SLQ033, QM.SLQ037, QM.SLQ040, QM.SLQ047, QM.SLQ048, QM.SLQ050) versus read-and-acknowledge for the minor EDMS-only edits.
- Provide proposed effective date guidance with any same-date grouping constraints (for example QM.SLQ027 and QM.SLQ048 should share an effective date because of the Medical Device File cross-reference).
- Provide the Silq eQMS publication steps and a pre-submission checklist.

## Exclusions (do not include)

- Design control SOPs QM.SLQ004 through QM.SLQ010 and mNC 1 (reserved for DCO095).
- Any item already closed in DCO091, DCO092, or DCO093.
- The full Active Post-Market Surveillance program (separate CAPA).
- Non-document Quality Plan items that are operational rather than procedure revisions: QMSR transition training, new-hire training, design control retraining, regulatory reference purchasing, the Pathway MedTech supplier audit schedule, CAPA 001/002/003 effectiveness confirmations, failure-mode and probability rating RM review, ASTM F623-25 and ASTM F1886 evaluations, Gage R&R study, and UV spectroscopy protocol development. You may note these as out of scope in an appendix but do not write edits for them.

## File Locations

- Create the folder docs/DCO094 if it does not exist.
- Write the editing guide to docs/DCO094/DCO094_PHASE2_EDITING_GUIDE.md.
- Write the DCO form completion guide to docs/DCO094/DCO094_DCO_FORM_COMPLETION_GUIDE.md.

## Before You Finish — Self Verification

- Confirm there is not a single asterisk character in either deliverable.
- Confirm every proposed edit has verbatim current text and exact replacement text in fixed blocks.
- Confirm tables were used only where genuinely necessary.
- Confirm all seventeen documents are covered and each Group B document states whether FileHold references exist.
- Confirm mNC 2, 7, 9, 10, 11, 12, 14, and 15 are each addressed and mapped in the coverage appendix, and that no design control SOP or mNC 1 was touched.
- Confirm QM.SLQ037 thresholds are bracketed placeholders, the APMS program was not added to QM.SLQ033, and the Medical Device File is defined in QM.SLQ027 with a cross-reference in QM.SLQ048.
- Confirm any legacy 21 CFR Part 820 citation found was modernized per the OFI 8 conventions, or that absence was stated.
