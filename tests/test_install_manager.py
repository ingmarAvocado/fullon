from libs.structs.symbol_struct import SymbolStruct
from libs.database import Database
from run.install_manager import InstallManager
from unittest.mock import MagicMock
import pytest
import os

@pytest.fixture
def install_manager():
    manager = InstallManager()
    manager._install_base_in_database = MagicMock(return_value=True)
    manager._install_strategy_in_database = MagicMock(return_value=True)
    manager._install_exchange_in_database = MagicMock(return_value=True)
    manager._install_cache_in_database = MagicMock(return_value=True)
    manager._get_top_from_database = MagicMock(return_value=[])
    manager._clean_top_in_database = MagicMock(return_value=[])
    return manager



@pytest.mark.order(1)
def test_init(install_manager):
    assert install_manager is not None

@pytest.mark.order(2)
def test_make_backup(install_manager):
    res = install_manager.make_backup(full=False)
    assert 'backup' in res
    # Check if the file exists and then remove it
    if os.path.exists(res):
        os.remove(res)


@pytest.mark.order(3)
def test_list_backups(install_manager):
    backups = install_manager.list_backups()
    assert isinstance(backups, list)

"""
def test_install_base(install_manager):
    result = install_manager.install_base()
    assert result is None


def test_clean_base(install_manager):
    result = install_manager.clean_base()
    assert result is None
"""


@pytest.mark.order(4)
def test_test_pre_install(install_manager):
    result = install_manager.test_pre_install()
    assert isinstance(result, bool)


@pytest.mark.order(5)
def test_install_strategies(install_manager):
    res = install_manager.install_strategies()
    assert isinstance(res, bool)


@pytest.mark.order(6)
def test_list_cat_strategies(install_manager):
    res = install_manager.list_cat_strategies(page=1, page_size=2)
    assert isinstance(res, list)
    assert len(res) > 1


@pytest.mark.order(7)
def test_list_symbols(install_manager):
    res = install_manager.list_symbols(page=1, page_size=2)
    assert isinstance(res, list)
    assert len(res) > 1


@pytest.mark.order(9)
def test_list_cat_exchanges(install_manager):
    res = install_manager.list_cat_strategies(page=1, page_size=2)
    assert isinstance(res, list)
    assert len(res) > 0


@pytest.mark.order(9)
def test_list_strategy_bots(install_manager):
    name = 'trading101'
    res = install_manager.list_strategy_bots(cat_str_name=name)
    assert isinstance(res[0].name, str)


@pytest.mark.order(10)
def test_list_symbols_exchange(install_manager):
    res = install_manager.list_symbols_exchange(exchange='krak')
    assert 'Error' in res[0]
    res = install_manager.list_symbols_exchange(exchange='kraken')
    assert len(res) > 2


@pytest.mark.order(11)
def test_install_exchanges(install_manager):
    res = install_manager.install_exchanges()
    assert res is None


@pytest.mark.order(12)
def test_install_and_remove_symbol(install_manager):
    # Define a sample symbol to be installed
    SYMBOL_NAME = "AGLD/USD"
    dbase = Database()
    cat_ex_id = dbase.get_exchange_cat_id(name="kraken")
    SYMBOL = {"symbol": SYMBOL_NAME,
              "exchange_name": "kraken",
              "updateframe": "1h",
              "backtest": 5,
              "decimals": 6,
              "base": "USD",
              "futures": False,
              "cat_ex_id": cat_ex_id,
              "ohlcv_view": ''}
    sample_symbol = SymbolStruct.from_dict(SYMBOL)


    # Install the symbol
    install_manager.install_symbol(symbol=sample_symbol)

    # Verify if the symbol was installed correctly
    symbol = dbase.get_symbol(symbol=sample_symbol.symbol,
                              cat_ex_id=cat_ex_id)
    assert symbol is not None

    # Remove the symbol
    install_manager.remove_symbol(symbol_id=symbol.symbol_id)

    # Verify if the symbol was removed correctly
    symbol = dbase.get_symbol(symbol=sample_symbol.symbol,
                              cat_ex_id=cat_ex_id)
    assert symbol is None
    del dbase
