#!/usr/bin/python3
from libs.settings_config import fullon_settings_loader
from libs import settings
from libs import simul
from run.simul_manager import SimulManager
from libs.database import start as start_database, stop as stop_database
from libs.database_ohlcv import start as start_ohlcv, stop as stop_ohlcv
from libs.simul_launcher import simulator
from libs.bot import Bot
settings.NOISE = True
settings.LOG_LEVEL = 'ERROR'
start_database()
start_ohlcv()
simulator.start()

params1 = {"sma1": "45",
           "sma2": "13",
           "zshort": "-3.0",
           "zlong": "3.0",
           "zexitlow": "-1.5",
           "zexithigh": "1.5",
           "stop_loss": "1",
           "take_profit": "1",
           "size_pct": "10",
           "leverage": "1"}
#77
params2 = {
          "stop_loss": "50",
          'take_profit': "50",  # 19
          'trailing_stop': "50",  # 45
          "timeout": "60",
          'rsi': "12",
          'rsi_entry': "70",
          'rsi_exit': "61",
          'cmf': "18",
          'cmf_entry': '11',
          'cmf_exit': '5',
          'vwap_entry': "0.2",
          'vwap_exit': "0.4",
          'ad_line': "17",
          'ad_line_entry': "9",
          'ad_line_exit': "5",
          'obv': "62",
          'obv_entry': "62",
          'obv_exit': "62",
          "leverage": "2",
          "size_pct": "10"}

#params = {"sma1": "30", "sma2": "13", "zshort": "-1", "zlong": "1", "zexitlow": "-0.75", "zexithigh": "0.75", "stop_loss": "4.1"}
BOT = {"bot_id": 21,
       "periods": 2300,
       "warm_up": 50,
       "xls": False,
       "verbose": False,
       "visual": False}
filename = None
#filename = "rsi2long2.csv"
#feeds = {2: {'compression': 30}, 3: {'compression': 30}}
#feeds = {1: {'compression': 240}}
feeds = {}
'''
abot = Bot(10, 1150)
params3 = {}
for p, key in params2.items():
    params3[p] = float(key)

abot.run_simul_loop(feeds=feeds, warm_up=60, visual=False, test_params=params3, event=True)
#params2 = {}
#params2 = {"size_pct": "10"}
'''

simul = SimulManager()
simul.bot_simul(bot=BOT,
                event_based=True,
                feeds=feeds,
                params=params2,
                filename=filename,
                montecarlo=10,
                sharpe_filter=-10.00)
stop_database()
stop_ohlcv()
simulator.stop()

# necesito bitcoin

# necesito eth

# necesiot eth/btc  veamos.

# rsi1 XMR/USD BEst settings:  SL: 1.5 TP: 2.1 TS: 0.5 TO: 25.0 rsi_upper: 66.0 rsi_lower: 34.0 rsi_period: 14.0

# rsi2 xmr: SL: 1.5 TP: 2.1 TS: 0.6 TO: 25.0 rsi_upper: 53.0 rsi_lower: 40.0 rsi_period: 14.0

# rsi 1 matic SL: SL: 1.5 TP: 2.1 TS: 1.4 TO: 25.0 rsi_upper: 68.0 rsi_lower: 31.0 rsi_period: 14.0

# rsi 2 matic  SL: 1.5 TP: 2.1 TS: 0.6 TO: 25.0 rsi_upper: 53.0 rsi_lower: 40.0 rsi_period: 14.0
