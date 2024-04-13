from dataclasses import dataclass
from typing import Optional
from libs.structs.struct import Struct


@dataclass
class StrategyStruct(Struct):
    """Strategy struct"""
    str_id: Optional[int] = None
    cat_str_id: Optional[int] = None
    bot_id: Optional[int] = None
    uid: Optional[int] = None
    mail: str = ''
    name: str = ''
    cat_name: str = ''
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    trailing_stop: Optional[float] = None
    timeout: Optional[int] = None
    leverage: Optional[float] = None
    size_pct: Optional[float] = None
    size: Optional[float] = None
    size_currency: str = ""
    pre_load_bars: Optional[int] = 0
    feeds: Optional[int] = 2
    pairs: bool = False
