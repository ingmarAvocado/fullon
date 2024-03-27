from dataclasses import dataclass
from typing import Optional
from libs.structs.struct import Struct


@dataclass
class CatStrategyStruct(Struct):
    """Strategy struct"""
    cat_str_id: str = ''
    name: Optional[str] = ''
    take_profit: str = ''
    stop_loss: str = ''
    trailing_stop: str = ''
    timeout: str = ''
    pre_load_bars: Optional[int] = 0
    feeds: Optional[int] = 2
    pairs: bool = False
