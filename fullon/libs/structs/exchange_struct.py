"""
exchange struct
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from libs.structs.struct import Struct


@dataclass
class ExchangeStruct(Struct):
    """Exchange struct"""
    name: str = ''
    cat_name: str = ''
    ex_id: Optional[int] = None
    uid: str = '-'
    key: str = ''
    key2: str = ''
    secret: str = ''
    test: bool = False
    cat_ex_id: str = ''
    active: bool = False
    bot: str = ''
    dry_run: bool = True
    symbol: str = ''
