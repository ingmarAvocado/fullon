from dataclasses import dataclass
from libs.structs.struct import Struct
import arrow

@dataclass
class PositionStruct(Struct):
    """Position struct"""
    symbol: str
    cost: float = 0
    volume: float = 0
    fee: float = 0
    count: float = 0
    price: float = 0
    timestamp: float = arrow.utcnow().timestamp()
    ex_id: str = ""
