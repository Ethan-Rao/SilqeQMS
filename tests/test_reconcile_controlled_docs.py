"""Unit tests for the controlled-document reconciliation engine (Dev Prompt 4).

These cover the deterministic pure helpers: filename parsing, revision ordering,
HX->SLQ normalization, document-control classification, and the DCO085/QM.SLQ018
corrections. No real files or DB are required.
"""
import scripts.reconcile_controlled_docs as rc


# --- normalization / HX->SLQ ------------------------------------------------
def test_hx_to_slq_normalization():
    assert rc.normalize_doc_number("QM.HX001") == "QM.SLQ001"
    assert rc.normalize_doc_number("FM1-QM.HX001") == "FM1-QM.SLQ001"
    assert rc.normalize_doc_number("TMP1-QM.HX005") == "TMP1-QM.SLQ005"


def test_bare_form_token_gets_qm_prefix():
    assert rc.normalize_doc_number("FM1-SLQ020") == "FM1-QM.SLQ020"
    assert rc.normalize_doc_number("TMP1-SLQ005") == "TMP1-QM.SLQ005"


def test_normalization_is_idempotent_and_case_stable():
    assert rc.normalize_doc_number("QM.slq001") == "QM.SLQ001"
    assert rc.normalize_doc_number(rc.normalize_doc_number("QM.HX014")) == "QM.SLQ014"


def test_is_document_number_and_dco_rejected():
    assert rc.is_document_number("QM.SLQ001")
    assert rc.is_document_number("FM6-QM.SLQ015")
    assert rc.is_document_number("SP-C.SLQ001")
    assert rc.is_document_number("SLQ-4000")
    assert not rc.is_document_number("DCO092")
    assert not rc.is_document_number("Attachment")


def test_is_document_control_classification():
    assert rc.is_document_control("QM.SLQ001")
    assert rc.is_document_control("FM1-QM.SLQ001")
    assert rc.is_document_control("TMP3-QM.SLQ013")
    # Records families are not Document Control.
    assert not rc.is_document_control("SW.SLQ007")
    assert not rc.is_document_control("VV.SLQ012")
    assert not rc.is_document_control("SP-C.SLQ001")
    assert not rc.is_document_control("QC-C.SLQ001")


# --- revision ordering ------------------------------------------------------
def test_rev_ordering_base26():
    assert rc.rev_to_int("A") == 1
    assert rc.rev_to_int("Z") == 26
    assert rc.rev_to_int("AA") == 27
    assert rc.rev_to_int("A") < rc.rev_to_int("B") < rc.rev_to_int("Z") < rc.rev_to_int("AA")
    assert rc.rev_to_int(None) == 0
    assert rc.rev_to_int("") == 0
    assert rc.rev_to_int("12") == 0  # numeric/non-alpha is not a base-26 rev


def test_int_to_rev_roundtrip():
    for n in [1, 2, 26, 27, 28, 52, 53]:
        assert rc.rev_to_int(rc._int_to_rev(n)) == n


# --- filename parsing -------------------------------------------------------
def test_parse_standard_filename():
    pf = rc.parse_filename("QM.SLQ001 B Document Control SOP.docx")
    assert pf.doc_number == "QM.SLQ001"
    assert pf.revision == "B"
    assert pf.title == "Document Control SOP"
    assert pf.ext == "docx"
    assert not pf.is_redline


def test_parse_mixed_case_extension_and_hx():
    pf = rc.parse_filename("QM.HX001 A Document Control SOP.DOCX")
    assert pf.doc_number == "QM.SLQ001"
    assert pf.revision == "A"
    assert pf.ext == "docx"


def test_parse_redline_variants_flagged():
    for name in [
        "QM.SLQ001 B Document Control SOP_Redline.docx",
        "QM.SLQ014 C Electronic Doc System WI_RedLine.docx",
        "QM.SLQ046 B Shipping SOP_RedLinde.docx",
        "QM.SLQ034 G Organization Chart_RL.docx",
        "QM.SLQ022 A Medical Device Reporting_RedLineV1.docx",
    ]:
        pf = rc.parse_filename(name)
        assert pf is not None
        assert pf.is_redline, name


def test_parse_rev_prefixed_token():
    pf = rc.parse_filename("Authorized Approvers Form Rev C.pdf")
    # Leading token 'Authorized' is not a doc number -> None.
    assert pf is None


def test_parse_underscore_embedded_revision():
    pf = rc.parse_filename("SLQ-4000_A.pdf")
    assert pf is not None
    assert pf.doc_number == "SLQ-4000"
    assert pf.revision == "A"


def test_parse_parenthetical_noise():
    pf = rc.parse_filename("QM.SLQ034 E Organization Chart (DCO050).docx")
    assert pf.doc_number == "QM.SLQ034"
    assert pf.revision == "E"
    assert "Organization Chart" in pf.title


def test_parse_dco_form_is_not_a_document():
    assert rc.parse_filename("DCO092.docx") is None
    assert rc.parse_filename("DCO 091 Signed.pdf") is None


def test_parse_missing_revision():
    pf = rc.parse_filename("FM2-QM.SLQ052 Design Change Assessment.docx")
    assert pf is not None
    assert pf.doc_number == "FM2-QM.SLQ052"
    assert pf.revision is None


# --- classification helpers -------------------------------------------------
def test_doc_type_classification():
    assert rc.classify_doc_type("FM1-QM.SLQ001", "Document Change Order Form") == "Form"
    assert rc.classify_doc_type("TMP1-QM.SLQ005", "Design Project Plan Template") == "Template"
    assert rc.classify_doc_type("QM.SLQ027", "Quality Manual") == "Manual"
    assert rc.classify_doc_type("QM.SLQ035", "Quality Policy") == "Policy"
    assert rc.classify_doc_type("QM.SLQ014", "Electronic Doc System WI") == "WI"
    assert rc.classify_doc_type("QM.SLQ001", "Document Control SOP") == "SOP"


# --- DCO085 typo correction -------------------------------------------------
def test_dco085_typo_correction(tmp_path):
    # Build a tiny DCO log with the QM.SLQ024 typo on DCO085.
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["intro"])
    ws.append(["banner"])
    ws.append(["DCO Number", "", "Affected", "Curr", "New", "Title"])
    ws.append(["085", "1", "QM.SLQ024", "E", "F", "Organization Chart"])
    ws.append(["085", "2", "QM.SLQ035", "C", "D", "Quality Policy"])
    p = tmp_path / "log.xlsx"
    wb.save(p)

    lines = rc.parse_dco_log(p)
    org = [l for l in lines if l.document_title == "Organization Chart"][0]
    assert org.document_number == "QM.SLQ034"  # corrected from QM.SLQ024
    assert org.corrections and "typo" in org.corrections[0].lower()


def test_dco_sort_key_handles_suffix():
    assert rc.dco_sort_key("085") == (85, "")
    assert rc.dco_sort_key("042A") == (42, "A")
    assert rc.dco_sort_key("053B") == (53, "B")


# --- title-named-file matcher (Part A) --------------------------------------
def test_normalize_title():
    assert rc.normalize_title("Authorized Approvers Form") == "authorized approvers form"
    assert rc.normalize_title("SQ SA Survey - Mfg!") == "sq sa survey mfg"


def test_match_title_named_file():
    index = {
        "authorized approvers form": "FM2-QM.SLQ001",
        "electronic signature acknowledgement form": "FM1-QM.SLQ014",
    }
    assert rc.match_title_named_file("Authorized Approvers Form Rev C.pdf", index) == ("FM2-QM.SLQ001", "C")
    assert rc.match_title_named_file("Electronic Signature Acknowledgement Form Rev B.pdf", index) == ("FM1-QM.SLQ014", "B")


def test_match_title_named_file_requires_rev_and_match():
    index = {"authorized approvers form": "FM2-QM.SLQ001"}
    # No trailing "Rev X".
    assert rc.match_title_named_file("Authorized Approvers Form.pdf", index) is None
    # Unknown title -> unmatched (not force-linked).
    assert rc.match_title_named_file("220_12965_035 Rev A Hydrophilix.pdf", index) is None


def test_match_title_named_file_skips_ambiguous():
    index = {"design review record": "FM3-QM.SLQ052"}
    ambiguous = {"design review record"}
    assert rc.match_title_named_file("Design Review Record Rev A.pdf", index, ambiguous) is None


def test_build_title_index_flags_ambiguous():
    lines = [
        rc.DcoLine("001", 1, "FM2-QM.SLQ001", "-", "A", "Authorized Approvers Form", "", None, None, []),
        rc.DcoLine("003", 1, "FM9-QM.SLQ099", "-", "A", "Authorized Approvers Form", "", None, None, []),
        rc.DcoLine("004", 1, "FM1-QM.SLQ014", "-", "A", "Electronic Signature Acknowledgement Form", "", None, None, []),
    ]
    index, ambiguous = rc.build_title_index(lines)
    assert "authorized approvers form" in ambiguous
    assert "authorized approvers form" not in index  # dropped due to conflict
    assert index["electronic signature acknowledgement form"] == "FM1-QM.SLQ014"
