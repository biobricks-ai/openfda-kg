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
        WHERE brand_name IS NOT NULL
    )
    SELECT DISTINCT ON (brand_name)
        brand_name,
        array_agg(DISTINCT generic_name) as generic_name,
        array_agg(DISTINCT rxcui_item) as rxcui
    FROM unnested_data
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
		brand_name,
		dosage_form_code,
		marketing_status_code,
		route_code,
		(
			SELECT array_agg(DISTINCT struct_pack(name := ingredient.name, strength := ingredient.strength, cid := s.CID))
			FROM (
				SELECT unnest(active_ingredients) as ingredient
			)
			INNER JOIN synonyms s 
			ON UPPER(TRIM(s.Drug)) = UPPER(TRIM(ingredient.name))
		) as ingredients
	FROM products
""")
con.sql("""
	CREATE OR REPLACE TABLE products AS
	SELECT 
		p.brand_name,
		p.dosage_form_code,
		p.marketing_status_code,
		p.route_code,
		p.ingredients,
		o.rxcui
	FROM products p
	LEFT JOIN openfda o ON p.brand_name = o.brand_name
""")

con.sql("""
    CREATE OR REPLACE TABLE fda_side_effects AS
	SELECT 
		p.brand_name,
		p.dosage_form_code,
		p.marketing_status_code,
		p.route_code,
		p.ingredients,
		p.rxcui,
		array_agg(DISTINCT struct_pack(cui := u.cui, concept := u.concept)) FILTER (WHERE u.cui IS NOT NULL OR u.concept IS NOT NULL) as side_effect
	FROM products p
	LEFT JOIN (
		SELECT DISTINCT
			brand_name,
			dosage_form_code,
			marketing_status_code,
			route_code,
			ingredients,
			unnest(ingredients) as ingredient
		FROM products
	) p_unnested ON (
		p.brand_name = p_unnested.brand_name
		AND p.dosage_form_code IS NOT DISTINCT FROM p_unnested.dosage_form_code
		AND p.marketing_status_code IS NOT DISTINCT FROM p_unnested.marketing_status_code
		AND p.route_code IS NOT DISTINCT FROM p_unnested.route_code
	)
	LEFT JOIN (
		SELECT 
			STITCH_Compound_ID_stereo,
			UMLS_CUI as cui,
			UMLS_CUI_Concept_Name as concept,
		FROM side_effects
		WHERE UMLS_CUI IS NOT NULL
		
		UNION
		
		SELECT 
			STITCH_Compound_ID_stereo,
			UMLS_CUI_for_MedDRA_Term as cui,
			MedDRA_Concept_Name as concept,
		FROM side_effects
		WHERE UMLS_CUI_for_MedDRA_Term IS NOT NULL
	) u ON CAST(u.STITCH_Compound_ID_stereo AS BIGINT) = p_unnested.ingredient.cid
	WHERE p.brand_name IS NOT NULL
	GROUP BY 
		p.brand_name,
		p.dosage_form_code,
		p.marketing_status_code,
		p.route_code,
		p.ingredients,
		p.rxcui
""")
fda_side_effects = con.table("fda_side_effects")
fda_side_effects.show()




g = Graph()

# Define namespaces for your ontology
UMLS = Namespace("http://identifiers.org/umls:")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
GENE = Namespace("http://www.geneontology.org/formats/oboInOwl#")
RO = Namespace("http://purl.obolibrary.org/obo/RO_")
EDAM = Namespace("http://edamontology.org/")
EX = Namespace("http://example.org/drug/")
RXCUI = Namespace("http://purl.bioontology.org/ontology/RXNORM/")
DCE = Namespace("http://purl.org/dc/elements/1.1/")
BFO = Namespace("http://purl.obolibrary.org/obo/BFO_")
PUBCHEM = Namespace("http://rdf.ncbi.nlm.nih.gov/pubchem/compound/CID")
SIO = Namespace("http://semanticscience.org/resource/SIO_")

# Bind namespaces to the graph
g.bind("umls", UMLS)
g.bind("rdf", RDF)
g.bind("rdfs", RDFS)
g.bind("gene", GENE)
g.bind("ro", RO)
g.bind("edam", EDAM)
g.bind("ex", EX)
g.bind("rxcui", RXCUI)
g.bind("dce", DCE)
g.bind("bfo", BFO)
g.bind("pubchem", PUBCHEM)
g.bind("sio", SIO)


# Iterate through the products_meddra table and create triples
for row in tqdm(fda_side_effects.fetchall(), desc="Creating triples"):
	brand_name, dosage_form, marketing_status, route, ingredients, rxcuis, side_effects = row
	
	if not brand_name: continue

	# Create URI for the drug product
	drug_subject = EX[f"{hash(brand_name)}"]
	# Drug is a type of Medication (NCIT:C459)
	g.add((drug_subject, RDF.type, UMLS["C0013227"]))

	if ingredients:
		for name, strength, cid in ingredients:
			# drug has part cid + cid part of drug
			g.add((drug_subject, BFO["0000051"], PUBCHEM[f"{cid}"]))
			g.add((PUBCHEM[f"{cid}"], BFO["0000050"], drug_subject))

			# cid has type active ingredient
			g.add((PUBCHEM[f"{cid}"], RDF.type, UMLS["C1372955"]))
			# cid has value strength
			g.add((PUBCHEM[f"{cid}"], SIO["has-value"], Literal(f"{strength}")))
			

	# drug has label brand_name
	if brand_name:
		g.add((drug_subject, RDFS.label, Literal(brand_name)))
		# drug is a type of Proprietary Name (brand name; NCIT:C71898)
		g.add((drug_subject, RDF.type, UMLS["C0592503"]))
	
	# Drug has basic dose form
	if re.match(r'^C[0-9]+$', str(dosage_form)):
		g.add((drug_subject, UMLS["CL547851"], UMLS[f"{dosage_form}"]))
		# dosage_form is a type of dosage_form
		g.add((UMLS[f"{dosage_form}"], RDF.type, UMLS["C0013058"]))
		# dosage_form has source openfda
		g.add((UMLS[f"{dosage_form}"], DCE.source, Literal("openFDA")))
	else:
		g.add((drug_subject, UMLS["CL547851"], Literal(f"{dosage_form}")))
	# Drug has status
	if re.match(r'^C[0-9]+$', str(marketing_status)):
		g.add((drug_subject, GENE.status, UMLS[f"{marketing_status}"]))
		# marketing_status has type spl marketing status terminology
		g.add((UMLS[f"{marketing_status}"], RDF.type, UMLS["C3897481"]))
		# marketing status has source openfda
		g.add((UMLS[f"{marketing_status}"], DCE.source, Literal("openFDA")))
	else:
		g.add((drug_subject, GENE.status, Literal(f"{marketing_status}")))
	# Drug has exposure route
	if route:
		if re.match(r'^C[0-9]+$', str(route)):
			g.add((drug_subject, RO["0002242"], UMLS[f"{route}"]))
			# route is a type of drug route of administration
			g.add((UMLS[f"{route}"], RDF.type, UMLS["C0013153"]))
			# route has source openfda
			g.add((UMLS[f"{route}"], DCE.source, Literal("openFDA")))
		else:
			g.add((drug_subject, RO["0002242"], Literal(f"{route}")))
	
	# drug has identifier cid
	if rxcuis:
		for rxcui in rxcuis:
			g.add((drug_subject, EDAM.has_identifier, RXCUI[f"{rxcui}"]))

			# identifier has type identifier
			g.add((RXCUI[f"{rxcui}"], RDF.type, UMLS["C2348662"]))
			# identifier has type proprietary name
			g.add((RXCUI[f"{rxcui}"], RDF.type, UMLS["C0592503"]))
			# identifier has source Drugs@FDA
			g.add((RXCUI[f"{rxcui}"], DCE.source, Literal("openFDA")))
			# rxcui has label brand_name
			g.add((RXCUI[f"{rxcui}"], RDF.label, Literal(brand_name)))
	if side_effects:
		for cui, concept in side_effects:
			# drug has side effect term (umls term)
			g.add((drug_subject, UMLS["C0879626"], UMLS[f"{cui}"]))

			# identifier has type identifier
			g.add((UMLS[f"{cui}"], RDF.type, UMLS["C1707476"]))
			# identifier has source source
			g.add((UMLS[f"{cui}"], DCE.source, Literal("SIDER 4.1")))
			# identifier has label concept name
			g.add((UMLS[f"{cui}"], RDFS.label, Literal(str(concept))))

if not os.path.exists("brick"):
    os.mkdir("brick")

# Save the graph to a file
g.serialize(destination="brick/drugs@fda.ttl", format="turtle")
print(f"Created {len(g)} triples")

# close the duckdb con
con.close()

from datetime import datetime
import time
# debugging purposes triple counts:
triple_count_file = open('triple_count.txt', 'a')
triple_count_file.write(f"{len(g)} triples @ {datetime.now()} or {time.time()}")
triple_count_file.close()