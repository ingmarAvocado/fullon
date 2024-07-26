from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
from libs.structs.struct import Struct


@dataclass
class TradeStruct(Struct):
    """Trade struct"""
    trade_id: int = ''
    ex_trade_id: str = ''
    ex_order_id: str = ''
    uid: str = ''
    ex_id: str = ''
    symbol: str = ''
    order_type: str = ''
    order: str = ""
    side: str = ''
    volume: Optional[float] = 0
    price: Optional[float] = None
    cost: Optional[float] = 0
    prev_cost: Optional[float] = 0
    fee: Optional[float] = 0
    cur_volume: Optional[float] = 0
    cur_avg_price: Optional[float] = 0
    cur_avg_cost: Optional[float] = 0
    cur_fee: Optional[float] = 0
    roi: Optional[float] = 0
    roi_pct: Optional[float] = 0
    total_fee: float = 0.0
    time: str = ''
    timestamp: float = 0.0
    leverage: float = 1.0
    limit: str = ''
    closingtrade: bool = False
    bot_id: str = ''
    reason: str = ''
