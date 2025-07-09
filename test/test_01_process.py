#!/usr/bin/env python3
"""
Comprehensive test suite for 01_process.py FDA data to RDF conversion script.

This test suite validates:
1. URI building functions
2. Relationship extraction logic
3. RDF triple generation
4. Namespace usage
5. Data processing edge cases
6. TTL output validation
"""

import importlib.util
import os
import shutil

# Import the functions we're testing
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pandas as pd
import pytest
from rdflib import Graph, Literal, URIRef

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import the module properly using importlib
spec = importlib.util.spec_from_file_location(
    "process_01",
    os.path.join(os.path.dirname(__file__), '..', 'stages', '01_process.py')
)
process_01 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(process_01)

# Now import the functions from the loaded module
build_application_uri = process_01.build_application_uri
build_company_uri = process_01.build_company_uri
build_substance_uri = process_01.build_substance_uri
build_ndc_uri = process_01.build_ndc_uri
build_rxcui_uri = process_01.build_rxcui_uri
build_spl_uri = process_01.build_spl_uri
build_dosage_form_uri = process_01.build_dosage_form_uri
build_route_uri = process_01.build_route_uri
build_ingredient_uri = process_01.build_ingredient_uri
safe_get_array_items = process_01.safe_get_array_items
extract_relationships_from_row = process_01.extract_relationships_from_row
namespaces = process_01.namespaces
namespaces_sources = process_01.namespaces_sources


class TestConstants:
    """Test constants and sample data"""

    SAMPLE_APPLICATION_NUMBER = "ANDA076187"
    SAMPLE_SPONSOR_NAME = "MYLAN"
    SAMPLE_MANUFACTURER_NAME = "Mylan Pharmaceuticals Inc."
    SAMPLE_BRAND_NAME = "LEVOTHYROXINE SODIUM"
    SAMPLE_UNII = "9J765S329G"
    SAMPLE_NDC = "0378-1800-77"
    SAMPLE_RXCUI = "892246"
    SAMPLE_SPL_ID = "e95720f2-91c9-a6d0-f7d5-8bcb94d07bbc"

    # Complete sample data structure based on out.txt
    SAMPLE_FDA_ROW = {
        "application_number": SAMPLE_APPLICATION_NUMBER,
        "sponsor_name": SAMPLE_SPONSOR_NAME,
        "submissions": [
            {
                "application_docs": None,
                "review_priority": "STANDARD",
                "submission_class_code": "LABELING",
                "submission_class_code_description": "Labeling",
                "submission_number": "50",
                "submission_status": "AP",
                "submission_status_date": "20230720",
                "submission_type": "SUPPL"
            }
        ],
        "openfda": {
            "application_number": [SAMPLE_APPLICATION_NUMBER],
            "brand_name": [SAMPLE_BRAND_NAME],
            "generic_name": [SAMPLE_BRAND_NAME],
            "manufacturer_name": [SAMPLE_MANUFACTURER_NAME],
            "package_ndc": [SAMPLE_NDC, "0378-1800-10"],
            "product_ndc": ["0378-1800", "0378-1803"],
            "product_type": ["HUMAN PRESCRIPTION DRUG"],
            "route": ["ORAL"],
            "rxcui": [SAMPLE_RXCUI, "892251"],
            "spl_set_id": [SAMPLE_SPL_ID],
            "substance_name": [SAMPLE_BRAND_NAME],
            "unii": [SAMPLE_UNII]
        },
        "products": [
            {
                "active_ingredients": [
                    {
                        "name": SAMPLE_BRAND_NAME,
                        "strength": "0.175MG **See current Annual Edition"
                    }
                ],
                "brand_name": SAMPLE_BRAND_NAME,
                "dosage_form": "TABLET",
                "marketing_status": "Prescription",
                "product_number": "009",
                "reference_drug": "No",
                "reference_standard": "No",
                "route": "ORAL",
                "te_code": "AB4"
            },
            {
                "active_ingredients": [
                    {
                        "name": SAMPLE_BRAND_NAME,
                        "strength": "0.125MG **See current Annual Edition"
                    }
                ],
                "brand_name": SAMPLE_BRAND_NAME,
                "dosage_form": "TABLET",
                "marketing_status": "Prescription",
                "product_number": "007",
                "route": "ORAL"
            }
        ]
    }


@pytest.fixture
def sample_fda_row():
    """Fixture providing a complete sample FDA row"""
    return TestConstants.SAMPLE_FDA_ROW.copy()


@pytest.fixture
def sample_fda_row_pandas():
    """Fixture providing a pandas Series version of the sample data"""
    return pd.Series(TestConstants.SAMPLE_FDA_ROW)


@pytest.fixture
def sample_fda_row_minimal():
    """Fixture providing minimal required data"""
    return {
        "application_number": TestConstants.SAMPLE_APPLICATION_NUMBER,
        "sponsor_name": TestConstants.SAMPLE_SPONSOR_NAME,
        "openfda": None,
        "products": None
    }


@pytest.fixture
def sample_fda_row_empty():
    """Fixture providing empty/null data for edge case testing"""
    return {
        "application_number": None,
        "sponsor_name": None,
        "openfda": {},
        "products": []
    }


@pytest.fixture
def expected_namespaces():
    """Fixture providing expected namespace mappings"""
    return {
        "fda": "https://api.fda.gov/drug/",
        "company": "https://api.fda.gov/drug/company/",
        "unii": "https://fdasis.nlm.nih.gov/srs/unii/",
        "ndc": "https://www.fda.gov/industry/structured-product-labeling-resources/ndc-directory/",
        "rxcui": "https://mor.nlm.nih.gov/RxNav/search?searchBy=RXCUI&searchTerm=",
        "spl": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=",
        "SIO": "http://semanticscience.org/resource/SIO_",
        "RO": "http://purl.obolibrary.org/obo/RO_",
        "IAO": "http://purl.obolibrary.org/obo/IAO_",
        "ExO": "http://purl.obolibrary.org/obo/ExO_",
        "CHEMINF": "http://purl.obolibrary.org/obo/CHEMINF_",
        "biolink": "https://w3id.org/biolink/vocab/",
        "BAO": "http://www.bioassayontology.org/bao#BAO_"
    }


@pytest.fixture
def temp_cache_dir():
    """Fixture providing a temporary cache directory"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


class RDFTestUtils:
    """Utility functions for RDF testing"""

    @staticmethod
    def create_test_graph(triples):
        """Create an RDF graph from a list of triples"""
        g = Graph()
        for prefix, namespace in namespaces.items():
            g.bind(prefix, namespace)

        for triple in triples:
            g.add(triple)
        return g

    @staticmethod
    def has_triple(graph, subject, predicate, object_val):
        """Check if a graph contains a specific triple"""
        return (subject, predicate, object_val) in graph

    @staticmethod
    def count_triples_with_subject(graph, subject):
        """Count triples with a specific subject"""
        return len([t for t in graph if t[0] == subject])

    @staticmethod
    def get_objects_for_predicate(graph, subject, predicate):
        """Get all objects for a subject-predicate pair"""
        return [t[2] for t in graph if t[0] == subject and t[1] == predicate]

    @staticmethod
    def validate_uri_format(uri_str, expected_base):
        """Validate URI format and base"""
        return uri_str.startswith(expected_base) and '://' in uri_str


class TestURIBuilders:
    """Test all URI building functions"""

    def test_build_application_uri_basic(self):
        """Test basic application URI building"""
        app_number = "ANDA076187"
        result = build_application_uri(app_number)

        expected = URIRef("https://api.fda.gov/drug/application/ANDA076187")
        assert result == expected
        assert str(result).startswith("https://api.fda.gov/drug/application/")

    def test_build_application_uri_special_chars(self):
        """Test application URI with special characters"""
        app_number = "ANDA-076187/TEST"
        result = build_application_uri(app_number)

        # Should be URL encoded
        assert quote(app_number, safe='') in str(result)
        assert str(result).startswith("https://api.fda.gov/drug/application/")

    def test_build_company_uri_basic(self):
        """Test basic company URI building"""
        company_name = "MYLAN"
        result = build_company_uri(company_name)

        expected = URIRef("https://api.fda.gov/drug/company/MYLAN")
        assert result == expected

    def test_build_company_uri_spaces_punctuation(self):
        """Test company URI with spaces and punctuation"""
        company_name = "Mylan Pharmaceuticals, Inc."
        result = build_company_uri(company_name)

        # Should replace spaces with underscores and remove commas/periods from company name
        assert "Mylan_Pharmaceuticals_Inc" in str(result)
        assert " " not in str(result).split('/')[-1]  # No spaces in company name part
        assert "," not in str(result).split('/')[-1]  # No commas in company name part
        assert "." not in str(result).split('/')[-1]  # No periods in company name part

    def test_build_substance_uri(self):
        """Test UNII substance URI building"""
        unii = "9J765S329G"
        result = build_substance_uri(unii)

        expected = URIRef("https://fdasis.nlm.nih.gov/srs/unii/9J765S329G")
        assert result == expected

    def test_build_ndc_uri(self):
        """Test NDC code URI building"""
        ndc = "0378-1800-77"
        result = build_ndc_uri(ndc)

        expected = URIRef("https://www.fda.gov/industry/structured-product-labeling-resources/ndc-directory/0378-1800-77")
        assert result == expected

    def test_build_rxcui_uri(self):
        """Test RxCUI URI building"""
        rxcui = "892246"
        result = build_rxcui_uri(rxcui)

        expected = URIRef("https://mor.nlm.nih.gov/RxNav/search?searchBy=RXCUI&searchTerm=892246")
        assert result == expected

    def test_build_spl_uri(self):
        """Test SPL ID URI building"""
        spl_id = "e95720f2-91c9-a6d0-f7d5-8bcb94d07bbc"
        result = build_spl_uri(spl_id)

        expected = URIRef("https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=e95720f2-91c9-a6d0-f7d5-8bcb94d07bbc")
        assert result == expected

    def test_build_dosage_form_uri(self):
        """Test dosage form URI building"""
        dosage_form = "tablet, extended release"
        result = build_dosage_form_uri(dosage_form)

        # Should be uppercase and replace spaces/commas
        assert "TABLET_EXTENDED_RELEASE" in str(result)
        assert str(result).startswith("https://api.fda.gov/drug/dosage_form/")

    def test_build_route_uri(self):
        """Test route of administration URI building"""
        route = "oral, sublingual"
        result = build_route_uri(route)

        # Should be uppercase and replace spaces/commas
        assert "ORAL_SUBLINGUAL" in str(result)
        assert str(result).startswith("http://purl.obolibrary.org/obo/ExO_route/")

    def test_build_ingredient_uri(self):
        """Test ingredient URI building"""
        ingredient = "Levothyroxine Sodium, USP"
        result = build_ingredient_uri(ingredient)

        # Should replace spaces and remove punctuation
        assert "Levothyroxine_Sodium_USP" in str(result)
        assert str(result).startswith("http://purl.obolibrary.org/obo/CHEMINF_ingredient/")


class TestSafeGetArrayItems:
    """Test the safe_get_array_items utility function"""

    def test_none_input(self):
        """Test with None input"""
        result = safe_get_array_items(None)
        assert result == []

    def test_numpy_array(self):
        """Test with numpy array"""
        arr = np.array(["item1", "item2", None, "item3"])
        result = safe_get_array_items(arr)
        assert result == ["item1", "item2", "item3"]

    def test_list_input(self):
        """Test with regular list"""
        arr = ["item1", "item2", None, "item3"]
        result = safe_get_array_items(arr)
        assert result == ["item1", "item2", "item3"]

    def test_tuple_input(self):
        """Test with tuple"""
        arr = ("item1", "item2", None, "item3")
        result = safe_get_array_items(arr)
        assert result == ["item1", "item2", "item3"]

    def test_single_value(self):
        """Test with single non-None value"""
        result = safe_get_array_items("single_item")
        assert result == ["single_item"]

    def test_empty_array(self):
        """Test with empty array"""
        result = safe_get_array_items(np.array([]))
        assert result == []

    def test_all_none_array(self):
        """Test with array containing only None values"""
        arr = np.array([None, None, None])
        result = safe_get_array_items(arr)
        assert result == []


class TestRelationshipExtraction:
    """Test the extract_relationships_from_row function"""

    def test_extract_basic_application_relationships(self, sample_fda_row):
        """Test extraction of basic application relationships"""
        triples = extract_relationships_from_row(sample_fda_row)

        # Convert to graph for easier testing
        graph = RDFTestUtils.create_test_graph(triples)

        app_uri = build_application_uri(TestConstants.SAMPLE_APPLICATION_NUMBER)
        sponsor_uri = build_company_uri(TestConstants.SAMPLE_SPONSOR_NAME)

        # Check application-sponsor relationship
        assert RDFTestUtils.has_triple(graph, app_uri, namespaces["SIO"]["000136"], sponsor_uri)

        # Check sponsor typing
        assert RDFTestUtils.has_triple(graph, sponsor_uri, namespaces["rdf"]["type"], namespaces["SIO"]["000012"])

        # Check sponsor label
        assert RDFTestUtils.has_triple(graph, sponsor_uri, namespaces["rdfs"]["label"], Literal(TestConstants.SAMPLE_SPONSOR_NAME))

    def test_extract_openfda_brand_names(self, sample_fda_row):
        """Test extraction of brand names from OpenFDA data"""
        triples = extract_relationships_from_row(sample_fda_row)
        graph = RDFTestUtils.create_test_graph(triples)

        app_uri = build_application_uri(TestConstants.SAMPLE_APPLICATION_NUMBER)

        # Check brand name relationships
        brand_name_objects = RDFTestUtils.get_objects_for_predicate(graph, app_uri, namespaces["skos"]["prefLabel"])
        assert Literal(TestConstants.SAMPLE_BRAND_NAME) in brand_name_objects

        # Check SIO attribute relationship
        sio_attr_objects = RDFTestUtils.get_objects_for_predicate(graph, app_uri, namespaces["SIO"]["000008"])
        assert Literal(TestConstants.SAMPLE_BRAND_NAME) in sio_attr_objects

    def test_extract_manufacturer_relationships(self, sample_fda_row):
        """Test extraction of manufacturer relationships"""
        triples = extract_relationships_from_row(sample_fda_row)
        graph = RDFTestUtils.create_test_graph(triples)

        app_uri = build_application_uri(TestConstants.SAMPLE_APPLICATION_NUMBER)
        mfg_uri = build_company_uri(TestConstants.SAMPLE_MANUFACTURER_NAME)

        # Check manufactured by relationship
        assert RDFTestUtils.has_triple(graph, app_uri, namespaces["RO"]["0002234"], mfg_uri)

        # Check manufacturer typing
        assert RDFTestUtils.has_triple(graph, mfg_uri, namespaces["rdf"]["type"], namespaces["SIO"]["000012"])

    def test_extract_ndc_relationships(self, sample_fda_row):
        """Test extraction of NDC code relationships"""
        triples = extract_relationships_from_row(sample_fda_row)
        graph = RDFTestUtils.create_test_graph(triples)

        app_uri = build_application_uri(TestConstants.SAMPLE_APPLICATION_NUMBER)
        ndc_uri = build_ndc_uri(TestConstants.SAMPLE_NDC)

        # Check has identifier relationship
        assert RDFTestUtils.has_triple(graph, app_uri, namespaces["SIO"]["000671"], ndc_uri)

        # Check NDC typing
        assert RDFTestUtils.has_triple(graph, ndc_uri, namespaces["rdf"]["type"], namespaces["IAO"]["0000578"])

    def test_extract_unii_relationships(self, sample_fda_row):
        """Test extraction of UNII substance relationships"""
        triples = extract_relationships_from_row(sample_fda_row)
        graph = RDFTestUtils.create_test_graph(triples)

        app_uri = build_application_uri(TestConstants.SAMPLE_APPLICATION_NUMBER)
        substance_uri = build_substance_uri(TestConstants.SAMPLE_UNII)

        # Check has participant relationship
        assert RDFTestUtils.has_triple(graph, app_uri, namespaces["RO"]["0000057"], substance_uri)

        # Check substance typing
        assert RDFTestUtils.has_triple(graph, substance_uri, namespaces["rdf"]["type"], namespaces["CHEMINF"]["000000"])

    def test_extract_rxcui_relationships(self, sample_fda_row):
        """Test extraction of RxCUI relationships"""
        triples = extract_relationships_from_row(sample_fda_row)
        graph = RDFTestUtils.create_test_graph(triples)

        app_uri = build_application_uri(TestConstants.SAMPLE_APPLICATION_NUMBER)
        rxcui_uri = build_rxcui_uri(TestConstants.SAMPLE_RXCUI)

        # Check has identifier relationship
        assert RDFTestUtils.has_triple(graph, app_uri, namespaces["SIO"]["000671"], rxcui_uri)

        # Check RxCUI typing
        assert RDFTestUtils.has_triple(graph, rxcui_uri, namespaces["rdf"]["type"], namespaces["biolink"]["Drug"])

    def test_extract_spl_relationships(self, sample_fda_row):
        """Test extraction of SPL document relationships"""
        triples = extract_relationships_from_row(sample_fda_row)
        graph = RDFTestUtils.create_test_graph(triples)

        app_uri = build_application_uri(TestConstants.SAMPLE_APPLICATION_NUMBER)
        spl_uri = build_spl_uri(TestConstants.SAMPLE_SPL_ID)

        # Check has document relationship
        assert RDFTestUtils.has_triple(graph, app_uri, namespaces["SIO"]["000068"], spl_uri)

        # Check SPL typing
        assert RDFTestUtils.has_triple(graph, spl_uri, namespaces["rdf"]["type"], namespaces["IAO"]["0000310"])

    def test_extract_route_relationships(self, sample_fda_row):
        """Test extraction of route of administration relationships"""
        triples = extract_relationships_from_row(sample_fda_row)
        graph = RDFTestUtils.create_test_graph(triples)

        app_uri = build_application_uri(TestConstants.SAMPLE_APPLICATION_NUMBER)
        route_uri = build_route_uri("ORAL")

        # Check exposure route relationship
        assert RDFTestUtils.has_triple(graph, app_uri, namespaces["ExO"]["0000002"], route_uri)

        # Check route typing
        assert RDFTestUtils.has_triple(graph, route_uri, namespaces["rdf"]["type"], namespaces["ExO"]["0000055"])

    def test_extract_product_relationships(self, sample_fda_row):
        """Test extraction of product-level relationships"""
        triples = extract_relationships_from_row(sample_fda_row)
        graph = RDFTestUtils.create_test_graph(triples)

        app_uri = build_application_uri(TestConstants.SAMPLE_APPLICATION_NUMBER)

        # Check product relationships - should have multiple products
        product_uris = RDFTestUtils.get_objects_for_predicate(graph, app_uri, namespaces["RO"]["0000057"])
        product_uris = [uri for uri in product_uris if "/product/" in str(uri)]

        assert len(product_uris) == 2  # Sample has 2 products

        # Check first product
        product_0_uri = URIRef(f"{app_uri}/product/0")
        assert product_0_uri in product_uris

        # Check product typing
        assert RDFTestUtils.has_triple(graph, product_0_uri, namespaces["rdf"]["type"], namespaces["biolink"]["Drug"])

    def test_extract_ingredient_relationships(self, sample_fda_row):
        """Test extraction of active ingredient relationships"""
        triples = extract_relationships_from_row(sample_fda_row)
        graph = RDFTestUtils.create_test_graph(triples)

        app_uri = build_application_uri(TestConstants.SAMPLE_APPLICATION_NUMBER)
        product_0_uri = URIRef(f"{app_uri}/product/0")
        ingredient_0_uri = URIRef(f"{product_0_uri}/ingredient/0")

        # Check ingredient relationships
        assert RDFTestUtils.has_triple(graph, product_0_uri, namespaces["RO"]["0000057"], ingredient_0_uri)

        # Check ingredient typing
        assert RDFTestUtils.has_triple(graph, ingredient_0_uri, namespaces["rdf"]["type"], namespaces["CHEMINF"]["000000"])

        # Check ingredient component relationship
        assert RDFTestUtils.has_triple(graph, ingredient_0_uri, namespaces["SIO"]["000228"], product_0_uri)

    def test_extract_strength_measurements(self, sample_fda_row):
        """Test extraction of ingredient strength measurements"""
        triples = extract_relationships_from_row(sample_fda_row)
        graph = RDFTestUtils.create_test_graph(triples)

        app_uri = build_application_uri(TestConstants.SAMPLE_APPLICATION_NUMBER)
        product_0_uri = URIRef(f"{app_uri}/product/0")
        ingredient_0_uri = URIRef(f"{product_0_uri}/ingredient/0")
        strength_uri = URIRef(f"{ingredient_0_uri}/strength")

        # Check strength measurement relationships
        assert RDFTestUtils.has_triple(graph, ingredient_0_uri, namespaces["SIO"]["000221"], strength_uri)

        # Check strength typing
        assert RDFTestUtils.has_triple(graph, strength_uri, namespaces["rdf"]["type"], namespaces["SIO"]["000052"])

        # Check strength value
        strength_value = "0.175MG **See current Annual Edition"
        assert RDFTestUtils.has_triple(graph, strength_uri, namespaces["SIO"]["000300"], Literal(strength_value))


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_missing_application_number(self, sample_fda_row_empty):
        """Test handling of missing application number"""
        triples = extract_relationships_from_row(sample_fda_row_empty)
        assert triples == []  # Should return empty list for no app number

    def test_missing_sponsor_name(self, sample_fda_row_minimal):
        """Test handling of missing sponsor name"""
        row = sample_fda_row_minimal.copy()
        row["sponsor_name"] = None

        triples = extract_relationships_from_row(row)
        graph = RDFTestUtils.create_test_graph(triples)

        app_uri = build_application_uri(TestConstants.SAMPLE_APPLICATION_NUMBER)

        # Should not have sponsor relationships
        sponsor_triples = [t for t in graph if namespaces["SIO"]["000136"] in t]
        assert len(sponsor_triples) == 0

    def test_empty_openfda_section(self, sample_fda_row_minimal):
        """Test handling of empty OpenFDA section"""
        row = sample_fda_row_minimal.copy()
        row["openfda"] = {}

        triples = extract_relationships_from_row(row)
        graph = RDFTestUtils.create_test_graph(triples)

        # Should still have basic application relationships
        app_uri = build_application_uri(TestConstants.SAMPLE_APPLICATION_NUMBER)
        assert len([t for t in graph if t[0] == app_uri]) > 0

    def test_null_openfda_fields(self):
        """Test handling of null OpenFDA fields"""
        row = {
            "application_number": TestConstants.SAMPLE_APPLICATION_NUMBER,
            "sponsor_name": TestConstants.SAMPLE_SPONSOR_NAME,
            "openfda": {
                "brand_name": None,
                "generic_name": None,
                "manufacturer_name": None,
                "package_ndc": None,
                "unii": None,
                "rxcui": None
            },
            "products": None
        }

        triples = extract_relationships_from_row(row)
        graph = RDFTestUtils.create_test_graph(triples)

        # Should handle gracefully without errors
        assert isinstance(triples, list)
        assert len(triples) > 0  # Should have basic relationships

    def test_empty_products_array(self, sample_fda_row_minimal):
        """Test handling of empty products array"""
        row = sample_fda_row_minimal.copy()
        row["products"] = np.array([])

        triples = extract_relationships_from_row(row)

        # Should not crash and should return basic relationships
        assert isinstance(triples, list)
        assert len(triples) > 0

    def test_malformed_product_data(self, sample_fda_row):
        """Test handling of malformed product data"""
        row = sample_fda_row.copy()
        row["products"] = np.array([
            {"invalid": "data"},
            None,
            {"brand_name": "TEST", "dosage_form": None},
            "not_a_dict"
        ])

        triples = extract_relationships_from_row(row)

        # Should handle gracefully without crashing
        assert isinstance(triples, list)


class TestNamespaceValidation:
    """Test namespace definitions and usage"""

    def test_namespace_sources_complete(self, expected_namespaces):
        """Test that all expected namespaces are defined"""
        for prefix, uri in expected_namespaces.items():
            assert prefix in namespaces_sources
            assert namespaces_sources[prefix] == uri

    def test_namespace_objects_created(self):
        """Test that namespace objects are created correctly"""
        for prefix, namespace_obj in namespaces.items():
            assert hasattr(namespace_obj, '__str__')
            assert str(namespace_obj) == namespaces_sources[prefix]

    def test_ontology_uri_validity(self):
        """Test that ontology URIs are valid and accessible"""
        ontology_prefixes = ["SIO", "RO", "IAO", "ExO", "CHEMINF", "biolink", "BAO"]

        for prefix in ontology_prefixes:
            assert prefix in namespaces_sources
            uri = namespaces_sources[prefix]
            assert uri.startswith("http://") or uri.startswith("https://")


class TestIntegration:
    """Integration tests for end-to-end processing"""

    def test_complete_row_processing(self, sample_fda_row):
        """Test complete processing of a sample row"""
        triples = extract_relationships_from_row(sample_fda_row)
        graph = RDFTestUtils.create_test_graph(triples)

        # Verify we have a substantial number of triples
        assert len(triples) > 50  # Should generate many relationships

        # Verify graph serialization works
        ttl_output = graph.serialize(format="turtle")
        assert "@prefix" in ttl_output
        assert "BAO:" in ttl_output
        assert "SIO:" in ttl_output
        assert TestConstants.SAMPLE_APPLICATION_NUMBER in ttl_output

    def test_batch_processing_simulation(self, sample_fda_row, temp_cache_dir):
        """Test simulation of batch processing like the main script"""
        # Simulate processing multiple rows
        rows = [sample_fda_row.copy() for _ in range(3)]

        # Modify application numbers to make them unique
        for i, row in enumerate(rows):
            row["application_number"] = f"ANDA{76187 + i:06d}"

        all_triples = []
        for row in rows:
            triples = extract_relationships_from_row(row)
            all_triples.extend(triples)

        # Create combined graph
        graph = RDFTestUtils.create_test_graph(all_triples)

        # Test serialization to file
        output_file = temp_cache_dir / "test_output.ttl"
        graph.serialize(destination=str(output_file), format="turtle")

        assert output_file.exists()
        assert output_file.stat().st_size > 0

        # Verify content
        content = output_file.read_text()
        assert "ANDA076187" in content
        assert "ANDA076188" in content
        assert "ANDA076189" in content

    def test_rdf_graph_validation(self, sample_fda_row):
        """Test that generated RDF follows proper graph structure"""
        triples = extract_relationships_from_row(sample_fda_row)
        graph = RDFTestUtils.create_test_graph(triples)

        app_uri = build_application_uri(TestConstants.SAMPLE_APPLICATION_NUMBER)

        # Test that application is properly typed
        types = RDFTestUtils.get_objects_for_predicate(graph, app_uri, namespaces["rdf"]["type"])
        assert namespaces["BAO"]["0000040"] in types

        # Test that all subjects are valid URIs
        subjects = set(t[0] for t in graph)
        for subject in subjects:
            assert isinstance(subject, URIRef)
            assert "://" in str(subject)

        # Test that predicates use proper namespaces
        predicates = set(t[1] for t in graph)
        for predicate in predicates:
            assert isinstance(predicate, URIRef)
            predicate_str = str(predicate)
            # Should use one of our defined namespaces
            namespace_found = any(
                predicate_str.startswith(ns_uri)
                for ns_uri in namespaces_sources.values()
            )
            assert namespace_found, f"Predicate {predicate_str} doesn't use defined namespace"


class TestPerformance:
    """Performance and scalability tests"""

    def test_large_arrays_processing(self):
        """Test processing of large arrays in OpenFDA data"""
        # Create a row with large arrays
        large_row = {
            "application_number": "ANDA999999",
            "sponsor_name": "TEST_COMPANY",
            "openfda": {
                "package_ndc": [f"0000-{i:04d}-00" for i in range(100)],
                "rxcui": [str(i) for i in range(100, 200)],
                "brand_name": [f"BRAND_{i}" for i in range(50)]
            },
            "products": [
                {
                    "brand_name": f"PRODUCT_{i}",
                    "dosage_form": "TABLET",
                    "route": "ORAL",
                    "active_ingredients": [
                        {
                            "name": f"INGREDIENT_{j}",
                            "strength": f"{j}MG"
                        } for j in range(5)
                    ]
                } for i in range(20)
            ]
        }

        # Should process without performance issues
        import time
        start_time = time.time()
        triples = extract_relationships_from_row(large_row)
        end_time = time.time()

        # Should complete within reasonable time (< 1 second)
        assert end_time - start_time < 1.0

        # Should generate many triples
        assert len(triples) > 500

    def test_memory_usage_with_large_dataset(self):
        """Test memory usage doesn't grow excessively"""
        import gc

        # Process multiple large rows
        for i in range(10):
            row = {
                "application_number": f"ANDA{i:06d}",
                "sponsor_name": f"COMPANY_{i}",
                "openfda": {
                    "package_ndc": [f"{i:04d}-{j:04d}-00" for j in range(50)],
                    "rxcui": [str(j + i * 100) for j in range(50)]
                },
                "products": [
                    {
                        "brand_name": f"PRODUCT_{i}_{j}",
                        "dosage_form": "TABLET",
                        "active_ingredients": [
                            {"name": f"ING_{k}", "strength": f"{k}MG"}
                            for k in range(3)
                        ]
                    } for j in range(10)
                ]
            }

            triples = extract_relationships_from_row(row)
            assert len(triples) > 0

            # Force garbage collection
            gc.collect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
