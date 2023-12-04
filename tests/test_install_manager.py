from fullon.libs import log, settings, cache
from fullon.libs.settings_config import fullon_settings_loader
from fullon.libs.structs.symbol_struct import SymbolStruct
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


def test_init(install_manager):
    assert install_manager is not None


def test_make_backup(install_manager):
    res = install_manager.make_backup(full=False)
    assert 'backup' in res
    # Check if the file exists and then remove it
    if os.path.exists(res):
        os.remove(res)


def test_list_backups(install_manager):
    backups = install_manager.list_backups()
    assert isinstance(backups, list)

'''
def test_install_base(install_manager):
    result = install_manager.install_base()
    assert result is None


def test_clean_base(install_manager):
    result = install_manager.clean_base()
    assert result is None
'''


def test_test_pre_install(install_manager):
    result = install_manager.test_pre_install()
    assert isinstance(result, bool)


def test_install_strategies(install_manager):
    res = install_manager.install_strategies()
    assert isinstance(res, bool)


def test_list_cat_strategies(install_manager):
    res = install_manager.list_cat_strategies(page=1, page_size=2)
    assert isinstance(res, list)
    assert len(res) > 1


def test_list_symbols(install_manager):
    res = install_manager.list_symbols(page=1, page_size=2)
    assert isinstance(res, list)
    assert len(res) > 1


def test_list_cat_exchanges(install_manager):
    res = install_manager.list_cat_strategies(page=1, page_size=2)
    assert isinstance(res, list)
    assert len(res) > 0


def test_list_symbols_exchange(install_manager):
    res = install_manager.list_symbols_exchange(exchange='krak')
    assert 'Error' in res[0]
    res = install_manager.list_symbols_exchange(exchange='kraken')
    assert len(res) > 2


def test_install_exchanges(install_manager):
    res = install_manager.install_exchanges()
    assert res is None


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


def test_add_and_remove_user(install_manager):
    user = {
        'mail': 'test_password',
        'password': 'test_password',
        'f2a': 'test_f2a',
        'role': 'test_role',
        'name': 'Test',
        'lastname': 'User',
        'phone': '1234567890',
        'id_num': '123456',
    }

    # Add the user
    install_manager.add_user(user)

    # Check if the user was added
    dbase = Database()
    user_id = dbase.get_user_id(mail=user['mail'])
    assert user_id is not None
    # Remove the user
    install_manager.remove_user(user_id=user_id)

    # Check if the user was removed
    user_id_after_removal = dbase.get_user_id(mail=user['mail'])
    assert user_id_after_removal is None
    del dbase
