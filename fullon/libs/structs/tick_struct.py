from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
from libs.structs.struct import Struct


@dataclass
class TickStruct(Struct):
    """Symbol struct"""
    symbol: str
    exchange: str
    price: float
    volume: float
    time: float
