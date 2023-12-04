from dataclasses import dataclass
from typing import Optional
from libs.structs.struct import Struct


@dataclass
class StrategyStruct(Struct):
    """Strategy struct"""
    bot_id: int = ''
    cat_str_id: str = ''
    uid: str = ''
    mail: Optional[str] = ''
    name: Optional[str] = ''
    cat_name: str = ''
    take_profit: str = ''
    stop_loss: str = ''
    trailing_stop: str = ''
    timeout: str = ''
    leverage: Optional[float] = None
    size_pct: Optional[float] = None
    size: Optional[float] = None
    size_currency: str = ""
    pre_load_bars: Optional[int] = 0
    feeds: Optional[int] = 2
