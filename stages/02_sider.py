import os
import duckdb
import biobricks as bb
from tqdm import tqdm
from rdflib import Graph, Literal, Namespace, URIRef
import re

con = duckdb.connect()

of_brick = bb.assets('openfda')
s_brick = bb.assets('sider')

con.read_parquet(of_brick.drugs_fda_parquet).create("fda_parquet")
con.read_parquet(s_brick.meddra_all_label_indications_parquet).create("meddra_alip")
con.read_parquet(s_brick.meddra_freq_parquet).create("meddra_freq")

con.read_csv('stages/aux/CID-Synonym-filtered', delimiter='\t', quotechar='', names=['CID', 'Drug']).create("synonyms")

con.read_csv('stages/aux/fda_routes.tsv', delimiter='\t').create("routes")
con.read_csv('stages/aux/fda_routes_remapping.tsv', delimiter='\t').create("routes_map")
con.read_csv('stages/aux/fda_dosage_forms.tsv', delimiter='\t').create("dosage_forms")
con.read_csv('stages/aux/fda_dosage_forms_remapping.tsv', delimiter='\t').create("dosage_forms_map")
con.read_csv('stages/aux/fda_marketing_status.tsv', delimiter='\t').create("marketing_statuses")

con.sql("""
	CREATE OR REPLACE TABLE products AS
	SELECT
		unnest(products, recursive := true)
	FROM fda_parquet
""")
con.sql("""
	CREATE OR REPLACE TABLE side_effects AS
	SELECT
		REGEXP_REPLACE(STITCH_Compound_ID_stereo, '^CID0*', '') AS STITCH_Compound_ID_stereo, 
		UMLS_CUI, 
		UMLS_CUI_Concept_Name, 
		UMLS_CUI_for_MedDRA_Term, 
		MedDRA_Concept_Name 
	FROM meddra_alip
""")
con.sql("""
    CREATE OR REPLACE TABLE openfda AS
    WITH unnested_data AS (
        SELECT
            unnest(brand_name) AS brand_name,
            unnest(generic_name) AS generic_name,
            unnest(rxcui) AS rxcui_item
        FROM (
            SELECT unnest(openfda)
            FROM fda_parquet
        )
        WHERE brand_name IS NOT NULL AND rxcui IS NOT NULL
    )
    SELECT DISTINCT ON (brand_name)
        brand_name,
        array_agg(DISTINCT generic_name) as generic_name,
        array_agg(DISTINCT rxcui_item) as rxcui
    FROM unnested_data
	WHERE rxcui_item IS NOT NULL
    GROUP BY brand_name
""")

con.sql("""
	CREATE OR REPLACE TABLE products AS
	SELECT
		active_ingredients,
		brand_name,
		COALESCE(dosage_forms_map.spl_dosage_form, p.dosage_form) AS dosage_form,
		marketing_status,
		product_number,
		reference_drug,
		reference_standard,
		route,
		te_code
	FROM (
		SELECT
			active_ingredients,
			brand_name,
			dosage_form,
			marketing_status,
			product_number,
			reference_drug,
			reference_standard,
			COALESCE(routes_map.spl_route, products.route) AS route,
			te_code
		FROM products 
		LEFT JOIN routes_map 
		ON LOWER(products.route) = LOWER(routes_map.route)
	) AS p
	LEFT JOIN dosage_forms_map 
	ON LOWER(p.dosage_form) = LOWER(dosage_forms_map.dosage_form)
""")
products = con.table("products")
products.show()
side_effects = con.table("side_effects")
side_effects.show()

con.sql("""
	CREATE OR REPLACE TABLE products AS
	SELECT 
		active_ingredients,
		brand_name,
		COALESCE(cui, products.dosage_form) as dosage_form_code,
		marketing_status,
		product_number,
		reference_drug,
		reference_standard,
		route,
		te_code
	FROM products
	LEFT JOIN dosage_forms
	ON LOWER(dosage_forms.dosage_form) = LOWER(products.dosage_form)
""")

con.sql("""
	CREATE OR REPLACE TABLE products AS
	SELECT 
		active_ingredients,
		brand_name,
		dosage_form_code,
		marketing_status,
		product_number,
		reference_drug,
		reference_standard,
		COALESCE(cui, products.route) as route_code,
		te_code
	FROM products
	LEFT JOIN routes
	ON LOWER(routes.route) = LOWER(products.route)
""")

con.sql("""
	CREATE OR REPLACE TABLE products AS
	SELECT 
		active_ingredients,
		brand_name,
		dosage_form_code,
		COALESCE(cui, products.marketing_status) as marketing_status_code,
		product_number,
		reference_drug,
		reference_standard,
		route_code,
		te_code
	FROM products
	LEFT JOIN marketing_statuses
	ON LOWER(marketing_statuses.marketing_status) = LOWER(products.marketing_status)
""")

con.sql("""
	CREATE OR REPLACE TABLE products AS
	SELECT 
		active_ingredients,
		brand_name,
		dosage_form_code,
		marketing_status_code,
		route_code,
		(
			SELECT array_agg(DISTINCT s.CID)
			FROM (
				SELECT unnest(active_ingredients) as ingredient
			)
			INNER JOIN synonyms s 
			ON UPPER(TRIM(s.Drug)) = UPPER(TRIM(ingredient.name))
		) as cids
	FROM products
""")
con.sql("""
	CREATE OR REPLACE TABLE products AS
	SELECT 
		p.active_ingredients,
		p.brand_name,
		p.dosage_form_code,
		p.marketing_status_code,
		p.route_code,
		p.cids,
		o.rxcui
	FROM products p
	LEFT JOIN openfda o ON p.brand_name = o.brand_name
""")
products = con.table("products")
products.show()

# Join products with side_effects using the CIDs array
con.sql("""
	CREATE OR REPLACE TABLE fda_side_effects AS
	SELECT 
		p.active_ingredients,
		p.brand_name,
		p.dosage_form_code,
		p.marketing_status_code,
		p.route_code,
		p.cids,
		p.rxcui,
		array_agg(DISTINCT se.UMLS_CUI) FILTER (WHERE se.UMLS_CUI IS NOT NULL) as umls_cuis,
		array_agg(DISTINCT se.UMLS_CUI_for_MedDRA_Term) FILTER (WHERE se.UMLS_CUI_for_MedDRA_Term IS NOT NULL) as umls_cui_for_meddra_terms,
	FROM products p
	LEFT JOIN (
		SELECT DISTINCT
			active_ingredients,
			brand_name,
			dosage_form_code,
			marketing_status_code,
			route_code,
			cids,
			unnest(cids) as cid
		FROM products
		WHERE cids IS NOT NULL
	) p_unnested ON (
		p.active_ingredients IS NOT DISTINCT FROM p_unnested.active_ingredients
		AND p.brand_name = p_unnested.brand_name
		AND p.dosage_form_code IS NOT DISTINCT FROM p_unnested.dosage_form_code
		AND p.marketing_status_code IS NOT DISTINCT FROM p_unnested.marketing_status_code
		AND p.route_code IS NOT DISTINCT FROM p_unnested.route_code
	)
	LEFT JOIN side_effects se ON CAST(se.STITCH_Compound_ID_stereo AS BIGINT) = p_unnested.cid
	WHERE p.rxcui IS NOT NULL
	GROUP BY 
		p.active_ingredients,
		p.brand_name,
		p.dosage_form_code,
		p.marketing_status_code,
		p.route_code,
		p.cids,
		p.rxcui
""")
fda_side_effects = con.table("fda_side_effects")
fda_side_effects.show()






g = Graph()

# Define namespaces for your ontology
UMLS = Namespace("https://evsexplore.semantics.cancer.gov/evsexplore/concept/ncim/")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
BFO = Namespace("http://purl.obolibrary.org/obo/BFO_")
EXO = Namespace("http://purl.obolibrary.org/obo/ExO_")
GENE = Namespace("http://www.geneontology.org/formats/oboInOwl#")
RO = Namespace("http://purl.obolibrary.org/obo/RO_")
EDAM = Namespace("http://edamontology.org/")
EX = Namespace("http://example.org/drug/")
RXCUI = Namespace("https://mor.nlm.nih.gov/RxNav/search?searchBy=RXCUI&searchTerm=")

# Bind namespaces to the graph
g.bind("umls", UMLS)
g.bind("rdf", RDF)
g.bind("rdfs", RDFS)
g.bind("bfo", BFO)
g.bind("exo", EXO)
g.bind("gene", GENE)
g.bind("ro", RO)
g.bind("edam", EDAM)
g.bind("rxcui", RXCUI)

# Iterate through the products_meddra table and create triples
for row in tqdm(fda_side_effects.fetchall(), desc="Creating triples"):
	active_ingredients, brand_name, dosage_form, marketing_status, route, cids, rxcuis, umls_cuis, umls_cuis_meddra = row
	
	if rxcuis is None: continue

	# Create URI for the drug product
	# drug_subject = URIRef(EX[f"{brand_name.replace(' || ', '_').replace(' ', '_')}"])
	for rxcui in rxcuis:
		drug_subject = RXCUI[f"{rxcui}"]
		# drug_subject = Literal(brand_name)
		
		# Drug is a type of Proprietary Name (brand name; NCIT:C71898)
		g.add((drug_subject, RDF.type, UMLS["C0592503"]))
		# Drug is a type of Medication (NCIT:C459)
		g.add((drug_subject, RDF.type, UMLS["C0013227"]))
		# TODO: Create a label for the drug when it is mapped to a proper URI
		if brand_name:
			g.add((drug_subject, RDFS.label, Literal(brand_name)))

		

		# Drug has basic dose form (SNOMEDCT:)
		if dosage_form and re.match(r'^C[0-9]+$', str(dosage_form)):
			g.add((drug_subject, UMLS["CL547851"], UMLS[f"{dosage_form}"]))
		# Drug has status
		if marketing_status and re.match(r'^C[0-9]+$', str(marketing_status)):
			g.add((drug_subject, GENE.status, UMLS[f"{marketing_status}"]))
		# Drug has exposure route
		if route and re.match(r'^C[0-9]+$', str(route)):
			g.add((drug_subject, RO["0002242"], UMLS[f"{route}"]))
		
		# drug has identifier cid
		if cids:
			for cid in cids:
				g.add((drug_subject, EDAM.has_identifier, UMLS[f"{cid}"]))
		# drug has side effect term (umls term)
		if umls_cuis:
			for umls_cui in umls_cuis:
				g.add((drug_subject, UMLS["C0879626"], UMLS[f"{umls_cui}"]))
		# drug has side effect term (meddra term)
		if umls_cuis_meddra:
			for umls_cui_meddra in umls_cuis_meddra:
				g.add((drug_subject, UMLS["C0879626"], UMLS[f"{umls_cui_meddra}"]))

if not os.path.exists("brick"):
    os.mkdir("brick")

# Save the graph to a file
g.serialize(destination="brick/side_effects.ttl", format="turtle")
print(f"Created {len(g)} triples")