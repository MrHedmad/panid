from tempfile import NamedTemporaryFile as TP
from pandas.testing import assert_frame_equal
import pandas as pd
from io import StringIO

from panid.bin import bin

ORIGINAL = """ensembl_gene_id,other_data
ENSG00000000003.16,restructured
ENSG00000001036.14,banana
ENSG00000001084.13,papaya
"""

EXPECTED = """other_data,ensembl,gene_name,refseq_id
restructured,ENSG00000000003,TSPAN6,NM_003270
restructured,ENSG00000000003,TSPAN6,NM_001278740
restructured,ENSG00000000003,TSPAN6,NM_001278741
restructured,ENSG00000000003,TSPAN6,NM_001278742
restructured,ENSG00000000003,TSPAN6,NM_001278743
banana,ENSG00000001036,FUCA2,NM_032020
papaya,ENSG00000001084,GCLC,NM_001498
papaya,ENSG00000001084,GCLC,NM_001197115
"""

def test_panid_integration():
    with TP() as input, TP() as output:
        input.write(ORIGINAL.encode("utf-8"))
        input.flush()
        
        args = [
            input.name,
            "--output", output.name,
            "ensembl_gene_id:ensg_version>ensembl:ensg",
            "ensembl:ensg+gene_name:hgnc_symbol",
            "ensembl:ensg+refseq_id:refseq_rna_id"
        ]

        bin(args)

        result = pd.read_csv(output)

    expected = pd.read_csv(StringIO(EXPECTED))

    assert_frame_equal(expected, result, check_like=True)

