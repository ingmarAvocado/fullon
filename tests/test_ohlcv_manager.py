"""
comment
"""
from __future__ import unicode_literals, print_function
from numpy import right_shift
import pytest
from fullon.libs import log
from fullon.libs import cache
from fullon.libs.structs.symbol_struct import SymbolStruct
from fullon.run.ohlcv_manager import OhlcvManager
from fullon.run.install_manager import InstallManager
import threading
from time import sleep


logger = log.fullon_logger(__name__)
symbol_name = "AGLD/USD"

@pytest.fixture(scope="module")
def symbol():
    VIEW_NAME = "kraken_xrp_usd.candles1m"
    OHLCV = f"""
    CREATE MATERIALIZED VIEW kraken_agld_usd.candles1m
    WITH (timescaledb.continuous) AS
    SELECT time_bucket('1 minutes', timestamp) AS ts,
            FIRST(price, timestamp) as open,
            MAX(price) as high,
            MIN(price) as low,
            LAST(price, timestamp) as close,
            SUM(volume) as vol
    FROM kraken_agld_usd.trades
    WHERE kraken_agld_usd.trades.timestamp > '2017-01-01'
    GROUP BY ts WITH NO DATA;
    commit;
    SELECT add_continuous_aggregate_policy('kraken_agld_usd.candles1m',
        start_offset => INTERVAL '2 h',
        end_offset => INTERVAL '1 h',
        schedule_interval => INTERVAL '1 h');
    commit;
    ALTER TABLE agld_usd_USD.candles1m  RENAME COLUMN ts to timestamp;
    """
    with cache.Cache() as store:
        sym = store.get_symbol(symbol='BTC/USD', exchange_name='kraken')

    SYMBOL = {"symbol": symbol_name,
              "exchange_name": "kraken",
              "updateframe": "1h",
              "backtest": 2,
              "decimals": 6,
              "base": "USD",
              "futures": False,
              "only_ticker": True,
              "cat_ex_id": sym.cat_ex_id,
              "ohlcv_view": OHLCV}

    yield SymbolStruct.from_dict(SYMBOL)


@pytest.fixture(scope="module")
def ohlcv():
    manager = OhlcvManager()
    yield manager
    del manager


@pytest.mark.order(1)
def test_install_test_symbols(symbol):
    """Test installation of test symbols."""
    install = InstallManager()
    install.remove_symbol_by_struct(symbol=symbol)
    install.install_symbol(symbol=symbol)


@pytest.mark.order(2)
def test_run_ohlcv_loop(ohlcv, symbol):
    """Test installation of test symbol."""
    result = ohlcv.run_ohlcv_loop(
        symbol=symbol_name, exchange=symbol.exchange_name, test=True)
    assert result is None


@pytest.mark.order(3)
def test_relaunch_dead_threads(ohlcv, symbol):
    ohlcv.threads[f'{symbol.exchange_name}:{symbol_name}'] = threading.Thread()
    ohlcv.threads[f'{symbol.exchange_name}:{symbol_name}'].is_alive = lambda: False
    ohlcv.relaunch_dead_threads(test=True)
    sleep(4)
    ohlcv.stop_all()
    install = InstallManager()
    install.remove_symbol(symbol_id=symbol.symbol_id)
