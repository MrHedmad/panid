from panid.panid import Conversion, IdType, MergeMethod

conversion_tests = [
    (
        "ensg:ensembl_gene_id+ensgv:ensembl_gene_id_version",
        Conversion(
            "ensg", 
            IdType.ENSEMBL_GENE_ID,
            "ensgv",
            IdType.ENSEMBL_GENE_ID_VERSION,
            MergeMethod.OUTER,
            True
        )
    ),
    (
        "banana:ensembl_gene_id_version>papayalama wow!:ensembl_gene_id?inner",
        Conversion(
            "banana",
            IdType.ENSEMBL_GENE_ID_VERSION,
            "papayalama wow!",
            IdType.ENSEMBL_GENE_ID,
            MergeMethod.INNER,
            False
        )
    )
]

def test_conversion_parsing():
    for string, conversion in conversion_tests:
        print(f"Testing {string}")
        assert Conversion.from_string(string) == conversion

