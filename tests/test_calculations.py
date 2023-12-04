from __future__ import unicode_literals, print_function
from libs import log, settings, database
from fullon.libs.calculations import TradeCalculator, Reg
from fullon.run.user_manager import UserManager
import unittest.mock
import pytest
from decimal import Decimal

@pytest.fixture
def exch():
    user = UserManager()
    UID = user.get_user_id(mail='admin@fullon')
    with database.Database() as dbase:
        exch = dbase.get_exchange(user_id=UID)[0]
    yield exch
    del exch


@pytest.fixture
def account():
    return TradeCalculator()


def test_blah(exch, account):
    account.update_trade_calcs(exch=exch)


def test_long_positive_return(account):
    trade = Reg()
    trade.side = "Sell"
    trade.volume = 0.2
    trade.price = 3001
    trade.cost = trade.price * trade.volume
    trade.fee = trade.cost * 0.01 / 100
    prev = Reg()
    prev.side = "Buy"
    prev.cur_volume = 0.2
    prev.cur_avg_price = 2456
    prev.cur_avg_cost = prev.cur_volume * prev.cur_avg_price
    prev.cur_fee = prev.cur_avg_cost * 0.01 / 100
    cur = Reg()
    cur.avg_cost = 0
    cur.fee = 0
    cur.volume = 0
    rois = account._get_rois(trade, cur, prev)

    expected_roi = (trade.cost + trade.fee) - (prev.cur_avg_cost + prev.cur_fee)
    expected_roi_pct = 100 * (expected_roi / (prev.cur_avg_cost + prev.cur_fee))
    # print(f"Actual ROI: {rois.roi}, Expected ROI: {expected_roi}")
    # print(f"Actual ROI pct: {rois.pct}, Expected ROI pct: {expected_roi_pct}")
    assert round(rois.roi, 2) == round(Decimal(expected_roi), 2)
    assert round(rois.pct, 2) == round(Decimal(expected_roi_pct), 2)

def test_long_negative_return(account):
    trade = Reg()
    trade.side = "Sell"
    trade.volume = 0.2
    trade.price = 2100
    trade.cost = trade.price * trade.volume
    trade.fee = trade.cost * 0.01 / 100
    prev = Reg()
    prev.side = "Buy"
    prev.cur_volume = 0.2
    prev.cur_avg_price = 3001
    prev.cur_avg_cost = prev.cur_volume * prev.cur_avg_price
    prev.cur_fee = prev.cur_avg_cost * 0.01 / 100
    cur = Reg()
    cur.avg_cost = 0
    cur.fee = 0
    cur.volume = 0
    rois = account._get_rois(trade, cur, prev)
    expected_roi = (trade.cost + trade.fee) - (prev.cur_avg_cost + prev.cur_fee)
    expected_roi_pct = 100 * (expected_roi / (prev.cur_avg_cost + prev.cur_fee))
    # print(f"Actual ROI: {rois.roi}, Expected ROI: {expected_roi}")
    # print(f"Actual ROI pct: {rois.pct}, Expected ROI pct: {expected_roi_pct}")
    assert round(rois.roi, 2) == round(Decimal(expected_roi), 2)
    assert round(rois.pct, 2) == round(Decimal(expected_roi_pct), 2)


def test_short_positive_return(account):
    trade = Reg()
    trade.side = "Buy"
    trade.volume = 0.2
    trade.price = 2100
    trade.cost = trade.price * trade.volume
    trade.fee = trade.cost * 0.01 / 100
    prev = Reg()
    prev.side = "Sell"
    prev.cur_volume = 0.2
    prev.cur_avg_price = 3001
    prev.cur_avg_cost = prev.cur_volume * prev.cur_avg_price
    prev.cur_fee = prev.cur_avg_cost * 0.01 / 100
    cur = Reg()
    cur.avg_cost = 0
    cur.fee = 0
    cur.volume = 0
    rois = account._get_rois(trade, cur, prev)
    expected_roi = (prev.cur_avg_cost + prev.cur_fee) - (trade.cost + trade.fee)
    expected_roi_pct = 100 * (expected_roi / (trade.cost + trade.fee))
    # print(f"Actual ROI: {rois.roi}, Expected ROI: {expected_roi}")
    # print(f"Actual ROI pct: {rois.pct}, Expected ROI pct: {expected_roi_pct}")
    assert round(rois.roi, 2) == round(Decimal(expected_roi), 2)
    assert round(rois.pct, 2) == round(Decimal(expected_roi_pct), 2)


def test_short_negative_return(account):
    trade = Reg()
    trade.side = "Buy"
    trade.volume = 0.2
    trade.price = 3100
    trade.cost = trade.price * trade.volume
    trade.fee = trade.cost * 0.01 / 100
    prev = Reg()
    prev.side = "Sell"
    prev.cur_volume = 0.2
    prev.cur_avg_price = 2500
    prev.cur_avg_cost = prev.cur_volume * prev.cur_avg_price
    prev.cur_fee = prev.cur_avg_cost * 0.01 / 100
    cur = Reg()
    cur.avg_cost = 0
    cur.fee = 0
    cur.volume = 0
    rois = account._get_rois(trade, cur, prev)
    expected_roi = (prev.cur_avg_cost + prev.cur_fee) - (trade.cost + trade.fee)
    expected_roi_pct = 100 * (expected_roi / (trade.cost + trade.fee))
    # print(f"Actual ROI: {rois.roi}, Expected ROI: {expected_roi}")
    # print(f"Actual ROI pct: {rois.pct}, Expected ROI pct: {expected_roi_pct}")
    assert round(rois.roi, 2) == round(Decimal(expected_roi), 2)
    assert round(rois.pct, 2) == round(Decimal(expected_roi_pct), 2)


def test_long_positive_return_partial(account):
    trade = Reg()
    trade.side = "Sell"
    trade.volume = 0.14270576
    trade.price = 1924.18
    trade.cost = trade.price * trade.volume
    trade.fee = trade.cost * 0.01 / 100
    prev = Reg()
    prev.side = "Buy"
    prev.cur_volume = 3
    prev.cur_avg_price = 1879.769814
    prev.cur_avg_cost = prev.cur_volume * prev.cur_avg_price
    prev.cur_fee = prev.cur_avg_cost * 0.01 / 100
    cur = Reg()
    cur.avg_cost = 0
    cur.fee = 0
    cur.volume = 0
    rois = account._get_rois(trade, cur, prev)
    previous_cost = trade.volume * prev.cur_avg_price
    previous_fee = prev.cur_fee * (trade.volume / prev.cur_volume)
    expected_roi = (trade.cost + trade.fee) - (previous_cost + previous_fee)
    expected_roi_pct = 100 * (expected_roi / (previous_cost + previous_fee))
    # print(f"Actual ROI: {rois.roi}, Expected ROI: {expected_roi}")
    # print(f"Actual ROI pct: {rois.pct}, Expected ROI pct: {expected_roi_pct}")
    assert round(rois.roi, 2) == round(Decimal(expected_roi), 2)
    assert round(rois.pct, 2) == round(Decimal(expected_roi_pct), 2)