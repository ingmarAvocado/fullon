from dataclasses import dataclass
from typing import Optional
from libs.structs.struct import Struct


@dataclass
class CrawlerStruct(Struct):
    """Symbol struct"""
    fid: Optional[int] = None
    uid: Optional[int] = None
    site: str = ''
    account: str = ''
    ranking: Optional[int] = None
    contra: bool = False
    expertise: str = ''
