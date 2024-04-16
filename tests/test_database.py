from __future__ import unicode_literals, print_function
import sys
from requests.cookies import MockRequest
from libs import log, settings, database, cache
from libs.structs.trade_struct import TradeStruct
from run.user_manager import UserManager
import datetime
import pytest


@pytest.fixture(scope="module")
def params():
    user = UserManager()
    uid = user.get_user_id(mail='admin@fullon')
    with database.Database() as dbase:
        params = dbase.get_exchange(user_id=uid)[0]
    return params


@pytest.fixture
def mock_trade():
    return TradeStruct(
        trade_id='',
        ex_trade_id="test_ex_trade_id",
        ex_order_id="test_ex_order_id",
        uid=10,  # convert UUID to string
        ex_id=5,  # convert UUID to string
        symbol="test_symbol",
        order_type="test_order_type",
        side="buy",
        volume=1.0,
        price=100.0,
        cost=100.0,
        fee=0.1,
        cur_volume=1.0,
        cur_avg_price=100.0,
        cur_avg_cost=100.0,
        cur_fee=0.1,
        roi=10.0,
        roi_pct=10.0,
        total_fee=0.1,
        time="2023-06-08 00:00:00",
        timestamp=1623105600.0,
        leverage=1.0,
        limit="test_limit",
    )


def test_get_user_list(dbase):
    # Test new_process for tick type
    users = dbase.get_user_list()
    assert len(users) > 0


def test_get_exchanges(dbase, uid):
    exchange = dbase.get_exchange(user_id=uid)[0]
    assert exchange.name != ''


def test_save_get_delete_trades(dbase, mock_trade):
    # Saving the trade
    save_result = dbase.save_trades(trades=[mock_trade])
    assert save_result is not None  # or any other condition based on your implementation

    # Retrieving the trade
    trades = dbase.get_trades(ex_id=mock_trade.ex_id)
    assert trades is not None
    assert len(trades) == 1
    assert mock_trade.ex_id == trades[0].ex_id
    assert mock_trade.ex_order_id == trades[0].ex_order_id
    assert mock_trade.symbol == trades[0].symbol
    assert mock_trade.volume == trades[0].volume
    assert mock_trade.price == trades[0].price
    assert mock_trade.cost == trades[0].cost

    # Deleting the trade
    delete_result = dbase.delete_trade(trade_id=trades[0].trade_id)
    assert delete_result is not None  # or any other condition based on your implementation

    # Verifying the trade is deleted
    trades_after_deletion = dbase.get_trades(ex_id=trades[0].ex_id)
    assert trades_after_deletion is None or len(trades_after_deletion) == 0
