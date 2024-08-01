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

params = [
            {"size_pct": "20",
             "trailing_stop": "26",  # 15
             "take_profit": "14",  # 14
             'threshold': "0.45",
             "sma": "200"}
        ]
BOT = {"bot_id": 4,
       "periods": 365*3,
       "warm_up": 234}
filename = ''
feeds = {}
#filename = "rsi2long2.csv"
#feeds = {2: {'compression': 30}, 3: {'compression': 30}}
#feeds = {1: {'compression': 480}}
event = True


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
                    montecarlo=3,
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


'''
Multiple sim results: - Bot: 4 - Strategy: xgb_forest_mom_long - Symbol: BTC/USD - Periods: (mins, days) - Compressions: (1, 1) - From: 2021-08-10 00:01:00 to 2024-07-30 23:59:00
+---+-----------+------+-----------+------+-----------+------------+------------+-------+------------------+-----------+----------+------+------+-------+-------------+---------------+------------+------------+------------+------------+
|   | mfi_entry | rsi  | rsi_entry | cmf  | cmf_entry | vwap_entry | macd_entry |  sma  | prediction_steps | threshold | size_pct |  TP  |  TS  | Count | Profit_mean | Profit_median | Profit_max | Profit_min | Profit_std | Risk_Score |
+---+-----------+------+-----------+------+-----------+------------+------------+-------+------------------+-----------+----------+------+------+-------+-------------+---------------+------------+------------+------------+------------+
| 2 |   60.0    | 14.0 |   60.0    | 18.0 |    9.0    |    0.4     |    2.5     | 200.0 |       1.0        |   0.45    |   20.0   | 14.0 | 26.0 | 36.0  |   3205.79   |    3201.85    |  3412.38   |  3132.43   |   54.53    |    0.02    
'''