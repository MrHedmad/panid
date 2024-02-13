from typing import TextIO, Self, Callable
from enum import StrEnum, Enum, auto
from dataclasses import dataclass
import re
import logging
from pathlib import Path
import time
import os
from io import BytesIO
import shutil
from functools import reduce
from copy import copy

import pandas as pd
from tqdm import tqdm
import requests

log = logging.getLogger(__name__)


BASE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query  virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" datasetConfigVersion = "0.6" >

	<Dataset name = "hsapiens_gene_ensembl" interface = "default" >
        {}
    </Dataset>
</Query>"""

def gen_xml_query(attributes: list[str]) -> str:
    queries = []
    for item in attributes:
        queries.append('<Attribute name = "{}" />'.format(item))

    return BASE_XML.format("\n".join(queries))

BIOMART = "https://asia.ensembl.org/biomart/martservice"
BIOMART_XML_REQUESTS = {
    "entrez": gen_xml_query(["ensembl_gene_id_version", "entrezgene_id"]),
    "refseq": gen_xml_query(
        [
            "ensembl_gene_id_version",
            "ensembl_transcript_id_version",
            "refseq_mrna",
            "refseq_ncrna"
        ]
    ),
    "symbols": gen_xml_query(["ensembl_gene_id_version", "hgnc_id", "hgnc_symbol"])
}

def lmap(*args, **kwargs):
    return list(map(*args, **kwargs))

class IdType(StrEnum):
    ENSG_VERSION = auto()
    ENSG = auto()
    ENST_VERSION = auto()
    ENST = auto()
    NCBI_GENE_ID = auto()
    REFSEQ_RNA_ID = auto()
    HGNC_ID = auto()
    HGNC_SYMBOL = auto()

class Symbol(Enum):
    ADD = "+"
    REPLACE = ">"

@dataclass
class Conversion:
    original: str
    original_type: IdType
    to: str
    to_type: IdType
    additive: bool

    @staticmethod
    def from_string(raw: str) -> Self:
        """Generate a new Conversion from a string

        Conversion synthax is as follows `<from>:<type><symbol><to>:<type>[?<how>]` where:
            - `<from>` is the name of the column in the input that has the IDs,
            - `<type>` is the type of the input or output columns, to be chosen
              from the available data types.
            - `<to>` is the name of the output column.
            - `<symbol>` either `+` or `>` to either preserve (`+`) or replace
              `>` the input column.
        """
        deconstructor = re.compile(r"(.+?):(.+?)(\+|>)(.+?):(.+?)$")

        res = deconstructor.match(raw)
        
        try:
            original = res.group(1)
            original_type = IdType(res.group(2))
            symbol = Symbol(res.group(3))
            to = res.group(4)
            to_type = IdType(res.group(5))
        except Exception as e:
            log.error(f"Invalid input conversion string: {e}")

        return Conversion(
            original=original,
            original_type=original_type,
            to=to,
            to_type=to_type,
            additive=(symbol == Symbol.ADD)
        )

class CachedData:
    # 604800 seconds = 7 days
    def __init__(
        self,
        location: Path,
        loader: Callable,
        saver: Callable,
        timeout_sec: int = 604800,
        binary: bool = False
    ):
        self._location: Path = location
        self._loader: Callable = loader
        self._saver: Callable = saver
        self._timeout: int = timeout_sec
        self._binary: bool = binary

    @property
    def is_timed_out(self) -> bool:
        try:
            diff = self._location.lstat().st_mtime - time.time()
        except FileNotFoundError:
            # If there is no file, it's timed out.
            return True
        return diff > self._timeout

    @property
    def data(self):
        """Return the cached data"""
        if self.is_timed_out:
            os.makedirs(self._location.parent, exist_ok=True)
            with self._location.open("wb+" if self._binary else "w+") as stream:
                try:
                    self._saver(stream)
                except Exception as e:
                    # Remove the probably broken data
                    os.remove(self._location)
                    raise e
        
        with self._location.open("rb" if self._binary else "r") as stream:
            return self._loader(stream)

def pbar_get(url: str, params: dict = {}, disable: bool = False) -> BytesIO:
    """A requests.get() call with an added download bar

    The bar is suppressed if the log has an effective level of more than 20
    - anything greater than INFO - so the program runs silently if we don't want
    logging.

    Raises Abort, killing Daedalus if the download fails. This is intended.

    Tries to estimate download sizes from the response headers.

    Args:
        url (str): The url to download from
        params (dict, optional): The params to pass to the GET request. Defaults to {}.
        disable (bool, optional): Disable the progress bar?. Defaults to False.

    Raises:
        Abort: If the request failed.

    Returns:
        BytesIO: The downloaded data, as bytes wrapped in a BytesIO object.
    """
    resp = requests.get(url=url, params=params, stream=True)

    # Show only if we can show INFOs
    disable = disable or log.getEffectiveLevel() > 20

    if resp.status_code > 299 or resp.status_code < 200:
        log.error(
            f"Request got response {resp.status_code} -- {resp.reason}. Aborting."
        )
        raise RuntimeError

    log.info(f"Retrieving response from {url}...")
    size = int(resp.headers.get("Content-Length", 0))

    desc = "[Unknown file size]" if size == 0 else ""
    bytes = BytesIO()
    # I add some delay so the logging does not get (too) mangled up.
    # The download bars are there just to check on very long download tasks,
    # like from biomart.
    with tqdm.wrapattr(
        resp.raw, "read", total=size, desc=desc, disable=disable
    ) as read_raw:
        shutil.copyfileobj(read_raw, bytes)

    # Reset the pointer after we've written all the data
    bytes.seek(0)
    return bytes


def retrieve_biomart() -> dict[pd.DataFrame]:
    """Retrieve data from biomart.

    Acts upon all biomart URLs. The columns are hard-coded in.

    TODO: It might be possible to act on the XMLs to have the colnames arrive
    with the data.

    Returns:
        DataDict: The dictionary with the downloaded data.
    """
    log.info("Starting to retrieve from BioMart.")

    result = {}
    for key, value in BIOMART_XML_REQUESTS.items():
        log.info(f"Attempting to retrieve {key}...")

        data = pbar_get(url=BIOMART, params={"query": value})

        log.info("Casting response...")
        # The downloaded frames are sometimes big, so typing of the cols can
        # be hard. See the docs for why low_memory is needed here.
        # Not like it makes a real difference, memory-wise.
        df = pd.read_table(data, sep="\t", header=0, low_memory=False)

        result[key] = df

        # I don't want to deal with THe rANdom CaPItaLizATIon ThAt biOMarT uSEs
        # so I just standardize all colnames here
        def standardize_col(x: str):
            return x.lower().strip().replace(" ", "_")

        df.columns = lmap(standardize_col, df.columns)

    log.info("Got all necessary data from BioMart.")

    return result

def drop_version(id: str) -> str:
    return ".".join(id.split(".")[:-1])

def fetch_id_data() -> pd.DataFrame:
    """Fetch IDs from biomart"""
    data = retrieve_biomart()

    # collapse all the biomart frames
    frames = data.values()
    for frame in frames:
        print(frame.columns)
    merged = reduce(
            lambda x, y: pd.merge(x, y, how="outer", on="gene_stable_id_version"),
            frames
        )

    # Run some cleanup since the colnames are pretty bad
    merged.rename(
        columns = {
            "gene_stable_id_version": "ensg_version",
            "ncbi_gene_(formerly_entrezgene)_id": "ncbi_gene_id",
            "transcript_stable_id_version": "enst_version",
            "refseq_mrna_id": "refseq_rna_id"
        },
        inplace=True,
    )

    # Fuse the `refseq_mrna_id` and `refseq_ncrna_id` columns
    # since they do not conflict
    merged["refseq_rna_id"] = merged["refseq_rna_id"].fillna(merged["refseq_ncrna_id"])
    merged.drop(columns=["refseq_ncrna_id"], inplace=True)

    # bloat the "ensg" column
    merged["ensg"] = lmap(drop_version, merged["ensg_version"].tolist())
    merged["enst"] = lmap(drop_version, merged["enst_version"].tolist())

    return merged


def panid_convert(input: pd.DataFrame, conversion: Conversion, id_table: pd.DataFrame) -> pd.DataFrame:
    selection = id_table[[conversion.to_type.value, conversion.original_type.value]]
    # If the target column (the one to merge) has missing data, it's best to
    # simply drop the NAs here, since the merge would re-add them.
    # If we do not, the selection might have entries like this:
    # col_one col_two
    #     aaa     bbb
    #     aaa      NA
    # (since it derives from a much larger frame), and we would get these
    # duplicated values in the resulting dataframe.
    # So, we just drop the NAs in the additional column.
    selection = selection.dropna(axis=0, subset=conversion.to_type.value)
    selection = selection.rename(columns = {conversion.original_type.value : conversion.original})
    selection = selection.drop_duplicates()
    
    merged = input.merge(
        selection,
        how = "left"
    )
    merged = merged.drop_duplicates()
    
    if not conversion.additive:
        merged = merged.drop(columns=[conversion.original])

    merged = merged.rename(columns={conversion.to_type: conversion.to})

    return merged


def panid(input_stream: TextIO, output_stream: TextIO, conversions: list[Conversion]):
    cache = CachedData(
        location=Path("/var/tmp/panid_cache/ID_data.csv"),
        loader=pd.read_csv,
        saver=lambda conn: fetch_id_data().to_csv(conn, index=False)
    )

    data: pd.DataFrame = cache.data

    input_data = pd.read_csv(input_stream)
    conversions = [Conversion.from_string(x) for x in conversions]

    converted_data = input_data
    for i, conv in enumerate(conversions):
        log.info(f"Applying conversion {i + 1}...")
        if conv.original not in converted_data.columns:
            raise ValueError(f"\t-{conv.original} not in input columns: {input_data.columns}")
        converted_data = panid_convert(converted_data, conv, copy(data))

    converted_data = converted_data.drop_duplicates()

    converted_data.to_csv(output_stream, index=False)

