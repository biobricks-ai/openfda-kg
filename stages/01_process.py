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
of_brick = bb.assets('openfda')
print("Done.")
# use pyarrow to read the relevant parquet file in chunks
rawpa = pq.ParquetFile(of_brick.drugs_fda_parquet)
n_row = rawpa.metadata.num_rows
print(f"Number of rows: {n_row}")

# get row0 and make it json for a pretty print
row_group0 = rawpa.read_row_group(0).to_pandas()
row0 = row_group0.iloc[0]
print(json.dumps(row0.apply(str).to_dict(), indent=4))

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
}

namespaces = {key: Namespace(val) for key, val in namespaces_sources.items()}

# ---------------------------------------------------------------------------
# Helper: build URIs for different FDA entities
# ---------------------------------------------------------------------------
def build_application_uri(app_number: str) -> URIRef:
    """Build URI for FDA application number."""
    return URIRef(namespaces["fda"] + f"application/{quote(app_number, safe='')}")

def build_company_uri(company_name: str) -> URIRef:
    """Build URI for drug company/sponsor."""
    clean_name = company_name.replace(' ', '_').replace(',', '').replace('.', '')
    return URIRef(namespaces["company"] + quote(clean_name, safe=''))

def build_substance_uri(unii: str) -> URIRef:
    """Build URI for substance using UNII."""
    return URIRef(namespaces["unii"] + unii)

def build_ndc_uri(ndc: str) -> URIRef:
    """Build URI for NDC code."""
    return URIRef(namespaces["ndc"] + ndc)

def build_rxcui_uri(rxcui: str) -> URIRef:
    """Build URI for RxCUI."""
    return URIRef(namespaces["rxcui"] + rxcui)

def build_spl_uri(spl_id: str) -> URIRef:
    """Build URI for SPL ID."""
    return URIRef(namespaces["spl"] + spl_id)

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
    
    # Application -> Sponsor relationship
    if sponsor_name:
        sponsor_uri = build_company_uri(sponsor_name)
        triples.append((app_uri, namespaces["ofrel"]["sponsoredBy"], sponsor_uri))
        triples.append((sponsor_uri, namespaces["rdfs"]["label"], Literal(sponsor_name)))
    
    # Process OpenFDA standardized data
    openfda = row.get('openfda')
    if openfda and isinstance(openfda, dict):
        
        # Brand names
        brand_names = safe_get_array_items(openfda.get('brand_name'))
        for brand_name in brand_names:
            triples.append((app_uri, namespaces["ofrel"]["brandName"], Literal(brand_name)))
        
        # Generic names
        generic_names = safe_get_array_items(openfda.get('generic_name'))
        for generic_name in generic_names:
            triples.append((app_uri, namespaces["ofrel"]["genericName"], Literal(generic_name)))
        
        # Manufacturer names
        manufacturer_names = safe_get_array_items(openfda.get('manufacturer_name'))
        for mfg_name in manufacturer_names:
            mfg_uri = build_company_uri(mfg_name)
            triples.append((app_uri, namespaces["ofrel"]["manufacturedBy"], mfg_uri))
            triples.append((mfg_uri, namespaces["rdfs"]["label"], Literal(mfg_name)))
        
        # NDC codes
        package_ndcs = safe_get_array_items(openfda.get('package_ndc'))
        for ndc in package_ndcs:
            ndc_uri = build_ndc_uri(ndc)
            triples.append((app_uri, namespaces["ofrel"]["hasPackageNDC"], ndc_uri))
        
        product_ndcs = safe_get_array_items(openfda.get('product_ndc'))
        for ndc in product_ndcs:
            ndc_uri = build_ndc_uri(ndc)
            triples.append((app_uri, namespaces["ofrel"]["hasProductNDC"], ndc_uri))
        
        # UNII codes for substances
        uniis = safe_get_array_items(openfda.get('unii'))
        for unii in uniis:
            substance_uri = build_substance_uri(unii)
            triples.append((app_uri, namespaces["ofrel"]["containsSubstance"], substance_uri))
        
        # RxCUI codes
        rxcuis = safe_get_array_items(openfda.get('rxcui'))
        for rxcui in rxcuis:
            rxcui_uri = build_rxcui_uri(rxcui)
            triples.append((app_uri, namespaces["ofrel"]["hasRxCUI"], rxcui_uri))
        
        # SPL IDs
        spl_set_ids = safe_get_array_items(openfda.get('spl_set_id'))
        for spl_id in spl_set_ids:
            spl_uri = build_spl_uri(spl_id)
            triples.append((app_uri, namespaces["ofrel"]["hasSPL"], spl_uri))
        
        # Routes of administration
        routes = safe_get_array_items(openfda.get('route'))
        for route in routes:
            triples.append((app_uri, namespaces["ofrel"]["route"], Literal(route)))
        
        # Product types
        product_types = safe_get_array_items(openfda.get('product_type'))
        for prod_type in product_types:
            triples.append((app_uri, namespaces["ofrel"]["productType"], Literal(prod_type)))
        
        # Substance names
        substance_names = safe_get_array_items(openfda.get('substance_name'))
        for substance_name in substance_names:
            triples.append((app_uri, namespaces["ofrel"]["substanceName"], Literal(substance_name)))
    
    # Process products array
    products = row.get('products')
    if products is not None and isinstance(products, np.ndarray):
        for i, product in enumerate(products):
            if isinstance(product, dict):
                product_uri = URIRef(f"{app_uri}/product/{i}")
                triples.append((app_uri, namespaces["ofrel"]["hasProduct"], product_uri))
                
                # Product properties
                if product.get('brand_name'):
                    triples.append((product_uri, namespaces["ofrel"]["brandName"], Literal(product['brand_name'])))
                
                if product.get('dosage_form'):
                    triples.append((product_uri, namespaces["ofrel"]["dosageForm"], Literal(product['dosage_form'])))
                
                if product.get('route'):
                    triples.append((product_uri, namespaces["ofrel"]["route"], Literal(product['route'])))
                
                if product.get('marketing_status'):
                    triples.append((product_uri, namespaces["ofrel"]["marketingStatus"], Literal(product['marketing_status'])))
                
                # Active ingredients
                active_ingredients = product.get('active_ingredients')
                if active_ingredients is not None and isinstance(active_ingredients, np.ndarray):
                    for j, ingredient in enumerate(active_ingredients):
                        if isinstance(ingredient, dict):
                            ingredient_uri = URIRef(f"{product_uri}/ingredient/{j}")
                            triples.append((product_uri, namespaces["ofrel"]["hasActiveIngredient"], ingredient_uri))
                            
                            if ingredient.get('name'):
                                triples.append((ingredient_uri, namespaces["rdfs"]["label"], Literal(ingredient['name'])))
                            
                            if ingredient.get('strength'):
                                triples.append((ingredient_uri, namespaces["ofrel"]["strength"], Literal(ingredient['strength'])))
    
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
