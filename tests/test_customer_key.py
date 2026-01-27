"""
Unit tests for customer key canonicalization functions.

Tests cover:
- Basic normalization
- Business suffix removal
- Abbreviation handling (documented behavior)
- Edge cases (PO Box, special characters, etc.)
- Sales order key computation
"""

import pytest
from app.eqms.modules.customer_profiles.utils import (
    canonical_customer_key,
    normalize_facility_name,
    compute_customer_key_from_sales_order,
)


class TestCanonicalCustomerKey:
    """Tests for canonical_customer_key()"""
    
    def test_basic_normalization(self):
        """Basic names produce expected keys"""
        assert canonical_customer_key("Hospital A") == "HOSPITALA"
        assert canonical_customer_key("Medical Center") == "MEDICALCENTER"
        assert canonical_customer_key("Clinic") == "CLINIC"
    
    def test_uppercase_conversion(self):
        """All keys are uppercase"""
        assert canonical_customer_key("hospital a") == "HOSPITALA"
        assert canonical_customer_key("HOSPITAL A") == "HOSPITALA"
        assert canonical_customer_key("Hospital A") == "HOSPITALA"
    
    def test_removes_spaces_and_punctuation(self):
        """Spaces and punctuation are removed"""
        assert canonical_customer_key("Hospital - A") == "HOSPITALA"
        assert canonical_customer_key("Hospital, A") == "HOSPITALA"
        assert canonical_customer_key("Hospital.A") == "HOSPITALA"
        assert canonical_customer_key("Hospital  A") == "HOSPITALA"  # Multiple spaces
    
    def test_preserves_numbers(self):
        """Numbers are preserved in keys"""
        assert canonical_customer_key("Hospital 123") == "HOSPITAL123"
        assert canonical_customer_key("123 Main St") == "123MAINST"
    
    def test_business_suffix_removal(self):
        """Business suffixes are removed before key generation"""
        # Inc.
        assert canonical_customer_key("Hospital A, Inc.") == "HOSPITALA"
        assert canonical_customer_key("Hospital A Inc") == "HOSPITALA"
        
        # LLC
        assert canonical_customer_key("Hospital A LLC") == "HOSPITALA"
        assert canonical_customer_key("Hospital A, LLC") == "HOSPITALA"
        
        # Corp./Corporation
        assert canonical_customer_key("Hospital A Corp") == "HOSPITALA"
        assert canonical_customer_key("Hospital A Corporation") == "HOSPITALA"
        
        # Ltd./Limited
        assert canonical_customer_key("Hospital A Ltd") == "HOSPITALA"
        assert canonical_customer_key("Hospital A Limited") == "HOSPITALA"
        
        # Co./Company
        assert canonical_customer_key("Hospital A Co.") == "HOSPITALA"
        assert canonical_customer_key("Hospital A Company") == "HOSPITALA"
        
        # Same key regardless of suffix
        assert canonical_customer_key("Hospital A") == canonical_customer_key("Hospital A, Inc.")
        assert canonical_customer_key("Hospital A") == canonical_customer_key("Hospital A LLC")
    
    def test_abbreviations_not_normalized(self):
        """Abbreviations are NOT normalized (documented behavior)"""
        # St vs Street produce different keys (by design)
        assert canonical_customer_key("123 Main St") == "123MAINST"
        assert canonical_customer_key("123 Main Street") == "123MAINSTREET"
        assert canonical_customer_key("123 Main St") != canonical_customer_key("123 Main Street")
        
        # Ave vs Avenue
        assert canonical_customer_key("123 Oak Ave") == "123OAKAVE"
        assert canonical_customer_key("123 Oak Avenue") == "123OAKAVENUE"
        assert canonical_customer_key("123 Oak Ave") != canonical_customer_key("123 Oak Avenue")
    
    def test_po_box_included(self):
        """PO Box is included if part of name"""
        assert canonical_customer_key("Hospital PO Box 123") == "HOSPITALPOBOX123"
        assert canonical_customer_key("PO Box 456 Clinic") == "POBOX456CLINIC"
    
    def test_special_characters(self):
        """Special characters are removed"""
        assert canonical_customer_key("St. Joseph's Hospital") == "STJOSEPHSHOSPITAL"
        assert canonical_customer_key("O'Brien Clinic") == "OBRIENCLINIC"
        assert canonical_customer_key("Hospital & Clinic") == "HOSPITALCLINIC"
    
    def test_empty_or_whitespace(self):
        """Empty or whitespace-only names return empty string"""
        assert canonical_customer_key("") == ""
        assert canonical_customer_key("   ") == ""
        assert canonical_customer_key(None) == ""  # type: ignore
    
    def test_hospital_name_variations(self):
        """Various hospital name formats"""
        # These should all produce different keys (different names)
        assert canonical_customer_key("Hospital A") == "HOSPITALA"
        assert canonical_customer_key("Hospital B") == "HOSPITALB"
        
        # These should produce same key (same name, different format)
        assert canonical_customer_key("Hospital A") == canonical_customer_key("Hospital A, Inc.")
        assert canonical_customer_key("Hospital A") == canonical_customer_key("  Hospital A  ")


class TestNormalizeFacilityName:
    """Tests for normalize_facility_name()"""
    
    def test_removes_business_suffixes(self):
        assert normalize_facility_name("Hospital A, Inc.") == "Hospital A"
        assert normalize_facility_name("Hospital A LLC") == "Hospital A"
        assert normalize_facility_name("Hospital A Corp") == "Hospital A"
    
    def test_strips_whitespace(self):
        assert normalize_facility_name("  Hospital A  ") == "Hospital A"
    
    def test_handles_empty(self):
        assert normalize_facility_name("") == ""
        assert normalize_facility_name(None) == ""  # type: ignore


class TestComputeCustomerKeyFromSalesOrder:
    """Tests for compute_customer_key_from_sales_order()"""
    
    def test_priority_1_customer_number(self):
        """Customer number takes highest priority"""
        data = {
            "customer_number": "CUST12345",
            "ship_to_name": "Hospital A",
            "city": "New York",
            "state": "NY",
        }
        assert compute_customer_key_from_sales_order(data) == "CUST:CUST12345"
    
    def test_priority_1_account_number_fallback(self):
        """Account number used if customer_number missing"""
        data = {
            "account_number": "ACC-999",
            "ship_to_name": "Hospital A",
        }
        assert compute_customer_key_from_sales_order(data) == "CUST:ACC999"
    
    def test_priority_2_full_address(self):
        """Full address used when no customer number"""
        data = {
            "ship_to_name": "Hospital A",
            "ship_to_address1": "123 Main St",
            "ship_to_city": "New York",
            "ship_to_state": "NY",
            "ship_to_zip": "10001",
        }
        # Should combine all fields
        result = compute_customer_key_from_sales_order(data)
        assert "HOSPITALA" in result
        assert "123MAINST" in result
        assert "NEWYORK" in result
        assert "NY" in result
        assert "10001" in result
    
    def test_priority_3_name_city_state(self):
        """Name + city + state used when address incomplete"""
        data = {
            "facility_name": "Hospital A",
            "city": "New York",
            "state": "NY",
        }
        result = compute_customer_key_from_sales_order(data)
        assert "HOSPITALA" in result
        assert "NEWYORK" in result
        assert "NY" in result
    
    def test_priority_4_name_only(self):
        """Name only as last resort"""
        data = {
            "customer_name": "Hospital A",
        }
        assert compute_customer_key_from_sales_order(data) == "HOSPITALA"
    
    def test_fallback_unknown(self):
        """Returns UNKNOWN when no data provided"""
        data = {}
        assert compute_customer_key_from_sales_order(data) == "UNKNOWN"
    
    def test_alternative_field_names(self):
        """Supports multiple field name variations"""
        # facility_name instead of ship_to_name
        data1 = {"facility_name": "Hospital A"}
        assert compute_customer_key_from_sales_order(data1) == "HOSPITALA"
        
        # address1 instead of ship_to_address1
        data2 = {
            "facility_name": "Hospital A",
            "address1": "123 Main St",
            "city": "NYC",
            "state": "NY",
            "zip": "10001",
        }
        result = compute_customer_key_from_sales_order(data2)
        assert "HOSPITALA" in result
        assert "123MAINST" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
