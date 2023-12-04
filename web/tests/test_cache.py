from __future__ import unicode_literals, print_function
import sys
from libs import settings
from run import system_manager
from libs import cache
import arrow


def test_start_cache_server():
    """description"""
    install = system_manager.InstallManager()
    store = cache.Cache()
    flag = store.test()
    if flag:
        install.install_cache()
    assert (flag is True) is True


def test_delete_from_top_1():
    """description"""
    store = cache.Cache()
    component = "tick"
    pid = 1001
    result = store.delete_from_top(component=None,
                                   pid=pid)
    assert (result == 0) is True
    result = store.delete_from_top(component=component,
                                   pid=None)
    assert (result == 0) is True
    del(store)
    return True


def test_update_process_1():
    """description"""
    store = cache.Cache()
    tipe = "tick"
    key = "kraken"
    message = "update"
    result = store.update_process(tipe=tipe,
                              key=key,
                              message=message)
    assert (result is False) is True
    tipe = "ohlcv"
    result = store.update_process(tipe=tipe,
                              key=key,
                              message=message)
    assert (result is False) is True
    del(store)
    return True


def test_new_process():
    """description"""
    store = cache.Cache()
    tipe = "tick"
    key = "kraken"
    pid = "1000"
    params = "test param"
    message = "new"
    result = store.new_process(tipe=tipe,
                              key=key,
                              pid=pid,
                              params=params,
                              message=message)
    assert (result == 1) is True
    tipe = "ohlcv"
    pid = "1001"
    result = store.new_process(tipe=tipe,
                              key=key,
                              pid=pid,
                              params=params,
                              message=message)
    assert (result == 1) is True
    del(store)
    return True


def test_update_process_2():
    """description"""
    store = cache.Cache()
    tipe = "tick"
    key = "kraken"
    message = "update"
    result = store.update_process(tipe=tipe,
                              key=key,
                              message=message)
    assert (result is True) is True
    tipe = "ohlcv"
    result = store.update_process(tipe=tipe,
                              key=key,
                              message=message)
    assert (result is True) is True
    del(store)
    return True


def test_get_top_1():
    store = cache.Cache()
    deltatime = 1
    filter_in = "hola"
    filter_out = "no hola"
    result = store.get_top()
    assert (len(result) > 0) is True
    fields = ['type', 'key', 'pid', 'params', 'message', 'timestamp']
    flag = True
    for res in result:
        for field in fields:
            if not hasattr(res, field):
                flag = False
    assert (flag is True) is True


def test_get_top_2():
    store = cache.Cache()
    comp = "ohlcv"
    result = store.get_top(deltatime=0.0001, comp=comp)
    assert (len(result) > 0) is True
    flag = True
    for res in result:
        if res.type != comp:
            flag = False
    assert (flag is True) is True
    comp = "ohlcvv"
    result = store.get_top(deltatime=0.0001, comp=comp)
    assert (len(result) == 0) is True


def test_get_top_3():
    store = cache.Cache()
    comp = "ohlcv"
    result = store.get_top(deltatime=None, comp=comp)
    assert (len(result) > 0) is True
    fields = ['type', 'key', 'pid', 'params', 'message', 'timestamp']
    flag = True
    for res in result:
        if res.type != comp:
            flag = False
    assert (flag is True) is True
    comp = "ohlcvv"
    result = store.get_top(deltatime=None, comp=comp)
    assert (len(result) == 0) is True


def test_get_top_4():
    store = cache.Cache()
    comp = None
    result = store.get_top(deltatime=0.0001, comp=comp)
    assert (len(result) > 0) is True
    fields = ['type', 'key', 'pid', 'params', 'message', 'timestamp']
    flag = True
    for res in result:
        for field in fields:
            if not hasattr(res, field):
                print(res)
                flag = False
    assert (flag is True) is True


def test_upsert_tickers():
    store = cache.Cache()
    tick1 = {"cat_ex_id": "00000-0000-00001",
             "symbol": "BTC/USD",
             "open": 19200.1,
             "high": 19200.2,
             "low": 19200.0,
             "close": 19200.1,
             "volume": 12,
             "timestamp": arrow.utcnow().shift(seconds=-3).format()}
    tick2 = {"cat_ex_id": "00000-0000-00002",
             "symbol": "ETH/USD",
             "open": 1300.1,
             "high": 1300.2,
             "low": 1300.0,
             "close": 1300.1,
             "volume": 13,
             "timestamp": arrow.utcnow().shift(seconds=-3).format()}
    result = store.upsert_tickers(tickers=[tick1, tick2])
    assert (result is True) is True
    tick1 = {"cat_ex_id": "00000-0000-00001",
             "symbol": "BTC/USD",
             "open": 19200.1,
             "high": 19200.2,
             "low": 19200.0,
             "close": 19200.1,
             "volume": 12,
             "timestamp": arrow.utcnow().format()}
    tick2 = {"cat_ex_id": "00000-0000-00002",
             "symbol": "ETH/USD",
             "open": 1300.1,
             "high": 1300.2,
             "low": 1300.0,
             "close": 1300.1,
             "volume": 13,
             "timestamp": arrow.utcnow().format()}
    tick3 = {"cat_ex_id": "00000-0000-00001",
             "symbol": "ETH/USD",
             "open": 1300.1,
             "high": 1300.2,
             "low": 1300.0,
             "close": 1300.1,
             "volume": 13,
             "timestamp": arrow.utcnow().format()}
    tick4 = {"cat_ex_id": "00000-0000-00001",
             "symbol": "XRP/USD",
             "open": 0.46,
             "high": 0.46,
             "low": 0.46,
             "close": 0.46,
             "volume": 13,
             "timestamp": arrow.utcnow().format()}
    tick5 = {"cat_ex_id": "00000-0000-00001",
             "symbol": "ETH/BTC",
             "open": 0.6,
             "high": 0.6,
             "low": 0.6,
             "close": 0.6,
             "volume": 13,
             "timestamp": arrow.utcnow().format()}
    tick6 = {"cat_ex_id": "00000-0000-00001",
             "symbol": "XRP/ETH",
             "open": 0.02,
             "high": 0.02,
             "low": 0.02,
             "close": 0.02,
             "volume": 13,
             "timestamp": arrow.utcnow().format()}
    result = store.upsert_tickers(tickers=[tick1, tick2, tick3, tick4, tick5, tick6])
    assert (result is True) is True


def test_get_all_tickers():
    store = cache.Cache()
    rows = store.get_all_tickers()
    assert (len(rows) == 6) is True
    rows = store.get_all_tickers(cat_ex_id='00000-0000-00001')
    assert (len(rows) == 5) is True


def test_get_ticker_1():
    store = cache.Cache()
    ticker, stamp = store.get_ticker(cat_ex_id='00000-0000-00003', symbol="BTC/USD")
    assert (stamp is None and ticker is None) is True


def test_get_ticker_2():
    store = cache.Cache()
    ticker, stamp = store.get_ticker(cat_ex_id='00000-0000-00001', symbol="BTC/USD")
    assert (isinstance(ticker, float) is True) is True
    assert (arrow.get(stamp).timestamp() > arrow.utcnow().shift(minutes=-1).timestamp()) is True


def test_get_ticker_3():
    store = cache.cache(test=True)
    ticker, stamp = store.get_ticker(cat_ex_id='00000-0000-00001', symbol="BTC/USD", wait_last=True)
    assert (isinstance(ticker, float) is True) is True
    assert (arrow.get(stamp).timestamp() > arrow.utcnow().shift(minutes=-1).timestamp()) is True


def test_get_ticker_4():
    store = cache.cache(test=True)
    tick1 = {"cat_ex_id": "00000-0000-00001",
             "symbol": "BTC/USD",
             "open": 19200.1,
             "high": 19200.2,
             "low": 19200.0,
             "close": 19200.1,
             "volume": 12,
             "timestamp": arrow.utcnow().shift(seconds=-5).format()}
    result = store.upsert_tickers(tickers=[tick1])
    ticker, stamp = store.get_ticker(cat_ex_id='00000-0000-00001', symbol="BTC/USD", wait_last=True)
    assert (stamp is None and ticker is None) is True


def test_get_price_1():
    store = cache.Cache()
    ticker = store.get_price(cat_ex_id='00000-0000-00001', symbol="BTC/USD")
    assert (isinstance(ticker, float) is True) is True


def test_get_price_2():
    store = cache.Cache()
    ticker = store.get_price(cat_ex_id='00000-0000-00003', symbol="BTC/USD")
    assert (ticker is None) is True


def test_get_price_3():
    store = cache.Cache()
    ticker = store.get_price(symbol="BTC/USD")
    assert (isinstance(ticker, float) is True) is True


def test_get_price_4():
    store = cache.Cache()
    ticker = store.get_price(symbol="XBT/USD")
    assert (ticker is None) is True


def test_get_bnbprice_1():
    store = cache.Cache()
    tick1 = {"cat_ex_id": "00000-0000-00001",
             "symbol": "BNB/MMT",
             "open": 192,
             "high": 192.2,
             "low": 192.0,
             "close": 192.1,
             "volume": 12,
             "timestamp": arrow.utcnow().format()}
    tick2 = {"cat_ex_id": "00000-0000-00001",
             "symbol": "XLM/BNB",
             "open": 0.001,
             "high": 0.001,
             "low": 0.001,
             "close": 0.001,
             "volume": 13,
             "timestamp": arrow.utcnow().format()}
    result = store.upsert_tickers(tickers=[tick1, tick2])
    del store


def test_get_bnbprice_2():
    store = cache.Cache()
    ticker = store.get_bnbprice(cat_ex_id='00000-0000-00001', symbol='MMT')
    assert (isinstance(ticker, float) is True) is True


def test_get_bnbprice_3():
    store = cache.Cache()
    ticker = store.get_bnbprice(cat_ex_id='00000-0000-00001', symbol='XLM')
    assert (isinstance(ticker, float) is True) is True


def test_get_bnbprice_4():
    store = cache.Cache()
    ticker = store.get_bnbprice(cat_ex_id='00000-0000-00001', symbol='BTC')
    assert (ticker is None) is True


def test_update_bot_1():
    store = cache.Cache()
    bot = {"bot_id": '00000-0000-00001',
           "ex_id": '00000-0000-00001',
           "bot_name": "test name",
           "symbol": "BTC/USD",
           "exchange": "kraken",
           "tick": 19200,
           "roi": 200,
           "funds": 10000,
           "totfunds": 8000,
           "pos": 1,
           "pos_price": 100,
           "roi_pct": 2,
           "orders": "",
           "message": "updated",
           "live": "No",
           "strategy": "hot",
           "base": 'BTC',
           "params": {},
           "variables": 'var1, var2'}
    result = store.update_bot(bot=bot)
    assert (result is True) is True

def test_update_bot_2():
    store = cache.Cache()
    bot = {"bot_id": '00000-0000-00001',
           "ex_id": '00000-0000-00001',
           "bot_name": "test name",
           "symbol": "BTC/USD",
           "exchange": "kraken",
           "tick": 19200,
           "roi": 200,
           "funds": 10000,
           "totfunds": 8000,
           "pos": 1,
           "pos_price": 100,
           "roi_pct": 2,
           "orders": "",
           "message": "updated",
           "live": "No",
           "base": 'BTC',
           "params": {},
           "variables": 'var1, var2'}
    result = store.update_bot(bot=bot)
    assert (result is False) is True


def test_update_bot_ts_1():
    store = cache.Cache()
    result = store.update_bot_ts(bot_id='00000-0000-00001')
    assert (result is True) is True


def test_update_bot_ts_2():
    store = cache.Cache()
    result = store.update_bot_ts(bot_id='00000-0000-00002')
    assert (result is False) is True


def test_get_bot_lastseen_1():
    store = cache.Cache()
    result = store.get_bot_lastseen(bot_id='00000-0000-00001')
    assert (isinstance(result, str) is True) is True


def test_get_bot_lastseen_2():
    store = cache.Cache()
    result = store.get_bot_lastseen(bot_id='00000-0000-00002')
    assert (result is None) is True


def test_upsert_user_account_1():
    store = cache.Cache()
    uid = "0000-0000-0001"
    ex_id = "00000-0000-00001"
    account = {}
    account = {'total': 0.04976933,
               'used': 0.04976933,
               'free': 0.0,
               'base': 'BTC'}
    result = store.upsert_user_account(uid=uid,
                                             ex_id=ex_id,
                                             account=account,
                                             date=arrow.utcnow().format())
    assert (result is True) is True


def test_upsert_user_account_2():
    store = cache.Cache()
    uid = "0000-0000-0001"
    ex_id = "00000-0000-00001"
    account = {}
    account = {'total': 0.04976933,
               'used': 0.04976933,
               'base': 'BTC'}
    result = store.upsert_user_account(uid=uid,
                                             ex_id=ex_id,
                                             account=account,
                                             date=arrow.utcnow().format())
    assert (result is False) is True


def test_get_full_account_1():
    store = cache.Cache()
    result = store.get_full_account(uid='0000-0000-0001',
                                    ex_id='00000-0000-00001',
                                    currency='BTC').__dict__
    assert ('uid' in result) is True


def test_get_full_account_2():
    store = cache.Cache()
    result = store.get_full_account(uid='0000-0000-0001',
                                    ex_id='00000-0000-00001',
                                    currency='BTD')
    assert (result is None) is True


def test_get_full_accounts_1():
    store = cache.Cache()
    result = store.get_full_accounts(uid='0000-0000-0001',
                                    ex_id='00000-0000-00001')
    assert (isinstance(result[0].uid, str)) is True


def test_get_full_accounts_2():
    store = cache.Cache()
    result = store.get_full_accounts(uid='0000-0000-0003',
                                    ex_id='00000-0000-00001')
    assert (result == []) is True


def test_upsert_account_by_symbol_1():
    store = cache.Cache()
    pos = [{'symbol': 'BTC/USD', 'free': 0.0, 'used': 0.0, 'total': 0.0},
           {'symbol': 'ETH/BTC', 'free': 1, 'used': 1, 'total': 1},
           {'symbol': 'ETH/BTC', 'free': 1, 'used': 1, 'total': 1},
           {'symbol': 'XRP/ETH', 'free': 100, 'used': 100, 'total': 100},
           {'symbol': 'XRP/USD', 'free': 1000, 'used': 1000, 'total': 1000}]
    account = {'total': 0.04976933,
               'used': 0.04976933,
               'free': 0.0,
               'base': 'BTC',
               'positions': pos}
    result = store.upsert_account_by_symbol(uid='0000-0000-0001',
                                            ex_id='00000-0000-00001',
                                            cat_ex_id='00000-0000-00001',
                                            account=account,
                                            date=arrow.utcnow().format(),
                                            futures=False)
    assert (result is True) is True


def test_upsert_account_by_symbol_2():
    store = cache.Cache()
    account = {'total': 0.04976933,
               'used': 0.04976933,
               'free': 0.0,
               'base': 'BTC'}
    result = store.upsert_account_by_symbol(uid='0000-0000-0001',
                                            ex_id='00000-0000-00001',
                                            cat_ex_id='00000-0000-00001',
                                            account=account,
                                            date=arrow.utcnow().format(),
                                            futures=False)
    assert (result is False) is True


def test_upsert_account_by_symbol_3():
    store = cache.Cache()
    pos = []
    account = {'total': 0.04976933,
               'used': 0.04976933,
               'free': 0.0,
               'positions': pos,
               'base': 'BTC'}
    result = store.upsert_account_by_symbol(uid='0000-0000-0001',
                                            ex_id='00000-0000-00001',
                                            cat_ex_id='00000-0000-00001',
                                            account=account,
                                            date=arrow.utcnow().format(),
                                            futures=False)
    assert (result is True) is True


def test_upsert_account_by_symbol_4():
    store = cache.Cache()
    account = {'total': 0.04976933,
               'used': 0.04976933,
               'base': 'BTC'}
    result = store.upsert_account_by_symbol(uid='0000-0000-0001',
                                            ex_id='00000-0000-00001',
                                            cat_ex_id='00000-0000-00001',
                                            account=account,
                                            date=arrow.utcnow().format(),
                                            futures=False)
    assert (result is False) is True


def test_get_position_1():
    store = cache.Cache()
    result = store.get_position(symbol='XRP/USD',
                                uid='0000-0000-0001',
                                ex_id='00000-0000-00001')
    assert (result.ex_id == '00000-0000-00001') is True


def test_get_position_2():
    store = cache.Cache()
    result = store.get_position(symbol='XRP/USD',
                                uid='0000-0000-0000',
                                ex_id='00000-0000-00001')
    assert (result is None) is True


def test_get_position_3():
    store = cache.Cache()
    result = store.get_position(symbol='XRP/USD',
                                uid='0000-0000-0001',
                                ex_id='00000-0000-00001',
                                latest=True)
    assert (result.ex_id == '00000-0000-00001') is True


def test_get_bot_position_1():
    store = cache.Cache()
    total, price = store.get_bot_position(bot_id='00000-0000-00001',
                                          symbol='XRP/USD',
                                          uid='0000-0000-0001',
                                          ex_id='00000-0000-00001')
    assert (isinstance(price, float)) is True


def test_get_bot_position_2():
    store = cache.Cache()
    total, price = store.get_bot_position(bot_id='00000-0000-00001',
                                          symbol='XRP/USDD',
                                          uid='0000-0000-00001',
                                          ex_id='00000-0000-00001')
    assert (price == 0) is True


def test_get_all_positions_1():
    store = cache.Cache()
    results = store.get_all_positions(uid='0000-0000-0001',
                                      ex_id='00000-0000-00001')
    assert (results[0].uid == '0000-0000-0001') is True


def test_get_all_positions_2():
    store = cache.Cache()
    results = store.get_all_positions(uid='0000-0000-0000',
                                      ex_id='00000-0000-0003423423')
    assert (results == []) is True


def test_get_user_size_by_symbol_1():
    store = cache.Cache()
    result = store.get_user_size_by_symbol(uid='0000-0000-0001',
                                            ex_id='00000-0000-00001',
                                            symbol='XRP/USD',
                                            free=True,
                                            total=False)
    assert (result == 460.0) is True


def test_get_user_size_by_symbol_2():
    store = cache.Cache()
    result = store.get_user_size_by_symbol(uid='',
                                            ex_id='00000-0000-00001',
                                            symbol='XRP/USD',
                                            free=True,
                                            total=True)
    assert (result is None) is True


def test_block_order_1():
    store = cache.Cache()
    result = store.block_order(oid=4)
    assert (result == 1) is True


def test_unblock_order_1():
    store = cache.Cache()
    result = store.unblock_order(oid=4)
    assert (result == 1) is True


def test_unblock_order_2():
    store = cache.Cache()
    result = store.unblock_order(oid=4)
    assert (result == 0) is True


def test_unblock_orders_1():
    store = cache.Cache()
    store.block_order(oid=4)
    store.block_order(oid=1)
    result = store.unblock_orders()
    assert (result == 1) is True


def test_unblock_orders_2():
    store = cache.Cache()
    result = store.unblock_orders()
    assert (result == 0) is True


def test_get_order_status_1():
    store = cache.Cache()
    store.block_order(oid=1)    
    result = store.get_order_status(oid=1)
    assert (result.status == "Blocked") is True
    result = store.unblock_order(oid=1)
    assert (result == 1) is True


def test_get_order_status_1():
    store = cache.Cache()
    result = store.get_order_status(oid=1)
    assert (result is None) is True


def test_delete_from_top_2():
    """description"""
    store = cache.Cache()
    component = "tick"
    pid = 1001
    result = store.delete_from_top(component=None, pid=pid)
    assert (result == 1) is True
    result = store.delete_from_top(component=component, pid=None)
    assert (result == 1) is True

"""
test_start_cache_server()
test_delete_from_top_1()
test_update_process_1()
test_new_process()
test_update_process_2()
test_get_top_1()
test_get_top_2()
test_get_top_3()
test_get_top_4()
test_upsert_tickers()
test_get_all_tickers()
test_get_ticker_1()
test_get_ticker_2()
test_get_ticker_3()
test_get_ticker_4()
test_get_price_1()
test_get_price_2()
test_get_price_3()
test_get_price_4()
test_get_bnbprice_1()
test_get_bnbprice_2()
test_get_bnbprice_3()
test_update_bot_1()
test_update_bot_2()
test_update_bot_ts_1()
test_update_bot_ts_2()
test_get_bot_lastseen_1()
test_get_bot_lastseen_2()
test_upsert_user_account_1()
test_upsert_user_account_2()
test_get_full_account_1()
test_get_full_account_2()
test_get_full_accounts_1()
test_get_full_accounts_2()
test_upsert_account_by_symbol_1()
test_upsert_account_by_symbol_2()
test_upsert_account_by_symbol_3()
test_upsert_account_by_symbol_4()
test_get_position_1()
test_get_position_2()
test_get_position_3()
test_get_bot_position_1()
test_get_bot_position_2()
test_get_all_positions_1()
test_get_all_positions_2()
test_get_user_size_by_symbol_1()
test_get_user_size_by_symbol_2()
test_block_order_1()
test_unblock_order_1()
test_unblock_order_2()
test_unblock_orders_1()
test_unblock_orders_2()
test_get_order_status_1()
test_delete_from_top_2()
"""
