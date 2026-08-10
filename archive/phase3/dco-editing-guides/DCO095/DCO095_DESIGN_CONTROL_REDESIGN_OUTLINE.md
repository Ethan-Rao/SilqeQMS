# DCO095 - Design Control Redesign: Process Outline (Draft for Approval)

Date: June 30, 2026
Status: Draft outline for review. No documents have been edited. On approval, this outline becomes the basis for a prompt to a new SOP agent that will write the editing guides and the cross-reference sweep.

---

## 1. Objective

Replace SILQ's seven-SOP design control program with a single, streamlined Design Control SOP that supports two ends of the spectrum without extra ceremony:

- Move quickly on small efforts (minor design changes, supplier-initiated changes, and limited or retrospective projects like DC.SLQ001).
- Fully capture comprehensive development projects (new products such as the ClearTract Ureteral Stent) under a phase-gated framework.

The redesign must close IA-2025 mNC 1 (nine sub-issues), the FDA 483 Observation 2 root cause carried by CAPA 2025-003 (supplier-initiated change reaching distribution), and the related 2026 Quality Plan commitments, while reducing duplication and total document count.

---

## 2. Locked decisions (from review)

These were confirmed before drafting:

1. Architecture: one consolidated Design Control SOP. No child SOPs. Supporting forms and templates only.
2. Numbering: a brand-new SOP number, QM.SLQ052. QM.SLQ004 through QM.SLQ010 are all designated obsolete (superseded), along with their forms and templates.
3. Pathways: three. Full Development (phase-gated), Design Change (internally initiated), and Supplier/CMO-Initiated Change.
4. Phase model: compressed to three gates for the Full Development pathway (Plan and Inputs, Design and V&V, Transfer and Closure).
5. Forms: adapt the consultant phase-gate Design Review form concept and the single Fast-Track review form into a lean SILQ set, and consolidate the 13 existing forms and templates into a small core set.
6. Change mechanism: a single Design Change Assessment record, mandatory for any change to a released design including any supplier or CMO modification, capturing design impact, risk, V&V determination, and regulatory assessment (Letter-to-File or 510(k)), feeding the DCO process for document and record control.

QM.SLQ052 is the next free number in the register (current maximum is QM.SLQ051).

---

## 3. What becomes obsolete and what gets created

Designated obsolete (superseded by QM.SLQ052):

- SOPs: QM.SLQ004 Design Control Program, QM.SLQ005 Design Project Planning, QM.SLQ006 Design Input, QM.SLQ007 Design Output, QM.SLQ008 Design Review, QM.SLQ009 Design V&V, QM.SLQ010 Design Transfer.
- Forms and templates (13): FM1-QM.SLQ004; TMP1-QM.SLQ005; TMP1 and TMP2-QM.SLQ006; TMP1 and TMP2-QM.SLQ007; FM1-QM.SLQ008; FM1, TMP1, TMP2, TMP3-QM.SLQ009; TMP1 and TMP2-QM.SLQ010.

Created:

- One SOP: QM.SLQ052 Design Control SOP.
- A lean set of new forms and templates under the QM.SLQ052 family (see Section 8).

Note on records already created under the old SOPs (for example DC.SLQ001 deliverables, DC.SLQ002 Phase 0 design review minutes): those remain valid records. Section 13 raises how to handle in-flight projects.

---

## 4. QM.SLQ052 Design Control SOP - proposed section map

1. Purpose
2. Scope (all SILQ device design and development; new products, changes to released designs, and supplier or CMO modifications; subcontractor and CMO obligations)
3. References and standards (21 CFR 820.30; ISO 13485:2016 clause 7.3, now incorporated by the QMSR; ISO 14971; FDA guidance "Deciding When to Submit a 510(k) for a Change to an Existing Device")
4. Definitions (single consolidated list; removes the duplicate definition blocks repeated across the old seven SOPs)
5. Roles, responsibilities, and authorities (including who resolves conflicting inputs, with documented rationale and traceable approval - closes mNC 1)
6. Pathway selection and triage (the decision logic in Section 5 of this outline)
7. Pathway A - Full Development (the three-gate model)
8. Pathway B - Design Change (internally initiated)
9. Pathway C - Supplier or CMO-Initiated Change (mandatory trigger)
10. Design inputs (minimum requirements; control and freeze at Gate 1; conflict resolution)
11. Design outputs (all design outputs are formally controlled; criteria for what enters the DHF - closes mNC 1)
12. Design reviews (gate reviews and optional technical reviews; independent reviewer required; action-item closure)
13. Design verification and validation (V&V always planned and controlled; validation equivalence criteria and methodology defined - closes mNC 1)
14. Risk management integration (link to QM.SLQ012 and QM.SLQ013; risk evaluation required for every change even when a full hazard analysis is not - closes mNC 3 and OFI 2)
15. Design transfer (DMR release, manufacturing readiness, DHF audit; final review requirements preserved even when a transfer checklist is used - closes mNC 1)
16. Design changes and the Design Change Assessment record (Section 7 of this outline)
17. Traceability (single traceability matrix concept across inputs, outputs, and V&V)
18. Design History File and Medical Device File linkage (Section 11 of this outline)
19. Records
20. Associated forms and templates

---

## 5. Three pathways and triage

A short triage at the front of the SOP routes every design activity into exactly one pathway. Proposed routing:

- New product, new generation of an existing product, new intended use or indication, or any change with potential impact to safety or essential performance, goes to Pathway A (Full Development).
- A change to a released design that SILQ initiates and that is not "major" per the criteria above goes to Pathway B (Design Change).
- Any notification of a supplier or CMO modification to a component, material, or process, regardless of perceived significance, goes to Pathway C (Supplier/CMO-Initiated Change). Pathway C can escalate to Pathway A if the assessment finds the change is major.

Triage criteria will be written as a short, testable checklist (not prose) so the choice is defensible and repeatable. The Design Change Assessment record (Section 7) documents the routing decision for Pathways B and C.

### Pathway A - Full Development

- Used for comprehensive projects (for example the ureteral stent).
- Governed by a single scalable Design Project Scope and Plan record, then executed through three gate reviews.
- Scales down by documented rationale when a deliverable does not apply, rather than by ad hoc omission.

### Pathway B - Design Change (internally initiated)

- A single Design Change Assessment drives the work, paired with one scaled design review.
- Determines required V&V, risk review, and regulatory assessment, then routes document and record updates through the DCO process.

### Pathway C - Supplier or CMO-Initiated Change

- Same Design Change Assessment engine as Pathway B, but with a mandatory entry point: any supplier or CMO change notification triggers it before continued manufacturing or distribution.
- Hard link to Purchasing (QM.SLQ020, supplier change notification) and to the regulatory assessment. This is the direct corrective for FDA 483 Observation 2 and CAPA 2025-003.

---

## 6. The three-gate model (Pathway A)

Compresses the old phase set into three formal gate reviews, each closed with a gate Design Review record and an independent reviewer. Optional interim technical reviews are allowed but not required.

- Gate 1 - Planning and Inputs. Approved Design Project Scope and Plan, user needs, design inputs and product requirements (frozen at gate), preliminary risk analysis and risk plan, regulatory and clinical strategy. Exit: inputs under control.
- Gate 2 - Design Outputs and V&V. Controlled design outputs (drawings, specifications, BOM, software, labeling), V&V plan, protocols, and results, updated risk file, traceability matrix. Exit: design verified and validated against inputs and user needs.
- Gate 3 - Transfer and Closure. DMR release, manufacturing readiness, process validation status, DHF audit, regulatory clearance, and the final design review. Exit: design released, DHF complete and retrievable.

Plan updates between gates are themselves change-controlled (closes the mNC 1 sub-issue on plan revisions).

---

## 7. Design Change Assessment record and supplier trigger

A single new record (working name: Design Change Assessment, the DCR) is the engine for Pathways B and C. Minimum content:

- Change description and source (internal, or supplier/CMO with the notification reference and date).
- Triage result and rationale (Pathway B, Pathway C, or escalate to Pathway A).
- Design impact assessment (which inputs, outputs, and interfaces are affected).
- Risk assessment determination (link to QM.SLQ012 and QM.SLQ013; risk evaluation required even when a new hazard analysis is not).
- V&V determination (what verification or validation is required, or a documented rationale that none is needed - closes the mNC 1 sub-issue on V&V determination for changes).
- Regulatory assessment (Letter-to-File versus 510(k), against the FDA "Deciding When to Submit a 510(k)" guidance), with the determination retained in the DHF. This mirrors the CAPA 2025-003 Letter-to-File practice and makes it standard.
- Disposition and routing to the DCO process for document and record control, plus design review sign-off.

The supplier path is mandatory and time-ordered: notification received, manufacturing or distribution hold decision considered, assessment completed, before the change is accepted. This removes the gap that allowed the valve modification to reach approximately 280 distributed devices.

---

## 8. New forms and templates (lean core set) and old-to-new mapping

Proposed new set under the QM.SLQ052 family (final granularity is open for your tweak in Section 13):

- FM1-QM.SLQ052 Design Project Scope and Plan (merges the old scope form FM1-QM.SLQ004 and the plan template TMP1-QM.SLQ005 into one scalable artifact).
- FM2-QM.SLQ052 Design Change Assessment (the new DCR for Pathways B and C, including the supplier trigger).
- FM3-QM.SLQ052 Design Review Record (one scalable form with a gate selector, usable for Gate 1, 2, or 3 and as the single fast-track review; adapted from the consultant phase-gate forms and the Fast-Track form).
- FM4-QM.SLQ052 Design V&V Deviation (from FM1-QM.SLQ009).
- TMP1-QM.SLQ052 Design Input, Output, and Traceability Matrix (merges TMP1 and TMP2-QM.SLQ006, TMP2-QM.SLQ007, and the traceability requirement into one matrix).
- TMP2-QM.SLQ052 V&V Plan, Protocol, and Report (consolidates TMP1, TMP2, TMP3-QM.SLQ009 into one structured template).
- TMP3-QM.SLQ052 Design Transfer Checklist (merges the clinical and design transfer checklists TMP1 and TMP2-QM.SLQ010 into one scalable checklist).
- Source control specification content (old TMP1-QM.SLQ007) folded into design-output and DMR guidance rather than a standalone template.

This takes 13 controlled forms and templates down to approximately 7.

Mapping summary (old to new):

| Old | New home |
| --- | --- |
| FM1-QM.SLQ004 Scope Form | FM1-QM.SLQ052 (Scope and Plan) |
| TMP1-QM.SLQ005 Plan Template | FM1-QM.SLQ052 (Scope and Plan) |
| TMP1 and TMP2-QM.SLQ006 Inputs | TMP1-QM.SLQ052 (Input/Output/Traceability) |
| TMP1-QM.SLQ007 Source Control Spec | Folded into SOP output/DMR guidance |
| TMP2-QM.SLQ007 I/O Matrix | TMP1-QM.SLQ052 (Input/Output/Traceability) |
| FM1-QM.SLQ008 Design Review Minutes | FM3-QM.SLQ052 (Design Review Record) |
| FM1-QM.SLQ009 V&V Deviation | FM4-QM.SLQ052 (V&V Deviation) |
| TMP1, TMP2, TMP3-QM.SLQ009 V&V | TMP2-QM.SLQ052 (V&V Plan/Protocol/Report) |
| TMP1 and TMP2-QM.SLQ010 Transfer | TMP3-QM.SLQ052 (Transfer Checklist) |
| (new) | FM2-QM.SLQ052 Design Change Assessment |

---

## 9. How the findings are closed (traceability)

| Finding | Where closed in QM.SLQ052 |
| --- | --- |
| mNC 1 - design changes lack formal control with documented V&V determination | Sections 8, 9, 16; Design Change Assessment |
| mNC 1 - no minimum planning requirements | Section 7; FM1-QM.SLQ052 Scope and Plan |
| mNC 1 - plan revisions not change-controlled | Section 6 (plan updates are change-controlled) |
| mNC 1 - conflict resolution authority undefined | Section 10 (defined authority, rationale, traceable approval) |
| mNC 1 - design outputs not consistently controlled | Section 11 (all outputs controlled) |
| mNC 1 - DHF capture criteria undefined | Sections 11 and 18 |
| mNC 1 - V&V planning optional | Section 13 (V&V always planned and controlled) |
| mNC 1 - validation equivalence not defined | Section 13 (equivalence criteria and methodology) |
| mNC 1 - transfer checklist in lieu of final review | Section 15 (final review requirements preserved) |
| FDA 483 Obs 2 and CAPA 2025-003 - supplier change reached distribution | Pathway C and the mandatory supplier trigger (Section 7) |
| mNC 3 - risk evaluation for design changes | Section 14 and the DCR risk determination |
| OFI 2 - traceability of risk to inputs and V&V | Sections 14 and 17 |
| OFI 10 - risk linkage to design controls | Section 14 |
| 2026 Quality Plan - supplier modification trigger in design control | Pathway C |
| 2026 Quality Plan - design control retraining (CAPA 2025-003) | Training rollout on QM.SLQ052 (handled as part of DCO095 release and CAPA closure) |
| 2026 Quality Plan - Medical Device File framework | Section 18 (DHF and MDF linkage) |

---

## 10. Cross-references to update in other QM documents

The SOP agent will sweep the QMS and replace references to QM.SLQ004 through QM.SLQ010 with QM.SLQ052. Known referencing documents found so far:

- QM.SLQ027 Quality Manual (lists the design control SOP series)
- QM.SLQ047 Process Validation SOP
- QM.SLQ025 Quality Planning SOP
- QM.SLQ013 Risk Analysis SOP
- QM.SLQ012 Risk Management SOP
- QM.SLQ011 Statistical Techniques WI
- FM1-QM.SLQ018 Management Review Meeting Minutes (form)
- The QM Document Register and any design-control entries

The agent will also confirm there are no remaining references in DMR (QM.SLQ048), DHR (QM.SLQ029), and the in-process design projects.

---

## 11. DHF, Medical Device File, risk, and traceability integration

- DHF: one clear statement of what enters the DHF and when, replacing the FileHold-specific filing paragraph repeated across the old SOPs (and aligned to the SilqQMS EDMS now in place from DC.SLQ002).
- Medical Device File: QM.SLQ052 references the MDF framework called for in the 2026 Quality Plan, tying DHF, DMR (QM.SLQ048), and DHR (QM.SLQ029) together under ISO 13485 clause 4.2.3.
- Risk: a single integration point to QM.SLQ012 and QM.SLQ013, with traceability of risk outputs to inputs and V&V.
- Traceability: one matrix concept (TMP1-QM.SLQ052) used throughout, ending the current triplication.

---

## 12. Compliance anchors

The SOP will be structured so each clause maps cleanly to 21 CFR 820.30 and ISO 13485:2016 clause 7.3 (the QMSR now incorporates ISO 13485). Risk integration anchors to ISO 14971. The regulatory assessment step anchors to the FDA 510(k) change guidance. A short mapping table inside the SOP shows clause-to-section coverage.

---

## 13. Open items for your confirmation (non-blocking)

1. Form granularity: are you comfortable consolidating the three V&V templates into one (TMP2-QM.SLQ052), and using one gate Design Review form with a gate selector rather than three separate gate forms? If you prefer separate gate forms, I will split them.
2. In-flight projects: DC.SLQ001 (retrospective valve assessment, in progress) and DC.SLQ002 (EDMS transition, in progress) were built under the old SOPs. Recommendation: let them finish and close under the old SOPs (grandfathered), with new work starting under QM.SLQ052. Confirm, or tell me if you want either project transitioned.
3. Record naming: I used "Design Change Assessment (DCR)" as the working name. Confirm the name and whether it should be a form (FM2-QM.SLQ052) versus a section of the DCO form.
4. Retraining: confirm DCO095 release should trigger the CAPA 2025-003 design-control retraining as the effectiveness confirmation, so the prompt tells the agent to note training in the rollout.

---

## 14. Next step

On your approval of this outline (and any answers to Section 13), I will draft a comprehensive prompt for a new SOP agent. That prompt will instruct the agent to:

- Produce a copy and paste ready editing guide for the new QM.SLQ052 Design Control SOP and each new form and template, with no asterisk characters, minimal tables, and image-generation instruction blocks where a flowchart helps (for example the triage decision tree and the three-gate flow).
- Produce the obsolescence instructions for QM.SLQ004 through QM.SLQ010 and their forms and templates.
- Perform the cross-reference sweep in Section 10 and provide the exact replacement edits.
- Produce the DCO095 DCO form completion guide.
