import time
import logging
from run.user_manager import UserManager
from fullon.exchanges.kraken.websockets import WebSocket
import pytest


@pytest.fixture(scope="module")
def exchange_struct(dbase):
    user = UserManager()
    uid = user.get_user_id(mail='admin@fullon')
    exch = dbase.get_exchange(user_id=uid)[0]
    yield exch


@pytest.fixture(scope="module")
def websocket_instance(exchange_struct):
    ws = WebSocket(markets={}, ex_id=exchange_struct.ex_id)
    yield ws
    ws.stop()
    del ws


@pytest.mark.order(1)
def test_on_trade(websocket_instance, caplog):
    # Test trade message
    trades = [
        ["1000.00", "0.5", "1234567890.123", "s", "m", ""]
    ]
    event = {'subscriptionStatus': 'subscribed'}
    with caplog.at_level(logging.INFO):
        symbol = 'XRP/BTC'
        message = [event, trades, 'trades', symbol]
        websocket_instance.on_trade(message=message)
        assert websocket_instance.cache_trade_reply > 0
        symbol = "ETH/USD"
        message = ['error', trades, 'trades', symbol]
        websocket_instance.on_trade(message=message)
        assert websocket_instance.cache_trade_reply > 0
        symbol = "BTC/USD"
        message = ['error', trades, 'trades', symbol]
        websocket_instance.on_trade(message=message)
        assert websocket_instance.cache_trade_reply > 0


@pytest.mark.order(2)
def test_on_ticker(websocket_instance, caplog):
    # Test trade message
    data = [340, {'a': ['28499.40000', 0, '0.23590943'],
                  'b': ['28498.40000', 0, '0.35769872'],
                  'c': ['28499.40000', '0.00659057'],
                  'v': ['2350.54550764', '5891.16057349'],
                  'p': ['28716.17635', '29234.07452'],
                  't': [21551, 45317],
                  'l': ['28237.70000', '28237.70000'],
                  'h': ['29330.90000', '29975.00000'],
                  'o': ['29245.30000', '29295.40000']},
                  'ticker', 'XBT/USD']
    with caplog.at_level(logging.INFO):
        websocket_instance.on_ticker(message=data)
        assert websocket_instance.cache_ticker_reply > 0


@pytest.mark.order(3)
def test_run(websocket_instance, caplog):
    settings.LOG_LEVEL = "logging.INFO"
    pairs = ["XBT/USD", "ETH/USD"]
    subscription = {
        "name": "trade"
    }

    # Subscribe to public channels
    websocket_instance.subscribe_public(subscription=subscription,
                                        pair=pairs,
                                        callback=websocket_instance.on_trade)

    # Allow some time to receive messages
    time.sleep(2)

    assert len(caplog.records) > 0


@pytest.mark.order(4)
def test_on_my_open_orders(websocket_instance, caplog):
    # Test open orders message
    open_orders = [
        [
            {
                'O63H2U-4VBZL-SBIUYE': {
                    'avg_price': '0.00000',
                    'cost': '0.00000',
                    'descr': {
                        'close': None,
                        'leverage': '3:1',
                        'order': 'buy 0.00010000 XBT/USD @ limit 26643.50000 with 3:1 leverage',
                        'ordertype': 'limit',
                        'pair': 'XBT/USD',
                        'price': '26643.50000',
                        'price2': '0.00000',
                        'type': 'buy'
                    },
                    'expiretm': None,
                    'fee': '0.00000',
                    'limitprice': '0.00000',
                    'misc': '',
                    'oflags': 'fciq',
                    'opentm': '1685543665.241758',
                    'reduce_only': False,
                    'refid': None,
                    'starttm': None,
                    'status': 'pending',
                    'stopprice': '0.00000',
                    'timeinforce': 'GTC',
                    'userref': 0,
                    'vol': '0.00010000',
                    'vol_exec': '0.00000000'
                }
            }
        ]
    ]
    with caplog.at_level(logging.INFO):
        websocket_instance.on_my_open_orders(message=open_orders)
        assert websocket_instance.cache_order_reply > 0
    open_orders = [[{'O6BGMV-G2XX6-XOFPZ7': {'status': 'open', 'userref': 0}}], 'openOrders', {'sequence': 3}]
    websocket_instance.cache_order_reply = 0
    with caplog.at_level(logging.INFO):
        websocket_instance.on_my_open_orders(message=open_orders)
        assert websocket_instance.cache_order_reply == 0
    open_orders = [
        [
            {
                'OV4GAZ-XCJ7D-JMBZJL': {
                    'lastupdated': '1685545064.549686',
                    'status': 'canceled',
                    'vol_exec': '0.00000000',
                    'cost': '0.00000',
                    'fee': '0.00000',
                    'avg_price': '0.00000',
                    'userref': 0,
                    'cancel_reason': 'User requested'
                }
            }
        ]
    ]
    websocket_instance.cache_order_reply == 0
    with caplog.at_level(logging.INFO):
        websocket_instance.on_my_open_orders(message=open_orders)
        assert websocket_instance.cache_order_reply > 0
'''
def test_on_my_trade(websocket_instance, caplog):
    # Test my trade message
    trades = [
        {
            '000000001': {
                'posstatus': 'open',
                'margin': 0.0,
                'cost': 0.0,
                'fee': 0.0,
                'vol': 10.0,
                'vol_exec': 10.0,
                'cost': 0.1,
                'fee': 0.01,
                'ordertxid': 'xxxxxx',
                'ordertype': 'limit',
                'pair': 'XRP/BTC',
                'price': 10000.0,
                'time': arrow.utcnow().timestamp()
            }
        }
    ]
    with caplog.at_level(logging.INFO):
        websocket_instance.on_my_trade(message=trades)
        assert websocket_instance.cache_my_trade_reply > 0
'''