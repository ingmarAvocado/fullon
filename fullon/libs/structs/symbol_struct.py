from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
from libs.structs.struct import Struct


@dataclass
class SymbolStruct(Struct):
    """Symbol struct"""
    symbol_id: Optional[int] = None
    symbol: str = ''
    cat_ex_id: Optional[str] = None
    updateframe: Optional[str] = None
    backtest:  Optional[int] = None
    decimals: Optional[int] = None
    base: Optional[str] = None
    ex_base: Optional[str] = None
    only_ticker: Optional[bool] = False
    exchange_name: str = ''
    ohlcv_view: Optional[str] = None
    futures: Optional[bool] = False
