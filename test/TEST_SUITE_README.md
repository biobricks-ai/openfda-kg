# FDA Data Processing Test Suite

This comprehensive test suite validates the correctness of the `01_process.py` script that converts FDA drug application data from Parquet format to RDF/Turtle format.

## Overview

The test suite consists of multiple test files that validate different aspects of the data processing pipeline:

1. **`test_01_process.py`** - Main comprehensive test suite
2. **`test_ttl_validation.py`** - Specialized TTL output validation
3. **`run_tests.py`** - Test runner script with reporting
4. **`pytest.ini`** - Test configuration

## Test Categories

### 1. Unit Tests (`TestURIBuilders`, `TestSafeGetArrayItems`)
- **Purpose**: Test individual functions in isolation
- **Coverage**:
  - URI building functions for different entity types
  - Safe array item extraction utility
  - Special character handling and URL encoding
  - Edge cases with null/empty inputs

### 2. Relationship Extraction Tests (`TestRelationshipExtraction`)
- **Purpose**: Validate RDF triple generation from FDA data
- **Coverage**:
  - Application-sponsor relationships
  - OpenFDA data processing (brand names, manufacturers, etc.)
  - NDC, UNII, RxCUI, SPL ID relationships
  - Product and ingredient relationships
  - Strength measurements and dosage forms
  - Route of administration mappings

### 3. Edge Case Tests (`TestEdgeCases`)
- **Purpose**: Test error handling and data quality issues
- **Coverage**:
  - Missing application numbers
  - Null/empty sponsor names
  - Empty OpenFDA sections
  - Malformed product data
  - Large arrays and performance implications

### 4. Integration Tests (`TestIntegration`, `TestNamespaceValidation`)
- **Purpose**: Test end-to-end processing and semantic correctness
- **Coverage**:
  - Complete row processing workflow
  - Batch processing simulation
  - RDF graph validation
  - Namespace definitions and usage
  - Ontology URI validity

### 5. TTL Validation Tests (`TTLValidationTest`, `TTLComparisonTest`)
- **Purpose**: Validate the actual Turtle output format and content
- **Coverage**:
  - TTL syntax validity
  - Required namespace prefixes
  - URI format correctness
  - Semantic property usage
  - Graph connectivity and structure
  - Data type consistency

### 6. Performance Tests (`TestPerformance`)
- **Purpose**: Validate performance and scalability
- **Coverage**:
  - Large dataset processing
  - Memory usage optimization
  - Processing time constraints

## Data Structure Validation

The tests validate processing of the following FDA data structure:

```json
{
  "application_number": "ANDA076187",
  "sponsor_name": "MYLAN",
  "submissions": [...],
  "openfda": {
    "brand_name": ["LEVOTHYROXINE SODIUM"],
    "generic_name": ["LEVOTHYROXINE SODIUM"],
    "manufacturer_name": ["Mylan Pharmaceuticals Inc."],
    "package_ndc": ["0378-1800-77", ...],
    "product_ndc": ["0378-1800", ...],
    "unii": ["9J765S329G"],
    "rxcui": ["892246", ...],
    "spl_set_id": ["e95720f2-91c9-a6d0-f7d5-8bcb94d07bbc"],
    ...
  },
  "products": [
    {
      "active_ingredients": [
        {
          "name": "LEVOTHYROXINE SODIUM",
          "strength": "0.175MG"
        }
      ],
      "brand_name": "LEVOTHYROXINE SODIUM",
      "dosage_form": "TABLET",
      "route": "ORAL",
      ...
    }
  ]
}
```

## Expected RDF Output Patterns

The tests validate that the following RDF patterns are generated:

### Application Relationships
```turtle
<https://api.fda.gov/drug/application/ANDA076187> a BAO:0000040 ;
    SIO:000136 company:MYLAN ;                    # sponsored by
    RO:0000057 <.../product/0> ;                  # has participant
    dcterms:identifier "ANDA076187" .
```

### Company/Organization Relationships
```turtle
company:MYLAN a SIO:000012 ;                     # organization
    rdfs:label "MYLAN" .
```

### Substance/Chemical Relationships
```turtle
unii:9J765S329G a CHEMINF:000000 .              # chemical entity

<.../application/ANDA076187> RO:0000057 unii:9J765S329G .
```

### Product and Ingredient Relationships
```turtle
<.../product/0> a biolink:Drug ;
    RO:0000057 <.../ingredient/0> .              # has participant

<.../ingredient/0> a CHEMINF:000000 ;           # chemical entity
    SIO:000221 <.../strength> .                 # has measurement value
```

## Running the Tests

### Prerequisites
```bash
pip install pytest pandas pyarrow rdflib numpy tqdm
```

### Using the Test Runner (Recommended)
```bash
# Run all tests
python run_tests.py

# Run specific test categories
python run_tests.py --unit
python run_tests.py --integration
python run_tests.py --edge-cases
python run_tests.py --performance

# Validate sample data only
python run_tests.py --validate-data
```

### Using pytest directly
```bash
# Run all tests
pytest test_01_process.py -v

# Run specific test classes
pytest test_01_process.py::TestURIBuilders -v
pytest test_01_process.py::TestRelationshipExtraction -v

# Run TTL validation tests
pytest test_ttl_validation.py -v

# Run with detailed output
pytest test_01_process.py -v -s --tb=long
```

## Test Data Requirements

The test suite requires:

1. **`out.txt`** - Sample FDA data in JSON format (provided)
2. **`stages/01_process.py`** - The main processing script
3. **Sample TTL output** (generated during testing)

## Validation Criteria

### URI Format Validation
- Application URIs: `https://api.fda.gov/drug/application/{app_number}`
- Company URIs: `https://api.fda.gov/drug/company/{clean_name}`
- UNII URIs: `https://fdasis.nlm.nih.gov/srs/unii/{unii}`
- NDC URIs: `https://www.fda.gov/.../ndc-directory/{ndc}`

### Semantic Relationship Validation
- **SIO:000136** - "is sponsored by" (application → sponsor)
- **RO:0002234** - "manufactured by" (application → manufacturer)
- **SIO:000671** - "has identifier" (application → NDC/RxCUI)
- **RO:0000057** - "has participant" (application → substances/products)
- **SIO:000221** - "has measurement value" (ingredient → strength)
- **ExO:0000002** - "has exposure route" (product → route)

### Data Type Validation
- URI subjects and objects must be `URIRef` instances
- Labels and names must be `Literal` instances
- Type relationships must use `URIRef` objects
- Proper TTL syntax and namespace usage

## Expected Test Results

A successful test run should show:
- All URI builders working correctly with various inputs
- Proper RDF triple generation for all data fields
- Valid TTL syntax and semantic structure
- Correct namespace usage and ontology compliance
- Robust error handling for edge cases
- Acceptable performance for large datasets

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure the script is in the correct location
   ls stages/01_process.py
   ```

2. **Missing Dependencies**
   ```bash
   pip install -r requirements.txt  # if available
   pip install pytest pandas pyarrow rdflib numpy tqdm
   ```

3. **Sample Data Missing**
   ```bash
   # Ensure out.txt exists and contains valid JSON
   python -c "import json; json.load(open('out.txt'))"
   ```

4. **TTL Syntax Errors**
   - Check namespace definitions in the script
   - Validate URI encoding for special characters
   - Ensure proper literal quoting

### Debug Mode
```bash
# Run with maximum verbosity
pytest test_01_process.py -v -s --tb=long --capture=no

# Run single test for debugging
pytest test_01_process.py::TestRelationshipExtraction::test_extract_basic_application_relationships -v -s
```

## Extending the Test Suite

To add new tests:

1. **New URI Builder**: Add test in `TestURIBuilders`
2. **New Relationship Type**: Add test in `TestRelationshipExtraction`
3. **New Data Field**: Update sample data and add corresponding tests
4. **New Validation**: Add test in `TTLValidationTest`

Example new test:
```python
def test_new_relationship_type(self, sample_fda_row):
    """Test extraction of new relationship type"""
    triples = extract_relationships_from_row(sample_fda_row)
    graph = RDFTestUtils.create_test_graph(triples)
    
    # Add specific validation logic
    assert expected_condition, "Validation message"
```

## Performance Benchmarks

The test suite includes performance validation:
- Processing large arrays (100+ items) should complete in < 1 second
- Memory usage should remain stable across multiple large datasets
- Graph serialization should handle 500+ triples efficiently

## Contributing

When modifying the processing script (`01_process.py`), ensure:
1. All existing tests pass
2. New functionality includes corresponding tests
3. TTL output remains valid and semantically correct
4. Performance characteristics are maintained 