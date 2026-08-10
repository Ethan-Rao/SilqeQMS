# DCO095 Coverage Review Findings

Prepared by: QA compliance auditor (coverage review)
Date: June 30, 2026
Scope: Verify whether the currently scoped DCO095 plan closes, in full, (1) all IA-2025 minor non-conformities and OFIs, (2) all 2026 Quality Plan action items except employee training, and (3) all DC.SLQ002 Phase 1A, 1B, and 2 document obligations prior to the Phase 3 migration. This is a read-only coverage review. No controlled documents were edited.

Sources read in full:
- IA-2025 Final Report (docs/QMS-Readable-Texts/20-QMSInProcess/CAPA004/IA-2025 Final Report Readable.md)
- 2026 Quality Plan (docs/QMS-Readable-Texts/20-QMSInProcess/Quality Planning Documents/Silq 2026 Quality Plan.md)
- DC.SLQ002 transition plan (docs/QMS-Readable-Texts/20-QMSInProcess/DC.SLQ002/DC.SLQ002 A Design Project Plan, SilqQMS EDMS Transition.md)
- DCO095 outline (docs/DCO095/DCO095_DESIGN_CONTROL_REDESIGN_OUTLINE.md) and dev prompt (docs/DCO095/AGENT_PROMPT_DCO095_DESIGN_CONTROL_EDITING_GUIDES.md)
- Prior closures: docs/DCO091/ (README and editor guides), docs/DCO092/DCO092_PHASE1B_EDITING_GUIDE.md, docs/DCO093/DCO093_PHASE2_EDITING_GUIDE.md, docs/DCO094/DCO094_PHASE2_EDITING_GUIDE.md and DCO094/QM.SLQ037_Objectives_Management_Alignment.md, docs/CAPA004/CAPA004_2025_EDITING_GUIDE.md
- Current controlled mirrors in docs/QMS-Readable-Texts/01-QM-Documents/ and 02-Forms-Templates-Travelers/ (used to validate the cross-reference sweep)

Closure-label key used throughout:
- Closed (prior): closed by DCO091, DCO092, DCO093, DCO094, or CAPA004, with cited evidence.
- Planned (DCO095): covered by the current DCO095 outline or dev prompt, with cited location.
- GAP: not closed anywhere and not currently in the DCO095 plan.
- Out of scope - training: an employee-training action, excluded by direction.

Master remediation map (from CAPA 004-2025 editing guide, Section IV action plan and OFI disposition note): mNC 13 to DCO091; mNC 4 and 5 to DCO092; mNC 3, 6, 8 to DCO093; mNC 2, 7, 9, 10, 11, 12, 14, 15 to DCO094; mNC 1 to the dedicated Design Controls DCO (this is DCO095). OFI 4 and 7 to DCO092; OFI 1, 2, 3, 5, 6, 9, 10 to DCO093; OFI 8 systemic across DCO091 through DCO094.

---

## Section A - IA-2025 ledger

### Minor non-conformities

| ID | One-line summary | Document(s) | Status | Evidence |
|---|---|---|---|---|
| mNC 1 | Design control program lacks comprehensive requirements (nine sub-issues, see breakdown below) | QM.SLQ004 (to be superseded by QM.SLQ052) | Planned (DCO095) | CAPA004 Action 5 assigns mNC 1 to the dedicated Design Controls DCO; DCO095 outline Section 9 and dev prompt Sections 4.2 and 4.6 close all nine sub-issues in QM.SLQ052 |
| mNC 2 | Statistical Techniques WI does not require documented justification when statistics not applied | QM.SLQ011 | Closed (prior) | DCO094 doc table and Appendix B: QM.SLQ011 Rev A to B (Doc 12, edited) |
| mNC 3 | Risk Analysis SOP lacks mandatory systematic risk eval for design changes | QM.SLQ013 | Closed (prior) | DCO093 Document 2, mNC 3 additions to Scope and Procedure; also reinforced in QM.SLQ052 Section 14 and the Design Change Assessment (DCO095 dev prompt) |
| mNC 4 | Supplier QA frequencies not risk-based | QM.SLQ015 | Closed (prior) | DCO092 Section 6, mNC 4 risk-frequency language in Sections 8 and 15; FM7 column additions |
| mNC 5 | Supplier change notification permissive ("wherever possible") | QM.SLQ020 | Closed (prior) | DCO092 Section 4, mNC 5 Change A replaces "wherever possible" with mandatory language; adds response subsection 6.3.1 |
| mNC 6 | Complaint trending lacks CAPA escalation criteria | QM.SLQ021 | Closed (prior) | DCO093 Document 5, mNC 6 Complaint Trend Escalation to CAPA criteria |
| mNC 7 | Part number assignment not linked to traceability/UDI | QM.SLQ026 | Closed (prior) | DCO094 doc table and Appendix B: QM.SLQ026 Rev C to D (Doc 13, edited) |
| mNC 8 | Patient info SOP blanket internet ban; no secure transmission/RBAC/breach response | QM.SLQ028 | Closed (prior) | DCO093 Document 8, mNC 8 three changes (prohibition replacement, RBAC, data breach response) |
| mNC 9 | Post-market surveillance lacks escalation thresholds | QM.SLQ033 | Closed (prior) | DCO094 Doc 14 plus Part A supplemental finalizing the 1 percent complaint-rate trigger |
| mNC 10 | Process validation discretionary ("when necessary"); no not-required justification | QM.SLQ047 | Closed (prior) | DCO094 Document 17, mNC 10 objective criteria and Validation Applicability Determination |
| mNC 11 | DMR not owned/controlled when a CMO is used | QM.SLQ048 | Closed (prior) | DCO094 doc table and Appendix B: QM.SLQ048 Rev A to B (Doc 8, edited) |
| mNC 12 | Calibration allows out-of-tolerance use without formal impact assessment | QM.SLQ050 | Closed (prior) | DCO094 doc table and Appendix B: QM.SLQ050 Rev A to B (Doc 10, edited); FM4-QM.SLQ050 to Rev B |
| mNC 13 | Document Control three-day default effective date not risk-based | QM.SLQ001 | Closed (prior) | IA-2025 report note on mNC 13 ("addressed in DCO091"); DCO091 README NC 15 effective-date model; CAPA004 Action 1 |
| mNC 14 | Quality objectives limited; no trending/review/escalation | QM.SLQ037 | Closed (prior) | DCO094 Document 15, mNC 14 management requirements section plus five finalized objectives; QM.SLQ037 alignment sheet |
| mNC 15 | Nonconforming material allows undocumented handling; no CAPA linkage/use-as-is risk | QM.SLQ040 | Closed (prior) | DCO094 Document 16, mNC 15 three changes; FM1-QM.SLQ040 risk-assessment field |

mNC 1 sub-issue breakdown (each treated as its own line; all confirmed closed by the DCO095 dev prompt):

| mNC 1 sub-issue | Status | Closure location in the DCO095 plan |
|---|---|---|
| 1. Design changes lack formal change control with documented V&V determination | Planned (DCO095) | Pathway B and C driven by FM2-QM.SLQ052 Design Change Assessment; outline Sections 8, 9, 16; dev prompt 4.3 (FM2: V&V determination or rationale for none) |
| 2. No defined minimum planning requirements | Planned (DCO095) | FM1-QM.SLQ052 Design Project Scope and Plan; outline Section 7; dev prompt 4.2 and 4.3 |
| 3. Plan revisions not change-controlled | Planned (DCO095) | Plan updates between gates are change-controlled; outline Section 6; dev prompt 4.2 ("plan updates between gates are change-controlled") |
| 4. Conflict resolution authority undefined | Planned (DCO095) | Named authority with documented rationale and traceable approval; outline Sections 5 and 10; dev prompt 4.2 |
| 5. Design outputs not consistently controlled | Planned (DCO095) | All outputs formally controlled; outline Section 11; dev prompt 4.2 |
| 6. DHF capture criteria undefined | Planned (DCO095) | DHF entry criteria and responsibility; outline Sections 11 and 18; dev prompt 4.2 |
| 7. V&V planning optional | Planned (DCO095) | V&V always planned and controlled; outline Section 13; dev prompt 4.2 |
| 8. Validation equivalence not defined | Planned (DCO095) | Equivalence criteria and methodology; outline Section 13; dev prompt 4.2 |
| 9. Transfer checklist in lieu of final review | Planned (DCO095) | Final design review preserved at transfer; outline Section 15; dev prompt 4.2 |

### Opportunities for improvement

| ID | One-line summary | Document(s) | Status | Evidence |
|---|---|---|---|---|
| OFI 1 | Consolidated Risk Management Report at system level | QM.SLQ012 | Closed (prior) | DCO093 Document 1, OFI 1 fourth sub-bullet added |
| OFI 2 | Traceability of risk outputs to design inputs and V&V | QM.SLQ013 | Closed (prior); reinforced (DCO095) | DCO093 Document 2, OFI 2 traceability addition; reinforced by QM.SLQ052 Sections 14 and 17 (outline) and dev prompt 4.4 |
| OFI 3 | Management review annual input coverage documentation | QM.SLQ018 | Closed (prior) | DCO093 Document 4, OFI 3; FM1-QM.SLQ018 Rev B coverage field |
| OFI 4 | Documented justification for self-assessment supplier approvals | QM.SLQ015 | Closed (prior) | DCO092 Section 6, OFI 4 Cat I and III justification; FM1 and FM2-QM.SLQ015 fields |
| OFI 5 | MDR reportability decision methodology and UDI | QM.SLQ022 | Closed (prior) | DCO093 Document 6, OFI 5 decision framework and UDI requirement |
| OFI 6 | Recall metrics trending | QM.SLQ030 | Closed (prior) | DCO093 Document 9, OFI 6 Recall and Advisory Notice Metrics and Trending section |
| OFI 7 | Training effectiveness evaluation language | QM.SLQ003 | Closed (prior) | DCO092 Section 2, OFI 7 Section 9 strengthening |
| OFI 8 | Outdated pre-QMSR 21 CFR 820 references | QMS-wide | Closed (prior) | Systemic across DCO091 to DCO094 (CAPA004 OFI disposition note; DCO093 Appendix B; DCO094 per-document OFI 8 edits) |
| OFI 9 | Management Representative role designation | QM.SLQ018 (and QM.SLQ027) | Closed (prior) | DCO093 Document 4, OFI 9 designation paragraph; designation documented in QM.SLQ027 |
| OFI 10 | Risk Management linkage to FDA QMS expectations | QM.SLQ012 | Closed (prior); reinforced (DCO095) | DCO093 Document 1, OFI 10 Scope linkage statement; reinforced by QM.SLQ052 Section 14 (outline) and dev prompt 4.4 |

IA-2025 result: every mNC and OFI is assigned and addressed. Only mNC 1 (and the design-related reinforcement of mNC 3, OFI 2, OFI 10) is DCO095 work, and all nine mNC 1 sub-issues are Planned in the DCO095 plan. See Section D for one cross-reference integrity item that the DCO095 plan must add to keep the design-change-control chain intact (QM.SLQ020).

---

## Section B - 2026 Quality Plan ledger

| Quality Plan item (owner) | One-line summary | Status | Evidence and notes |
|---|---|---|---|
| QMSR Supplementary Provision Mapping (Ethan Rao, Q2) | Map 820.10(b) to procedures in QM.SLQ027; combination-product statement | Closed (prior) | DCO094 Appendix B: QMSR Supplementary Provision Mapping in QM.SLQ027 (Doc 1, edited) |
| Medical Device File Framework (Ethan Rao, Q2) | Define MDF construct tying DMR/DHF/DHR to clause 4.2.3 | Closed (prior); referenced (DCO095) | DCO094 Appendix B: MDF in QM.SLQ027 and QM.SLQ048 (Docs 1 and 8, edited); QM.SLQ052 references the MDF framework (outline Section 11; dev prompt 4.2) |
| QMS Platform Transition, DC.SLQ002 (per schedule) | Validate Silq eQMS and migrate procedures off FileHold | Closed (prior) for procedure text; migration deferred | Procedure-text transition delivered across DCO091 to DCO094 (non-design) and DCO095 (design); Phase 3 data migration and Phase 4 training remain out of scope. See Section C |
| Systemic Legacy 820 References (Ethan Rao, Q3) | Replace old Part 820 citations with ISO 13485 / QMSR | Closed (prior) | OFI 8 systemic updates across DCO091 to DCO094; design documents updated within DCO095 (dev prompt 4.4 OFI 8). Recommend a final confirmation pass at DCO095 release that no revised document retains a legacy citation |
| Quality Objectives: revise existing and add three new (Ethan Rao, Q2) | Tighten two objectives; add PMS, training, quarterly-execution objectives | Closed (prior) | DCO094 Document 15; QM.SLQ037 alignment sheet (five finalized objectives) |
| New Hire Training, Haley Shomo (Ethan Rao, May) | QMS training for new hire | Out of scope - training | Employee training delivery; excluded |
| QMSR Transition Training (Ethan Rao, Jun) | Train all employees on QMSR shift | Out of scope - training | Employee training delivery; excluded |
| Design Control Retraining, CAPA 2025-003 (Ethan Rao, Jul) | Retrain on design control series; CAPA003 effectiveness confirmation | Out of scope - training (triggered by DCO095) | Training is excluded; DCO095 release is noted as the trigger and the effectiveness confirmation for CAPA 2025-003 (outline Section 9; dev prompt 4.6) |
| Regulatory Reference Materials (Verne Sharma, Q2) | Purchase AAMI/ISO 13485 practical guide and standards | Out of scope - not a document action | Procurement action; not a QMS procedure revision and not design control; track on its own owner |
| Dynamic Employee Training Program (Ethan Rao, Q3) | Establish comprehension assessment beyond read-and-sign | Out of scope - training | DCO093 Appendix F.2.1 recommends a QM.SLQ003 comprehension-assessment addition; this is the training project and is excluded. The QM.SLQ037 training objective (count-based) is already Closed (prior) in DCO094 |
| Complaint/Advisory/MDR Escalation Pathway (Ethan Rao, Q2) | Cross-reference table mapping event types to procedures/owners | Closed (prior) | DCO093 Document 5, Event Escalation and Regulatory Pathway Cross-Reference |
| Design Control: Valve Modification Assessment, DC.SLQ001 (Ethan Rao, Jul) | Retrospective design controls on the valve change | Closed (prior) - separate project | CAPA 2025-003 Corrective Action 2; DC.SLQ001 is an in-flight project, grandfathered under the old SOPs (DCO095 outline Section 13; dev prompt Section 2). Not a DCO095 document edit |
| Design Control Procedure Revisions, CAPA 2025-003 (Ethan Rao, Jul) | Supplier modification triggers mandatory design review, risk, regulatory eval | Planned (DCO095) | Pathway C mandatory supplier/CMO trigger and FM2-QM.SLQ052 Design Change Assessment (outline Sections 5, 7; dev prompt 4.2). Carried into QM.SLQ052, which supersedes QM.SLQ004/005/006. See Section D item 1 for the reverse cross-reference in QM.SLQ020 |
| Supplier Audit: Pathway MedTech (Ethan Rao, Q4) | Add on-site CMO audit to the schedule | Closed (prior) - operational | DCO092 Appendix F.2.2: schedule data entry on FM7-QM.SLQ015 Rev B; not a procedure revision and not design control |
| Feedback Governance Procedure (Ethan Rao, Q2) | Governance section in QM.SLQ033 tying feedback inputs together | Closed (prior) | DCO094 Appendix B: Feedback Governance in QM.SLQ033 (Doc 14, edited) |
| Active Post-Market Surveillance Program (Greiner Q2; Rao Q3) | Establish active PMS objectives and procedures | Out of scope - separate CAPA (open elsewhere) | DCO094 Appendix B: PMS program deferred to a separate CAPA per locked decision; only the count-based QM.SLQ037 objective was added. Not design control; not a DCO095 obligation |
| Complaint Non-Investigation Rationale (Ethan Rao, Q2) | Require documented rationale for non-investigation (820.35) | Closed (prior) | DCO093 Document 5, Complaints Not Requiring Investigation addition |
| Regulatory Reporting QMSR Framing (Ethan Rao, Q2) | 820.10(b) crosswalk in MDR and recalls procedures | Closed (prior) | DCO093 Documents 6 and 9, QMSR framing statements |
| CAPA 2025-001 Effectiveness Confirmation (Ethan Rao, Nov) | Monitor complaints for inspected devices | Out of scope - not a document action | Effectiveness monitoring activity; not a procedure revision and not design control |
| CAPA 2025-002 Effectiveness Confirmation (Ethan Rao, Dec) | Evaluate complaints one year after QM.SLQ022 Rev B | Out of scope - not a document action | Effectiveness monitoring activity; not a procedure revision and not design control |
| CAPA 2025-003 Corrective Action Completion (Ethan Rao, Jul) | DC.SLQ001, Letter-to-File, QM.SLQ004/005/006 revisions, retraining | Partly Planned (DCO095) | Procedure-revision portion is Planned in DCO095 (Pathway C in QM.SLQ052); DC.SLQ001 and the Letter-to-File are separate project work; retraining is out of scope - training |
| Post-Production Risk File Update Triggers (Ethan Rao, Q3) | Trigger criteria for risk file revision in QM.SLQ012 Section 14 | Closed (prior) | DCO093 Document 1, Risk File Revision Trigger Criteria |
| Failure Mode and Probability Rating Review (Ethan Rao, Q2) | Review RM files against complaint history; recalibrate probabilities | Out of scope - operational risk activity (open elsewhere) | Risk-file review activity, not a procedure revision and not design control; track on its own owner |
| ASTM F623-25 Risk Management Alignment (Ethan Rao, Q3) | Update risk management policies for ASTM F623-25 scope change | Out of scope - risk activity (open elsewhere) | Risk-policy evaluation, not design control; not a DCO095 obligation |
| Packaging Inspection for ASTM F1886 (Ethan Rao, Q2) | Inspect finished goods for updated standard | Out of scope - operational inspection | Inspection activity; not a procedure revision and not design control |
| Gage R&R Study, UV Absorbance and Rinse Test (Ethan Rao, next production) | Complete Gage R&R or alternate study | Out of scope - operational study | Test-method study; not a procedure revision and not design control |
| UV Spectroscopy Test Protocol Development (Na He, Q3) | Develop UV spectroscopy test protocol | Out of scope - operational protocol development | Test-protocol development; not a procedure revision and not design control |

Quality Plan result: every design-related QMS procedure action is either Closed (prior) by DCO091 to DCO094 or Planned in DCO095 (the supplier-modification design control trigger). All training items are out of scope by direction. The remaining open Quality Plan items (Active PMS procedure, ASTM F623-25 and F1886 work, Gage R&R, UV protocol, failure-mode/probability review, regulatory reference purchase, and the comprehension-assessment training addition) are not design control and were never within the DCO095 mandate; they sit on separate CAPA or operational owners. The one design-control follow-through the DCO095 plan does not yet capture is the reverse cross-reference inside QM.SLQ020 (Section D item 1).

---

## Section C - DC.SLQ002 Phase 2 ledger

Phase boundaries (from DC.SLQ002 plan, Key Milestones and Table 1): Phase 1A and 1B are major and targeted revisions; Phase 2 is the batch of minor revisions; Phase 3 is data migration; Phase 4 is employee training. Phases 3 and 4 are out of scope for DCO095.

### Phase 1A (major rewrites)

| Document | Status | Evidence |
|---|---|---|
| QM.SLQ014 Electronic Doc System WI (and FM1-QM.SLQ014) | Closed (prior) | DCO091 README and editor guides; QM.SLQ014 Rev B to C |
| QM.SLQ001 Document Control SOP (and FM1, FM2, TMP1 family) | Closed (prior) | DCO091 README and combined QM001/QM014/FM1 guide; QM.SLQ001 Rev to B (also closes mNC 13) |

### Phase 1B (targeted revisions)

| Document | Status | Evidence |
|---|---|---|
| QM.SLQ003 Employee Training SOP | Closed (prior) | DCO092 Section 2 |
| QM.SLQ017 Internal Audits SOP | Closed (prior) | DCO092 Section 3 |
| QM.SLQ020 Purchasing Controls SOP | Closed (prior) for the transition; see Section D | DCO092 Section 4 (FileHold transition plus mNC 5). Note: DCO092 introduces new references to QM.SLQ004 inside QM.SLQ020 Rev E subsection 6.3.1; those references must be redirected to QM.SLQ052 by DCO095 (Section D item 1) |
| QM.SLQ036 Sales Order SOP | Closed (prior) | DCO092 Section 5 |
| QM.SLQ015 Supplier QA SOP | Closed (prior) | DCO092 Section 6 |
| QM.SLQ004 Design Control Program SOP | Planned (DCO095) | Deferred from DCO092 (DCO092 scope note and Appendix F.3); QM.SLQ004 is designated obsolete and superseded by QM.SLQ052 in DCO095 (outline Section 3; dev prompt 4.5 and 4.7). QM.SLQ052 contains no FileHold references (dev prompt 4.2), which closes the Phase 1B design-document transition obligation |

### Phase 2 (minor revisions)

Design documents (QM.SLQ005 through QM.SLQ010):

| Document | Status | Evidence |
|---|---|---|
| QM.SLQ005 Design Project Planning SOP | Planned (DCO095) | Designated obsolete, superseded by QM.SLQ052 (outline Section 3; dev prompt 4.5). Transition obligation closed because QM.SLQ052 has zero FileHold references (dev prompt 4.7) |
| QM.SLQ006 Design Input SOP | Planned (DCO095) | Same as above; content folded into QM.SLQ052 and TMP1-QM.SLQ052 |
| QM.SLQ007 Design Output SOP | Planned (DCO095) | Same as above; source-control content folded into SOP output/DMR guidance |
| QM.SLQ008 Design Review SOP | Planned (DCO095) | Same as above; folded into FM3-QM.SLQ052 |
| QM.SLQ009 Design V&V SOP | Planned (DCO095) | Same as above; folded into TMP2-QM.SLQ052 and FM4-QM.SLQ052 |
| QM.SLQ010 Design Transfer SOP | Planned (DCO095) | Same as above; folded into TMP3-QM.SLQ052 |

Non-design Phase 2 documents:

| Document | Status | Evidence |
|---|---|---|
| QM.SLQ012 Risk Management SOP | Closed (prior) | DCO093 Document 1 |
| QM.SLQ013 Risk Analysis SOP | Closed (prior) | DCO093 Document 2 |
| QM.SLQ016 CAPA SOP | Closed (prior) | DCO093 Document 3 |
| QM.SLQ018 Management Review SOP | Closed (prior) | DCO093 Document 4 |
| QM.SLQ021 Product Complaint System SOP | Closed (prior) | DCO093 Document 5 |
| QM.SLQ023 eMDR Submission WI | Closed (prior) | DCO093 Document 7 |
| QM.SLQ028 Protection of Confidential Patient Info | Closed (prior) | DCO093 Document 8 |
| QM.SLQ029 DHR Review and Approval SOP | Closed (prior) | DCO094 doc table (Doc 2, edited) |
| QM.SLQ030 Advisory Notices and Recalls SOP | Closed (prior) | DCO093 Document 9 |
| QM.SLQ038 Managing Regulatory Inspections SOP | Closed (prior) | DCO094 doc table (Doc 3, edited) |
| QM.SLQ043 Work Order SOP | Closed (prior) | DCO094 doc table (Doc 5, edited) |
| QM.SLQ046 Shipping SOP | Closed (prior) | DCO094 doc table (Doc 7, edited) |
| QM.SLQ048 Device Master Record SOP | Closed (prior) | DCO094 doc table (Doc 8, edited) |
| QM.SLQ051 Environmental Monitoring SOP | Closed (prior) | DCO094 doc table (Doc 11, edited) |
| QM.SLQ027 Quality Manual | Closed (prior) | DCO094 doc table (Doc 1, edited) |
| QM.SLQ039 Receiving Inspection SOP | Closed (prior) | DCO094 doc table (Doc 4, edited) |
| QM.SLQ045 Receiving SOP | Closed (prior) | DCO094 doc table (Doc 6, edited) |
| QM.SLQ049 Workstation Practices SOP | Closed (prior) | DCO094 doc table (Doc 9, edited) |
| QM.SLQ050 Calibration and Preventive Maintenance SOP | Closed (prior) | DCO094 doc table (Doc 10, edited) |

Design documents QM.SLQ004 through QM.SLQ010 handling: fully handled by the DCO095 plan. All seven are designated obsolete and superseded by the single QM.SLQ052, whose SOP and all new forms and templates contain zero FileHold references (dev prompt 4.2 and the dev-prompt self-check). This is the basis for the dev prompt Section 4.7 Phase 2 closure statement.

Non-design Phase 2 documents remaining open: none. Every non-design Phase 2 document maps to a Closed (prior) revision in DCO093 or DCO094.

Phase 3 and Phase 4 boundary: confirmed. Phase 3 (FileHold-to-eQMS data migration) and Phase 4 (employee training) are explicitly out of scope for DCO095 (DC.SLQ002 plan Key Milestones; DCO095 dev prompt Sections 4.7 and 7).

---

## Section D - Gaps for DCO095 (the actionable output)

The DCO095 plan, as currently scoped, closes IA-2025 mNC 1 (all nine sub-issues), the design-related Quality Plan items, and the DC.SLQ002 Phase 2 design-document transition. The items below are the concrete additions DCO095 should pick up. Items 1 and 2 are the substantive cross-reference gaps; items 3 and 4 are refinements that strengthen closure; item 5 is a completeness note confirming what DCO095 should not absorb.

1. QM.SLQ020 Purchasing Controls SOP reverse cross-reference to the obsoleted design SOP.
   - Obligation: After DCO092, QM.SLQ020 Rev E subsection 6.3.1 cites "QM.SLQ004 Design Control Program SOP" and requires that a supplier change "shall be initiated per QM.SLQ004." DCO095 obsoletes QM.SLQ004. This is the direct corrective chain for FDA 483 Observation 2 and CAPA 2025-003, so a dangling reference to an obsolete SOP here is a high-priority defect.
   - Why not yet covered: The DCO095 cross-reference sweep (outline Section 10; dev prompt 4.4) was built from the current controlled mirrors, where QM.SLQ020 Rev D contains no design-control reference. The QM.SLQ004 reference is added only by the DCO092 edit and so is invisible in those mirrors. QM.SLQ020 is not listed as a sweep target in either the outline or the dev prompt.
   - Recommendation: In the DCO095 editing-guide prompt, add QM.SLQ020 to the cross-reference sweep list. Instruct the dev agent to replace the QM.SLQ020 subsection 6.3.1 references to "QM.SLQ004 Design Control Program SOP" with "QM.SLQ052 Design Control SOP" and to route the supplier-change evaluation to the FM2-QM.SLQ052 Design Change Assessment under Pathway C, aligning the QM.SLQ020 mandatory-hold language with the Pathway C "no manufacture or distribution before assessment" requirement. Bump QM.SLQ020 to its next revision in the DCO095 package and on the DCO form.

2. Run the cross-reference sweep against the latest released revisions, not the pre-edit mirrors, and target the strings inserted by DCO093 and DCO094.
   - Obligation: The DCO091 to DCO094 edits inserted new references to the design SOP series that are not present in the readable mirrors. Confirmed examples: QM.SLQ013 Rev C (DCO093) inserts "QM.SLQ004 through QM.SLQ010" in the OFI 2 traceability text; QM.SLQ012 Rev C (DCO093) inserts "design control activities (QM.SLQ004 through QM.SLQ010)" in the OFI 10 scope text; QM.SLQ027 Rev F and QM.SLQ048 Rev B (DCO094) reference the "design control SOPs" in the Medical Device File framework.
   - Why not yet covered: QM.SLQ012, QM.SLQ013, QM.SLQ027, and QM.SLQ048 are already on the sweep list, but the dev prompt does not tell the agent to operate on the post-DCO091-094 released text, so the specific new strings could be missed if the agent works from the stale mirrors.
   - Recommendation: Instruct the dev agent to perform the sweep against the latest released revision of each document, to update the specific QM.SLQ004-through-QM.SLQ010 strings added by DCO093 (QM.SLQ012, QM.SLQ013) and the MDF design-control references added by DCO094 (QM.SLQ027, QM.SLQ048) to QM.SLQ052 (and the relevant new form or template IDs), and to add QM.SLQ015 and QM.SLQ016 to the verification checklist (confirm no design-SOP references; edit if found).

3. Operationalize mNC 1 sub-issues 3 and 7 at the form level in FM1-QM.SLQ052.
   - Obligation: mNC 1 sub-issue 3 (plan revisions must be change-controlled) and sub-issue 7 (V&V planning must be mandatory, not optional) are closed in the QM.SLQ052 narrative, but the predecessor DCO092 plan for FM1-QM.SLQ004 had added a "V&V Planning Requirement Determination" field and a "Project Plan Revision History" change-control log to capture these on the form.
   - Why not yet covered: The dev prompt Section 4.3 description of FM1-QM.SLQ052 (Design Project Scope and Plan) does not explicitly require a V&V-determination field or a plan-revision change-control log.
   - Recommendation: In the DCO095 editing-guide prompt, instruct the dev agent to include, in FM1-QM.SLQ052, a V&V planning determination field (with a documented rationale line and QA approval when V&V is limited) and a plan-revision change-control log, so sub-issues 3 and 7 are evidenced on the record and not only in the SOP text.

4. Add CAPA 004-2025 closure linkage to the DCO095 traceability and DCO form.
   - Obligation: CAPA 004-2025 Action 5 assigns mNC 1 closure to the dedicated Design Controls DCO (this is DCO095), and CAPA 004-2025 effectiveness check 1 depends on that DCO being released and effective. The DCO095 outline and dev prompt reference CAPA 2025-003 but not CAPA 004-2025.
   - Why not yet covered: The dev prompt finding-closure traceability (Section 4.6) lists IA-2025 findings and CAPA 2025-003 but does not state that DCO095 completes CAPA 004-2025 Action 5 (mNC 1).
   - Recommendation: In the DCO095 editing-guide prompt, add a line to the finding-closure traceability and to the DCO form completion guide stating that DCO095 release closes CAPA 004-2025 Action 5 (mNC 1) and supports CAPA 004-2025 effectiveness check 1, in addition to serving as the CAPA 2025-003 design-control corrective and retraining trigger.

5. Completeness note - items DCO095 should not absorb (no DCO095 action recommended).
   - The following 2026 Quality Plan items remain open but are not design control and were never within the DCO095 mandate: the Active Post-Market Surveillance procedure (deferred to a separate CAPA), the ASTM F623-25 and ASTM F1886 evaluations, the Gage R&R study, the UV spectroscopy protocol, the failure-mode and probability-rating review, the regulatory reference materials purchase, and the QM.SLQ003 comprehension-assessment training addition (training). Recommendation: confirm each is tracked on its existing CAPA or operational owner, but do not add them to DCO095, to avoid scope creep into the design-control redesign.

Gap counts by category:
- IA-2025: 0 content gaps (all nine mNC 1 sub-issues and the design-related reinforcements are Planned). 1 supporting cross-reference integrity gap that affects the design-change-control chain (item 1, QM.SLQ020), plus 1 sweep-execution gap (item 2) and 2 closure-strengthening refinements (items 3 and 4).
- 2026 Quality Plan (except training): 0 design content gaps. The design follow-through gap is shared with IA-2025 item 1 (QM.SLQ020). Non-design open items are out of DCO095 scope (item 5).
- DC.SLQ002 Phase 2: 0 gaps.

---

## Section E - Summary

As currently scoped, the DCO095 plan does close IA-2025 mNC 1 in full (all nine sub-issues are mapped to QM.SLQ052 in both the outline and the dev prompt), reinforces the design-related findings mNC 3, OFI 2, and OFI 10 (already closed in DCO093), carries the FDA 483 Observation 2 and CAPA 2025-003 supplier-modification corrective into Pathway C and the FM2-QM.SLQ052 Design Change Assessment, and completes the DC.SLQ002 design-document transition (Phase 1B QM.SLQ004 and Phase 2 QM.SLQ005 through QM.SLQ010) by superseding all seven with a single FileHold-free QM.SLQ052. Every other IA-2025 mNC and OFI and every design-related Quality Plan procedure action was already closed by DCO091 through DCO094, and every non-design Phase 2 document is closed in DCO093 or DCO094. Phase 3 migration and Phase 4 training are correctly out of scope.

The one substantive thing the DCO095 plan does not yet capture is the reverse cross-reference: DCO092 inserted references to the now-obsoleted QM.SLQ004 inside QM.SLQ020 Rev E (the supplier-change response that is the heart of the 483 Observation 2 corrective), and QM.SLQ020 is missing from the DCO095 cross-reference sweep. DCO095 must add QM.SLQ020 to the sweep and redirect those references to QM.SLQ052 and FM2-QM.SLQ052. The remaining recommendations strengthen closure: run the sweep against the latest released revisions and target the QM.SLQ004-through-QM.SLQ010 strings newly inserted by DCO093 and DCO094 (and verify QM.SLQ015 and QM.SLQ016); operationalize mNC 1 sub-issues 3 and 7 in FM1-QM.SLQ052; and add CAPA 004-2025 Action 5 to the DCO095 closure traceability.

Gap counts by category: IA-2025 - 0 content gaps, with 1 cross-reference integrity gap (QM.SLQ020) plus 1 sweep-execution item and 2 strengthening refinements; 2026 Quality Plan except training - 0 design content gaps (the QM.SLQ020 item is shared), with the remaining open items being non-design and out of DCO095 scope; DC.SLQ002 Phase 2 - 0 gaps.
