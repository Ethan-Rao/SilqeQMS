# Editing Guide: SW.SLQ012 A Requirements Traceability Matrix, SilqQMS

Document: SW.SLQ012 A Requirements Traceability Matrix, SilqQMS  
Project: DC.SLQ002 — SilqQMS EDMS Transition  
Structural model: SW.SLQ006 A Requirements Traceability Matrix, FileHold  
Output location: QMSInProcess/DC.SLQ002/  
Readable-text references:  
docs/QMS-Readable-Texts/12-DHF-Software/SW.SLQ008 A Product Requirements Specification, SilqQMS.md  
docs/QMS-Readable-Texts/12-DHF-Software/SW.SLQ009 A Software Verification Test Plan, SIlqQMS.md  
docs/QMS-Readable-Texts/12-DHF-Software/SW.SLQ010 A Software Verification Test Procedure, SilqQMS.md  

Frozen configuration item for design output (Git commit only; no release tag in this matrix):

79aaa9ade016e0e19b6983d1e05a04518243126c  

Short form for informal reference only: 79aaa9a  

Repository: https://github.com/Ethan-Rao/SilqeQMS  
Branch: main  

If main advances after SW.SLQ012 is approved, update Column D only when your QM procedure requires alignment with a new validated build; do not change historical rows retroactively without a document revision.

---

## How to use this guide

SW.SLQ012 is the design-input to design-output to verification map for SilqQMS. It must include every software requirement SRS-1.1 through SRS-8.3 from SW.SLQ008 A. The I/O matrix body has 43 rows (not 33): SRS-1.1 through SRS-1.11 (11), SRS-2.1 through SRS-2.5 (5), SRS-3.1 through SRS-3.8 (8), SRS-4.1 through SRS-4.5 (5), SRS-5.1 through SRS-5.3 (3), SRS-6.1 through SRS-6.6 (6), SRS-7.1 through SRS-7.2 (2), SRS-8.1 through SRS-8.3 (3). Use SW.SLQ006 A (FileHold) as the table layout model: front matter sections (Purpose, Scope, Reference Documents, Definitions), then one I/O Matrix table.

SW.SLQ011 A points readers here for traceability; do not duplicate the full matrix inside SW.SLQ011.

Assume SW.SLQ010 A was executed and closed with all eleven test cases passing unless you record a deviation.

Section order (match SW.SLQ006):

1. Title block / cover page  
2. Purpose  
3. Scope  
4. Reference Documents  
5. Definitions  
6. Input / Output Matrix (single Word table)  
7. Revision / approval blocks per QM.SLQ001  

Do not attach SW.SLQ010 or SW.SLQ011 inside SW.SLQ012; cross-reference them in Column E.

---

## Title block / cover page

Title: Requirements Traceability Matrix, SilqQMS  
Document ID: SW.SLQ012  
Revision: A  
Project: DC.SLQ002 — SilqQMS EDMS Transition  

Author, reviewer, and approver signature blocks per QM.SLQ001 A.

---

## Purpose (paste into Word)

The purpose of this document is to provide a link between verifiable product requirements (design inputs), the implemented software (design output), and the verification methods used to demonstrate that each design input is satisfied.

---

## Scope (paste into Word)

The scope of this document incorporates all product requirements (design inputs), design output, and verification testing related to the validation of the electronic document management system SilqQMS under DC.SLQ002 and SW.SLQ007 A.

---

## Reference Documents (paste as a list)

SW.SLQ007 A   Software Validation Plan, SilqQMS  
SW.SLQ008 A   Product Requirements Specification, SilqQMS  
SW.SLQ009 A   Software Verification Test Plan, SilqQMS  
SW.SLQ010 A   Software Verification Test Procedure, SilqQMS (executed)  
SW.SLQ011 A   Software Validation Report, SilqQMS  
QM.SLQ032 A   Software Validation SOP  
QM.SLQ001 A   Document Control SOP  

If SW.SLQ011 is not yet approved when SW.SLQ012 is signed, write in Column E for affected rows: Test report: SW.SLQ011 A (pending approval).

---

## Definitions (paste into Word)

Abbreviations / Acronyms

I/O: Input/Output  
SRS: Requirement identifier in SW.SLQ008  
DHF: Design History File  

General definitions

SilqQMS: Custom web application used as SILQ’s electronic document management system for controlled QMS documents and records (Document Control module, Admin Docs Libraries, authentication, roles, audit trail, storage).  

Verification: Confirmation, by examination and objective evidence, that specified requirements have been fulfilled by the product design.  

Validation (context): Overall conclusion documented in SW.SLQ011; this matrix supports validation by tracing each SRS to executed verification.  

Design output (for this matrix): SilqQMS application software identified by Git commit on branch main (Column D).

---

## Input / Output Matrix — column headers

Use exactly these headers left to right:

Item | Attribute / Characteristic | Verifiable Product Requirement (Design Input) | Design Output | Verification / Validation | Test Method  

---

## Column D — same text for every row (paste unchanged)

SilqQMS application software at Git commit 79aaa9ade016e0e19b6983d1e05a04518243126c on branch main; repository https://github.com/Ethan-Rao/SilqeQMS.

---

## Column F — same text for every row (paste unchanged)

Software test  

---

## Row-by-row paste instructions (Columns A through E)

For each block below, copy the labeled line into the matching column of one Word table row. Column D and Column F use the shared text above unless your template duplicates them per row.

---

### Row 1 — SRS-1.1

Column A (Item):  
1  

Column B (Attribute / Characteristic):  
Document Control — Lifecycle and files  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-1.1: SilqQMS shall allow authorized users to create a new document by providing a document number, title, and document type. All three fields are required. The document number shall be unique across all documents in the system. Upon creation, the document shall have status "Draft" and an initial revision of "A".  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 1 — Document Creation and Lifecycle. Evidence: executed procedure Steps 1-1 through 1-4 (required fields and successful creation). Test report: SW.SLQ011 A. Supplementary automated evidence (optional): pytest tests/test_document_control.py::test_document_control_vertical_slice_creates_releases_downloads_and_audits (see SW.SLQ009 Additional Info).  

---

### Row 2 — SRS-1.2

Column A (Item):  
2  

Column B (Attribute / Characteristic):  
Document Control — Lifecycle and files  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-1.2: SilqQMS shall allow authorized users to upload exactly one file to an unreleased draft revision. The upload shall be rejected if: (a) the document is not in Draft status, (b) the revision has already been released, or (c) the revision already has a file attached.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 1 — Document Creation and Lifecycle. Evidence: executed procedure Steps 1-6 and 1-7 (upload success and rejection of second file). Test report: SW.SLQ011 A. Supplementary automated evidence (optional): pytest tests/test_document_control.py::test_document_control_vertical_slice_creates_releases_downloads_and_audits.  

---

### Row 3 — SRS-1.3

Column A (Item):  
3  

Column B (Attribute / Characteristic):  
Document Control — Lifecycle and files  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-1.3: SilqQMS shall allow authorized users to release a draft revision. Release requires: (a) a reason for change (mandatory), and (b) at least one uploaded file on the revision. Upon release, the document status shall change from "Draft" to "Released", and the release timestamp and releasing user shall be recorded. Optional fields: change summary and effective date.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 1 — Document Creation and Lifecycle. Evidence: executed procedure Steps 1-8 through 1-9 (reason required; successful release), Step 1-12 (release rejected without file). Test report: SW.SLQ011 A. Supplementary automated evidence (optional): pytest tests/test_document_control.py::test_document_control_vertical_slice_creates_releases_downloads_and_audits.  

---

### Row 4 — SRS-1.4

Column A (Item):  
4  

Column B (Attribute / Characteristic):  
Document Control — Lifecycle and files  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-1.4: SilqQMS shall allow authorized users to create a new draft revision from a Released document. The new revision letter shall follow sequential alphabetical order (A → B → C → ... → Z → AA). The document status shall change from "Released" to "Draft". Creating a new revision from a Draft or Obsolete document shall be rejected.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 1 — Document Creation and Lifecycle. Evidence: executed procedure Steps 1-10 and 1-11 (new revision from Released; rejection from Draft). Test report: SW.SLQ011 A.  

---

### Row 5 — SRS-1.5

Column A (Item):  
5  

Column B (Attribute / Characteristic):  
Document Control — Lifecycle and files  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-1.5: SilqQMS shall allow authorized users to obsolete a document. Obsoleting requires a reason for change (mandatory). Upon obsoleting, the document status shall change to "Obsolete" and an audit event shall be recorded with the reason.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 2 — Document Obsoleting. Evidence: executed procedure Steps 2-1 through 2-3. Test report: SW.SLQ011 A.  

---

### Row 6 — SRS-1.6

Column A (Item):  
6  

Column B (Attribute / Characteristic):  
Document Control — Lifecycle and files  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-1.6: SilqQMS shall allow authorized users to download files from any document, including obsolete documents. The file shall be served as an attachment with the original filename. Downloads shall not be blocked based on document status.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 3 — Document Download and View. Evidence: executed procedure Steps 3-1, 3-3, 3-8, 3-9 (downloads across statuses and filename check). Test report: SW.SLQ011 A.  

---

### Row 7 — SRS-1.7

Column A (Item):  
7  

Column B (Attribute / Characteristic):  
Document Control — Lifecycle and files  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-1.7: SilqQMS shall allow authorized users to view files inline. For PDF and image files, the system shall serve the file for native browser rendering. For .docx, .xlsx, .xls, and .csv files, the system shall perform server-side rendering to HTML  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 3 — Document Download and View. Evidence: executed procedure Steps 3-2 through 3-7, 3-8 (inline view by file type). Test report: SW.SLQ011 A.  

---

### Row 8 — SRS-1.8

Column A (Item):  
8  

Column B (Attribute / Characteristic):  
Document Control — Lifecycle and files  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-1.8: SilqQMS shall enforce the following document lifecycle state transitions: Draft → Released (via release); Released → Draft (via new revision); any status → Obsolete (via obsolete). No other transitions shall be permitted.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 1 — Document Creation and Lifecycle. Evidence: executed procedure Steps 1-9 through 1-11 and 1-13 (Released to Draft; lifecycle enforcement). Test report: SW.SLQ011 A.  

---

### Row 9 — SRS-1.9

Column A (Item):  
9  

Column B (Attribute / Characteristic):  
Document Control — Lifecycle and files  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-1.9: Upon file upload to a Document Control revision, the system shall compute a SHA-256 cryptographic hash of the file contents and store it in the file record. The file size in bytes, filename, and content type shall also be stored.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 4 — File Integrity (SHA-256 and File Size). Evidence: executed procedure Steps 4-1 through 4-4 (and optional 4-5 if performed). Test report: SW.SLQ011 A.  

---

### Row 10 — SRS-1.10

Column A (Item):  
10  

Column B (Attribute / Characteristic):  
Document Control — Lifecycle and files  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-1.10: Document numbers shall be unique. The system shall reject creation of a document with a document number that already exists.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 1 — Document Creation and Lifecycle. Evidence: executed procedure Step 1-5 (duplicate document number rejected). Test report: SW.SLQ011 A. Supplementary automated evidence (optional): pytest tests/test_document_control.py::test_document_control_vertical_slice_creates_releases_downloads_and_audits.  

---

### Row 11 — SRS-1.11

Column A (Item):  
11  

Column B (Attribute / Characteristic):  
Document Control — Lifecycle and files  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-1.11: Revision letters shall follow sequential alphabetical order and shall be unique per document. The system shall automatically assign the next revision letter when creating a new revision.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 1 — Document Creation and Lifecycle. Evidence: executed procedure Steps 1-10 and 1-13 (revision letters A to B to C per document). Test report: SW.SLQ011 A.  

---

### Row 12 — SRS-2.1

Column A (Item):  
12  

Column B (Attribute / Characteristic):  
Document Control — Obsolete safeguards  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-2.1: Documents with status "Obsolete" shall display a red "OBSOLETE" badge in the document list view, visually distinguishing them from Draft and Released documents.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 5 — Obsolete Document Safeguards. Evidence: executed procedure Step 5-1. Test report: SW.SLQ011 A.  

---

### Row 13 — SRS-2.2

Column A (Item):  
13  

Column B (Attribute / Characteristic):  
Document Control — Obsolete safeguards  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-2.2: The detail page for an obsolete document shall display a prominent warning banner with the text: "This document is obsolete. It is retained for historical reference only. Do not use this document for current operations." If the reason for obsoleting is available, it shall be displayed.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 5 — Obsolete Document Safeguards. Evidence: executed procedure Step 5-2. Test report: SW.SLQ011 A.  

---

### Row 14 — SRS-2.3

Column A (Item):  
14  

Column B (Attribute / Characteristic):  
Document Control — Obsolete safeguards  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-2.3: Downloading a file from an obsolete document shall record an audit event with the action `doc.download_obsolete` (distinct from the standard `doc.download` action).  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 5 — Obsolete Document Safeguards. Evidence: executed procedure Step 5-4. Test report: SW.SLQ011 A. Supplementary automated evidence (optional): pytest tests/test_edms_improvements.py::test_obsolete_document_download_creates_distinct_audit_event.  

---

### Row 15 — SRS-2.4

Column A (Item):  
15  

Column B (Attribute / Characteristic):  
Document Control — Obsolete safeguards  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-2.4: Viewing a file from an obsolete document shall record an audit event with the action `doc.view_obsolete` (distinct from the standard `doc.view` action).  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 5 — Obsolete Document Safeguards. Evidence: executed procedure Step 5-5. Test report: SW.SLQ011 A. Supplementary automated evidence (optional): pytest tests/test_edms_improvements.py::test_obsolete_document_view_creates_distinct_audit_event.  

---

### Row 16 — SRS-2.5

Column A (Item):  
16  

Column B (Attribute / Characteristic):  
Document Control — Obsolete safeguards  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-2.5: The "Create next revision" and "Obsolete document" action forms shall not be displayed on the detail page when the document status is "Obsolete".  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 5 — Obsolete Document Safeguards. Evidence: executed procedure Step 5-3. Test report: SW.SLQ011 A.  

---

### Row 17 — SRS-3.1

Column A (Item):  
17  

Column B (Attribute / Characteristic):  
Admin Docs Libraries  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-3.1: SilqQMS shall provide eleven document libraries with the following names: (1) Quality Management Documents, (2) Employee Training, (3) Management Reviews, Audits & Approvals, (4) NCRs, (5) CAPAs, (6) Post Market Surveillance, (7) Regulatory Standards & Approvals, (8) Work Orders, (9) Risk Management, (10) Design History Files (DHFs), (11) Forms, Templates & Travelers.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 6 — Admin Docs Library Operations. Evidence: executed procedure Step 6-1 (eleven library titles and URLs). Test report: SW.SLQ011 A.  

---

### Row 18 — SRS-3.2

Column A (Item):  
18  

Column B (Attribute / Characteristic):  
Admin Docs Libraries  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-3.2: Each library shall support a hierarchical folder structure. Users shall be able to create folders within a library root or within existing folders  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 6 — Admin Docs Library Operations. Evidence: executed procedure Steps 6-2 and 6-3 (nested folders). Test report: SW.SLQ011 A.  

---

### Row 19 — SRS-3.3

Column A (Item):  
19  

Column B (Attribute / Characteristic):  
Admin Docs Libraries  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-3.3: SilqQMS shall allow authorized users to create folders within a library. Folder creation requires a name. A folder shall be associated with its library and optionally with a parent folder.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 6 — Admin Docs Library Operations. Evidence: executed procedure Steps 6-2 and 6-3 (folder creation with name). Test report: SW.SLQ011 A.  

---

### Row 20 — SRS-3.4

Column A (Item):  
20  

Column B (Attribute / Characteristic):  
Admin Docs Libraries  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-3.4: SilqQMS shall allow authorized users to upload one or more files to a library or folder. Individual files shall be limited to 50 MB each. The overall request size shall be limited to 100 MB.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 6 — Admin Docs Library Operations. Evidence: executed procedure Steps 6-5 through 6-7 (single upload, multi upload, over-size rejection). Test report: SW.SLQ011 A.  

---

### Row 21 — SRS-3.5

Column A (Item):  
21  

Column B (Attribute / Characteristic):  
Admin Docs Libraries  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-3.5: SilqQMS shall allow authorized users to download files from any library. The file shall be served as an attachment with the original filename.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 6 — Admin Docs Library Operations. Evidence: executed procedure Step 6-8. Test report: SW.SLQ011 A.  

---

### Row 22 — SRS-3.6

Column A (Item):  
22  

Column B (Attribute / Characteristic):  
Admin Docs Libraries  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-3.6: SilqQMS shall allow authorized users to view files inline from libraries. For .docx, .xlsx, .xls, and .csv files, the system shall perform server-side rendering to HTML. For PDF and image files, the system shall serve the file for native browser rendering.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 6 — Admin Docs Library Operations. Evidence: executed procedure Steps 6-9 through 6-12. Test report: SW.SLQ011 A.  

---

### Row 23 — SRS-3.7

Column A (Item):  
23  

Column B (Attribute / Characteristic):  
Admin Docs Libraries  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-3.7: SilqQMS shall allow authorized users to move a file from one library and/or folder to another. The move operation shall update the file's library and folder assignment.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 6 — Admin Docs Library Operations. Evidence: executed procedure Steps 6-13 and 6-14 (Move modal and library/folder update). Test report: SW.SLQ011 A.  

---

### Row 24 — SRS-3.8

Column A (Item):  
24  

Column B (Attribute / Characteristic):  
Admin Docs Libraries  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-3.8: When navigating within a library's folder hierarchy, the system shall display breadcrumb navigation showing the path from the library root to the current folder. Each breadcrumb element shall be a clickable link.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 6 — Admin Docs Library Operations. Evidence: executed procedure Steps 6-3 and 6-4 (breadcrumb path and clickable crumbs). Test report: SW.SLQ011 A.  

---

### Row 25 — SRS-4.1

Column A (Item):  
25  

Column B (Attribute / Characteristic):  
Authentication and session security  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-4.1: User authentication shall require a unique email address and password to access SilqQMS. Unauthenticated users attempting to access protected pages shall be redirected to the login page.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 7 — Authentication and Session Security. Evidence: executed procedure Steps 7-1 and 7-2 (redirect and successful login). Test report: SW.SLQ011 A.  

---

### Row 26 — SRS-4.2

Column A (Item):  
26  

Column B (Attribute / Characteristic):  
Authentication and session security  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-4.2: User passwords shall be stored as hashed values (not plaintext) using a secure hashing algorithm.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 7 — Authentication and Session Security. Evidence: executed procedure Step 7-8 (database inspection of password_hash). Test report: SW.SLQ011 A.  

---

### Row 27 — SRS-4.3

Column A (Item):  
27  

Column B (Attribute / Characteristic):  
Authentication and session security  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-4.3: Users shall be logged off of their session after 60 minutes of inactivity. The timeout shall use a sliding window — active sessions are refreshed on each request, so only truly idle sessions expire.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 7 — Authentication and Session Security. Evidence: executed procedure Steps 7-9 and 7-10 (idle timeout and sliding window). Test report: SW.SLQ011 A. Supplementary automated evidence (optional): pytest tests/test_edms_improvements.py::test_session_timeout_is_60_minutes.  

---

### Row 28 — SRS-4.4

Column A (Item):  
28  

Column B (Attribute / Characteristic):  
Authentication and session security  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-4.4: After 5 unsuccessful login attempts from the same IP address within 5 minutes, further login attempts from that IP shall be blocked with the message "Too many login attempts. Please wait 5 minutes.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 7 — Authentication and Session Security. Evidence: executed procedure Steps 7-5 and 7-6 (rate limit). Test report: SW.SLQ011 A.  

---

### Row 29 — SRS-4.5

Column A (Item):  
29  

Column B (Attribute / Characteristic):  
Authentication and session security  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-4.5: Login, logout, and failed login events shall be recorded in the audit trail. Failed login events shall record the attempted email address  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 7 — Authentication and Session Security. Evidence: executed procedure Steps 7-3 and 7-7 (logout and audit filters for auth events). Test report: SW.SLQ011 A.  

---

### Row 30 — SRS-5.1

Column A (Item):  
30  

Column B (Attribute / Characteristic):  
Access control (RBAC)  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-5.1: Access to system functions shall be controlled by role-based permissions. Users are assigned to roles, and roles carry specific permissions.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 8 — Access Control. Evidence: executed procedure Step 8-6 (qa_tester permitted). Test report: SW.SLQ011 A.  

---

### Row 31 — SRS-5.2

Column A (Item):  
31  

Column B (Attribute / Characteristic):  
Access control (RBAC)  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-5.2: Each protected route shall require a specific permission. Unauthenticated users shall be redirected to the login page. Authenticated users without the required permission shall receive a 403 Forbidden response.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 8 — Access Control. Evidence: executed procedure Steps 8-1 through 8-4 (redirect and 403). Test report: SW.SLQ011 A.  

---

### Row 32 — SRS-5.3

Column A (Item):  
32  

Column B (Attribute / Characteristic):  
Access control (RBAC)  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-5.3: Permission denials shall be logged, including the user email, the missing permission, and the requested path.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 8 — Access Control. Evidence: executed procedure Step 8-5 (RBAC log lines). Test report: SW.SLQ011 A.  

---

### Row 33 — SRS-6.1

Column A (Item):  
33  

Column B (Attribute / Characteristic):  
Audit trail  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-6.1: All significant user actions shall be recorded in an append-only audit trail. Recorded actions shall include: document creation, file upload, revision release, document revision, document obsoleting, file download, file view, login, logout, failed login, folder creation, Admin Docs file upload, and audit export.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 9 — Audit Trail. Evidence: executed procedure Step 9-2 (representative action types present). Test report: SW.SLQ011 A.  

---

### Row 34 — SRS-6.2

Column A (Item):  
34  

Column B (Attribute / Characteristic):  
Audit trail  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-6.2: Each audit record shall include: timestamp (UTC), actor email, action type, entity type and ID, reason for change (where applicable), metadata (JSON), client IP address, and per-request ID.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 9 — Audit Trail. Evidence: executed procedure Step 9-3 (field checklist). Test report: SW.SLQ011 A.  

---

### Row 35 — SRS-6.3

Column A (Item):  
35  

Column B (Attribute / Characteristic):  
Audit trail  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-6.3: The audit trail shall be queryable through a web interface with filters for: action type (contains match), actor email (contains match), and date range (from/to).  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 9 — Audit Trail. Evidence: executed procedure Steps 9-4 through 9-6 (filters). Test report: SW.SLQ011 A. Supplementary automated evidence (optional): pytest tests/test_edms_improvements.py::test_audit_trail_csv_export_with_date_filter.  

---

### Row 36 — SRS-6.4

Column A (Item):  
36  

Column B (Attribute / Characteristic):  
Audit trail  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-6.4: The audit trail shall be exportable as a CSV file containing all matching events (no row limit). The CSV shall include columns: id, created_at, action, actor_user_email, entity_type, entity_id, reason, metadata_json, client_ip, request_id.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 9 — Audit Trail. Evidence: executed procedure Steps 9-7 through 9-9 (CSV headers and row completeness). Test report: SW.SLQ011 A. Supplementary automated evidence (optional): pytest tests/test_edms_improvements.py::test_audit_trail_csv_export.  

---

### Row 37 — SRS-6.5

Column A (Item):  
37  

Column B (Attribute / Characteristic):  
Audit trail  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-6.5: The audit trail export action shall itself be recorded in the audit trail with the action `audit.export`, including the filters used and the count of exported events.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 9 — Audit Trail. Evidence: executed procedure Step 9-10. Test report: SW.SLQ011 A. Supplementary automated evidence (optional): pytest tests/test_edms_improvements.py::test_audit_trail_csv_export.  

---

### Row 38 — SRS-6.6

Column A (Item):  
38  

Column B (Attribute / Characteristic):  
Audit trail  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-6.6: Audit records shall not be modifiable or deletable through any application interface.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 9 — Audit Trail. Evidence: executed procedure Step 9-11 (no edit/delete controls). Test report: SW.SLQ011 A.  

---

### Row 39 — SRS-7.1

Column A (Item):  
39  

Column B (Attribute / Characteristic):  
Security controls (CSRF and HTTP headers)  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-7.1: CSRF protection shall be applied to all state-changing requests (POST, PUT, PATCH, DELETE). The login endpoint shall be exempt. Requests with missing or invalid CSRF tokens shall be rejected.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 10 — Security Controls. Evidence: executed procedure Steps 10-1 through 10-4 (CSRF token present; rejection without token; login exempt). Test report: SW.SLQ011 A.  

---

### Row 40 — SRS-7.2

Column A (Item):  
40  

Column B (Attribute / Characteristic):  
Security controls (CSRF and HTTP headers)  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-7.2: The following security headers shall be set on every HTTP response: Content-Security-Policy, X-Content-Type-Options (nosniff), X-Frame-Options (DENY), Referrer-Policy (strict-origin-when-cross-origin).  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 10 — Security Controls. Evidence: executed procedure Steps 10-5 and 10-6 (response headers on admin and login). Test report: SW.SLQ011 A.  

---

### Row 41 — SRS-8.1

Column A (Item):  
41  

Column B (Attribute / Characteristic):  
Data integrity — no delete; obsolete retention  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-8.1: No delete functionality shall exist for documents, document revisions, or document files in the Document Control module.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 11 — Data Integrity (No-Delete Verification). Evidence: executed procedure Steps 11-1 and 11-2 (Document Control UI inspection). Test report: SW.SLQ011 A.  

---

### Row 42 — SRS-8.2

Column A (Item):  
42  

Column B (Attribute / Characteristic):  
Data integrity — no delete; obsolete retention  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-8.2: No delete functionality shall exist for uploaded files in the Admin Docs Libraries module.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 11 — Data Integrity (No-Delete Verification). Evidence: executed procedure Step 11-3 (Admin Docs libraries inspection). Test report: SW.SLQ011 A.  

---

### Row 43 — SRS-8.3

Column A (Item):  
43  

Column B (Attribute / Characteristic):  
Data integrity — no delete; obsolete retention  

Column C (Verifiable Product Requirement — paste verbatim):  
SRS-8.3: Obsolete documents shall be retained in the system and remain accessible. They shall not be hidden, filtered out, or removed from the document list.  

Column E (Verification / Validation — paste verbatim):  
Test procedure: SW.SLQ010 A, Test Case 11 — Data Integrity (No-Delete Verification). Evidence: executed procedure Steps 11-4 and 11-5 (obsolete documents visible and accessible). Test report: SW.SLQ011 A.  

---

## Consistency checks before approval

1. Count: exactly 43 populated rows in the matrix body (SRS-1.1 through SRS-8.3).  
2. Column C text matches SW.SLQ008 Rev A for each SRS (controlled Word or readable-text export).  
3. Column D uses commit 79aaa9ade016e0e19b6983d1e05a04518243126c on every row unless your procedure updates the validated build.  
4. Column E references executed SW.SLQ010 A (not a blank template).  
5. Column F reads Software test on every row.  
6. When both are approved, SW.SLQ011 Reference Documents lists SW.SLQ012.

---

## Drafting reminders

Prefer one Word table for the whole matrix; repeat column headers if the table splits across pages.

Do not paste application source code into SW.SLQ012.

After SW.SLQ012 Rev A is approved and the docx is filed under QMSInProcess/DC.SLQ002/, add the filename to FILE_MAP in scripts/refresh_dc_slq002_readable_texts.py when your team enables extraction for SW.SLQ012.

Release per QM.SLQ001 A.

---

## QM.SLQ032 A alignment

SW.SLQ012 demonstrates traceability from design inputs (SW.SLQ008) through design output (SilqQMS at the stated Git commit) to verification (SW.SLQ010) and validation summary (SW.SLQ011).
