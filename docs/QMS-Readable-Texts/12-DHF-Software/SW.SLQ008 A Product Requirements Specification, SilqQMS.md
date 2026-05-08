

SilqQMS Document Management Software System


Product Requirements Specification

Purpose
The purpose of this document is to define the product requirements for the electronic document management system SilqQMS. This document specifies the requirements (design inputs) for the functional, security, and data integrity features that have been identified for SilqQMS based on SILQ's intended use of the system. This document also includes a risk analysis of the SilqQMS software application, per QM.SLQ032 (which allows the risk analysis to be combined with the system/product requirements specification).
Scope
This document applies to SilqQMS, which is used by SILQ as the electronic document management system (EDMS) to store, organize, retrieve, and lifecycle-manage Quality Management System documents and records. The requirements in this document cover two SilqQMS modules and their supporting infrastructure, as defined in SW.SLQ007 Software Validation Plan, SilqQMS:
Document Control Module: Formal numbered, revision-controlled QMS documents with a Draft → Released → Obsolete lifecycle
Admin Docs Libraries module: Eleven browsable document libraries for QMS subsystem files
Supporting Infrastructure: Authentication, role-based access control, audit trail, file storage, CSRF protection, and security headers
Documents
Reference Documents
SW.SLQ007		Software Validation Plan, SilqQMS
QM.SLQ032		Software Validation SOP
ISO 13485:2016	Medical Devices – Quality Management Systems – Requirements for Regulatory Purposes (clauses 4.1.6, 4.2.4, 4.2.5)
21 CFR Part 820	Quality Management System Regulation (QMSR, as revised)
21 CFR Part 11 	Electronic Records and Electronic Signatures
Associated Forms
N/A
Definitions
Abbreviations / Acronyms
EDMS: Electronic Document Management System
RBAC: Role Based Access Control
SRS: Software Requirements Specification
QMS: Quality Management System
General Definitions
SilqQMS:  A custom-developed, web-based electronic document management system (EDMS) used by SILQ to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records.
Document Control Module:	 The SilqQMS module that manages formal numbered, revision-controlled QMS documents through a Draft → Released → Obsolete lifecycle.
Admin Docs Libraries: The SilqQMS module that provides eleven browsable document libraries for organizing QMS subsystem files (e.g., NCRs, CAPAs, training records, management reviews).
Audit Trail: The append-only record of all significant actions performed in SilqQMS, including timestamp, actor, action type, entity reference, reason for change, and client IP address.
Harm: Physical injury and/or damage to health of people, damage to property, or damage to the environment.
Risk: The combined likelihood and severity of harm.
Risk Analysis: The systemic use of available information on a device or process to identify hazards and estimate risk.
Risk Assessment: The overall process of risk analysis and risk evaluation.
Risk Control:  An action taken to reduce the likelihood of a hazard or to reduce the effect from the hazard, or both.
Product Overview
SilqQMS is a custom-developed, web-based electronic document management system (EDMS) used to store, organize, retrieve, and lifecycle-manage documentation in SILQ's document control system as part of the Quality Management System. Documents are authored and approved outside of SilqQMS (per QM.SLQ001 Document Control SOP) and uploaded to SilqQMS for controlled storage, revision tracking, and retrieval. SilqQMS is used to retain all QMS documents and records within its validation scope (Document Control and Admin Docs Libraries modules). Access to the system is controlled by role-based permissions.
SilqQMS is currently used by SILQ's administrative personnel. Each user is granted secure access with unique identification (email address and password)
Assumptions and Dependencies
It is assumed that SilqQMS is deployed to the production environment (DigitalOcean App Platform) with the following infrastructure available and correctly configured
PostgreSQL database (DigitalOcean Managed Database) with automated backups enabled
S3-compatible object storage (DigitalOcean Spaces) for document file storage
HTTPS access via a valid TLS certificate
A modern web browser (Chrome, Firefox, Edge, or Safari — current or previous major version) on the user's workstation
Intended Use and Process Definition
The intended use of SilqQMS is to provide a secure means to store, organize, retrieve, and lifecycle-manage electronic QMS documentation and records as part of SILQ's document control process in accordance with ISO 13485:2016, the QMSR, and 21 CFR Part 11.
The following is the process definition for which SilqQMS is used:
Upload controlled documents to the Document Control module for formal revision tracking through a Draft → Released → Obsolete lifecycle.
Organize QMS subsystem files (NCRs, CAPAs, training records, management reviews, etc.) in the Admin Docs Libraries module.
Maintain all controlled documentation, including records, in electronic form on a secure, cloud-based server (DigitalOcean App Platform with PostgreSQL and S3-compatible storage)
Provide an append-only audit trail of all significant actions for compliance evidence
Risk Analysis
Risk Assessment

[Table]
|  | Risk assessment question | Yes / No |
| --- | --- | --- |
| 1.1 Product safety (harm) | Is there a potential risk to product safety if the software malfunctions? Patient harm Operator harm Bystander harm Environmental harm | No |
| 1.2 Product safety (harm) | Is there a potential risk to product safety if the user of the software makes a mistake? Patient harm Operator harm Bystander harm Environmental harm | No |
| 2.1 Product quality | Is there a potential risk to product quality (other than safety) if the software malfunctions? | No |
| 2.2 Product quality | Is there a potential risk to product quality (other than safety) if the user makes a mistake? | No |
| 3.1 Record integrity | Is there a potential risk to record integrity in a system that is a record repository? Record loss Record corruption | Yes |
| 4.1 Demonstration of compliance to an FDA regulation or ISO standard | Is there a potential risk regarding the ability to demonstrate regulatory compliance? Record loss Record corruption | Yes |


Analysis of process risk
Failure of the process, or SilqQMS, could result in the following:
Unauthorized access to controlled documents
Loss or corruption of QMS documentation and records
Loss/corruption of device history records
Loss of audit trail records
Inability to retrieve documents when needed
Unintended use of obsolete documents
Risk control measures in place to mitigate the identified risks include:
Role-based access control (RBAC) with permission checks on every route — prevents unauthorized access to system functions
Session-cookie authentication with bcrypt-hashed passwords — secures user access
60-minute inactivity session timeout with sliding window — limits exposure from idle sessions
Login rate limiting (5 attempts per 5 minutes per IP) — prevents brute-force attacks
CSRF protection on all state-changing requests — prevents cross-site request forgery
Security response headers (Content-Security-Policy, X-Content-Type-Options, X-Frame-Options, Referrer-Policy) — mitigates common web vulnerabilities
SHA-256 file hashing on Document Control uploads — enables integrity verification
No-delete design — documents, files, and audit events cannot be deleted through the application, preventing accidental or unauthorized data loss
Append-only audit trail with denormalized actor email — provides an immutable record of all actions
Obsolete document safeguards (red "OBSOLETE" badge in document list, warning banner on detail page, distinct audit events for access) — prevents unintended use of obsolete documents
Managed PostgreSQL database with automated nightly backups and point-in-time recovery (provided by DigitalOcean)
S3-compatible object storage with provider-managed redundancy for document files
A failure of the process would not result in direct or indirect harm to the patient. SilqQMS stores and manages QMS documents — it does not control manufacturing processes, medical devices, or clinical decisions. The risk controls in place would prevent loss of data in the unlikely event that multiple failures occur simultaneously. The risk category for use of SilqQMS is Minor.
Product Requirements
Note: The FileHold FRS requirements (SW.SLQ002) addressed features specific to the FileHold system that are not present in SilqQMS. Some previously used FRS capability areas have no direct SilqQMS equivalent, but are encompassed by the SRS requirements in the tables below

[Table]
| ID # | SilqQMS Requirement Specification (SRS) |
| --- | --- |
| 1 | Document Control Operations |
| SRS-1.1 | SilqQMS shall allow authorized users to create a new document by providing a document number, title, and document type. All three fields are required. The document number shall be unique across all documents in the system. Upon creation, the document shall have status "Draft" and an initial revision of "A". |
| SRS-1.2 | SilqQMS shall allow authorized users to upload exactly one file to an unreleased draft revision. The upload shall be rejected if: (a) the document is not in Draft status, (b) the revision has already been released, or (c) the revision already has a file attached. |
| SRS-1.3 | SilqQMS shall allow authorized users to release a draft revision. Release requires: (a) a reason for change (mandatory), and (b) at least one uploaded file on the revision. Upon release, the document status shall change from "Draft" to "Released", and the release timestamp and releasing user shall be recorded. Optional fields: change summary and effective date. |
| SRS-1.4 | SilqQMS shall allow authorized users to create a new draft revision from a Released document. The new revision letter shall follow sequential alphabetical order (A → B → C → ... → Z → AA). The document status shall change from "Released" to "Draft". Creating a new revision from a Draft or Obsolete document shall be rejected. |
| SRS-1.5 | SilqQMS shall allow authorized users to obsolete a document. Obsoleting requires a reason for change (mandatory). Upon obsoleting, the document status shall change to "Obsolete" and an audit event shall be recorded with the reason. |
| SRS-1.6 | SilqQMS shall allow authorized users to download files from any document, including obsolete documents. The file shall be served as an attachment with the original filename. Downloads shall not be blocked based on document status. |
| SRS-1.7 | SilqQMS shall allow authorized users to view files inline. For PDF and image files, the system shall serve the file for native browser rendering. For .docx, .xlsx, .xls, and .csv files, the system shall perform server-side rendering to HTML |
| SRS-1.8 | SilqQMS shall enforce the following document lifecycle state transitions: Draft → Released (via release); Released → Draft (via new revision); any status → Obsolete (via obsolete). No other transitions shall be permitted. |
| SRS-1.9 | Upon file upload to a Document Control revision, the system shall compute a SHA-256 cryptographic hash of the file contents and store it in the file record. The file size in bytes, filename, and content type shall also be stored. |
| SRS-1.10 | Document numbers shall be unique. The system shall reject creation of a document with a document number that already exists. |
| SRS-1.11 | Revision letters shall follow sequential alphabetical order and shall be unique per document. The system shall automatically assign the next revision letter when creating a new revision. |


[Table]
| ID # | SilqQMS Requirement Specification (SRS) |
| --- | --- |
| 2 | Obsolete Document Safeguards |
| SRS-2.1 | Documents with status "Obsolete" shall display a red "OBSOLETE" badge in the document list view, visually distinguishing them from Draft and Released documents. |
| SRS-2.2 | The detail page for an obsolete document shall display a prominent warning banner with the text: "This document is obsolete. It is retained for historical reference only. Do not use this document for current operations." If the reason for obsoleting is available, it shall be displayed. |
| SRS-2.3 | Downloading a file from an obsolete document shall record an audit event with the action `doc.download_obsolete` (distinct from the standard `doc.download` action). |
| SRS-2.4 | Viewing a file from an obsolete document shall record an audit event with the action `doc.view_obsolete` (distinct from the standard `doc.view` action). |
| SRS-2.5 | The "Create next revision" and "Obsolete document" action forms shall not be displayed on the detail page when the document status is "Obsolete". |


[Table]
| ID # | SilqQMS Requirement Specification (SRS) |
| --- | --- |
| 3 | Admin Docs Libraries |
| SRS-3.1 | SilqQMS shall provide eleven document libraries with the following names: (1) Quality Management Documents, (2) Employee Training, (3) Management Reviews, Audits & Approvals, (4) NCRs, (5) CAPAs, (6) Post Market Surveillance, (7) Regulatory Standards & Approvals, (8) Work Orders, (9) Risk Management, (10) Design History Files (DHFs), (11) Forms, Templates & Travelers. |
| SRS-3.2 | Each library shall support a hierarchical folder structure. Users shall be able to create folders within a library root or within existing folders |
| SRS-3.3 | SilqQMS shall allow authorized users to create folders within a library. Folder creation requires a name. A folder shall be associated with its library and optionally with a parent folder. |
| SRS-3.4 | SilqQMS shall allow authorized users to upload one or more files to a library or folder. Individual files shall be limited to 50 MB each. The overall request size shall be limited to 100 MB. |
| SRS-3.5 | SilqQMS shall allow authorized users to download files from any library. The file shall be served as an attachment with the original filename. |
| SRS-3.6 | SilqQMS shall allow authorized users to view files inline from libraries. For .docx, .xlsx, .xls, and .csv files, the system shall perform server-side rendering to HTML. For PDF and image files, the system shall serve the file for native browser rendering. |
| SRS-3.7 | SilqQMS shall allow authorized users to move a file from one library and/or folder to another. The move operation shall update the file's library and folder assignment. |
| SRS-3.8 | When navigating within a library's folder hierarchy, the system shall display breadcrumb navigation showing the path from the library root to the current folder. Each breadcrumb element shall be a clickable link. |


[Table]
| ID # | SilqQMS Requirement Specification (SRS) |
| --- | --- |
| 4 | Authentication and Session Management |
| SRS-4.1 | User authentication shall require a unique email address and password to access SilqQMS. Unauthenticated users attempting to access protected pages shall be redirected to the login page. |
| SRS-4.2 | User passwords shall be stored as hashed values (not plaintext) using a secure hashing algorithm. |
| SRS-4.3 | Users shall be logged off of their session after 60 minutes of inactivity. The timeout shall use a sliding window — active sessions are refreshed on each request, so only truly idle sessions expire. |
| SRS-4.4 | After 5 unsuccessful login attempts from the same IP address within 5 minutes, further login attempts from that IP shall be blocked with the message "Too many login attempts. Please wait 5 minutes. |
| SRS-4.5 | Login, logout, and failed login events shall be recorded in the audit trail. Failed login events shall record the attempted email address |


[Table]
| ID # | SilqQMS Requirement Specification (SRS) |
| --- | --- |
| 5 | Access Control |
| SRS-5.1 | Access to system functions shall be controlled by role-based permissions. Users are assigned to roles, and roles carry specific permissions. |
| SRS-5.2 | Each protected route shall require a specific permission. Unauthenticated users shall be redirected to the login page. Authenticated users without the required permission shall receive a 403 Forbidden response. |
| SRS-5.3 | Permission denials shall be logged, including the user email, the missing permission, and the requested path. |


[Table]
| ID # | SilqQMS Requirement Specification (SRS) |
| --- | --- |
| 6 | Audit Trail |
| SRS-6.1 | All significant user actions shall be recorded in an append-only audit trail. Recorded actions shall include: document creation, file upload, revision release, document revision, document obsoleting, file download, file view, login, logout, failed login, folder creation, Admin Docs file upload, and audit export. |
| SRS-6.2 | Each audit record shall include: timestamp (UTC), actor email, action type, entity type and ID, reason for change (where applicable), metadata (JSON), client IP address, and per-request ID. |
| SRS-6.3 | The audit trail shall be queryable through a web interface with filters for: action type (contains match), actor email (contains match), and date range (from/to). |
| SRS-6.4 | The audit trail shall be exportable as a CSV file containing all matching events (no row limit). The CSV shall include columns: id, created_at, action, actor_user_email, entity_type, entity_id, reason, metadata_json, client_ip, request_id. |
| SRS-6.5 | The audit trail export action shall itself be recorded in the audit trail with the action `audit.export`, including the filters used and the count of exported events. |
| SRS-6.6 | Audit records shall not be modifiable or deletable through any application interface. |


[Table]
| ID # | SilqQMS Requirement Specification (SRS) |
| --- | --- |
| 7 | Security |
| SRS-7.1 | CSRF protection shall be applied to all state-changing requests (POST, PUT, PATCH, DELETE). The login endpoint shall be exempt. Requests with missing or invalid CSRF tokens shall be rejected. |
| SRS-7.2 | The following security headers shall be set on every HTTP response: Content-Security-Policy, X-Content-Type-Options (nosniff), X-Frame-Options (DENY), Referrer-Policy (strict-origin-when-cross-origin). |


[Table]
| ID # | SilqQMS Requirement Specification (SRS) |
| --- | --- |
| 8 | Data Integrity |
| SRS-8.1 | No delete functionality shall exist for documents, document revisions, or document files in the Document Control module. |
| SRS-8.2 | No delete functionality shall exist for uploaded files in the Admin Docs Libraries module. |
| SRS-8.3 | Obsolete documents shall be retained in the system and remain accessible. They shall not be hidden, filtered out, or removed from the document list. |
