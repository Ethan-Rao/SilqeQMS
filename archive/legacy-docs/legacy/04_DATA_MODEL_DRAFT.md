## Core platform tables

- **users**
- **roles**
- **permissions**
- **user_roles** (m2m)
- **role_permissions** (m2m)
- **audit_events** (append-only)

## Draft domain tables (high-level)

### Document Control & QMS

- controlled_documents
- document_revisions
- document_approvals
- capas
- ncrs
- change_requests
- change_approvals

### Design Controls

- design_inputs
- design_outputs
- design_reviews
- verification_activities
- trace_links (generic: from_type/from_id/from_rev → to_type/to_id/to_rev)

### PLM

- items
- item_revisions
- ecos (or changes, linked to change_requests)
- releases

### Supplier Management

- suppliers
- asl_entries
- supplier_qualifications
- supplier_scores
- supplier_audits
- supplier_findings

### Manufacturing

- work_orders
- lots
- dhr_records (evidence pointers + references to released instructions)

### Manufacturing File Output

- output_templates
- output_bundles
- output_bundle_revisions
- output_artifacts (files stored via storage abstraction)

### Employee Training

- training_items
- training_matrix_rules
- training_assignments
- training_completions

## Revision strategy (draft)

- **Documents**: `controlled_documents` is the “container”; `document_revisions` contains immutable released revisions.
- **Product**: `items` + `item_revisions` similar pattern; released revision is immutable.
- **Training evidence**: `training_completions` are immutable records; retraining creates a new completion record.
- **Exports**: `output_bundle_revisions` are immutable; regenerated output is a new revision.

