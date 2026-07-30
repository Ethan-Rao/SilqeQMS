"""Tests for customer key helpers (P41 / P41b Ship-To facility keys)."""
from app.eqms.modules.customer_profiles.utils import (
    canonical_customer_key,
    compute_customer_key_from_sales_order,
    compute_facility_key_from_ship_to,
    facility_display_name,
    normalize_facility_name,
    normalize_street_for_key,
    prettify_facility_name,
)


class TestCanonicalCustomerKey:
    """Tests for canonical_customer_key()"""

    def test_basic_normalization(self):
        assert canonical_customer_key("Hospital A") == "HOSPITALA"
        assert canonical_customer_key("Medical Center") == "MEDICALCENTER"
        assert canonical_customer_key("Clinic") == "CLINIC"

    def test_case_insensitive(self):
        assert canonical_customer_key("hospital a") == "HOSPITALA"
        assert canonical_customer_key("HOSPITAL A") == "HOSPITALA"
        assert canonical_customer_key("Hospital A") == "HOSPITALA"

    def test_punctuation_removed(self):
        assert canonical_customer_key("Hospital - A") == "HOSPITALA"
        assert canonical_customer_key("Hospital, A") == "HOSPITALA"
        assert canonical_customer_key("Hospital.A") == "HOSPITALA"
        assert canonical_customer_key("Hospital  A") == "HOSPITALA"

    def test_numbers_preserved(self):
        assert canonical_customer_key("Hospital 123") == "HOSPITAL123"
        assert canonical_customer_key("123 Main St") == "123MAINST"

    def test_business_suffixes_removed(self):
        assert canonical_customer_key("Hospital A, Inc.") == "HOSPITALA"
        assert canonical_customer_key("Hospital A Inc") == "HOSPITALA"
        assert canonical_customer_key("Hospital A LLC") == "HOSPITALA"
        assert canonical_customer_key("Hospital A, LLC") == "HOSPITALA"
        assert canonical_customer_key("Hospital A Corp") == "HOSPITALA"
        assert canonical_customer_key("Hospital A Corporation") == "HOSPITALA"
        assert canonical_customer_key("Hospital A Ltd") == "HOSPITALA"
        assert canonical_customer_key("Hospital A Limited") == "HOSPITALA"
        assert canonical_customer_key("Hospital A Co.") == "HOSPITALA"
        assert canonical_customer_key("Hospital A Company") == "HOSPITALA"
        assert canonical_customer_key("Hospital A") == canonical_customer_key("Hospital A, Inc.")
        assert canonical_customer_key("Hospital A") == canonical_customer_key("Hospital A LLC")

    def test_street_abbreviations_not_normalized(self):
        assert canonical_customer_key("123 Main St") == "123MAINST"
        assert canonical_customer_key("123 Main Street") == "123MAINSTREET"
        assert canonical_customer_key("123 Main St") != canonical_customer_key("123 Main Street")
        assert canonical_customer_key("123 Oak Ave") == "123OAKAVE"
        assert canonical_customer_key("123 Oak Avenue") == "123OAKAVENUE"
        assert canonical_customer_key("123 Oak Ave") != canonical_customer_key("123 Oak Avenue")

    def test_po_box_included(self):
        assert canonical_customer_key("Hospital PO Box 123") == "HOSPITALPOBOX123"
        assert canonical_customer_key("PO Box 456 Clinic") == "POBOX456CLINIC"

    def test_special_characters(self):
        assert canonical_customer_key("St. Joseph's Hospital") == "STJOSEPHSHOSPITAL"
        assert canonical_customer_key("O'Brien Clinic") == "OBRIENCLINIC"
        assert canonical_customer_key("Hospital & Clinic") == "HOSPITALCLINIC"

    def test_empty_or_whitespace(self):
        assert canonical_customer_key("") == ""
        assert canonical_customer_key("   ") == ""
        assert canonical_customer_key(None) == ""  # type: ignore

    def test_hospital_name_variations(self):
        assert canonical_customer_key("Hospital A") == "HOSPITALA"
        assert canonical_customer_key("Hospital B") == "HOSPITALB"
        assert canonical_customer_key("Hospital A") == canonical_customer_key("Hospital A, Inc.")
        assert canonical_customer_key("Hospital A") == canonical_customer_key("  Hospital A  ")


class TestNormalizeFacilityName:
    def test_removes_business_suffixes(self):
        assert normalize_facility_name("Hospital A, Inc.") == "Hospital A"
        assert normalize_facility_name("Hospital A LLC") == "Hospital A"
        assert normalize_facility_name("Hospital A Corp") == "Hospital A"

    def test_strips_whitespace(self):
        assert normalize_facility_name("  Hospital A  ") == "Hospital A"

    def test_handles_empty(self):
        assert normalize_facility_name("") == ""
        assert normalize_facility_name(None) == ""  # type: ignore


class TestComputeFacilityKeyP41:
    def test_address2_ignored_same_key(self):
        k1 = compute_facility_key_from_ship_to(
            address1="100 Main St", city="Long Beach", state="CA", zip="90802",
            facility_name="Marathon Medical",
        )
        k2 = compute_facility_key_from_ship_to(
            address1="100 Main St", city="Long Beach", state="CA", zip="90802-1234",
            facility_name="Marathon Medical Corp",
        )
        # Same street/state/zip5 → same key (city + name ignored when complete)
        assert k1 == k2
        assert k1 == "100MAINST|CA|90802"

    def test_different_cities_different_keys(self):
        k1 = compute_facility_key_from_ship_to(
            address1="100 Main St", city="Long Beach", state="CA", zip="90802",
            facility_name="Marathon Medical",
        )
        k2 = compute_facility_key_from_ship_to(
            address1="200 Oak Ave", city="Torrance", state="CA", zip="90503",
            facility_name="Marathon Medical",
        )
        assert k1 != k2

    def test_avenue_abbrev_and_suite_merge(self):
        k1 = compute_facility_key_from_ship_to(
            address1="26520 Cactus Avenue", city="Moreno Valley", state="CA", zip="92555",
        )
        k2 = compute_facility_key_from_ship_to(
            address1="26520 Cactus Ave Ste 100", city="Moreno Valley", state="CA", zip="92555",
        )
        assert k1 == k2
        assert normalize_street_for_key("26520 Cactus Avenue") == normalize_street_for_key(
            "26520 Cactus Ave #200"
        )

    def test_word_order_variants_merge(self):
        k1 = compute_facility_key_from_ship_to(
            address1="6010 Amarillo Blvd West", city="Amarillo", state="TX", zip="79106",
        )
        k2 = compute_facility_key_from_ship_to(
            address1="6010 West Amarillo Blvd", city="Amarillo", state="TX", zip="79106",
        )
        assert k1 == k2

    def test_temple_sites_stay_separate(self):
        philly = compute_facility_key_from_ship_to(
            address1="7600 Central Ave", city="Philadelphia", state="PA", zip="19111",
        )
        ft_wash = compute_facility_key_from_ship_to(
            address1="450 Pennsylvania Ave", city="Fort Washington", state="PA", zip="19034",
        )
        assert philly != ft_wash

    def test_customer_number_not_sole_key(self):
        data = {
            "customer_number": "MARATHON-001",
            "ship_to_name": "Marathon Medical",
            "ship_to_address1": "100 Main St",
            "ship_to_city": "Long Beach",
            "ship_to_state": "CA",
            "ship_to_zip": "90802",
        }
        key = compute_customer_key_from_sales_order(data)
        assert not key.startswith("CUST:")
        assert key == compute_facility_key_from_ship_to(
            address1="100 Main St", city="Long Beach", state="CA", zip="90802",
        )

    def test_incomplete_uses_name_tiebreak(self):
        key = compute_facility_key_from_ship_to(
            address1=None, city="Riverside", state="CA", zip=None,
            facility_name="RCRMC",
        )
        assert "RCRMC" in key or "RIVERSIDE" in key

    def test_clinical_display_name(self):
        assert facility_display_name("VAMC AMARILLO", city="Amarillo") == "VAMC Amarillo"
        assert "Marathon" not in facility_display_name(
            "VAMC Amarillo", sold_to_name="MARATHON MEDICAL CORPORATION", city="AMARILLO"
        )
        assert prettify_facility_name("Marathon Medical Corporation — AMARILLO").startswith(
            "Marathon Medical Corporation"
        )
        # Hyphenated clinical names must not be stripped as city suffixes
        assert "Loma" in prettify_facility_name("VAMC - LOMA LINDA")
        assert "San Diego" in prettify_facility_name("VAMC-SAN DIEGO HEALTHCARE") or (
            "San" in prettify_facility_name("VAMC-SAN DIEGO HEALTHCARE")
        )
