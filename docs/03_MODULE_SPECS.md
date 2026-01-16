## Design Controls

- **Entities**: DesignInput, DesignOutput, DesignReview, VerificationActivity, TraceLink
- **Workflows**: Draft → Review → Released; change creates new revision/record where applicable
- **Screens**: DHF overview, input/output lists, trace matrix, review log
- **Reports/exports**: DHF packet export (links to released docs + evidence)

## Document Control & QMS (CAPA / NCR / Change Control)

- **Entities**: ControlledDocument, DocumentRevision, CAPA, NCR, ChangeRequest, ChangeApproval
- **Workflows**:
  - Docs: Draft → Review → Released → Obsolete
  - CAPA: Open → Containment → RCA → Actions → Effectiveness → Closed
  - NCR: Open → Disposition → Closed (optional CAPA link)
  - Change: Requested → Impact assessed → Approved → Implemented → Verified → Closed
- **Screens**: doc library, doc viewer, CAPA board, NCR list, change requests
- **Reports/exports**: controlled doc list, open CAPAs, change history export

## PLM

- **Entities**: Item (SKU/component), ItemRevision, Release, ECO/ECN, TraceLink
- **Workflows**: item revision drafted → released; ECO drives document/manufacturing updates
- **Screens**: item master, revision comparison, release dashboard, ECO list/detail
- **Reports/exports**: released item packet (linked docs, outputs, affected lots)

## Supplier Management

- **Entities**: Supplier, ASLEntry, SupplierQualification, SupplierScore, SupplierAudit, SupplierFinding
- **Workflows**: onboard → qualify → approve → monitor (scores/audits) → requalify as needed
- **Screens**: supplier directory, ASL, audit scheduler, findings list
- **Reports/exports**: ASL export, supplier performance report

## Manufacturing

- **Entities**: WorkOrder, Lot, DHRRecord (evidence pointers), DMRPointer (links to released instructions)
- **Workflows**: work order created → lots issued → evidence collected → closed
- **Screens**: work order list/detail, lot history, DHR evidence view
- **Reports/exports**: lot genealogy, work order summary

## Manufacturing File Output

- **Entities**: OutputTemplate, OutputBundle, OutputBundleRevision, OutputArtifact
- **Workflows**: select released sources → generate bundle → release bundle → distribute
- **Screens**: output generator, bundle library, artifact viewer/download
- **Reports/exports**: DMR bundle, DHR packet, label/router export

## Employee Training

- **Entities**: TrainingItem, TrainingAssignment, TrainingCompletion, TrainingMatrixRoleRule
- **Workflows**: assignment → completion evidence → retraining triggers (doc rev changes)
- **Screens**: training matrix, my training queue, completion log, admin assignment UI
- **Reports/exports**: training status report by role/person, overdue training list

