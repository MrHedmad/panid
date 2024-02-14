<div align="center">
  
![PanID logo](https://raw.githubusercontent.com/MrHedmad/panID/main/docs/resources/panid_logo.png)

</div>

Panid is a small tool to convert between different gene IDs.

It currently supports conversions from/to these IDs:
- Ensembl Gene IDs (`ensg`) and Ensembl Gene ID with Version (`ensg_version`);
- Ensembl Transcript Ids (`enst`) and Ensembl Transcript ID with Version (`enst_version`);
- NCBI Gene ID (formerly Entrez gene ID) (`ncbi_gene_id`);
- Refseq coding and non-coding transcript ID (`refseq_rna_id`);
- Hugo Gene Nomenclature ID (`hgnc_id`) and symbol (`hgnc_symbol`);

More IDs may be implemented in the future.

The tool contacts BioMart and downloads these IDs upon first runtime.
It saves them to `/var/tmp/panid/` to reuse them later.
After one week, the data is regenerated upon the next execution.
It uses this data to convert between the different IDs relatively quickly.

## Installation
You need Python `3.11` or later.
Install `panid` with:
```bash
pip install git+https://github.com/MrHedmad/panid.git
```

## Usage
Use `panid -h` to get an overview:
```
usage: panid [-h] [--output OUTPUT] input_file conversion_string [conversion_string ...]

Convert between IDs quickly!

positional arguments:
  input_file         An input .csv file to convert
  conversion_string  A conversion string to use

options:
  -h, --help         show this help message and exit
  --output OUTPUT    An output file to save to
```
The only difficult parameter is `conversion_string` that are used to map one ID
to another.
By default `panid` prints the output `.csv` to `stdout`.

A conversion string looks like this:
```
<from>:<type><symbol><to>:<type>
```
where:
- `<from>` is the name of the column in the input that has the IDs,
- `<type>` is the type of the input or output columns, to be chosen
  from the available data types (the values in parentheses above).
- `<to>` is the name of the output column.
- `<symbol>` either `+` or `>` to either preserve (`+`) or replace
  `>` the input column.

Some examples:
- `ensembl_gene_id:ensg_version>ensembl:ensg`
  - Convert the `ensembl_gene_id` column, that hold IDs of type `ensg_version`
    to the `ensembl` column that holds `ensg` IDs.
- `ensembl:ensg+gene_name:hgnc_symbol`
  - Add the the `gene_name` column that holds gene symbols following the IDs in
    the `ensembl` column.
- `ensembl:ensg+refseq_id:refseq_rna_id`
  - Same as before, adding the `refseq_id` column with RefSeq ids.

You can use multiple conversion strings in a single call to `panid` to convert
multiple times.
Each string is applied in order, so you can do back-to-back conversion (if you
like, for some reason).

For example, this frame:
```
     ensembl_gene_id   other_data
1 ENSG00000000003.16 restructured
2 ENSG00000001036.14       banana
3 ENSG00000001084.13       papaya
```
Becomes this frame by appling the above examples in order:
```
    other_data         ensembl gene_name    refseq_id
1 restructured ENSG00000000003    TSPAN6    NM_003270
2 restructured ENSG00000000003    TSPAN6 NM_001278740
3 restructured ENSG00000000003    TSPAN6 NM_001278741
4 restructured ENSG00000000003    TSPAN6 NM_001278742
5 restructured ENSG00000000003    TSPAN6 NM_001278743
6       banana ENSG00000001036     FUCA2    NM_032020
7       papaya ENSG00000001084      GCLC    NM_001498
8       papaya ENSG00000001084      GCLC NM_001197115
```
(this case is [one of PanID tests](https://github.com/MrHedmad/panID/blob/main/tests/test_integration.py))

> [!WARNING]
> The order of the columns in the output **might not be the same** as the one in
> the input!

