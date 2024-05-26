#!/usr/bin/python3
from libs.settings_config import fullon_settings_loader
from libs import settings
from libs import simul
from run.simul_manager import SimulManager
from libs.database import start as start_database, stop as stop_database
from libs.database_ohlcv import start as start_ohlcv, stop as stop_ohlcv
from libs.simul_launcher import simulator
from libs.bot import Bot
import psutil
settings.LOG_LEVEL = 'INFO'
start_database()
start_ohlcv()
simulator.start()

params1 = {
          'rsi': "12",
          'entry': "35",
          'exit': "60",
          "leverage": "2",
          "size_pct": "10"}
params2 = {
          'rsi': "12",
          'entry': "35",
          'exit': "55",
          "leverage": "2",
          "size_pct": "10"}
#params = [params1, params2]
#params = [params1]
#params = [{'sma_period': '1', 'size_pct': '20'}, {'sma_period': '2', 'size_pct': '20'}, {'sma_period': '4', 'size_pct': '20'}, {'sma_period': '10', 'size_pct': '20'},{'sma_period': '20', 'size_pct': '20'}]
#params = [{'sma_period': '20', 'size_pct': '50'}, {'sma_period': '14', 'size_pct': '50'}]
#params = [{'sma_period': '20', 'size_pct': '80'}]
params = [
            {"size_pct": "20",
             "trailing_stop": "15",
             "take_profit": "20",
             'threshold': "0.55",
             "sma": "200"}
        ]
BOT = {"bot_id": 7,
       "periods": 365*2,
       "warm_up": 250}
filename = ''
feeds = {}
#filename = "rsi2long2.csv"
#feeds = {2: {'compression': 30}, 3: {'compression': 30}}
#feeds = {1: {'compression': 480}}
event = False


def path1():
    abot = Bot(BOT['bot_id'], BOT['periods'])
    # Assuming params is a list of dictionaries
    for param in params:
        for key, value in param.items():
            try:
                param[key] = float(value)
            except ValueError:
                if value == "None":
                    param[key] = None
                else:
                    raise ValueError(f"Could not convert value for {key}: '{value}'")

    abot.run_simul_loop(feeds=feeds, warm_up=BOT['warm_up'], visual=False, test_params=params, event=event)


def path2():
    simul = SimulManager()
    simul.bot_simul(bot=BOT,
                    event_based=event,
                    feeds=feeds,
                    params=params,
                    filename=filename,
                    montecarlo=1000,
                    sharpe_filter=-10.00,
                    xls=False,
                    verbose=False,
                    visual=False,
                    leverage=1)


#path1()
path2()
stop_database()
stop_ohlcv()
simulator.stop()


'''
Strategy: xgb_forest_mom_long - Symbol: BTC/USD - Periods: (mins, days) - Compressions: (1, 1) - From: 2020-06-20 00:01:00 to 2024-01-26 23:59:00
--------------------------------------------------------------------------------
+---+------+-----------+------+------------+------+-----------+------------------+------+-----------+-------------+-----------+------------+------+------+---------+------------+--------+---------+-------+-----------+----------+-----------+-----------+-----------+-------------+
|   | cmf  | cmf_entry | ema  | macd_entry | obv  | obv_entry | prediction_steps | rsi  | rsi_entry | stoch_entry | threshold | vwap_entry |  TP  |  TS  | TTrades | Win rate % |  Fees  | Profit  |  ROI  | AvgReturn | Duration | MedReturn | NegStdDev | PosStdDev | SharpeRatio |
+---+------+-----------+------+------------+------+-----------+------------------+------+-----------+-------------+-----------+------------+------+------+---------+------------+--------+---------+-------+-----------+----------+-----------+-----------+-----------+-------------+
| 0 | 18.0 |    9.0    | 20.0 |    3.0     | 18.0 |    0.8    |       1.0        | 14.0 |   60.0    |     0.0     |   0.48    |    0.4     | 14.0 | 13.0 |  83.0   |   48.19    | 658.08 | 5694.08 | 56.94 |   2.85    |  342.34  |   -1.74   |   3.51    |   0.52    |    0.26     |
+---+------+-----------+------+------------+------+-----------+------------------+------+-----------+-------------+-----------+------------+------+------+---------+------------+--------+---------+-------+-----------+----------+-----------+-----------+-----------+-------------+




Multiple sim results: - Strategy: xgb_forest_mom_long - Symbol: ETH/USD - Periods: (mins, days) - Compressions: (1, 1) - From: 2020-06-19 00:01:00 to 2024-01-25 23:59:00
+---+------+-----------+------+------------+------+-----------+------------------+------+-----------+-------------+-----------+------------+------+------+-------+-------------+---------------+------------+------------+------------+------------+
|   | cmf  | cmf_entry | ema  | macd_entry | obv  | obv_entry | prediction_steps | rsi  | rsi_entry | stoch_entry | threshold | vwap_entry |  TP  |  TS  | Count | Profit_mean | Profit_median | Profit_max | Profit_min | Profit_std | Risk_Score |
+---+------+-----------+------+------------+------+-----------+------------------+------+-----------+-------------+-----------+------------+------+------+-------+-------------+---------------+------------+------------+------------+------------+
| 0 | 18.0 |   13.0    | 20.0 |    2.0     | 18.0 |    0.8    |       1.0        | 14.0 |   60.0    |     0.0     |   0.35    |    0.4     | 14.0 | 13.0 | 18.0  |   4247.8    |    4518.15    |  5249.57   |  2762.73   |   807.84   |    0.19    |
+---+------+-----------+------+------------+------+-----------+------------------+------+-----------+-------------+-----------+------------+------+------+-------+-------------+---------------+------------+------------+------------+------------+
--------------------------------------------------------------------------------


--------------------------------------------------------------------------------
Multiple sim results: - Strategy: xgb_forest_mom_long - Symbol: XMR/USD - Periods: (mins, days) - Compressions: (1, 1) - From: 2020-06-23 00:01:00 to 2023-12-12 00:01:00
+---+------+-----------+------+------------+------+-----------+------------------+------+-----------+-------------+-----------+------------+------+------+-------+-------------+---------------+------------+------------+------------+------------+
|   | cmf  | cmf_entry | ema  | macd_entry | obv  | obv_entry | prediction_steps | rsi  | rsi_entry | stoch_entry | threshold | vwap_entry |  TP  |  TS  | Count | Profit_mean | Profit_median | Profit_max | Profit_min | Profit_std | Risk_Score |
+---+------+-----------+------+------------+------+-----------+------------------+------+-----------+-------------+-----------+------------+------+------+-------+-------------+---------------+------------+------------+------------+------------+
| 0 | 18.0 |    9.0    | 20.0 |    2.5     | 18.0 |    0.8    |       1.0        | 14.0 |   60.0    |     0.0     |   0.48    |    0.4     | 14.0 | 13.0 |  6.0  |   2019.79   |    2038.7     |  3553.24   |   245.85   |  1127.03   |    0.56    |
+---+------+-----------+------+------------+------+-----------+------------------+------+



--------------------------------------------------------------------------------
Multiple sim results: - Strategy: xgb_forest_mom_short - Symbol: SOL/USD - Periods: (mins, days) - Compressions: (1, 1) - From: 2022-05-08 00:01:00 to 2023-03-12 21:25:00
+---+------+-----------+------------+-------------+------+------------------+-----------+------+------+-------+-------------+---------------+------------+------------+------------+------------+
|   | rsi  | rsi_entry | macd_entry | stoch_entry | ema  | prediction_steps | threshold |  TP  |  TS  | Count | Profit_mean | Profit_median | Profit_max | Profit_min | Profit_std | Risk_Score |
+---+------+-----------+------------+-------------+------+------------------+-----------+------+------+-------+-------------+---------------+------------+------------+------------+------------+
| 0 | 14.0 |   40.0    |    1.5     |    50.0     | 21.0 |       1.0        |   0.35    | 16.0 | 13.0 |  6.0  |   4454.22   |    4501.29    |  4981.22   |  3907.76   |   423.91   |    0.1     |
+---+------+-----------+------------+-------------+------+------------------+-----------+------+------+-------+-------------+---------------+------------+------------+------------+------------+
--------------------------------------------------------------------------------





params2 = {
          "stop_loss": "None",
          'take_profit': "6:18",
          'trailing_stop': "4:10",  # 12
          "timeout": "None",
          'rsi': "14",  #
          'rsi_entry': "43",
          'cmf': "18",
          'cmf_entry': '-21',
          'vwap_entry': "-3.2",
          'obv': "18",
          'obv_entry': "-4",
          'macd_entry': "0",
          'stoch_entry': "45",
          "ema": "20",
          "leverage": "2",
          "size_pct": "10",
          "prediction_steps": "1",
          "threshold": "0.35",
          "size": "500"}




params2 = {
          "stop_loss": "None",
          'take_profit': "12",
          'trailing_stop': "5",  # 12
          "timeout": "None",
          'rsi': "14",  #
          'rsi_entry': "43",
          'macd_entry': "0",
          'stoch_entry': "45",
          "ema": "21",
          "leverage": "2",
          "size_pct": "24",
          "prediction_steps": "1",
          "threshold": "0.35",
          "size": "500"}



params2 = {
          "stop_loss": "None",
          'take_profit': "20",  #18
          'trailing_stop': "12", #12
          "timeout": "None",
          'rsi': "14",  #
          'rsi_entry': "60",
          'rsi_exit': "50",
          'rsi_weight': "3",
          'cmf': "18",
          'cmf_entry': '8',
          'cmf_exit': '6',
          'cmf_weight': '2',
          'vwap_entry': "0.4",
          'vwap_exit': "0.6",
          'vwap_weight': "1",
          'obv': "18",
          'obv_entry': "0.8",
          'obv_exit': "0.6",
          'obv_weight': "2",
          'macd_entry': "4",
          'macd_exit': "2",
          'macd_weight': "1",
          'stoch_entry': "70",
          'stoch_exit': "65",
          'stoch_weight': "1",
          'ema': '21',
          'entry': "33",
          'exit': "62",
          "leverage": "2",
          "size_pct": "45",
          "size": "500"}


params2 = {
          "stop_loss": "None",
          'take_profit': "15",
          'trailing_stop': "10",
          "timeout": "None",
          'rsi': "14",  #
          'rsi_entry': "45",
          'rsi_exit': "45",
          'rsi_weight': "4",
          'rsi_sma': "18",
          'rsi_sma_weight': "1",
          'vwap_entry': "-2",
          'vwap_exit': "-1",
          'vwap_weight': "1",
          'macd_entry': "-1",
          'macd_exit': "-2",
          'macd_weight': "1",
          'ema': '21',
          'entry': "18",
          'exit': "56",
          "leverage": "2",
          "size_pct": "24",
          "size": "2000"}



params2 = {
          "stop_loss": "None",
          'take_profit': "16",
          'trailing_stop': "13",  # 12
          "timeout": "None",
          'rsi': "14",  #
          'rsi_entry': "40", #43
          'macd_entry': "1.5",
          'stoch_entry': "50",
          "ema": "21",
          "leverage": "2",
          "prediction_steps": "1",
          "threshold": "0.35",
          "size_pct": "20"}





'''


def kill_processes_by_cmdline(search_term):
    """Kill processes where the command line contains the given search term."""
    for proc in psutil.process_iter(attrs=['cmdline']):
        # Check if search_term is in the cmdline; this returns a list of command line arguments
        try:
            if any(search_term in cmd for cmd in proc.info['cmdline']):
                try:
                    print(f"Killing process: {proc.pid} - {' '.join(proc.info['cmdline'])}")
                    proc.kill()  # Terminate the process
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass  # Process already terminated or access denied
        except TypeError:
            pass

# Use part of the command that uniquely identifies your script
search_term = "fullon.py"
kill_processes_by_cmdline(search_term)