"""
It loads a user strategy depending on the type of strategy
STRATEGY_TYPE = "live"  # for live trading
STRATEGY_TYPE = "livedry"  # for live dry trading
STRATEGY_TYPE = "backtest"   # for step by step backtesting
STRATEGY_TYPE = "event"  # for event based backtesging
"""
from libs import strategy as strat

match strat.STRATEGY_TYPE:
    case "event":
        from libs.strategy import event_backtest_strategy as strategy
    case "backtest":
        from libs.strategy import backtest_strategy as strategy
    case "testlive":
        from libs.strategy import testlive_strategy as strategy
    case "live":
        from libs.strategy import live_strategy as strategy
    case "drylive":
        from libs.strategy import drylive_strategy as strategy
    case other:
        from libs.strategy import strategy
