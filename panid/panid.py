from typing import TextIO, Self, Callable
from enum import StrEnum, Enum, auto
from dataclasses import dataclass
import re
import logging
import pandas as pd
from pathlib import Path
import time
import os

log = logging.getLogger(__name__)

class MergeMethod(StrEnum):
    INNER = auto()
    OUTER = auto()

class IdType(StrEnum):
    ENSEMBL_GENE_ID = auto()
    ENSEMBL_GENE_ID_VERSION = auto()

class Symbol(Enum):
    ADD = "+"
    REPLACE = ">"

@dataclass
class Conversion:
    original: str
    original_type: IdType
    to: str
    to_type: IdType
    how: MergeMethod
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
            - `<how>` either `inner` or `outer` to control how the column is
              substituted. If omitted, defaults to `outer`, adding NAs to
              unmatched IDs.
        """
        deconstructor = re.compile(r"(.+?):(.+?)(\+|>)(.+?):(.+?)(?:\?(.+?))?$")

        res = deconstructor.match(raw)
        
        try:
            original = res.group(1)
            original_type = IdType(res.group(2))
            symbol = Symbol(res.group(3))
            to = res.group(4)
            to_type = IdType(res.group(5))
            how = MergeMethod(res.group(6) or "outer")
        except Exception as e:
            log.error(f"Invalid input conversion string: {e}")

        return Conversion(
            original=original,
            original_type=original_type,
            to=to,
            to_type=to_type,
            how=how,
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
        diff = self._location.getmtime() - time.time()
        return diff > self._timeout

    @property
    def data(self):
        """Return the cached data"""
        if not self._location.exists or self.is_timed_out:
            os.makedirs(self._location.parent, exist_ok=True)
            with self._location.open("wb+" if self._binary else "w+") as stream:
                self._saver(stream)
        
        with self._location.open("rb" if self._binary else "r") as stream:
            return self._loader(stream)


def panid(input_stream: TextIO, output_stream: TextIO, conversions: list[Conversion]):
    cache = CachedData()
