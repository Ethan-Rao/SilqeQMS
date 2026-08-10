## Purpose

Build a **minimal ISO 13485-aligned eQMS** for Silqe that is small-company friendly (1 product family, 3 SKUs) and prioritizes **controlled records, auditability, and simple workflows** over enterprise complexity.

## Non-goals (explicitly not in v1)

- ERP/MRP replacement, full MES, or full-blown “enterprise PLM”
- Complex multi-site / multi-business-unit workflows
- Deep integrations (except basic export interfaces and storage abstraction)
- Advanced e-signature / 21 CFR Part 11 features (see `02_COMPLIANCE_ASSUMPTIONS.md`)
- Automated regulatory submissions tooling
- Any Rep QMS-specific features (distribution logs, tracing, ShipStation, customer sync, etc.)

## Core modules (v1 backbone)

### Design Controls

- **Artifacts**: design inputs, outputs, reviews, verification evidence links, validation references (as needed).
- **Traceability**: basic trace links (Input → Output → Verification).
- **Reviews**: simple review records with attendees, date, and outcome.
- **Change linkage**: design changes link to ECO/ECN and released revisions.

### Document Control & QMS (includes CAPA, NCR, Change Control)

- **Document control**: controlled docs with revisions, status (Draft/Released/Obsolete), and distribution.
- **CAPA**: problem statement, containment, root cause, actions, effectiveness check, closure.
- **NCR**: nonconformance record with disposition and linkage to lots/work orders when applicable.
- **Change control**: change request → impact assessment → approval → implementation → release linkage.

### Product Lifecycle Management (PLM)

- **Items/parts**: minimal item master for the 3 SKUs and supporting components.
- **Revisions/releases**: revisioned product records; released revisions immutable.
- **ECO/ECN**: engineering change records linked to items, docs, and manufacturing outputs.
- **Traceability**: basic links between released docs, BOM-ish references (minimal), and outputs.

### Supplier Management

- **ASL**: approved supplier list with scope, status, and criticality.
- **Qualification**: simple qualification checklist and evidence attachments.
- **Scoring**: basic periodic score (quality, delivery, responsiveness).
- **Supplier audits**: audit plan, findings, follow-ups (link to CAPA if needed).

### Manufacturing

- **Lots**: lot records with status and linkage to outputs/evidence.
- **Work orders**: minimal work order tracking; avoid full routing/MES.
- **DHR/DMR hooks**: store pointers/evidence for what was built and what controlled instructions applied.

### Manufacturing File Output

- **Controlled exports**: generate versioned bundles (DMR, DHR packets, labels/routers) from released sources.
- **Immutability**: exported artifacts are immutable once released (new export = new revision).
- **Distribution**: download access controlled; audit downloads/events.

### Employee Training

- **Training matrix**: roles → required trainings/doc read-and-understand.
- **Assignments**: assign training by role or by person.
- **Evidence**: completion records, dates, acknowledgements, and linked controlled docs.
- **Re-training**: periodic retraining / triggers from doc revision changes.

