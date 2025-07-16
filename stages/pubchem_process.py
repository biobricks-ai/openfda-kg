#!/usr/bin/env python3
"""
OpenFDA to PubChem Knowledge Graph Processing Script

This script processes the Drugs@FDA parquet file from biobricks and creates
RDF triples using PubChem Compound URIs for the specified columns.
"""

from io import TextIOBase
import json
import pathlib
import sys
from urllib.parse import quote
from typing import Dict, List, Set, Optional, TextIO
from collections import defaultdict
import biobricks as bb
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from rdflib import Graph, Literal, Namespace, URIRef
from tqdm import tqdm

# Add the current directory to Python path to import modules
sys.path.insert(0, str(pathlib.Path(__file__).parent / "stages"))
from predicates import create_predicates, create_entity_types
from uri_builders import create_openfda_uri_builders

tqdm.pandas()

# Setup directories
cachedir = pathlib.Path("cache/pubchem_process")
cachedir.mkdir(parents=True, exist_ok=True)

outdir = pathlib.Path("./brick")
outdir.mkdir(parents=True, exist_ok=True)

# Global variable to store CID-Synonym mapping
_cid_synonym_map = defaultdict(set)

def load_cid_synonym_map():
    """Load the CID-Synonym mapping from the filtered file."""
    global _cid_synonym_map
    
    if _cid_synonym_map:  # Already loaded
        return
    
    print("Loading CID-Synonym mapping...")
    with open("stages/CID-Synonym-filtered", "r") as f:
        for line in tqdm(f, desc="Loading synonyms"):
            try:
                cid, synonym = line.strip().split("\t")
                _cid_synonym_map[synonym.lower()].add(cid)
            except ValueError:
                continue  # Skip malformed lines
    
    print(f"Loaded {len(_cid_synonym_map)} unique synonyms")

def get_cids_for_name(name: str) -> List[str]:
    """Get PubChem CIDs for a given name using the local synonym mapping."""
    if not name or not name.strip():
        return []
    
    # Ensure mapping is loaded
    load_cid_synonym_map()
    
    # Look up name in mapping (case-insensitive)
    name_lower = name.strip().lower()
    cids = _cid_synonym_map.get(name_lower, set())
    
    # Convert to sorted list for consistent results
    return sorted(list(cids))

# Define namespaces (same as in 01_process.py but with focus on PubChem)
namespaces_sources = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "fda": "https://api.fda.gov/drug/drugsfda.json?search=",
    "ndc": "https://www.fda.gov/industry/structured-product-labeling-resources/ndc-directory/",
    "unii": "https://fdasis.nlm.nih.gov/srs/unii/",
    "rxcui": "https://mor.nlm.nih.gov/RxNav/search?searchBy=RXCUI&searchTerm=",
    "spl": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=",
    "company": "https://api.fda.gov/drug/company/",
    "ofrel": "https://api.fda.gov/drug/relationship/",
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
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "puml": "http://plantuml.com/ontology#",
    "ncim": "https://identifiers.org/umls:",
    "iceprop": "https://ice.ntp.niehs.nih.gov/property/",
    "invitrodb": "https://comptox.epa.gov/property/",
    "ncbigene": "https://www.ncbi.nlm.nih.gov/gene/",
    "biolink": "https://w3id.org/biolink/vocab/",
    "SDDO": "http://purl.obolibrary.org/obo/SDDO_",
    "AFO": "http://purl.allotrope.org/ontologies/property#AFX_",
    "opmi": "http://purl.obolibrary.org/obo/OPMI_",
    "anatomy": "https://rdf.ncbi.nlm.nih.gov/pubchem/anatomy/",
    "author": "https://rdf.ncbi.nlm.nih.gov/pubchem/author/",
    "bioassay": "https://rdf.ncbi.nlm.nih.gov/pubchem/bioassay/",
    "book": "https://rdf.ncbi.nlm.nih.gov/pubchem/book/",
    "cell": "https://rdf.ncbi.nlm.nih.gov/pubchem/cell/",
    "compound": "https://rdf.ncbi.nlm.nih.gov/pubchem/compound/",
    "concept": "https://rdf.ncbi.nlm.nih.gov/pubchem/concept/",
    "conserveddomain": "https://rdf.ncbi.nlm.nih.gov/pubchem/conserveddomain/",
    "cooccurrence": "https://rdf.ncbi.nlm.nih.gov/pubchem/cooccurrence/",
    "descriptor": "https://rdf.ncbi.nlm.nih.gov/pubchem/descriptor/",
    "disease": "https://rdf.ncbi.nlm.nih.gov/pubchem/disease/",
    "endpoint": "https://rdf.ncbi.nlm.nih.gov/pubchem/endpoint/",
    "gene": "https://rdf.ncbi.nlm.nih.gov/pubchem/gene/",
    "grant": "https://rdf.ncbi.nlm.nih.gov/pubchem/grant/",
    "inchikey": "https://rdf.ncbi.nlm.nih.gov/pubchem/inchikey/",
    "journal": "https://rdf.ncbi.nlm.nih.gov/pubchem/journal/",
    "measuregroup": "https://rdf.ncbi.nlm.nih.gov/pubchem/measuregroup/",
    "organization": "https://rdf.ncbi.nlm.nih.gov/pubchem/organization/",
    "patent": "https://rdf.ncbi.nlm.nih.gov/pubchem/patent/",
    "patentcpc": "https://rdf.ncbi.nlm.nih.gov/pubchem/patentcpc/",
    "patentipc": "https://rdf.ncbi.nlm.nih.gov/pubchem/patentipc/",
    "pathway": "https://rdf.ncbi.nlm.nih.gov/pubchem/pathway/",
    "protein": "https://rdf.ncbi.nlm.nih.gov/pubchem/protein/",
    "reference": "https://rdf.ncbi.nlm.nih.gov/pubchem/reference/",
    "source": "https://rdf.ncbi.nlm.nih.gov/pubchem/source/",
    "substance": "https://rdf.ncbi.nlm.nih.gov/pubchem/substance/",
    "synonym": "https://rdf.ncbi.nlm.nih.gov/pubchem/synonym/",
    "taxonomy": "https://rdf.ncbi.nlm.nih.gov/pubchem/taxonomy/",
    "MI": "http://purl.obolibrary.org/obo/MI_",
    "DRON": "http://www.geneontology.org/formats/oboInOwl#"
}

namespaces = {key: Namespace(val) for key, val in namespaces_sources.items()}

# Initialize predicate, entity type, and URI builder helpers
predicates = create_predicates(namespaces)
entity_types = create_entity_types(namespaces)
uri_builders = create_openfda_uri_builders(namespaces)

# Helper functions for PubChem integration

def safe_get_array_items(arr):
    """Safely extract items from numpy array, handling None and various data types."""
    if arr is None:
        return []
    if isinstance(arr, np.ndarray):
        return [str(item) for item in arr if item is not None]
    if isinstance(arr, (list, tuple)):
        return [str(item) for item in arr if item is not None]
    return [str(arr)] if arr is not None else []

def uri_from_cid(cid: str) -> URIRef:
    """Build PubChem compound URI from CID."""
    return URIRef(namespaces_sources["compound"] + f"CID{cid}")

def create_pubchem_compound_triples(names: List[str], entity_type: URIRef, 
                                    verbose: bool = False) -> (List[URIRef], List[tuple]):
    """Create RDF triples for PubChem compounds from names and return their URIs."""
    triples = []
    pubchem_cid_uris = []
    
    for name in names:
        if not name:
            continue
            
        cids = get_cids_for_name(name)
        
        if cids:
            if verbose:
                print(f"🔗 Found {len(cids)} CID(s) for '{name}': {cids[:3]}{'...' if len(cids) > 3 else ''}")
            
            for cid_val in cids[:5]:  # Limit to first 5 CIDs
                pubchem_uri = uri_from_cid(cid_val)
                pubchem_cid_uris.append(pubchem_uri)
                
                # Basic triples for the compound
                triples.append((pubchem_uri, predicates.rdf_type, entity_type))
                triples.append((pubchem_uri, predicates.rdfs_label, Literal(name)))
                triples.append((pubchem_uri, predicates.preferred_label, Literal(name)))
                triples.append((pubchem_uri, predicates.dc_title, Literal(f"PubChem Compound {cid_val}")))
                triples.append((pubchem_uri, predicates.identifier, Literal(cid_val)))
        elif verbose:
            print(f"❌ No CIDs found for '{name}'")

    return list(set(pubchem_cid_uris)), triples

def extract_pubchem_relationships_from_row(row, verbose: bool = False):
    """
    Extract RDF triples from openFDA data using PubChem compound URIs.
    
    Focuses on the specified columns:
    - openFDA.brand_name
    - openFDA.generic_name  
    - openFDA.manufacturer_name
    - openFDA.pharm_class_cs
    - openFDA.pharm_class_epc
    - openFDA.pharm_class_moa
    - openFDA.pharm_class_pe
    - openFDA.product_type
    - openFDA.route
    - openFDA.substance_name
    """
    triples = []
    
    # Process OpenFDA standardized data
    openfda = row.get("openfda")
    if not openfda or not isinstance(openfda, dict):
        return triples
    
    app_number = row.get("application_number", "N/A")
    if verbose:
        print(f"\n🔄 Processing data from source row (application: {app_number})")
    
    # 1. Collect all names and create PubChem compound URIs and base triples
    all_names = []
    all_names.extend(safe_get_array_items(openfda.get("brand_name")))
    all_names.extend(safe_get_array_items(openfda.get("generic_name")))
    all_names.extend(safe_get_array_items(openfda.get("substance_name")))
    
    pubchem_cid_uris, base_triples = create_pubchem_compound_triples(
        list(set(all_names)), 
        entity_types.chemical_entity,
        verbose
    )
    triples.extend(base_triples)
    
    if not pubchem_cid_uris:
        return triples # No compounds found, nothing to link to

    if verbose:
        print(f"  🔬 Found {len(pubchem_cid_uris)} unique PubChem compounds to use as subjects.")

    # Link all other properties to each PubChem compound found
    for cid_uri in pubchem_cid_uris:
        
        # 2. Manufacturer names
        manufacturer_names = safe_get_array_items(openfda.get("manufacturer_name"))
        for mfg_name in manufacturer_names:
            if mfg_name:
                mfg_uri = uri_builders.build_manufacturer_uri(mfg_name)
                triples.append((cid_uri, predicates.created_by, mfg_uri))
                triples.append((mfg_uri, predicates.rdf_type, entity_types.manufacturer))
                triples.append((mfg_uri, predicates.rdfs_label, Literal(mfg_name)))

        # 3. Pharmaceutical classes
        pharm_classes = {
            "pharm_class_cs": "chemical_structure_class",
            "pharm_class_epc": "established_pharmacologic_class", 
            "pharm_class_moa": "mechanism_of_action",
            "pharm_class_pe": "physiologic_effect"
        }
        
        # for pharm_key, class_type in pharm_classes.items():
        #     pharm_values = safe_get_array_items(openfda.get(pharm_key))
        #     for pharm_value in pharm_values:
        #         if pharm_value:
        #             clean_value = pharm_value.replace(" ", "_").replace(",", "").replace("[", "").replace("]", "")
        #             pharm_uri = URIRef(namespaces_sources["fda"] + f"{pharm_key}/{quote(clean_value, safe='')}")
                    
        #             triples.append((cid_uri, predicates.has_classification, pharm_uri))
        #             triples.append((pharm_uri, predicates.rdf_type, entity_types.drug_class))
        #             triples.append((pharm_uri, predicates.rdfs_label, Literal(pharm_value)))
        #             triples.append((pharm_uri, predicates.dc_type, Literal(class_type)))

        # 4. Product type
        product_types = safe_get_array_items(openfda.get("product_type"))
        for prod_type in product_types:
            if prod_type:
                # Using a literal for product type as it's a simple string classification
                triples.append((cid_uri, predicates.has_product_type, Literal(prod_type)))

        # 5. Routes of administration
        routes = safe_get_array_items(openfda.get("route"))
        for route in routes:
            if route:
                route_uri = uri_builders.build_route_uri(route)
                triples.append((cid_uri, predicates.has_exposure_route, route_uri))
                triples.append((route_uri, predicates.rdf_type, entity_types.route_of_administration))
                triples.append((route_uri, predicates.rdfs_label, Literal(route)))
    
    return triples

def process_dataset(batch_size: int = 500, max_batches: Optional[int] = None, verbose: bool = True):
    """
    Process the full openFDA dataset and create PubChem-linked RDF triples.
    
    Args:
        batch_size: Number of rows to process in each batch
        max_batches: Maximum number of batches to process (None for all)
        verbose: Whether to print detailed progress information
    """
    print(f"🔍 Loading openFDA brick...")
    of_brick = bb.assets("openfda")
    print(f"✅ OpenFDA brick loaded")
    
    # Load the parquet file 
    rawpa = pq.ParquetFile(of_brick.drugs_fda_parquet)
    n_row = rawpa.metadata.num_rows
    print(f"📊 Total rows in dataset: {n_row:,}")
    
    print(f"🚀 Starting dataset processing...")
    print(f"📦 Batch size: {batch_size}")
    
    num_batches = rawpa.metadata.num_rows // batch_size + 1
    if max_batches:
        num_batches = min(num_batches, max_batches)
        print(f"🎯 Processing limited to {max_batches} batches")
    
    total_triples = 0
    processed_rows = 0
    
    for batch_idx, record_batch in enumerate(
        tqdm(rawpa.iter_batches(batch_size), total=num_batches, desc="Processing batches")
    ):
        if max_batches and batch_idx >= max_batches:
            break
            
        # Convert to pandas DataFrame
        df = record_batch.to_pandas()
        
        # Filter to rows with openFDA data
        df_with_openfda = df[df['openfda'].notna()].copy()
        
        if df_with_openfda.empty:
            continue
            
        if verbose:
            print(f"\n📦 Batch {batch_idx + 1}/{num_batches}: {len(df_with_openfda)} rows with openFDA data")
        
        # Create RDF graph for this batch
        g = Graph()
        [g.bind(prefix, namespace) for prefix,namespace in namespaces.items()]

        batch_triples = 0
        for _, row in df_with_openfda.iterrows():
            try:
                triples = extract_pubchem_relationships_from_row(row, verbose=False)  # Set to True for detailed logging
                for triple in triples:
                    g.add(triple)
                batch_triples += len(triples)
                processed_rows += 1
            except Exception as e:
                print(f"⚠️ Error processing row {row.get('application_number', 'unknown')}: {e}")
                continue
        
        # Save batch to TTL file
        ttl_out = cachedir / f"pubchem_fda_relations_batch_{batch_idx:04d}.ttl"
        g.serialize(destination=str(ttl_out), format="turtle")
        
        total_triples += batch_triples
        if verbose:
            print(f"✅ Batch {batch_idx + 1} complete: {batch_triples} triples -> {ttl_out}")
    
    print(f"\n🎉 Processing complete!")
    print(f"📊 Statistics:")
    print(f"  • Processed rows: {processed_rows:,}")
    print(f"  • Total triples: {total_triples:,}")
    print(f"  • Output directory: {cachedir}")
    print(f"  • Average triples per row: {total_triples/processed_rows:.1f}" if processed_rows > 0 else "  • No rows processed")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Process openFDA data with PubChem integration")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch size for processing")
    parser.add_argument("--max-batches", type=int, help="Maximum number of batches to process")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()

    process_dataset(batch_size=args.batch_size, max_batches=args.max_batches, verbose=args.verbose) 