"""
Maintainable QMS classification map (Prompt 7 / E2).

Single committed source that maps a controlled document to its ISO 13485:2016
clause and QMS subsystem, so the "QMS Document Index" page can present the
controlled set as a navigable map instead of only the flat category grouping.

The mapping is keyed by the SILQ *SLQ family number* extracted from a document
number (e.g. ``QM.SLQ016``, ``FM1-QM.SLQ016``, ``TMP1-QM.SLQ016`` all resolve to
family 16), because forms/templates/travelers inherit the subsystem of their
parent SOP. Anything not covered here resolves to the visible "Unclassified"
bucket so gaps are obvious rather than hidden.

To extend/correct the map, edit ``_BY_SLQ_FAMILY`` below (and, if needed, the
per-document overrides in ``_BY_DOC_NUMBER``). No template or route changes are
required.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

UNCLASSIFIED = "Unclassified"


@dataclass(frozen=True)
class QmsClassification:
    iso_clause: str
    subsystem: str


# ISO 13485:2016 clause + QMS subsystem per SILQ SLQ document family.
# Starting mapping for the current controlled set (QM.SLQ001–052 and their
# FM/TMP derivatives). Partial is fine — unmapped docs surface as Unclassified.
_BY_SLQ_FAMILY: dict[int, QmsClassification] = {
    1:  QmsClassification("4.2.4 Control of Documents", "Document Control"),
    2:  QmsClassification("4.2.1 Documentation (Good Documentation Practices)", "Document Control"),
    3:  QmsClassification("6.2 Human Resources (Competence & Training)", "Training"),
    4:  QmsClassification("7.3 Design and Development", "Design Control"),
    5:  QmsClassification("7.3.2 Design and Development Planning", "Design Control"),
    6:  QmsClassification("7.3.3 Design and Development Inputs", "Design Control"),
    7:  QmsClassification("7.3.4 Design and Development Outputs", "Design Control"),
    8:  QmsClassification("7.3.5 Design and Development Review", "Design Control"),
    9:  QmsClassification("7.3.6 Design and Development Verification & Validation", "Design Control"),
    10: QmsClassification("7.3.8 Design and Development Transfer", "Design Control"),
    11: QmsClassification("8.4 Analysis of Data (Statistical Techniques)", "Design Control"),
    12: QmsClassification("7.1 Planning of Product Realization (Risk Management)", "Risk Management"),
    13: QmsClassification("7.1 Risk Management (ISO 14971)", "Risk Management"),
    14: QmsClassification("4.1.6 Software Validation (Electronic Doc System)", "Document Control"),
    15: QmsClassification("7.4.1 Purchasing Process (Supplier QA)", "Purchasing & Suppliers"),
    16: QmsClassification("8.5 Improvement (CAPA)", "CAPA"),
    17: QmsClassification("8.2.4 Internal Audit", "Audits"),
    18: QmsClassification("5.6 Management Review", "Management"),
    19: QmsClassification("7.5.8 Identification & 7.5.9 Traceability", "Production & Service"),
    20: QmsClassification("7.4 Purchasing", "Purchasing & Suppliers"),
    21: QmsClassification("8.2.2 Complaint Handling", "Post-Market"),
    22: QmsClassification("8.2.3 Reporting to Regulatory Authorities (MDR)", "Post-Market"),
    23: QmsClassification("8.2.3 Reporting to Regulatory Authorities (eMDR)", "Post-Market"),
    24: QmsClassification("5.5.1 Responsibility and Authority", "Management"),
    25: QmsClassification("5.4.2 Quality Management System Planning", "Quality Planning"),
    26: QmsClassification("7.5.1 Control of Production (Part Numbering)", "Production & Service"),
    27: QmsClassification("4.2.2 Quality Manual", "Document Control"),
    28: QmsClassification("4.2.5 Control of Records (Confidential Patient Information)", "Document Control"),
    # Debatable: SLQ029 (DHR Review) is a records-control activity (4.2.5) but is grouped
    # under Production & Service because DHRs are production records. Left as-is pending
    # coordinator confirmation.
    29: QmsClassification("4.2.5 Control of Records (DHR Review)", "Production & Service"),
    30: QmsClassification("8.3 Control of Nonconforming Product (Advisory Notices & Recalls)", "Post-Market"),
    32: QmsClassification("4.1.6 / 7.5.6 Software Validation", "Design Control"),
    33: QmsClassification("8.2.1 Feedback (Post-Market Surveillance)", "Post-Market"),
    34: QmsClassification("5.5.1 Responsibility and Authority (Organization Chart)", "Management"),
    35: QmsClassification("5.3 Quality Policy", "Management"),
    36: QmsClassification("7.2 Customer-Related Processes (Sales Order)", "Sales & Customer"),
    37: QmsClassification("5.4.1 Quality Objectives", "Management"),
    38: QmsClassification("8.2.4 / Regulatory Inspections", "Regulatory"),
    39: QmsClassification("7.4.3 Verification of Purchased Product (Receiving Inspection)", "Purchasing & Suppliers"),
    40: QmsClassification("8.3 Control of Nonconforming Product", "Nonconforming Material"),
    43: QmsClassification("7.5.1 Control of Production (Work Order)", "Production & Service"),
    # SLQ045 Receiving SOP moved to Purchasing & Suppliers so it sits alongside the
    # Receiving Inspection SOP (SLQ039); both are part of the incoming-receiving workflow.
    45: QmsClassification("7.4.3 / 7.5.1 Receiving", "Purchasing & Suppliers"),
    46: QmsClassification("7.5.5 Preservation of Product (Shipping)", "Production & Service"),
    47: QmsClassification("7.5.6 Validation of Processes for Production", "Production & Service"),
    48: QmsClassification("7.3.10 / 4.2.3 Device Master Record", "Design Control"),
    # Debatable: SLQ049 / SLQ051 are 6.4 Work Environment controls; grouped under
    # Production & Service since they govern the production environment. Left as-is.
    49: QmsClassification("6.4 Work Environment (Workstation Practices)", "Production & Service"),
    50: QmsClassification("7.6 Control of Monitoring and Measuring Equipment", "Equipment & Calibration"),
    51: QmsClassification("6.4 Work Environment (Environmental Monitoring)", "Production & Service"),
    52: QmsClassification("7.3.9 Control of Design and Development Changes", "Design Control"),
}

# Optional per-document overrides (full normalized doc number -> classification),
# for documents that do not follow the SLQ-family pattern or need a special case.
_BY_DOC_NUMBER: dict[str, QmsClassification] = {}

_SLQ_RE = re.compile(r"SLQ0*(\d+)")


def slq_family(doc_number: str | None) -> int | None:
    """Return the SILQ SLQ family number for a document number, or None.

    The family ties a parent SOP to its forms/templates/travelers, e.g.
    ``QM.SLQ015``, ``FM1-QM.SLQ015`` and ``TMP1-QM.SLQ015`` all resolve to 15.
    Shared by the QMS Index (classification) and the related-documents feature.
    """
    m = _SLQ_RE.search((doc_number or "").upper())
    return int(m.group(1)) if m else None


def classify(doc_number: str | None) -> QmsClassification:
    """Resolve a document number to its ISO clause + subsystem.

    Falls back to the visible "Unclassified" bucket for anything not covered,
    so mapping gaps are surfaced rather than hidden.
    """
    key = (doc_number or "").strip().upper()
    if not key:
        return QmsClassification(UNCLASSIFIED, UNCLASSIFIED)
    if key in _BY_DOC_NUMBER:
        return _BY_DOC_NUMBER[key]
    fam = slq_family(key)
    if fam is not None:
        mapped = _BY_SLQ_FAMILY.get(fam)
        if mapped is not None:
            return mapped
    return QmsClassification(UNCLASSIFIED, UNCLASSIFIED)
