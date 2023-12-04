import sys
import time
from libs import settings
from exchanges.ccxt.interface import Interface
from libs import log
logger = log.fullon_logger(__name__)


#This the interface for Binance

class Interface(Interface):
    
    def __init__(self, exchange, db, db_ohlcv, params, dry_run=False):
        logger.info("Loading Binance Exchange")
        super().__init__(exchange, db, db_ohlcv, params)
        self.ws.verbose = False
        self.short = True

    
    def fetch_all_trades(self,symbol = None, since = None, limit = None, params = {}):
        trades = self.execute_ws("fetch_trades",[symbol,since,limit,params,])
        correctedtrades=[]
        for t in trades:
            if t['info']['m'] == "True":
                t['takerOrMaker']="Maker"
            else:
                t['takerOrMaker']="Taker"
            correctedtrades.append(t)
        return correctedtrades


    def create_order(self, symbol, order_type, side, amount, price="", params=[]):
        #print (amount)
        #print (float(amount)-.00001)
        #self.ws.verbose = True
        amount = self.find_minimum_order_cost(amount = amount, price = price, symbol = sybmol)
        return (self.execute_ws("create_order",[symbol, order_type, side, float(amount)-.00001, price, params]))
        
        
    def get_my_trades_from(self, symbol, from_id=None, from_date=None):
        import arrow
        ts = round (arrow.get(from_date).float_timestamp, 3)
        ts = int(str(ts).replace('.', ''))
        params={ 'startTime': ts }  #i am testing here.
        return self.fetch_my_trades( symbol = symbol, params=params )


    def find_minimum_order_cost(self, amount, price, symbol):
        if not price:
            price = float(self.cache.get_price( symbol = symbol, cat_ex_id = self.cat_ex_id) )
        mincost = self.minimum_order_cost(symbol = symbol)
        cost = amount * price
        if cost < mincost:
            return ( mincost / price  ) #return new amount
        return amount


    def minimum_order_cost(self, symbol):
        currency = symbol.split("/")[1]
        if currency == 'BTC':
            return .00101
        elif 'USD' in currency:
            return  10.2

        
    #binance does not appear to support stop loss, so here we emualte it with a stop limit
    def create_stop_order(self, symbol, side, volume, price,  params=[]):
        if side == "Sell":
            finalprice = price/1.01 # minus 0.1%
        if side == "Buy":
            finalprice = price*1.01 # plus .1%
        finalprice = self.decimal_rules(finalprice, symbol)
        price = self.decimal_rules(price, symbol)
        binance_params = {'type' : 'STOP_LOSS_LIMIT', 'stopPrice' : price,'timeInForce':'GTC','price':finalprice};
        binance_params.update(params)
        self.ws.verbose = False
        order = self.execute_ws("create_order",[symbol, 'market', side, volume, price, binance_params])
        return order
        
        
    #binance does not appear to support stop loss, so here we emualte it with a stop limit
    def create_stop_limit_order(self, symbol, side, volume, price, plimit, params):
        plimit = self.decimal_rules(plimit, symbol)
        price = self.decimal_rules(price, symbol)
        binance_params = {'type' : 'STOP_LOSS_LIMIT', 'stopPrice' : plimit,'timeInForce':'GTC','price':price};
        binance_params.update(params)
        order =  self.execute_ws("create_order",[symbol, 'market', side, volume, price, binance_params])
        return order


        


    def get_open_orders(self, symbol = None, since = None, limit = None, params={}):
        ret_orders = {}
        if limit == None:
            limit = 300        
        if since:
            import arrow
            since = int(float(arrow.get(since).shift(days= -3).format('X')))
        symbols = []
        if not symbol:
            tmp = self.db.get_my_symbols(uid = self.uid, ex_id = self.ex_id)
            for s in tmp:
                symbols.append(s.symbol)
        else:
            symbols.append(symbol)
        for symbol in symbols:
            orders = self.execute_ws("fetch_orders",[symbol, since, limit, params,])
            for o in orders:
                status = o['status'].capitalize()
                if status == 'New' or status =='Open':
                    ret_orders[o['id']] = status
            time.sleep(settings.INTERVAL)
        time.sleep(1)
        return ret_orders #,open_orders



 
