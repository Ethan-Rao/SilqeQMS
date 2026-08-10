# QMS Gap Analysis: FDA QMSR and ISO 13485:2016

**Date:** 2026-03-16  
**Prepared for:** Silq Leadership Team  
**Scope:** Regulatory policy assessment of Silq's current QMS against ISO 13485:2016, FDA QMSR supplementary provisions, and ISO 14971:2019 risk management requirements

---

## 1. Executive Summary

The FDA's Quality Management System Regulation (QMSR) replaces the legacy 21 CFR Part 820 framework with ISO 13485:2016 as the foundational QMS requirement, supplemented by FDA-specific provisions. The rule took effect **February 2, 2026**.

**Overall posture:** Silq is **well-positioned for compliance.** The existing QMS was built for Part 820, which is substantially similar to ISO 13485. Most procedural architecture is already aligned. The gaps identified below are targeted and manageable — they involve making existing practices more explicit, adding specific governance language, and updating regulatory citations.

**Risk management alignment** is a particular strength. QM.SLQ012 and QM.SLQ013 directly reference ISO 14971:2019 and implement its full process lifecycle. One minor enhancement opportunity was identified.

**Gap summary:**

| Classification | Count |
|---|---:|
| Significant Gap | 2 |
| Minor Gap | 5 |
| Adequate | 24 |
| Not Applicable (formal exclusions) | 4 |
| Editorial (legacy citation updates) | 19 documents |

**Priority areas for leadership attention:**

1. **Medical device file governance (clause 4.2.3)** — Silq has the underlying components (DMR, DHF, DHR) but lacks the explicit ISO 13485 "medical device file" framework that an auditor would look for. The content exists; the framing does not.
2. **Unified feedback procedure (clause 8.2.1)** — The individual feedback elements exist across several SOPs but are not tied together under a single governance statement with defined escalation triggers. QM.SLQ033 (Post-Market Surveillance) is the natural home for this governance language.
3. **QMSR supplementary provision integration** — Top-level QMS documents should explicitly reference the new supplementary provisions (§820.10(b), §820.35, §820.45) for audit traceability.
4. **Legacy 820 citation refresh** — 19 documents contain outdated Part 820 section references that need updating.

---

## 2. Regulatory Background

### What Changed

Under the former Part 820, the FDA wrote quality system requirements directly as U.S.-specific regulation text. The QMSR restructures this: the FDA now incorporates ISO 13485:2016 by reference as the core QMS requirement, then adds supplementary provisions where FDA-specific expectations go beyond the international standard.

### The Old Part 820 → QMSR Transition

| QMS Area | Old 820 Structure | New QMSR Structure |
|---|---|---|
| Core QMS requirements | FDA-specific regulations (§820.20–§820.250) | ISO 13485:2016 incorporated by reference via §820.10(a) |
| Document controls | §820.40 | ISO 13485 clause 4.2.4 |
| Design controls | §820.30 | ISO 13485 clause 7.3, plus §820.10(c) for scope |
| Purchasing controls | §820.50 | ISO 13485 clause 7.4 |
| CAPA | §820.100 | ISO 13485 clauses 8.5.2/8.5.3 (fully absorbed — no QMSR overlay) |
| Labeling / packaging | §820.120 / §820.130 | ISO 13485 clause 7.5.1, plus §820.45 supplementary |
| Complaint records | §820.198 | ISO 13485 clause 8.2.2, plus §820.35 supplementary |
| Other FDA-specific | Various | §820.10(b) overlay: UDI (21 CFR 830), MDR (21 CFR 803), corrections/removals (21 CFR 806), combination products (21 CFR 4) |

### QMSR Supplementary Provisions

The QMSR is not a pure adoption of ISO 13485. The FDA retained these U.S.-specific requirements:

- **§820.10(b):** The QMS must address UDI requirements (21 CFR 830), Medical Device Reporting (21 CFR 803), corrections and removals (21 CFR 806), and combination product requirements (21 CFR 4).
- **§820.35:** Supplementary requirements for complaint handling (including documented rationale for non-investigation decisions), record controls, and reporting linkage.
- **§820.45:** Supplementary requirements for device labeling and packaging controls beyond ISO 13485 clause 7.5.1.

### Compliance Timeline

The final rule was published February 2, 2024 with a two-year implementation period. The effective date was **February 2, 2026**.

### What This Analysis Covers and Does Not Cover

This is a **procedural-level** gap assessment. It evaluates whether Silq's SOPs address the requirements of ISO 13485 and the QMSR supplementary provisions. It does not audit individual records, training completion, lot files, or complaint files. ASTM testing standards are not analyzed — this analysis is about QMS structure, not product test methods. The FileHold-to-SilqQMS platform migration is a separate project (documented in the QMS Transition Plan) and is not addressed here.

### Note on SilqQMS and the Paper-Based QMS

Silq's quality management system is **paper-based**. The SilqQMS application is an **electronic document management system (EDMS)** that acts in support of the paper-based QMS — it provides controlled storage, retrieval, revision tracking, and audit trail capabilities for QMS documents. It does not replace the paper-based QMS processes themselves.

At the time of this assessment, the SilqQMS application is accessed exclusively by **administrative users**. There are no general end-users editing documents within the system; document authoring occurs outside the EDMS, and controlled document files (primarily PDFs) are uploaded to the system for storage and lifecycle management. Approvals are currently conducted via PDF upload rather than electronic signature workflow. The system will undergo formal software validation per QM.SLQ032 prior to production use.

---

## 3. Methodology

This assessment reviewed each ISO 13485:2016 clause (4 through 8) and each ISO 14971:2019 clause (4 through 10) against Silq's QM procedures, using the official clause-to-document mapping from QM.SLQ027 (Quality Manual) Appendix 1.

All 46 QM procedure texts were reviewed. The ISO 13485:2016 standard text, ISO 14971:2019 standard text, FDA QMSR Final Rule, ISO 13485 Practical Guide, and ISO/TR 24971:2020 guidance were consulted. Risk management file artifacts and QMS subsystem evidence folders were sampled for maturity assessment.

**Gap classifications:**

| Level | Meaning |
|---|---|
| **Adequate** | Current procedure substantially addresses the requirement. May need citation updates only. |
| **Minor Gap** | Requirement is partially addressed but the procedure lacks specific language or an explicit documentation element for a practice that likely exists. |
| **Significant Gap** | The requirement is not adequately addressed in current procedures. A new or substantially revised procedure element is needed. |
| **Not Applicable** | Formally excluded in the Quality Manual with documented justification. |

---

## 4. Gap Assessment: ISO 13485:2016 Clause by Clause

### Clause 4 — Quality Management System

| Clause | Requirement | Current Coverage | Assessment | Reconciliation Strategy |
|---|---|---|---|---|
| 4.1 | QMS processes defined and controlled with risk-based approach; QMS software validated | QM.SLQ027, QM.SLQ001, QM.SLQ032 | **Minor Gap** — QMS architecture and software validation are in place. Top-level documents do not explicitly integrate QMSR supplementary provisions as "applicable regulatory requirements." | Add a QMSR integration statement to QM.SLQ027 identifying each supplementary provision and the Silq procedures that address it. Include a combination-product applicability determination. |
| 4.2.1–4.2.2 | Documentation structure and quality manual | QM.SLQ027, QM.SLQ001, QM.SLQ002 | Adequate | — |
| 4.2.3 | Medical device file for each device type/family | QM.SLQ048 (DMR), QM.SLQ029 (DHR), design control SOPs (DHF) | **Significant Gap** — ISO 13485 requires a "medical device file" as a single defined construct that contains or references all documentation needed to demonstrate device conformity. This concept was not in the old Part 820. Silq maintains DMR, DHF, and DHR components, but there is no explicit framework tying them together under this ISO construct. An auditor asking for the "medical device file" would not find a single defined reference. | Revise QM.SLQ027 or QM.SLQ048 to include a "Medical Device File" section. This section should define the construct and provide a cross-reference table mapping Silq's existing DMR (QM.SLQ048), DHF (design SOPs), and DHR (QM.SLQ029) to clause 4.2.3. The underlying content already exists — this is a framing exercise. |
| 4.2.4 | Control of documents | QM.SLQ001, QM.SLQ002 | Adequate | — |
| 4.2.5 | Control of records | QM.SLQ001, QM.SLQ028 | Adequate | — |

### Clause 5 — Management Responsibility

| Clause | Requirement | Current Coverage | Assessment | Reconciliation Strategy |
|---|---|---|---|---|
| 5.1–5.5 | Management commitment, customer focus, quality policy, objectives, roles, authority, and communication | QM.SLQ018, QM.SLQ027, QM.SLQ035, QM.SLQ034, QM.SLQ037, QM.SLQ025 | Adequate | — |
| 5.6 | Management review with required inputs/outputs and retained records | QM.SLQ018, QM.SLQ027 | Adequate | Legacy citation update needed (see Section 7). |

### Clause 6 — Resource Management

| Clause | Requirement | Current Coverage | Assessment | Reconciliation Strategy |
|---|---|---|---|---|
| 6.1 | Adequate resources for QMS | QM.SLQ027, QM.SLQ018, QM.SLQ025 | Adequate | — |
| 6.2 | Competence, training, awareness, records | QM.SLQ003, QM.SLQ027 | Adequate | — |
| 6.3 | Infrastructure including maintenance | QM.SLQ027, QM.SLQ050 | Adequate | — |
| 6.4 | Work environment and contamination control | QM.SLQ027, QM.SLQ051 | Adequate | — |

### Clause 7 — Product Realization

| Clause | Requirement | Current Coverage | Assessment | Reconciliation Strategy |
|---|---|---|---|---|
| 7.1 | Product realization planning with risk management integration | QM.SLQ004, QM.SLQ012, QM.SLQ013, QM.SLQ025 | Adequate | — |
| 7.2 | Customer and regulatory requirements; communication with regulators | QM.SLQ004, QM.SLQ020, QM.SLQ021, QM.SLQ030, QM.SLQ036 | **Minor Gap** — Coverage is broad. Ownership boundaries between complaint (QM.SLQ021), advisory notice/recall (QM.SLQ030), and MDR (QM.SLQ022) workflows should be clarified so the escalation pathway is unambiguous for an auditor. | Add a cross-reference table to QM.SLQ021 or QM.SLQ030 that maps event types to the responsible procedure and decision owner. Brief addition to an existing SOP. |
| 7.3 | Design and development (planning through transfer, change control, files) | QM.SLQ004–010, QM.SLQ012, QM.SLQ013 | Adequate — Design control architecture is mature. Note: clause 7.3.10 (design files) relates to the 4.2.3 medical device file gap. | Resolve concurrently with the 4.2.3 strategy. |
| 7.4 | Purchasing: risk-based supplier evaluation, purchasing information, verification | QM.SLQ015, QM.SLQ020, QM.SLQ039 | Adequate | — |
| 7.5.1/7.5.8/7.5.9/7.5.11 | Production control, identification, traceability, preservation | QM.SLQ019, QM.SLQ029, QM.SLQ043–049 | Adequate | — |
| 7.5.3 | Installation activities | Excluded (QM.SLQ027) | Not Applicable — Products ship ready to use. | — |
| 7.5.4 | Servicing activities | Excluded (QM.SLQ027) | Not Applicable — No servicing required. | — |
| 7.5.6 | Process validation | QM.SLQ047 | Adequate | — |
| 7.5.9.2 | Particular requirements for implantable devices | Excluded (QM.SLQ027) | Not Applicable — No implantable devices. | — |
| 7.5.10 | Customer property | Excluded (QM.SLQ027) / QM.SLQ028 | Not Applicable — No physical customer property. Patient data protected per QM.SLQ028. | — |
| 7.6 | Control of monitoring and measuring equipment | QM.SLQ050, QM.SLQ047 | Adequate | — |

### Clause 8 — Measurement, Analysis, and Improvement

| Clause | Requirement | Current Coverage | Assessment | Reconciliation Strategy |
|---|---|---|---|---|
| 8.1 | Plan monitoring, measurement, analysis, improvement | QM.SLQ011, QM.SLQ027 | Adequate | — |
| 8.2.1 | Documented feedback procedure with production/post-production data and early warning input to risk management and CAPA | QM.SLQ021, QM.SLQ033, QM.SLQ018, QM.SLQ016 | **Significant Gap** — ISO 13485 requires a documented procedure for feedback that provides early warning of quality problems and feeds into risk management. Silq has the underlying pieces (complaints, PMS, management review, CAPA) but no single governance statement tying them together as a unified feedback system with escalation triggers. | QM.SLQ033 (Post-Market Surveillance) already aggregates post-market data and is the natural home for this governance language. Add a section to QM.SLQ033 that explicitly defines how complaint data (QM.SLQ021), CAPA trend data (QM.SLQ016), and management review outputs (QM.SLQ018) feed into the feedback loop, and define what constitutes an escalation trigger. This leverages all existing SOPs — it does not require a new standalone procedure. |
| 8.2.2 | Complaint handling with investigation, reportability, and records | QM.SLQ021, QM.SLQ022, QM.SLQ023 | **Minor Gap** — Core complaint process is documented. ISO 13485 and QMSR §820.35 require that when a complaint is not investigated, the documented rationale must be retained. QM.SLQ021 does not currently contain an explicit standalone requirement for this. | Add a requirement statement to QM.SLQ021 mandating documented rationale for every non-investigation decision. Single-sentence addition. |
| 8.2.3 | Reporting to regulatory authorities | QM.SLQ022, QM.SLQ023, QM.SLQ030 | **Minor Gap** — Reporting channels exist for MDR and corrections/removals. Procedures should include an explicit crosswalk to the QMSR §820.10(b) "applicable regulatory requirements" framework. | Add a brief "applicable regulatory requirements" statement to QM.SLQ022 or QM.SLQ030 referencing the QMSR §820.10(b) overlay. |
| 8.2.4 | Internal audit program | QM.SLQ017 | Adequate | Legacy citation update needed (see Section 7). |
| 8.2.5/8.2.6 | Process and product monitoring/measurement | QM.SLQ011, QM.SLQ039, QM.SLQ029, QM.SLQ018 | Adequate | — |
| 8.3 | Control of nonconforming product | QM.SLQ040, QM.SLQ030 | Adequate | — |
| 8.4 | Data analysis | QM.SLQ011, QM.SLQ016, QM.SLQ018 | Adequate | — |
| 8.5.1 | General improvement | QM.SLQ016, QM.SLQ018 | Adequate | — |
| 8.5.2 | Corrective action | QM.SLQ016 | Adequate | Legacy citation update needed (see Section 7). |
| 8.5.3 | Preventive action | QM.SLQ016 | Adequate | Legacy citation update needed (see Section 7). |

---

## 5. QMSR Supplementary Provisions

These are FDA-specific requirements that sit on top of ISO 13485. Silq's procedures need to demonstrably address them.

### §820.10(b): Other Applicable FDA Requirements

**Assessment: Minor Gap** (consolidated with clause 4.1 finding above)

§820.10(b) requires the QMS to address specific FDA regulatory obligations:

| FDA Requirement | Silq Procedure | Status |
|---|---|---|
| UDI (21 CFR 830) | QM.SLQ019 | Addressed |
| MDR (21 CFR 803) | QM.SLQ022, QM.SLQ023 | Addressed |
| Corrections/Removals (21 CFR 806) | QM.SLQ030 | Addressed |
| Combination products (21 CFR 4) | Not documented | Not addressed |

**Gap:** The individual regulatory channels exist but the Quality Manual does not explicitly frame them as the §820.10(b) "applicable regulatory requirements" set. Additionally, combination-product applicability should be formally documented — even if the determination is "not applicable to Silq's current product portfolio," that determination should be on record.

**Strategy:** Add a §820.10(b) cross-reference table to QM.SLQ027 that maps each requirement to the implementing procedure, and include a formal combination-product applicability statement.

### §820.35: Complaint and Record Supplementary Requirements

**Assessment: Minor Gap** (same finding as clause 8.2.2)

QM.SLQ021 defines a designated complaint unit, investigation process, reportability handoff to MDR (QM.SLQ022), and complaint logging. The process is robust.

**Gap:** §820.35 requires documented rationale when a complaint is not investigated. QM.SLQ021 does not currently contain an explicit requirement statement for this.

**Strategy:** Add the requirement statement to QM.SLQ021. Single-sentence addition to an existing procedure.

### §820.45: Device Labeling and Packaging

**Assessment: Adequate**

§820.45 carries forward supplementary requirements for device labeling controls and labeling inspection from the old §820.120/§820.130. Silq's labeling controls were validated under the former Part 820 framework and are addressed through production SOPs and the Device Master Record (QM.SLQ048). The labeling reference in Silq's procedures should be confirmed to align with the renumbered §820.45 provision during the legacy citation refresh campaign (Section 7).

**Note:** The previous draft of this report incorrectly identified §820.45 as a CAPA supplementary provision. The QMSR §820.45 addresses labeling and packaging. CAPA requirements from the old §820.100 are now fully covered by ISO 13485 clauses 8.5.2 and 8.5.3 without a separate QMSR supplementary provision.

---

## 6. Risk Management Assessment: ISO 14971:2019

ISO 13485:2016 references ISO 14971 throughout as the expected framework for risk management. The QMSR places increased emphasis on risk-based approaches across the QMS. This section provides a detailed assessment of Silq's risk management procedures against ISO 14971:2019.

### Standard Version Alignment

**QM.SLQ012** (Risk Management SOP, Rev B) explicitly references:
- **ISO 14971:2019** — Medical devices — Application of risk management to medical devices
- **ISO/TR 24971:2020** — Medical devices — Guidance on the application of ISO 14971

**QM.SLQ013** (Risk Analysis SOP, Rev B) references the same standards.

This is the current edition of both documents. No version alignment gap exists.

### Clause-by-Clause Assessment

| ISO 14971 Clause | Requirement | Silq Coverage | Assessment |
|---|---|---|---|
| **4.1** Risk management process | Establish, document, and maintain throughout the product lifecycle | QM.SLQ012 defines the overall process (Sections 8–15) with lifecycle integration through design control and post-production monitoring. | Adequate |
| **4.2** Management responsibilities | Top management ensures adequate resources, defines risk acceptability policy, reviews at planned intervals | QM.SLQ012 assigns management responsibility for risk acceptability criteria, resource allocation, and periodic review. QM.SLQ018 requires risk management status as a management review input. | Adequate |
| **4.3** Competence of personnel | Personnel performing risk management shall be competent | QM.SLQ012 assigns responsibility to a cross-functional team (R&D, Manufacturing, QA, RA, Clinical, Executive Management). QM.SLQ003 governs competency and training. | Adequate |
| **4.4** Risk management plan | Document a plan for each device/family: scope, responsibilities, review requirements, acceptability criteria, verification activities, post-production review | QM.SLQ012 Section 8 specifies all required plan elements. TMP1-QM.SLQ012 provides a structured template that addresses each element. | Adequate |
| **4.5** Risk management file | Maintain a file containing all risk management records and deliverables | QM.SLQ012 Section 15 defines the risk management file as part of the DHF with complete contents enumerated (plan, analyses, evaluations, controls, report). | Adequate |
| **5.1** Risk analysis process | Identify intended use, hazards, and estimate risks using systematic methods | QM.SLQ012 Section 9 + QM.SLQ013 provide two complementary methods: top-down PHA (master hazard analysis) and bottom-up FMEA (design and process). | Adequate |
| **5.2** Intended use and foreseeable misuse | Document intended use, foreseeable misuse, and device characteristics | QM.SLQ013 PHA procedure requires an overview including intended use, general function, principle of operation, potential users, and reasonably foreseeable misuse. | Adequate |
| **5.3** Safety characteristics identification | Use device characteristic questions (per ISO 14971 Annex C) to identify safety-relevant properties | QM.SLQ013 Appendix 1 reproduces the full set of device characterization questions from ISO/TR 24971:2020 Annex A (34 questions covering all hazard domains). These are incorporated into the PHA template. | Adequate |
| **5.4** Hazard identification | Identify known and foreseeable hazards in normal and fault conditions | QM.SLQ013 references ISO 14971 Table C.1 hazard categories (reproduced in Appendix 2) and requires systematic identification via PHA and FMEA methods. | Adequate |
| **5.5** Risk estimation | Estimate risk (severity × probability) for each hazardous situation | QM.SLQ012 Appendix 1 defines 5-level severity and 5-level likelihood scales with both design and process failure frequency ratings. Risk estimation is required for both pre-mitigation and post-mitigation states. | Adequate |
| **6** Risk evaluation | Compare estimated risks against defined acceptability criteria | QM.SLQ012 Section 10 + Appendix 2 define a severity/likelihood matrix yielding Major, Moderate, and Minor categories. Any risk involving likely death or irreversible injury must be Major. Criteria required in each Risk Management Plan. | Adequate |
| **7.1** Risk control option analysis | Identify and analyze options following the priority order: inherent safety → protective measures → information for safety | QM.SLQ012 Section 11 specifies the three-tier hierarchy in the correct ISO 14971 priority order. Explicitly states that information for safety "must be assumed not to quantifiably reduce residual risk." | Adequate |
| **7.2** Implementation of risk control measures | Implement controls and verify implementation | QM.SLQ012 requires that implementation of each mitigation be verified and recorded. Statistical verification requirements are linked to risk category (QM.SLQ011). | Adequate |
| **7.3** Residual risk evaluation | Re-evaluate risk after controls are implemented | QM.SLQ012 Section 12 requires re-evaluation with updated ratings and documentation. Residual risks are reviewed in design reviews. | Adequate |
| **7.4** Benefit-risk analysis | When residual risk exceeds criteria, conduct benefit-risk analysis | QM.SLQ012 Sections 12.5–12.6 require benefit-risk analysis using literature, post-market data, and internal surveillance. Moderate or Major residual risks receive targeted analysis. Management team reviews and approves. | Adequate |
| **7.5** Risks from controls | Evaluate whether implemented controls introduce new hazards | QM.SLQ012 explicitly states: "All implemented risk mitigations are considered part of the design, so must themselves be evaluated to determine if they introduce new hazards or affect the risk ratings of previously identified ones." | Adequate |
| **7.6** Completeness of risk control | Verify all identified hazards have been addressed | Covered through risk management report requirements (QM.SLQ012 Section 13) which must confirm all planned activities were implemented. | Adequate |
| **8** Overall residual risk | Document that overall residual risk is acceptable | QM.SLQ012 Section 12 requires overall benefit-risk analysis and management team approval of acceptability based on criteria in the Risk Management Plan. | Adequate |
| **9** Risk management review | Confirm plan executed, overall risk acceptable, production/post-production methods in place | QM.SLQ012 Section 13 (Risk Management Report) requires confirmation of all three elements. Report is retained in the risk management file. | Adequate |
| **10.1–10.2** Information collection | Actively collect safety-relevant information from production and field sources | QM.SLQ012 Section 14 enumerates specific sources: CAPAs, NCMRs, MDRs, production monitoring, user information, supply chain, publicly available information, state-of-the-art data. QM.SLQ033 defines the post-market surveillance plan. | Adequate |
| **10.3–10.4** Information review and action | Review collected information for relevance to risk analyses; take action when indicated | QM.SLQ012 requires evaluation for impact on previous risk management activities. | **Minor Gap** — see below |
| **10.5** Risk management experience | Periodically review the risk management process for continued effectiveness | QM.SLQ012 requires annual review prior to management review. QM.SLQ018 includes risk management status in review agenda. | Adequate |

### Risk Management Gap Finding

**ISO 14971 clauses 10.3–10.4: Post-production information triggers**

**Classification: Minor Gap**

QM.SLQ012 Section 14 states that Silq "evaluates the information for impact on previous risk management activities and provides it as an input back into the risk management process, revising risk management deliverables such as the Master Hazard Analysis as needed." It further states that "review of post-production information for new or changes to hazards is to occur as an on-going activity" with a minimum formal review cadence of annually (prior to management review).

The gap is one of specificity: the SOP does not define explicit trigger criteria for when post-production information requires a formal risk file revision versus when it is noted and monitored until the next scheduled review. ISO 14971 expects that the decision framework — what types of information trigger immediate action — be more explicitly defined in the governing procedure.

**Reconciliation Strategy:** Add a short decision framework to QM.SLQ012 Section 14 (or to QM.SLQ033) that defines specific trigger criteria for risk file revision. Examples of triggers: new hazard identified, change in severity or probability of a known hazard, safety-relevant regulatory alert, or adverse trend in post-market data. This is a brief addition to existing SOP language, not a new procedure.

### Risk Management Summary

Silq's risk management framework is comprehensive and well-aligned to ISO 14971:2019. The procedures cover the full lifecycle from planning through post-production monitoring. The explicit references to ISO 14971:2019 and ISO/TR 24971:2020, the structured use of PHA and FMEA methods, the correct three-tier risk control hierarchy, and the integration with design control and management review all provide strong audit evidence. The single minor gap is about making the post-production trigger criteria more explicit.

---

## 7. Legacy 820 Citation Refresh

19 QM documents contain explicit references to old Part 820 section numbers. These are **editorial updates, not procedural gaps**. The underlying procedures are functional; only the regulatory citations need updating.

| Document | Current Citation | Updated Reference |
|---|---|---|
| QM.SLQ001 | 820.40 | ISO 13485 clauses 4.2.4/4.2.5 |
| QM.SLQ003 | 820.25 | ISO 13485 clause 6.2 |
| QM.SLQ004 | 820.30 | ISO 13485 clause 7.3 |
| QM.SLQ006 | 820.30 | ISO 13485 clause 7.3 |
| QM.SLQ007 | 820.30 | ISO 13485 clause 7.3 |
| QM.SLQ011 | 820.250 | ISO 13485 clauses 8.1/8.4 |
| QM.SLQ015 | 820.50(a) | ISO 13485 clause 7.4 |
| QM.SLQ016 | 820.100 | ISO 13485 clauses 8.5.2/8.5.3 |
| QM.SLQ017 | 820.22 | ISO 13485 clause 8.2.4 |
| QM.SLQ018 | 820.20 | ISO 13485 clause 5.6 |
| QM.SLQ019 | 820.60/820.65 | ISO 13485 clauses 7.5.8/7.5.9 |
| QM.SLQ020 | 820.50 | ISO 13485 clause 7.4 |
| QM.SLQ021 | 820.198 | ISO 13485 clause 8.2.2 + QMSR §820.35 |
| QM.SLQ030 | 820.198 | ISO 13485 clause 8.2.3 |
| QM.SLQ032 | 820.70 | ISO 13485 clauses 7.5.1/4.1.6 |
| QM.SLQ039 | 820.80 | ISO 13485 clauses 7.4.3/8.2.6 |
| QM.SLQ040 | 820.90 | ISO 13485 clause 8.3 |
| QM.SLQ045 | 820.80 | ISO 13485 clauses 7.4.3/8.2.6 |
| QM.SLQ047 | 820.75 | ISO 13485 clause 7.5.6 |

Most citations are in the "References" or "Applicable Standards" section near the top of each SOP — a bounded, predictable update. Two documents (QM.SLQ017 and QM.SLQ018) also contain 820 references in body text that will require slightly more careful revision.

---

## 8. Reconciliation Strategy

### Tier 1 — Significant Gaps (Procedural Revision Required)

**1. Medical Device File Framework (clause 4.2.3)**

Silq already maintains DMR documentation (QM.SLQ048), Design History Files (via design control SOPs), and Device History Records (QM.SLQ029). The gap is not in content but in how these components are presented for ISO 13485 compliance.

- Revise QM.SLQ027 (Quality Manual) or QM.SLQ048 (DMR SOP) to include a "Medical Device File" section
- Define the construct and provide a cross-reference table mapping existing DMR, DHF, DHR, risk management file, labeling documentation, and product specifications to the clause 4.2.3 requirement
- This is a framing and cross-reference exercise — the underlying documentation already exists

**2. Feedback Governance (clause 8.2.1)**

QM.SLQ021 (complaints), QM.SLQ033 (post-market surveillance), QM.SLQ016 (CAPA), and QM.SLQ018 (management review) each contain elements of the required feedback system.

- Add a governance section to QM.SLQ033 (Post-Market Surveillance SOP), which already serves as the post-market data aggregation point
- This section should explicitly define how complaint data (QM.SLQ021), CAPA trend data (QM.SLQ016), and management review outputs (QM.SLQ018) feed into the feedback loop
- Define what constitutes an escalation trigger — the threshold at which routine monitoring becomes an action item
- This does not require a new procedure; it is a short governance section in an existing SOP that ties the others together

### Tier 2 — Minor Gaps (Targeted SOP Additions)

These gaps can be addressed through focused additions to existing procedures. None require new standalone documents.

| Gap | Affected Procedure | Revision Needed |
|---|---|---|
| QMSR top-level framing and §820.10(b) integration | QM.SLQ027 | Add a QMSR supplementary provision mapping table and combination-product applicability statement |
| Complaint non-investigation rationale (§820.35) | QM.SLQ021 | Add a requirement statement mandating documented rationale for non-investigation decisions |
| Complaint/advisory/MDR escalation pathway (clause 7.2) | QM.SLQ021 or QM.SLQ030 | Add a cross-reference table mapping event types to responsible procedures and decision owners |
| Regulatory reporting QMSR framing (clause 8.2.3) | QM.SLQ022 or QM.SLQ030 | Add a statement linking reporting procedures to the QMSR §820.10(b) overlay |
| Risk file update triggers (ISO 14971 clause 10) | QM.SLQ012 or QM.SLQ033 | Add a decision framework defining trigger criteria for formal risk file revision |

### Tier 3 — Editorial Campaign (Citation Refresh)

The 19-document legacy 820 citation refresh (detailed in Section 7) is a bounded, mechanical update. Most changes are in the "References" section of each SOP. This can be executed as a controlled batch through the document control process with minimal risk of affecting procedural content.

### What This Strategy Does Not Include

- **Implementation ownership, timelines, or staffing** — These are leadership decisions to be made after this assessment is reviewed.
- **ASTM product testing standard analysis** — Testing standards are active and in use; they are not affected by the QMSR transition.
- **Employee training record review** — The training system (QM.SLQ003) is adequate; individual record completeness is an operational audit item.
- **FileHold-to-SilqQMS platform migration** — Documented separately in the QMS Transition Plan. Some documents identified here will also need platform-related revisions; coordinating the two is a leadership decision.
- **SilqQMS EDMS software validation** — The SilqQMS application will be validated per QM.SLQ032 as a separate project prior to production use. Validation scope covers the Document Control and Admin Docs Libraries modules (the EDMS functions that support the paper-based QMS). Validation deliverables are maintained in the software validation project folder.

---

*This report identifies procedural-level gaps and recommends reconciliation strategies that leverage Silq's existing QMS documentation. It does not prescribe implementation owners, timelines, staffing, or operational design choices. Those decisions rest with the leadership team.*
