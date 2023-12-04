from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from libs.structs.struct import Struct


@dataclass
class OrderStruct(Struct):
    """Order struct"""

    order_id: str = ''
    bot_id: str = ''
    uid: str = ''
    ex_id: str = ''
    ex_order_id: str = ''
    cat_ex_id: str = ''
    exchange: str = ''
    symbol: str = ''
    order_type: str = ''
    side: str = ''
    volume: float = 0.0
    fee: float = 0
    cost: float = 0
    price: Optional[float] = None
    plimit: Optional[float] = None
    futures: bool = False
    leverage: float = 1
    status: str = ''
    command: str = ''
    subcommand: str = ''
    reason: str = ''
    reduce_only: bool = False
    timestamp: str = ''
