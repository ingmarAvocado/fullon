from dataclasses import dataclass
from typing import Optional
from libs.structs.struct import Struct


@dataclass
class CrawlerAnalyzerStruct(Struct):
    """crawler post struct"""
    prompt: str = ''
    title: str = ''
    aid:  int = 0
