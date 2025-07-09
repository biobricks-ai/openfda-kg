#!/usr/bin/env python3
"""
Predicate URIs module for OpenFDA knowledge graph construction.

This module provides property-based access to all semantic predicate URIs
used in the OpenFDA knowledge graph, organized by their semantic purpose.
"""

from rdflib import Namespace, URIRef


class Predicates:
    """
    Centralized access to all predicate URIs used in OpenFDA knowledge graph construction.
    
    Properties are organized by their semantic meaning and purpose:
    - Type predicates for RDF typing
    - Relationship predicates for connecting entities
    - Attribute predicates for properties and values
    - Identifier predicates for various ID types
    - Label predicates for names and descriptions
    - Temporal predicates for dates and time-based info
    """
    
    def __init__(self, namespaces: dict):
        """Initialize with namespace dictionary."""
        self._namespaces = namespaces
    
    # =============================================================================
    # TYPE PREDICATES - RDF typing relationships
    # =============================================================================
    
    @property
    def rdf_type(self) -> URIRef:
        """RDF type predicate for entity classification."""
        return self._namespaces["rdf"]["type"]
    
    # =============================================================================
    # CORE RELATIONSHIP PREDICATES - Fundamental entity relationships
    # =============================================================================
    
    @property
    def funds(self) -> URIRef:
        """SIO predicate for sponsorship relationships (SIO:000136)."""
        return self._namespaces["SDDO"]["3000014"]
    
    @property
    def has_manufacturer(self) -> URIRef:
        """RO predicate for manufacturing relationships (RO:0000737)."""
        return self._namespaces["RO"]["0000737"]
    
    @property
    def has_participant(self) -> URIRef:
        """RO predicate for participation relationships (RO:0000057)."""
        return self._namespaces["RO"]["0000057"]
    
    @property
    def is_component_of(self) -> URIRef:
        """SIO predicate for component relationships (SIO:000228)."""
        return self._namespaces["SIO"]["000228"]

    @property
    def ingredient_of(self) -> URIRef:
        """SIO predicate for ingredient relationships (AFX:000228)."""
        return self._namespaces["afx"]["0002845"]
    
    @property
    def has_exposure_route(self) -> URIRef:
        """ExO predicate for exposure route relationships (ExO:0000002)."""
        return self._namespaces["RO"]["0002242"]
    
    # =============================================================================
    # ATTRIBUTE PREDICATES - Properties and characteristics
    # =============================================================================
    
    @property
    def has_attribute(self) -> URIRef:
        """SIO predicate for general attributes (SIO:000008)."""
        return self._namespaces["SIO"]["000008"]
    
    @property
    def has_classification(self) -> URIRef:
        """SIO predicate for classification relationships (SIO:000332)."""
        return self._namespaces["SIO"]["000332"]
    
    @property
    def has_status(self) -> URIRef:
        """OPMI predicate for status attributes (OPMI:0000622)."""
        return self._namespaces["opmi"]["0000622"]

    @property
    def has_value(self) -> URIRef:
        """SIO predicate for value attributes (SIO:000300) - alias for has_status."""
        return self._namespaces["SIO"]["000300"]
    
    @property
    def has_measurement_value(self) -> URIRef:
        """SIO predicate for measurement values (SIO:000216)."""
        return self._namespaces["SIO"]["000216"]
    
    @property
    def refers_to(self) -> URIRef:
        """SIO predicate for reference relationships (SIO:000628)."""
        return self._namespaces["SIO"]["000628"]
    
    # =============================================================================
    # IDENTIFIER PREDICATES - Various ID and identifier relationships
    # =============================================================================
    
    @property
    def has_identifier(self) -> URIRef:
        """SIO predicate for identifier relationships (SIO:000671)."""
        return self._namespaces["SIO"]["000671"]
    
    # TODO: incorrect URI
    @property
    def identifier(self) -> URIRef:
        """Dublin Core terms identifier (dcterms:identifier)."""
        return self._namespaces["dcterms"]["identifier"]
    
    
    @property
    def dc_type(self) -> URIRef:
        """Dublin Core terms type (dcterms:type)."""
        return self._namespaces["dcterms"]["type"]
    
    # =============================================================================
    # LABEL PREDICATES - Names, labels, and descriptions
    # =============================================================================
    
    @property
    def rdfs_label(self) -> URIRef:
        """RDFS label for entity names (rdfs:label)."""
        return self._namespaces["rdfs"]["label"]
    
    @property
    def preferred_label(self) -> URIRef:
        """SKOS preferred label (skos:prefLabel)."""
        return self._namespaces["skos"]["prefLabel"]
    
    @property
    def alternative_label(self) -> URIRef:
        """SKOS alternative label (skos:altLabel)."""
        return self._namespaces["skos"]["altLabel"]
    
    @property
    def biolink_name(self) -> URIRef:
        """Biolink name predicate (biolink:name)."""
        return self._namespaces["biolink"]["name"]
    
    @property
    def dc_title(self) -> URIRef:
        """Dublin Core terms title (dcterms:title)."""
        return self._namespaces["dcterms"]["title"]
    
    # =============================================================================
    # TEMPORAL PREDICATES - Date and time-related relationships
    # =============================================================================
    
    @property
    def created(self) -> URIRef:
        """Dublin Core terms creation date (dcterms:created)."""
        return self._namespaces["dcterms"]["created"]
    
    @property
    def modified(self) -> URIRef:
        """Dublin Core terms modification date (dcterms:modified)."""
        return self._namespaces["dcterms"]["modified"]
    
    @property
    def valid(self) -> URIRef:
        """Dublin Core terms validity period (dcterms:valid)."""
        return self._namespaces["dcterms"]["valid"]
    
    @property
    def issued(self) -> URIRef:
        """Dublin Core terms issue date (dcterms:issued)."""
        return self._namespaces["dcterms"]["issued"]
    
    @property
    def rights(self) -> URIRef:
        """Dublin Core terms rights (dcterms:rights)."""
        return self._namespaces["dcterms"]["rights"]


# =============================================================================
# CONVENIENCE CLASSES FOR SPECIFIC ENTITY TYPES
# =============================================================================

class EntityTypes:
    """Commonly used entity type URIs."""
    
    def __init__(self, namespaces: dict):
        """Initialize with namespace dictionary."""
        self._namespaces = namespaces
    
    # Organizations and companies
    @property
    def organization(self) -> URIRef:
        """SIO organization type (SIO:000012)."""
        return self._namespaces["SIO"]["000012"]
    
    # Chemical and pharmaceutical entities
    @property
    def chemical_entity(self) -> URIRef:
        """CHEMINF chemical entity type (CHEMINF:000000)."""
        return self._namespaces["CHEMINF"]["000000"]
    
    @property
    def drug(self) -> URIRef:
        """Biolink drug type (biolink:Drug)."""
        return self._namespaces["biolink"]["Drug"]
    
    @property
    def dosage_form(self) -> URIRef:
        """SIO dosage form type (SIO:000614)."""
        return self._namespaces["SIO"]["000614"]
    
    @property
    def measurement_value(self) -> URIRef:
        """SIO measurement value type (SIO:000052)."""
        return self._namespaces["SIO"]["000052"]
    
    # Identifiers and documents
    @property
    def centrally_registered_identifier(self) -> URIRef:
        """IAO centrally registered identifier type (IAO:0000578)."""
        return self._namespaces["IAO"]["0000578"]
    
    @property
    def document(self) -> URIRef:
        """IAO document type (IAO:0000310)."""
        return self._namespaces["IAO"]["0000310"]
    
    # Routes and bioassays
    @property
    def route_of_administration(self) -> URIRef:
        """ExO route of administration type (ExO:0000055)."""
        return self._namespaces["ExO"]["0000055"]
    
    @property
    def bioassay(self) -> URIRef:
        """BAO bioassay type (BAO:0000040)."""
        return self._namespaces["BAO"]["0000040"]


def create_predicates(namespaces: dict) -> Predicates:
    """Factory function to create Predicates instance with namespace dictionary."""
    return Predicates(namespaces)


def create_entity_types(namespaces: dict) -> EntityTypes:
    """Factory function to create EntityTypes instance with namespace dictionary."""
    return EntityTypes(namespaces) 