from pytest import mark
from panid import panid
import pandas as pd

slow = mark.skipif("not config.getoption('longrun')")

def test_drop_version():
    assert panid.drop_version("hello.there.nice.22") == "hello.there.nice"

@slow
def test_biomart_retrieve():
    data = panid.retrieve_biomart()
    
    # We can only do a loose check here
    assert data.keys() == panid.BIOMART_XML_REQUESTS.keys()
    for item in data.values():
        assert isinstance(item, pd.DataFrame)

EXPECTED_QUERY = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query  virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" datasetConfigVersion = "0.6" >

	<Dataset name = "hsapiens_gene_ensembl" interface = "default" >
        <Attribute name = "test" />
<Attribute name = "test2" />
    </Dataset>
</Query>"""

def test_query_generator():
    query = panid.gen_xml_query(["test", "test2"])

    assert query == EXPECTED_QUERY

