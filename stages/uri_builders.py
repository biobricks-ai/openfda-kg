#!/usr/bin/env python3
"""
URI Builders module for OpenFDA knowledge graph construction.

This module provides centralized URI building functionality for all entities
in the OpenFDA knowledge graph, organized by entity type and purpose.
"""

from urllib.parse import quote
from rdflib import URIRef


class URIBuilders:
    """
    Centralized URI building functionality for OpenFDA knowledge graph entities.
    
    Provides semantic methods for building URIs for different entity types:
    - FDA applications and submissions
    - Companies and organizations
    - Chemical substances and ingredients
    - Drug products and identifiers
    - Documents and labels
    - Routes and dosage forms
    - Nested entities (products, ingredients, measurements)
    """
    
    def __init__(self, namespaces: dict):
        """Initialize with namespace dictionary."""
        self._namespaces = namespaces
    
    # =============================================================================
    # FDA ADMINISTRATIVE ENTITIES - Applications, companies, submissions
    # =============================================================================
    
    def build_application_uri(self, app_number: str) -> URIRef:
        """Build URI for FDA application number using SIO chemical entity."""
        return URIRef(self._namespaces["fda"] + f"openfda.application_number:{quote(app_number, safe='')}")
    
    def build_sponsor_uri(self, sponsor_name: str) -> URIRef:
        """Build URI for sponsor organization using company namespace."""
        clean_name = sponsor_name.replace(" ", "_").replace(",", "").replace(".", "")
        return URIRef(self._namespaces["company"] + f"sponsor/{quote(clean_name, safe='')}")
    
    def build_manufacturer_uri(self, manufacturer_name: str) -> URIRef:
        """Build URI for manufacturer organization using company namespace."""
        clean_name = manufacturer_name.replace(" ", "_").replace(",", "").replace(".", "")
        return URIRef(self._namespaces["company"] + f"manufacturer/{quote(clean_name, safe='')}")
        
    # =============================================================================
    # SUBMISSION ENTITIES - Submissions, documents, statuses  
    # =============================================================================
    
    def build_submission_uri(self, app_uri: URIRef, submission_number: str) -> URIRef:
        """Build URI for FDA submission within an application."""
        return URIRef(f"{app_uri}/submission/{submission_number}")
    
    def build_submission_type_uri(self, submission_type: str) -> URIRef:
        """Build URI for submission type classification."""
        clean_type = submission_type.replace(" ", "_").replace(",", "").upper()
        return URIRef(self._namespaces["fda"] + f"submission_type/{quote(clean_type, safe='')}")
    
    def build_submission_status_uri(self, submission_status: str) -> URIRef:
        """Build URI for submission status classification."""
        clean_status = submission_status.replace(" ", "_").replace(",", "").upper()
        return URIRef(self._namespaces["fda"] + f"submission_status/{quote(clean_status, safe='')}")
    
    def build_submission_class_code_uri(self, class_code: str) -> URIRef:
        """Build URI for submission class code."""
        clean_code = class_code.replace(" ", "_").replace("(", "").replace(")", "").upper()
        return URIRef(self._namespaces["fda"] + f"submission_class/{quote(clean_code, safe='')}")
    
    def build_review_priority_uri(self, priority: str) -> URIRef:
        """Build URI for review priority classification."""
        clean_priority = priority.replace(" ", "_").upper()
        return URIRef(self._namespaces["fda"] + f"review_priority/{quote(clean_priority, safe='')}")
    
    def build_application_document_uri(self, submission_uri: URIRef, doc_id: str) -> URIRef:
        """Build URI for application document within a submission."""
        return URIRef(f"{submission_uri}/document/{doc_id}")
    
    def build_document_type_uri(self, doc_type: str) -> URIRef:
        """Build URI for document type classification."""
        clean_type = doc_type.replace(" ", "_").upper()
        return URIRef(self._namespaces["fda"] + f"document_type/{quote(clean_type, safe='')}")
    
    def build_submission_property_type_uri(self, property_type: str) -> URIRef:
        """Build URI for submission property type (e.g., Orphan designation)."""
        clean_type = property_type.replace(" ", "_").upper()
        return URIRef(self._namespaces["fda"] + f"submission_property_type/{quote(clean_type, safe='')}")
    
    def build_submission_public_notes_uri(self, app_uri: URIRef, note_hash: str) -> URIRef:
        """Build URI for submission public notes using hash for uniqueness."""
        return URIRef(f"{app_uri}/public_note/{note_hash}")
    
    def build_document_date_uri(self, document_uri: URIRef) -> URIRef:
        """Build URI for document date associated with a document."""
        return URIRef(f"{document_uri}/date")
    
    def build_document_url_uri(self, document_uri: URIRef) -> URIRef:
        """Build URI for document URL associated with a document."""
        return URIRef(f"{document_uri}/url")
    
    def build_submission_status_date_uri(self, submission_uri: URIRef) -> URIRef:
        """Build URI for submission status date."""
        return URIRef(f"{submission_uri}/status_date")
    
    def build_submission_number_uri(self, app_uri: URIRef, submission_number: str) -> URIRef:
        """Build URI for submission number within an application."""
        return URIRef(f"{app_uri}/submission_number/{submission_number}")
    
    def build_document_title_uri(self, document_uri: URIRef) -> URIRef:
        """Build URI for document title."""
        return URIRef(f"{document_uri}/title")
    
    def build_document_id_uri(self, submission_uri: URIRef, doc_id: str) -> URIRef:
        """Build URI for document ID within a submission."""
        return URIRef(f"{submission_uri}/document_id/{doc_id}")
        
    # =============================================================================
    # CHEMICAL ENTITIES - Substances, ingredients, drugs
    # =============================================================================
    
    def build_substance_uri(self, unii: str) -> URIRef:
        """Build URI for substance using UNII - represents a chemical substance."""
        return URIRef(self._namespaces["unii"] + unii)
    
    def build_ingredient_uri(self, ingredient_name: str) -> URIRef:
        """Build URI for active ingredient using CHEMINF chemical information ontology."""
        clean_name = ingredient_name.replace(" ", "_").replace(",", "").replace(".", "")
        return URIRef(self._namespaces["CHEMINF"] + f"ingredient/{quote(clean_name, safe='')}")
    
    def build_drug_uri(self, drug_name: str) -> URIRef:
        """Build URI for drug entity using biolink namespace."""
        clean_name = drug_name.replace(" ", "_").replace(",", "").replace(".", "")
        return URIRef(self._namespaces["biolink"] + f"drug/{quote(clean_name, safe='')}")
    
    # =============================================================================
    # PRODUCT IDENTIFIERS - NDC, RxCUI, SPL codes, NUI, brand/generic names
    # =============================================================================
    
    def build_ndc_uri(self, ndc: str) -> URIRef:
        """Build URI for NDC code - represents a drug product identifier."""
        return URIRef(self._namespaces["ndc"] + ndc)
    
    def build_package_ndc_uri(self, ndc: str) -> URIRef:
        """Build URI for package NDC code (alias for ndc_uri)."""
        return self.build_ndc_uri(ndc)
    
    def build_product_ndc_uri(self, ndc: str) -> URIRef:
        """Build URI for product NDC code (alias for ndc_uri)."""
        return self.build_ndc_uri(ndc)
    
    def build_rxcui_uri(self, rxcui: str) -> URIRef:
        """Build URI for RxCUI - represents a clinical drug concept."""
        return URIRef(self._namespaces["rxcui"] + rxcui)
    
    def build_spl_uri(self, spl_id: str) -> URIRef:
        """Build URI for SPL ID - structured product labeling identifier."""
        return URIRef(self._namespaces["spl"] + spl_id)
    
    def build_nui_uri(self, nui: str) -> URIRef:
        """Build URI for NUI (National Drug Code Directory Number) identifier."""
        return URIRef(self._namespaces["ndc"] + f"nui/{nui}")
    
    def build_brand_name_uri(self, brand_name: str) -> URIRef:
        """Build URI for brand name using biolink drug entity."""
        clean_name = brand_name.replace(" ", "_").replace(",", "").replace(".", "")
        return URIRef(self._namespaces["biolink"] + f"brand_name/{quote(clean_name, safe='')}")
    
    def build_generic_name_uri(self, generic_name: str) -> URIRef:
        """Build URI for generic name using biolink drug entity."""
        clean_name = generic_name.replace(" ", "_").replace(",", "").replace(".", "")
        return URIRef(self._namespaces["biolink"] + f"generic_name/{quote(clean_name, safe='')}")
    
    # =============================================================================
    # PHARMACEUTICAL CLASSIFICATION - Pharm classes, mechanisms of action
    # =============================================================================
    
    def build_pharm_class_cs_uri(self, pharm_class: str) -> URIRef:
        """Build URI for chemical structure-based pharmaceutical class."""
        clean_class = pharm_class.replace(" ", "_").replace(",", "").replace("[", "").replace("]", "")
        return URIRef(self._namespaces["fda"] + f"pharm_class_cs/{quote(clean_class, safe='')}")
    
    def build_pharm_class_epc_uri(self, pharm_class: str) -> URIRef:
        """Build URI for established pharmacologic class."""
        clean_class = pharm_class.replace(" ", "_").replace(",", "").replace("[", "").replace("]", "")
        return URIRef(self._namespaces["fda"] + f"pharm_class_epc/{quote(clean_class, safe='')}")
    
    def build_pharm_class_moa_uri(self, pharm_class: str) -> URIRef:
        """Build URI for mechanism of action pharmaceutical class."""
        clean_class = pharm_class.replace(" ", "_").replace(",", "").replace("[", "").replace("]", "")
        return URIRef(self._namespaces["fda"] + f"pharm_class_moa/{quote(clean_class, safe='')}")
    
    def build_pharm_class_pe_uri(self, pharm_class: str) -> URIRef:
        """Build URI for physiologic effect pharmaceutical class."""
        clean_class = pharm_class.replace(" ", "_").replace(",", "").replace("[", "").replace("]", "")
        return URIRef(self._namespaces["fda"] + f"pharm_class_pe/{quote(clean_class, safe='')}")
    
    # =============================================================================
    # PHARMACEUTICAL PROPERTIES - Dosage forms, routes, categories
    # =============================================================================
    
    def build_dosage_form_uri(self, dosage_form: str) -> URIRef:
        """Build URI for dosage form using pharmaceutical ontology concepts."""
        clean_form = dosage_form.replace(" ", "_").replace(",", "").upper()
        return URIRef(self._namespaces["fda"] + f"products.dosage_form:{quote(clean_form, safe='')}")
    
    def build_route_uri(self, route: str) -> URIRef:
        """Build URI for administration route using ExO (Exposure Ontology)."""
        clean_route = route.replace(" ", "_").replace(",", "").upper()
        return URIRef(self._namespaces["ExO"] + f"route/{quote(clean_route, safe='')}")
    
    def build_marketing_category_uri(self, category: str) -> URIRef:
        """Build URI for marketing category."""
        clean_category = category.replace(" ", "_").replace(",", "").upper()
        return URIRef(self._namespaces["fda"] + f"products.marketing_status:{quote(clean_category, safe='')}")
    
    def build_marketing_status_uri(self, status: str) -> URIRef:
        """Build URI for marketing status."""
        clean_status = status.replace(" ", "_").replace(",", "").upper()
        return URIRef(self._namespaces["fda"] + f"marketing_status/{quote(clean_status, safe='')}")
    
    def build_product_type_uri(self, product_type: str) -> URIRef:
        """Build URI for product type."""
        clean_type = product_type.replace(" ", "_").replace(",", "").upper()
        return URIRef(self._namespaces["fda"] + f"openfda.product_type:{quote(clean_type, safe='')}")
    
    # =============================================================================
    # PRODUCT ATTRIBUTES - Product numbers, reference standards, TE codes
    # =============================================================================
    
    def build_product_number_uri(self, app_uri: URIRef, product_number: str) -> URIRef:
        """Build URI for product number within an application."""
        return URIRef(f"{app_uri}/product_number/{product_number}")
    
    def build_te_code_uri(self, te_code: str) -> URIRef:
        """Build URI for Therapeutic Equivalence (TE) code."""
        clean_code = te_code.replace(" ", "_").upper()
        return URIRef(self._namespaces["fda"] + f"te_code/{quote(clean_code, safe='')}")
    
    def build_reference_drug_uri(self, reference_status: str) -> URIRef:
        """Build URI for reference drug status."""
        clean_status = reference_status.replace(" ", "_").upper()
        return URIRef(self._namespaces["fda"] + f"reference_drug/{quote(clean_status, safe='')}")
    
    def build_reference_standard_uri(self, reference_status: str) -> URIRef:
        """Build URI for reference standard status."""
        clean_status = reference_status.replace(" ", "_").upper()
        return URIRef(self._namespaces["fda"] + f"reference_standard/{quote(clean_status, safe='')}")
    
    # =============================================================================
    # NSDE SPECIFIC ENTITIES - Proprietary names and specialized identifiers
    # =============================================================================
    
    def build_proprietary_name_uri(self, proprietary_name: str) -> URIRef:
        """Build URI for proprietary drug name."""
        clean_name = proprietary_name.replace(" ", "_").replace(",", "").replace(".", "")
        return URIRef(self._namespaces["fda"] + f"results.proprietary_name:{quote(clean_name, safe='')}")
    
    # =============================================================================
    # NESTED ENTITIES - Products, ingredients, measurements within applications
    # =============================================================================
    
    def build_product_uri(self, app_uri: URIRef, product_index: int) -> URIRef:
        """Build URI for a product within an application."""
        return URIRef(f"{app_uri}/product/{product_index}")
    
    def build_ingredient_uri_nested(self, product_uri: URIRef, ingredient_index: int) -> URIRef:
        """Build URI for an ingredient within a product."""
        return URIRef(f"{product_uri}/ingredient/{ingredient_index}")
    
    def build_strength_uri(self, ingredient_uri: URIRef) -> URIRef:
        """Build URI for strength measurement of an ingredient."""
        return URIRef(f"{ingredient_uri}/strength")
    
    def build_measurement_uri(self, entity_uri: URIRef, measurement_type: str) -> URIRef:
        """Build URI for any measurement associated with an entity."""
        return URIRef(f"{entity_uri}/{measurement_type}")
    
    # =============================================================================
    # CONVENIENCE METHODS - Common entity combinations
    # =============================================================================
    
    def build_application_product_uri(self, app_number: str, product_index: int) -> URIRef:
        """Build URI for a product within an application (convenience method)."""
        app_uri = self.build_application_uri(app_number)
        return self.build_product_uri(app_uri, product_index)
    
    def build_application_ingredient_uri(self, app_number: str, product_index: int, ingredient_index: int) -> URIRef:
        """Build URI for an ingredient within an application product (convenience method)."""
        product_uri = self.build_application_product_uri(app_number, product_index)
        return self.build_ingredient_uri_nested(product_uri, ingredient_index)
    
    def build_application_submission_uri(self, app_number: str, submission_number: str) -> URIRef:
        """Build URI for a submission within an application (convenience method)."""
        app_uri = self.build_application_uri(app_number)
        return self.build_submission_uri(app_uri, submission_number)
    
    # =============================================================================
    # VALIDATION AND UTILITY METHODS
    # =============================================================================
    
    def validate_uri(self, uri: URIRef, expected_base: str) -> bool:
        """Validate that a URI has the expected base."""
        return str(uri).startswith(expected_base)
    
    def extract_identifier_from_uri(self, uri: URIRef, base_namespace: str) -> str:
        """Extract the identifier portion from a URI."""
        uri_str = str(uri)
        if uri_str.startswith(base_namespace):
            return uri_str[len(base_namespace):]
        return ""
    
    def get_uri_type(self, uri: URIRef) -> str:
        """Determine the type of entity based on URI structure."""
        uri_str = str(uri)
        
        if "/application/" in uri_str:
            return "application"
        elif "/company/" in uri_str or self._namespaces["company"] in uri_str:
            return "company"
        elif "/sponsor/" in uri_str:
            return "sponsor"
        elif "/manufacturer/" in uri_str:
            return "manufacturer"
        elif "/submission/" in uri_str:
            return "submission"
        elif "/unii/" in uri_str or self._namespaces["unii"] in uri_str:
            return "substance"
        elif "/ndc/" in uri_str or self._namespaces["ndc"] in uri_str:
            return "ndc"
        elif "/nui/" in uri_str:
            return "nui"
        elif "/rxcui/" in uri_str or self._namespaces["rxcui"] in uri_str:
            return "rxcui"
        elif "/spl/" in uri_str or self._namespaces["spl"] in uri_str:
            return "spl"
        elif "/dosage_form/" in uri_str:
            return "dosage_form"
        elif "/route/" in uri_str:
            return "route"
        elif "/proprietary/" in uri_str:
            return "proprietary"
        elif "/product/" in uri_str:
            return "product"
        elif "/ingredient/" in uri_str:
            return "ingredient"
        elif "/strength" in uri_str:
            return "strength"
        elif "/pharm_class_" in uri_str:
            return "pharm_class"
        elif "/te_code/" in uri_str:
            return "te_code"
        elif "/reference_" in uri_str:
            return "reference"
        elif "/brand_name/" in uri_str:
            return "brand_name"
        elif "/generic_name/" in uri_str:
            return "generic_name"
        else:
            return "unknown"


# =============================================================================
# SPECIALIZED BUILDERS FOR DIFFERENT PROCESSING MODULES
# =============================================================================

class OpenFDAURIBuilders(URIBuilders):
    """URI builders specialized for OpenFDA drug application processing."""
    pass


class NSDEURIBuilders(URIBuilders):
    """URI builders specialized for NSDE (National Drug Code Directory) processing."""
    
    def build_ndc11_uri(self, ndc11: str) -> URIRef:
        """Build URI for 11-digit NDC code format."""
        return self.build_ndc_uri(ndc11)
    
    def build_proprietary_name_uri(self, proprietary_name: str) -> URIRef:
        """Build URI for proprietary name using biolink drug entity."""
        clean_name = proprietary_name.replace(" ", "_").replace(",", "").replace(".", "").replace("&", "and")
        return URIRef(self._namespaces["nsde"] + f"proprietary_name/{quote(clean_name, safe='')}")
    
    def build_nsde_application_uri(self, app_number: str) -> URIRef:
        """Build URI for FDA application number using IAO identifier in NSDE context."""
        return URIRef(self._namespaces["fda"] + f"application/{quote(app_number, safe='')}")
    
    def build_nsde_dosage_form_uri(self, dosage_form: str) -> URIRef:
        """Build URI for dosage form using SIO pharmaceutical concepts in NSDE context."""
        clean_form = dosage_form.replace(" ", "_").replace(",", "").upper()
        return URIRef(self._namespaces["nsde"] + f"dosage_form/{quote(clean_form, safe='')}")
    
    def build_nsde_marketing_category_uri(self, category: str) -> URIRef:
        """Build URI for marketing category using SIO organization concepts."""
        clean_category = category.replace(" ", "_").replace(",", "").upper()
        return URIRef(self._namespaces["nsde"] + f"marketing_category/{quote(clean_category, safe='')}")
    
    def build_nsde_product_type_uri(self, product_type: str) -> URIRef:
        """Build URI for product type using SIO classification concepts."""
        clean_type = product_type.replace(" ", "_").replace(",", "").upper()
        return URIRef(self._namespaces["nsde"] + f"product_type/{quote(clean_type, safe='')}")


def create_uri_builders(namespaces: dict, builder_type: str = "general") -> URIBuilders:
    """
    Factory function to create appropriate URI builders instance.
    
    Args:
        namespaces: Dictionary of namespace mappings
        builder_type: Type of builder to create ("general", "openfda", "nsde")
    
    Returns:
        URIBuilders instance of the appropriate type
    """
    if builder_type.lower() == "openfda":
        return OpenFDAURIBuilders(namespaces)
    elif builder_type.lower() == "nsde":
        return NSDEURIBuilders(namespaces)
    else:
        return URIBuilders(namespaces)


def create_openfda_uri_builders(namespaces: dict) -> OpenFDAURIBuilders:
    """Factory function to create OpenFDA URI builders instance."""
    return OpenFDAURIBuilders(namespaces)


def create_nsde_uri_builders(namespaces: dict) -> NSDEURIBuilders:
    """Factory function to create NSDE URI builders instance."""
    return NSDEURIBuilders(namespaces) 