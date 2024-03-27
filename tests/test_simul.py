import pytest
from libs.simul import simul
from pandas import DataFrame, Timestamp



@pytest.fixture(scope="module")
def sim():
    sim = simul()
    yield sim
    del sim


@pytest.mark.order(1)
def test_calculate_final_summary(sim):
    # Test this beast
    summaries = {
        0: {
            'Strategy': 'trading_rsi', 'Symbol': 0,
            'Start Date': Timestamp('2023-08-14 14:01:00'),
            'End Date': Timestamp('2023-09-01 18:41:00'),
            'stop_loss': 1.5, 'take_profit': 2.5, 'trailing_stop': 0.8,
            'timeout': 24.0, 'size_pct': 10.0, 'size': 1, 'rsi_upper': 63.0,
            'rsi_lower': 25.0, 'rsi_period': 14.0, 'leverage': 2.0,
            'Total Trades': 18, 'Profitable Trades': 13, 'Loss Trades': 5,
            'Win Rate (%)': 72.22, 'Total Fees': 72.94,
            'Average Return %': 0.8294, 'Total Return': 302.21,
            'Total ROI %': 3.02, 'Median Return': 0.985,
            'Negative Returns Standard Deviation': 0.1484,
            'Positive Returns Standard Deviation': 0.9383,
            'Average Duration (hours)': 4.0, 'Profit Factor': 'placeholder',
            'Recovery Factor': 'placeholder', 'Sharpe Ratio': 0.6619,
            'params': {},
            'df': DataFrame(),
            'Compression': 1,
            'Period': 'Days'
        },
        1: {
            'Strategy': 'trading_moving_avg', 'Symbol': 1,
            'Start Date': Timestamp('2023-08-10 09:30:00'),
            'End Date': Timestamp('2023-08-30 16:00:00'),
            'stop_loss': 1.8, 'take_profit': 2.8, 'trailing_stop': 1.0,
            'timeout': 48.0, 'size_pct': 12.0, 'size': 1, 'rsi_upper': 65.0,
            'rsi_lower': 20.0, 'rsi_period': 12.0, 'leverage': 3.0,
            'Total Trades': 21, 'Profitable Trades': 15, 'Loss Trades': 6,
            'Win Rate (%)': 71.43, 'Total Fees': 100.23,
            'Average Return %': 1.2, 'Total Return': 400.0,
            'Total ROI %': 4.0, 'Median Return': 1.2,
            'Negative Returns Standard Deviation': 0.2,
            'Positive Returns Standard Deviation': 1.2,
            'Average Duration (hours)': 5.0, 'Profit Factor': 'placeholder',
            'Recovery Factor': 'placeholder', 'Sharpe Ratio': 0.8,
            'params': {},
            'df': DataFrame(),
            'Compression': 1,
            'Period': 'Days'
        },
        2: {
            'Strategy': 'trading_macd', 'Symbol': 2,
            'Start Date': Timestamp('2023-07-01 11:00:00'),
            'End Date': Timestamp('2023-07-20 15:20:00'),
            'stop_loss': 1.3, 'take_profit': 2.3, 'trailing_stop': 0.7,
            'timeout': 36.0, 'size_pct': 8.0, 'size': 1, 'rsi_upper': 70.0,
            'rsi_lower': 30.0, 'rsi_period': 10.0, 'leverage': 2.5,
            'Total Trades': 12, 'Profitable Trades': 9, 'Loss Trades': 3,
            'Win Rate (%)': 75.0, 'Total Fees': 50.3,
            'Average Return %': 0.9, 'Total Return': 300.5,
            'Total ROI %': 3.005, 'Median Return': 1.0,
            'Negative Returns Standard Deviation': 0.1,
            'Positive Returns Standard Deviation': 0.9,
            'Average Duration (hours)': 3.0, 'Profit Factor': 'placeholder',
            'Recovery Factor': 'placeholder', 'Sharpe Ratio': 0.75,
            'params': {},
            'df': DataFrame(),
            'Compression': 1,
            'Period': 'Days'
        }
    }
    res = sim.calculate_final_summary(summaries)
    print(res)
