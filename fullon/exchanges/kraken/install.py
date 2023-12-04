import sys
import time
from libs import settings
from run import system_manager
from libs import log
import arrow
from munch import munchify


logger = log.fullon_logger(__name__)


class install_exchange():
    
    def __init__(self):
        return None
        
    def install(self):
        return True
        
        
    def get_params(self):
        params=[]
        param={'name':'SIMUL_FUNDS','type':'int','default':1}
        params.append(param)
        param={'name':'SIMUL_LIMITFEE','type':'float','default':.01}
        params.append(param)
        param={'name':'SIMUL_MKTFEE','type':'bool','default':.01}
        params.append(param)
        return params
        
    def get_ohlcv_view(self):
        OHLCV =f"""
            CREATE MATERIALIZED VIEW SCHEMA.candles1m
            WITH (timescaledb.continuous) AS
            SELECT time_bucket('1 minutes', timestamp) AS ts,
                    FIRST(price, timestamp) as open,
                    MAX(price) as high,
                    MIN(price) as low,
                    LAST(price, timestamp) as close,
                    SUM(volume) as vol
            FROM SCHEMA.trades
            WHERE SCHEMA.trades.timestamp > '2017-01-01'
            GROUP BY ts WITH NO DATA;
            commit;

            SELECT add_continuous_aggregate_policy('SCHEMA.candles1m',
                start_offset => INTERVAL '2 h',
                end_offset => INTERVAL '1 h',
                schedule_interval => INTERVAL '1 h');
            commit;
            ALTER TABLE SCHEMA.candles1m  RENAME COLUMN ts to timestamp;
            """
        return OHLCV

