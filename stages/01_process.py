#!/usr/bin/env python3

import json
import pathlib
import sys
from urllib.parse import quote

import biobricks as bb
import numpy as np
import pyarrow.parquet as pq
from rdflib import Graph, Literal, Namespace, URIRef
from tqdm import tqdm

# Add the current directory to Python path to import modules
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from predicates import create_predicates, create_entity_types
from uri_builders import create_openfda_uri_builders

tqdm.pandas()

# cachedir for ttl files
cachedir = pathlib.Path("cache/process")
cachedir.mkdir(parents=True, exist_ok=True)

# outdir should be brick (hdt file only)
outdir = pathlib.Path("./brick")
outdir.mkdir(parents=True, exist_ok=True)

# Define namespaces for OpenFDA data
namespaces_sources = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "fda": "https://api.fda.gov/drug/drugsfda.json?search=",  # FDA drug applications
    "ndc": "https://www.fda.gov/industry/structured-product-labeling-resources/ndc-directory/",  # NDC codes
    "unii": "https://fdasis.nlm.nih.gov/srs/unii/",  # UNII substance identifiers
    "rxcui": "https://mor.nlm.nih.gov/RxNav/search?searchBy=RXCUI&searchTerm=",  # RxNorm concept IDs
    "spl": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=",  # SPL set IDs
    "company": "https://api.fda.gov/drug/company/",  # Drug companies/sponsors
    "ofrel": "https://api.fda.gov/drug/relationship/",  # FDA relationship predicates
    "BAO": "http://www.bioassayontology.org/bao#BAO_",
    "CAS": "http://identifiers.org/cas/",
    "CHEMINF": "http://purl.obolibrary.org/obo/CHEMINF_",
    "SIO": "http://semanticscience.org/resource/SIO_",
    "OBI": "http://purl.obolibrary.org/obo/OBI_",
    "IAO": "http://purl.obolibrary.org/obo/IAO_",
    "RO": "http://purl.obolibrary.org/obo/RO_",
    "ExO": "http://purl.obolibrary.org/obo/ExO_",
    "SDDO": "ttp://purl.obolibrary.org/obo/SDDO_",
    "EDAM": "http://edamontology.org/",
    "afx": "http://purl.allotrope.org/ontologies/property#AFX_",
    "dce": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "puml": "http://plantuml.com/ontology#",
    "ncim": "https://identifiers.org/umls:",
    "iceprop": "https://ice.ntp.niehs.nih.gov/property/",
    "invitrodb": "https://comptox.epa.gov/property/",
    "ncbigene": "https://www.ncbi.nlm.nih.gov/gene/",
    "biolink": "https://w3id.org/biolink/vocab/",
    "opmi": "http://purl.obolibrary.org/obo/OPMI_"
}

namespaces = {key: Namespace(val) for key, val in namespaces_sources.items()}

# Initialize predicate, entity type, and URI builder helpers
predicates = create_predicates(namespaces)
entity_types = create_entity_types(namespaces)
uri_builders = create_openfda_uri_builders(namespaces)


# URI building functions are now handled by the uri_builders module


def safe_get_array_items(arr):
    """Safely extract items from numpy array, handling None and various data types."""
    if arr is None:
        return []
    if isinstance(arr, np.ndarray):
        return [str(item) for item in arr if item is not None]
    if isinstance(arr, list | tuple):
        return [str(item) for item in arr if item is not None]
    return [str(arr)] if arr is not None else []


# ---------------------------------------------------------------------------
# Extract relationships from FDA data
# ---------------------------------------------------------------------------
def extract_relationships_from_row(row):
    """Extract RDF triples from a single FDA drug application row."""
    triples = []

    app_number = row["application_number"]
    sponsor_name = row["sponsor_name"]

    if not app_number:
        return triples

    app_uri = uri_builders.build_application_uri(app_number)

    # Application -> Sponsor relationship using semantic predicates
    if sponsor_name:
        sponsor_uri = uri_builders.build_sponsor_uri(sponsor_name)
        # Use SIO relationships for sponsorship and organization typing
        triples.append(
            (sponsor_uri, predicates.funds, app_uri)
        )  # SIO:is sponsored by
        triples.append(
            (sponsor_uri, predicates.rdf_type, entity_types.organization)
        )  # SIO:organization
        triples.append(
            (sponsor_uri, predicates.rdfs_label, Literal(sponsor_name))
        )
        triples.append(
            (sponsor_uri, predicates.dc_title, Literal(sponsor_name))
        )

    # Process OpenFDA standardized data
    openfda = row.get("openfda")
    if openfda and isinstance(openfda, dict):

        # Brand names using SKOS preferred label and SIO terminology
        brand_names = safe_get_array_items(openfda.get("brand_name"))
        for brand_name in brand_names:
            triples.append(
                (app_uri, predicates.preferred_label, Literal(brand_name))
            )
            triples.append(
                (app_uri, predicates.has_attribute, Literal(brand_name))
            )  # SIO:has attribute (brand name)

        # Generic names using alternative labels and biolink naming
        generic_names = safe_get_array_items(openfda.get("generic_name"))
        for generic_name in generic_names:
            triples.append(
                (app_uri, predicates.alternative_label, Literal(generic_name))
            )
            triples.append(
                (app_uri, predicates.biolink_name, Literal(generic_name))
            )

        # Manufacturer names using RO (Relations Ontology) and SIO
        manufacturer_names = safe_get_array_items(openfda.get("manufacturer_name"))
        for mfg_name in manufacturer_names:
            mfg_uri = uri_builders.build_manufacturer_uri(mfg_name)
            triples.append(
                (app_uri, predicates.has_manufacturer, mfg_uri)
            )  # RO:manufactured by
            triples.append(
                (mfg_uri, predicates.rdf_type, entity_types.organization)
            )  # SIO:organization
            triples.append((mfg_uri, predicates.rdfs_label, Literal(mfg_name)))
            triples.append((mfg_uri, predicates.dc_title, Literal(mfg_name)))

        # NDC codes using SIO identifiers and IAO information artifacts
        package_ndcs = safe_get_array_items(openfda.get("package_ndc"))
        for ndc in package_ndcs:
            ndc_uri = uri_builders.build_package_ndc_uri(ndc)
            triples.append(
                (app_uri, predicates.has_identifier, ndc_uri)
            )  # SIO:has identifier
            triples.append(
                (ndc_uri, predicates.rdf_type, entity_types.centrally_registered_identifier)
            )  # IAO:centrally registered identifier
            triples.append(
                (ndc_uri, predicates.dc_type, Literal("package_ndc"))
            )

        product_ndcs = safe_get_array_items(openfda.get("product_ndc"))
        for ndc in product_ndcs:
            ndc_uri = uri_builders.build_product_ndc_uri(ndc)
            triples.append(
                (app_uri, predicates.has_identifier, ndc_uri)
            )  # SIO:has identifier
            triples.append(
                (ndc_uri, predicates.rdf_type, entity_types.centrally_registered_identifier)
            )  # IAO:centrally registered identifier
            triples.append(
                (ndc_uri, predicates.dc_type, Literal("product_ndc"))
            )

        # UNII codes for substances using CHEMINF chemical information
        uniis = safe_get_array_items(openfda.get("unii"))
        for unii in uniis:
            substance_uri = uri_builders.build_substance_uri(unii)
            triples.append(
                (app_uri, predicates.has_participant, substance_uri)
            )  # RO:has participant (contains substance)
            triples.append(
                (
                    substance_uri,
                    predicates.rdf_type,
                    entity_types.chemical_entity,
                )
            )  # CHEMINF:chemical entity

        # RxCUI codes using biolink and SIO identifiers
        rxcuis = safe_get_array_items(openfda.get("rxcui"))
        for rxcui in rxcuis:
            rxcui_uri = uri_builders.build_rxcui_uri(rxcui)
            triples.append(
                (app_uri, predicates.has_identifier, rxcui_uri)
            )  # SIO:has identifier
            triples.append(
                (rxcui_uri, predicates.rdf_type, entity_types.drug)
            )
            triples.append((rxcui_uri, predicates.dc_type, Literal("rxcui")))

        # SPL IDs using IAO document identifiers
        spl_set_ids = safe_get_array_items(openfda.get("spl_set_id"))
        for spl_id in spl_set_ids:
            spl_uri = uri_builders.build_spl_uri(spl_id)
            triples.append(
                (app_uri, predicates.has_document, spl_uri)
            )  # SIO:has document
            triples.append(
                (spl_uri, predicates.rdf_type, entity_types.document)
            )  # IAO:document
            triples.append(
                (
                    spl_uri,
                    predicates.dc_type,
                    Literal("structured_product_label"),
                )
            )

        # Routes of administration using ExO exposure routes
        routes = safe_get_array_items(openfda.get("route"))
        for route in routes:
            route_uri = uri_builders.build_route_uri(route)
            triples.append(
                (app_uri, predicates.has_exposure_route, route_uri)
            )  # ExO:has exposure route
            triples.append(
                (route_uri, predicates.rdf_type, entity_types.route_of_administration)
            )  # ExO:route of administration
            triples.append((route_uri, predicates.rdfs_label, Literal(route)))

        # Product types using SIO classification
        product_types = safe_get_array_items(openfda.get("product_type"))
        for prod_type in product_types:
            triples.append(
                (app_uri, predicates.has_classification, Literal(prod_type))
            )  # SIO:has classification
            triples.append((app_uri, predicates.dc_type, Literal(prod_type)))

        # Substance names using CHEMINF and biolink
        substance_names = safe_get_array_items(openfda.get("substance_name"))
        for substance_name in substance_names:
            substance_name_uri = uri_builders.build_ingredient_uri(substance_name)
            triples.append(
                (app_uri, predicates.has_participant, substance_name_uri)
            )  # RO:has participant
            triples.append(
                (
                    substance_name_uri,
                    predicates.rdf_type,
                    entity_types.chemical_entity,
                )
            )  # CHEMINF:chemical entity
            triples.append(
                (
                    substance_name_uri,
                    predicates.rdfs_label,
                    Literal(substance_name),
                )
            )
            triples.append(
                (
                    substance_name_uri,
                    predicates.biolink_name,
                    Literal(substance_name),
                )
            )

    # Process products array using pharmaceutical and chemical ontologies
    products = row.get("products")
    if products is not None:
        # Handle both numpy arrays (from pandas/parquet) and regular Python lists (from tests)
        if isinstance(products, np.ndarray):
            products_list = products
        elif isinstance(products, list | tuple):
            products_list = products
        else:
            products_list = []

        for i, product in enumerate(products_list):
            if isinstance(product, dict):
                product_uri = uri_builders.build_product_uri(app_uri, i)
                triples.append(
                    (app_uri, predicates.has_participant, product_uri)
                )  # RO:has participant
                triples.append(
                    (
                        product_uri,
                        predicates.rdf_type,
                        entity_types.drug,
                    )
                )

                # Product properties using semantic predicates
                if product.get("brand_name"):
                    triples.append(
                        (
                            product_uri,
                            predicates.preferred_label,
                            Literal(product["brand_name"]),
                        )
                    )
                    triples.append(
                        (
                            product_uri,
                            predicates.biolink_name,
                            Literal(product["brand_name"]),
                        )
                    )

                if product.get("dosage_form"):
                    dosage_uri = uri_builders.build_dosage_form_uri(product["dosage_form"])
                    triples.append(
                        (product_uri, predicates.has_attribute, dosage_uri)
                    )  # SIO:has attribute
                    triples.append(
                        (
                            dosage_uri,
                            predicates.rdf_type,
                            entity_types.dosage_form,
                        )
                    )  # SIO:dosage form
                    triples.append(
                        (
                            dosage_uri,
                            predicates.rdfs_label,
                            Literal(product["dosage_form"]),
                        )
                    )

                if product.get("route"):
                    route_uri = uri_builders.build_route_uri(product["route"])
                    triples.append(
                        (product_uri, predicates.has_exposure_route, route_uri)
                    )  # ExO:has exposure route
                    triples.append(
                        (
                            route_uri,
                            predicates.rdf_type,
                            entity_types.route_of_administration,
                        )
                    )  # ExO:route of administration
                    triples.append(
                        (
                            route_uri,
                            predicates.rdfs_label,
                            Literal(product["route"]),
                        )
                    )

                if product.get("marketing_status"):
                    triples.append(
                        (
                            product_uri,
                            predicates.has_status,
                            Literal(product["marketing_status"]),
                        )
                    )  # SIO:has status
                    triples.append(
                        (
                            product_uri,
                            predicates.rights,
                            Literal(product["marketing_status"]),
                        )
                    )

                # Active ingredients using CHEMINF and pharmaceutical ontologies
                active_ingredients = product.get("active_ingredients")
                if active_ingredients is not None:
                    # Handle both numpy arrays (from pandas/parquet) and regular Python lists (from tests)
                    if isinstance(active_ingredients, np.ndarray):
                        ingredients_list = active_ingredients
                    elif isinstance(active_ingredients, list | tuple):
                        ingredients_list = active_ingredients
                    else:
                        ingredients_list = []

                    for j, ingredient in enumerate(ingredients_list):
                        if isinstance(ingredient, dict):
                            ingredient_uri = uri_builders.build_ingredient_uri_nested(product_uri, j)
                            triples.append(
                                (
                                    product_uri,
                                    predicates.has_participant,
                                    ingredient_uri,
                                )
                            )  # RO:has participant
                            triples.append(
                                (
                                    ingredient_uri,
                                    predicates.rdf_type,
                                    entity_types.chemical_entity,
                                )
                            )  # CHEMINF:chemical entity
                            triples.append(
                                (
                                    ingredient_uri,
                                    predicates.is_component_of,
                                    product_uri,
                                )
                            )  # SIO:is component of
                            triples.append(
                                (
                                    ingredient_uri,
                                    predicates.ingredient_of,
                                    product_uri,
                                )
                            )

                            if ingredient.get("name"):
                                triples.append(
                                    (
                                        ingredient_uri,
                                        predicates.rdfs_label,
                                        Literal(ingredient["name"]),
                                    )
                                )
                                triples.append(
                                    (
                                        ingredient_uri,
                                        predicates.biolink_name,
                                        Literal(ingredient["name"]),
                                    )
                                )
                                triples.append(
                                    (
                                        ingredient_uri,
                                        predicates.preferred_label,
                                        Literal(ingredient["name"]),
                                    )
                                )

                            if ingredient.get("strength"):
                                # Create strength measurement using SIO and OBI
                                strength_uri = uri_builders.build_strength_uri(ingredient_uri)
                                triples.append(
                                    (
                                        ingredient_uri,
                                        predicates.has_measurement_value,
                                        strength_uri,
                                    )
                                )  # SIO:has measurement value
                                triples.append(
                                    (
                                        strength_uri,
                                        predicates.rdf_type,
                                        entity_types.measurement_value,
                                    )
                                )  # SIO:measurement value
                                triples.append(
                                    (
                                        strength_uri,
                                        predicates.has_value,
                                        Literal(ingredient["strength"]),
                                    )
                                )  # SIO:has value
                                triples.append(
                                    (
                                        strength_uri,
                                        predicates.rdfs_label,
                                        Literal(f"Strength: {ingredient['strength']}"),
                                    )
                                )

        # Add typing for the application using bioassay ontology (moved outside the ingredient loop)
        if len(products_list) > 0:  # Only add if there are products
            triples.append(
                (app_uri, predicates.rdf_type, entity_types.bioassay)
            )  # BAO:bioassay
            triples.append(
                (app_uri, predicates.identifier, Literal(app_number))
            )
            triples.append(
                (app_uri, predicates.created, Literal("FDA Application"))
            )
            triples.append(
                (app_uri, predicates.refers_to, Literal("pharmaceutical"))
            )  # SIO:refers to

    return triples


def main():
    """Main execution function for processing FDA data."""
    print("Loading openFDA brick …")
    of_brick = bb.assets("openfda")
    print("Done.")
    # use pyarrow to read the relevant parquet file in chunks
    rawpa = pq.ParquetFile(of_brick.drugs_fda_parquet)
    n_row = rawpa.metadata.num_rows
    print(f"Number of rows: {n_row}")

    # get row0 and make it json for a pretty print
    row_group0 = rawpa.read_row_group(0).to_pandas()
    row0 = row_group0.iloc[0]
    parsed = json.loads(row0.to_json())
    print(json.dumps(parsed, indent=4))

    BATCH_SIZE = 1000  # Smaller batch size for FDA data due to complexity
    num_batches = rawpa.metadata.num_rows // BATCH_SIZE + 1

    for batch_idx, record_batch in enumerate(
        tqdm(
            rawpa.iter_batches(BATCH_SIZE), total=num_batches, desc="Processing batches"
        )
    ):
        df = record_batch.to_pandas()
        g = Graph()
        for prefix, namespace in namespaces.items():
            g.bind(prefix, namespace)

        for _, row in df.iterrows():
            triples = extract_relationships_from_row(row)
            for triple in triples:
                g.add(triple)

        ttl_out = cachedir / f"fda_relations_{batch_idx}.ttl"
        g.serialize(destination=str(ttl_out), format="turtle")

    print("Conversion complete: Turtle files written to", cachedir)


if __name__ == "__main__":
    main()
