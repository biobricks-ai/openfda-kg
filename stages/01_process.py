#!/usr/bin/env python3

import biobricks as bb
import pandas as pd
import pyarrow.parquet as pq
import json
import pathlib
from tqdm import tqdm
from rdflib import Graph, Literal, Namespace, RDF, URIRef
import glob
from urllib.parse import quote
import numpy as np

tqdm.pandas()

# cachedir for ttl files
cachedir = pathlib.Path('cache/process')
cachedir.mkdir(parents=True, exist_ok=True)

# outdir should be brick (hdt file only)
outdir = pathlib.Path('./brick')
outdir.mkdir(parents=True, exist_ok=True)

print("Loading openFDA brick …")
# of_brick = bb.assets('openfda')
# print("Done.")
# # use pyarrow to read the relevant parquet file in chunks
# rawpa = pq.ParquetFile(of_brick.drugs_fda_parquet)
# n_row = rawpa.metadata.num_rows
# print(f"Number of rows: {n_row}")

print("Loading parquet file …")
rawpa = pq.ParquetFile('drugs_fda.parquet')
n_row = rawpa.metadata.num_rows
print(f"Number of rows: {n_row}")

# get row0 and make it json for a pretty print
row_group0 = rawpa.read_row_group(0).to_pandas()
row0 = row_group0.iloc[0]
parsed = json.loads(row0.to_json())
print(json.dumps(parsed, indent=4))

# Define namespaces for OpenFDA data
namespaces_sources = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "fda": "https://api.fda.gov/drug/",  # FDA drug applications
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
    "EDAM": "http://edamontology.org/",
    "dce": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "puml": "http://plantuml.com/ontology#",
    "ncim": "https://identifiers.org/umls:",
    "iceprop": "https://ice.ntp.niehs.nih.gov/property/",
    "invitrodb": "https://comptox.epa.gov/property/",
    "ncbigene": "https://www.ncbi.nlm.nih.gov/gene/",
    "biolink": "https://w3id.org/biolink/vocab/",
}

namespaces = {key: Namespace(val) for key, val in namespaces_sources.items()}

# ---------------------------------------------------------------------------
# Helper: build URIs for different FDA entities using semantic ontologies
# ---------------------------------------------------------------------------
def build_application_uri(app_number: str) -> URIRef:
    """Build URI for FDA application number using SIO chemical entity."""
    return URIRef(namespaces["fda"] + f"application/{quote(app_number, safe='')}")

def build_company_uri(company_name: str) -> URIRef:
    """Build URI for drug company/sponsor using SIO organization."""
    clean_name = company_name.replace(' ', '_').replace(',', '').replace('.', '')
    return URIRef(namespaces["company"] + quote(clean_name, safe=''))

def build_substance_uri(unii: str) -> URIRef:
    """Build URI for substance using UNII - represents a chemical substance."""
    return URIRef(namespaces["unii"] + unii)

def build_ndc_uri(ndc: str) -> URIRef:
    """Build URI for NDC code - represents a drug product identifier."""
    return URIRef(namespaces["ndc"] + ndc)

def build_rxcui_uri(rxcui: str) -> URIRef:
    """Build URI for RxCUI - represents a clinical drug concept."""
    return URIRef(namespaces["rxcui"] + rxcui)

def build_spl_uri(spl_id: str) -> URIRef:
    """Build URI for SPL ID - structured product labeling identifier."""
    return URIRef(namespaces["spl"] + spl_id)

def build_dosage_form_uri(dosage_form: str) -> URIRef:
    """Build URI for dosage form using pharmaceutical ontology concepts."""
    clean_form = dosage_form.replace(' ', '_').replace(',', '').upper()
    return URIRef(namespaces["fda"] + f"dosage_form/{quote(clean_form, safe='')}")

def build_route_uri(route: str) -> URIRef:
    """Build URI for administration route using ExO (Exposure Ontology)."""
    clean_route = route.replace(' ', '_').replace(',', '').upper()
    return URIRef(namespaces["ExO"] + f"route/{quote(clean_route, safe='')}")

def build_ingredient_uri(ingredient_name: str) -> URIRef:
    """Build URI for active ingredient using CHEMINF chemical information ontology."""
    clean_name = ingredient_name.replace(' ', '_').replace(',', '').replace('.', '')
    return URIRef(namespaces["CHEMINF"] + f"ingredient/{quote(clean_name, safe='')}")

def safe_get_array_items(arr):
    """Safely extract items from numpy array, handling None and various data types."""
    if arr is None:
        return []
    if isinstance(arr, np.ndarray):
        return [str(item) for item in arr if item is not None]
    if isinstance(arr, (list, tuple)):
        return [str(item) for item in arr if item is not None]
    return [str(arr)] if arr is not None else []

# ---------------------------------------------------------------------------
# Extract relationships from FDA data
# ---------------------------------------------------------------------------
def extract_relationships_from_row(row):
    """Extract RDF triples from a single FDA drug application row."""
    triples = []
    
    app_number = row['application_number']
    sponsor_name = row['sponsor_name']
    
    if not app_number:
        return triples
        
    app_uri = build_application_uri(app_number)
    
    # Application -> Sponsor relationship using semantic predicates
    if sponsor_name:
        sponsor_uri = build_company_uri(sponsor_name)
        # Use SIO relationships for sponsorship and organization typing
        triples.append((app_uri, namespaces["SIO"]["000136"], sponsor_uri))  # SIO:is sponsored by
        triples.append((sponsor_uri, namespaces["rdf"]["type"], namespaces["SIO"]["000012"]))  # SIO:organization
        triples.append((sponsor_uri, namespaces["rdfs"]["label"], Literal(sponsor_name)))
        triples.append((sponsor_uri, namespaces["dcterms"]["title"], Literal(sponsor_name)))
    
    # Process OpenFDA standardized data
    openfda = row.get('openfda')
    if openfda and isinstance(openfda, dict):
        
        # Brand names using SKOS preferred label and SIO terminology
        brand_names = safe_get_array_items(openfda.get('brand_name'))
        for brand_name in brand_names:
            triples.append((app_uri, namespaces["skos"]["prefLabel"], Literal(brand_name)))
            triples.append((app_uri, namespaces["SIO"]["000008"], Literal(brand_name)))  # SIO:has attribute (brand name)
        
        # Generic names using alternative labels and biolink naming
        generic_names = safe_get_array_items(openfda.get('generic_name'))
        for generic_name in generic_names:
            triples.append((app_uri, namespaces["skos"]["altLabel"], Literal(generic_name)))
            triples.append((app_uri, namespaces["biolink"]["name"], Literal(generic_name)))
        
        # Manufacturer names using RO (Relations Ontology) and SIO
        manufacturer_names = safe_get_array_items(openfda.get('manufacturer_name'))
        for mfg_name in manufacturer_names:
            mfg_uri = build_company_uri(mfg_name)
            triples.append((app_uri, namespaces["RO"]["0002234"], mfg_uri))  # RO:manufactured by
            triples.append((mfg_uri, namespaces["rdf"]["type"], namespaces["SIO"]["000012"]))  # SIO:organization
            triples.append((mfg_uri, namespaces["rdfs"]["label"], Literal(mfg_name)))
            triples.append((mfg_uri, namespaces["dcterms"]["title"], Literal(mfg_name)))
        
        # NDC codes using SIO identifiers and IAO information artifacts
        package_ndcs = safe_get_array_items(openfda.get('package_ndc'))
        for ndc in package_ndcs:
            ndc_uri = build_ndc_uri(ndc)
            triples.append((app_uri, namespaces["SIO"]["000671"], ndc_uri))  # SIO:has identifier
            triples.append((ndc_uri, namespaces["rdf"]["type"], namespaces["IAO"]["0000578"]))  # IAO:centrally registered identifier
            triples.append((ndc_uri, namespaces["dcterms"]["type"], Literal("package_ndc")))
        
        product_ndcs = safe_get_array_items(openfda.get('product_ndc'))
        for ndc in product_ndcs:
            ndc_uri = build_ndc_uri(ndc)
            triples.append((app_uri, namespaces["SIO"]["000671"], ndc_uri))  # SIO:has identifier
            triples.append((ndc_uri, namespaces["rdf"]["type"], namespaces["IAO"]["0000578"]))  # IAO:centrally registered identifier
            triples.append((ndc_uri, namespaces["dcterms"]["type"], Literal("product_ndc")))
        
        # UNII codes for substances using CHEMINF chemical information
        uniis = safe_get_array_items(openfda.get('unii'))
        for unii in uniis:
            substance_uri = build_substance_uri(unii)
            triples.append((app_uri, namespaces["RO"]["0000057"], substance_uri))  # RO:has participant (contains substance)
            triples.append((substance_uri, namespaces["rdf"]["type"], namespaces["CHEMINF"]["000000"]))  # CHEMINF:chemical entity
        
        # RxCUI codes using biolink and SIO identifiers
        rxcuis = safe_get_array_items(openfda.get('rxcui'))
        for rxcui in rxcuis:
            rxcui_uri = build_rxcui_uri(rxcui)
            triples.append((app_uri, namespaces["SIO"]["000671"], rxcui_uri))  # SIO:has identifier
            triples.append((rxcui_uri, namespaces["rdf"]["type"], namespaces["biolink"]["Drug"]))
            triples.append((rxcui_uri, namespaces["dcterms"]["type"], Literal("rxcui")))
        
        # SPL IDs using IAO document identifiers
        spl_set_ids = safe_get_array_items(openfda.get('spl_set_id'))
        for spl_id in spl_set_ids:
            spl_uri = build_spl_uri(spl_id)
            triples.append((app_uri, namespaces["SIO"]["000068"], spl_uri))  # SIO:has document
            triples.append((spl_uri, namespaces["rdf"]["type"], namespaces["IAO"]["0000310"]))  # IAO:document
            triples.append((spl_uri, namespaces["dcterms"]["type"], Literal("structured_product_label")))
        
        # Routes of administration using ExO exposure routes
        routes = safe_get_array_items(openfda.get('route'))
        for route in routes:
            route_uri = build_route_uri(route)
            triples.append((app_uri, namespaces["ExO"]["0000002"], route_uri))  # ExO:has exposure route
            triples.append((route_uri, namespaces["rdf"]["type"], namespaces["ExO"]["0000055"]))  # ExO:route of administration
            triples.append((route_uri, namespaces["rdfs"]["label"], Literal(route)))
        
        # Product types using SIO classification
        product_types = safe_get_array_items(openfda.get('product_type'))
        for prod_type in product_types:
            triples.append((app_uri, namespaces["SIO"]["000332"], Literal(prod_type)))  # SIO:has classification
            triples.append((app_uri, namespaces["dcterms"]["type"], Literal(prod_type)))
        
        # Substance names using CHEMINF and biolink
        substance_names = safe_get_array_items(openfda.get('substance_name'))
        for substance_name in substance_names:
            substance_name_uri = build_ingredient_uri(substance_name)
            triples.append((app_uri, namespaces["RO"]["0000057"], substance_name_uri))  # RO:has participant
            triples.append((substance_name_uri, namespaces["rdf"]["type"], namespaces["CHEMINF"]["000000"]))  # CHEMINF:chemical entity
            triples.append((substance_name_uri, namespaces["rdfs"]["label"], Literal(substance_name)))
            triples.append((substance_name_uri, namespaces["biolink"]["name"], Literal(substance_name)))
    
    # Process products array using pharmaceutical and chemical ontologies
    products = row.get('products')
    if products is not None and isinstance(products, np.ndarray):
        for i, product in enumerate(products):
            if isinstance(product, dict):
                product_uri = URIRef(f"{app_uri}/product/{i}")
                triples.append((app_uri, namespaces["RO"]["0000057"], product_uri))  # RO:has participant
                triples.append((product_uri, namespaces["rdf"]["type"], namespaces["biolink"]["Drug"]))
                
                # Product properties using semantic predicates
                if product.get('brand_name'):
                    triples.append((product_uri, namespaces["skos"]["prefLabel"], Literal(product['brand_name'])))
                    triples.append((product_uri, namespaces["biolink"]["name"], Literal(product['brand_name'])))
                
                if product.get('dosage_form'):
                    dosage_uri = build_dosage_form_uri(product['dosage_form'])
                    triples.append((product_uri, namespaces["SIO"]["000008"], dosage_uri))  # SIO:has attribute
                    triples.append((dosage_uri, namespaces["rdf"]["type"], namespaces["SIO"]["000614"]))  # SIO:dosage form
                    triples.append((dosage_uri, namespaces["rdfs"]["label"], Literal(product['dosage_form'])))
                
                if product.get('route'):
                    route_uri = build_route_uri(product['route'])
                    triples.append((product_uri, namespaces["ExO"]["0000002"], route_uri))  # ExO:has exposure route
                    triples.append((route_uri, namespaces["rdf"]["type"], namespaces["ExO"]["0000055"]))  # ExO:route of administration
                    triples.append((route_uri, namespaces["rdfs"]["label"], Literal(product['route'])))
                
                if product.get('marketing_status'):
                    triples.append((product_uri, namespaces["SIO"]["000300"], Literal(product['marketing_status'])))  # SIO:has status
                    triples.append((product_uri, namespaces["dcterms"]["rights"], Literal(product['marketing_status'])))
                
                # Active ingredients using CHEMINF and pharmaceutical ontologies
                active_ingredients = product.get('active_ingredients')
                if active_ingredients is not None and isinstance(active_ingredients, np.ndarray):
                    for j, ingredient in enumerate(active_ingredients):
                        if isinstance(ingredient, dict):
                            ingredient_uri = URIRef(f"{product_uri}/ingredient/{j}")
                            triples.append((product_uri, namespaces["RO"]["0000057"], ingredient_uri))  # RO:has participant
                            triples.append((ingredient_uri, namespaces["rdf"]["type"], namespaces["CHEMINF"]["000000"]))  # CHEMINF:chemical entity
                            triples.append((ingredient_uri, namespaces["SIO"]["000228"], product_uri))  # SIO:is component of
                            
                            if ingredient.get('name'):
                                ingredient_name_uri = build_ingredient_uri(ingredient['name'])
                                triples.append((ingredient_uri, namespaces["rdfs"]["label"], Literal(ingredient['name'])))
                                triples.append((ingredient_uri, namespaces["biolink"]["name"], Literal(ingredient['name'])))
                                triples.append((ingredient_uri, namespaces["skos"]["prefLabel"], Literal(ingredient['name'])))
                            
                            if ingredient.get('strength'):
                                # Create strength measurement using SIO and OBI
                                strength_uri = URIRef(f"{ingredient_uri}/strength")
                                triples.append((ingredient_uri, namespaces["SIO"]["000221"], strength_uri))  # SIO:has measurement value
                                triples.append((strength_uri, namespaces["rdf"]["type"], namespaces["SIO"]["000052"]))  # SIO:measurement value
                                triples.append((strength_uri, namespaces["SIO"]["000300"], Literal(ingredient['strength'])))  # SIO:has value
                                triples.append((strength_uri, namespaces["rdfs"]["label"], Literal(f"Strength: {ingredient['strength']}")))
                                
                    # Add typing for the application using bioassay ontology
                    triples.append((app_uri, namespaces["rdf"]["type"], namespaces["BAO"]["0000040"]))  # BAO:bioassay
                    triples.append((app_uri, namespaces["dcterms"]["identifier"], Literal(app_number)))
                    triples.append((app_uri, namespaces["dcterms"]["created"], Literal("FDA Application")))
                    triples.append((app_uri, namespaces["SIO"]["000628"], Literal("pharmaceutical")))  # SIO:refers to
    
    return triples

BATCH_SIZE = 1000  # Smaller batch size for FDA data due to complexity
num_batches = rawpa.metadata.num_rows // BATCH_SIZE + 1

for batch_idx, record_batch in enumerate(tqdm(rawpa.iter_batches(BATCH_SIZE), total=num_batches, desc="Processing batches")):
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
