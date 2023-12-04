
import sys
import time
from libs import settings
from exchanges.ccxt.interface  import Interface
from libs import log
import arrow

logger = log.fullon_logger(__name__)



#This the interface for deribit
class Interface(Interface):
    
    def __init__(self, exchange, db, db_ohlcv, params, dry_run=False):
        logger.info("Loading derbit Exchange")
        self.contract = 1
        super().__init__(exchange, db, db_ohlcv, params)
        self.tradehistory = True
        self.futures = True
     
        
    """
    def get_historical_data(self,symbol,timeframe,since,limit,params={}):
        #does not seem to be working
        return  None
    """
            
    def set_leverage(self, symbol, leverage):
        self.leverage = leverage
        return None  
        
    def test_url(self):
        return "https://test.deribit.com"


    def get_all_tickers(self, sleep = 1):
        try:
            time.sleep(settings.INTERVAL)
            tickers = {}
            #markets = self.db.get_symbols(exchange='deribit')
            #this is for BTC-Perpetual
            deribit_params={
                "instrument_name": "BTC-PERPETUAL",
                "count": "1"
            }
            trade = self.execute_ws("public_get_get_last_trades_by_instrument",[deribit_params])
            #date = arrow.get(int(trade['result'][0]['timeStamp'])/1000).format()
            date = arrow.utcnow().format()
            price = trade['result']['trades'][0]['price']
            tickers.update({'BTC-PERPETUAL':{'symbol':'BTC-PERPETUAL','datetime':date,'openPrice':price,'highPrice':price,'lowPrice':price,'close':price,'volume':'0'}})
            time.sleep(settings.INTERVAL)
            deribit_params={
                "instrument_name": "ETH-PERPETUAL",
                "count": "1"
            }
            trade = self.execute_ws("public_get_get_last_trades_by_instrument",[deribit_params])
            #date = arrow.get(int(trade['result'][0]['timeStamp'])/1000).format()
            price = trade['result']['trades'][0]['price']
            tickers.update({'ETH-PERPETUAL':{'symbol':'ETH-PERPETUAL','datetime':date,'openPrice':price,'highPrice':price,'lowPrice':price,'close':price,'volume':'0'}})
            return tickers
        except:
            #raise
            logger.warn("cant get_all_tickers")
            time.sleep(sleep)
            return self.get_all_tickers(sleep = sleep +1)

  

    
    def get_total_user_account(self):
        accounts = []
        accounts.append(self.get_account(currency = "BTC"))
        accounts.append(self.get_account(currency = "ETH"))
        #private_get_get_account_summary("deribit:",accounts)
        return accounts
    

    def get_account(self, currency, sleep = 1):
        params = {"currency": currency}
        try:
            balance = self.execute_ws("private_get_get_account_summary",[params,])['result']
        except:
            time.sleep(sleep)
            return self.get_account(currency = currency, sleep = sleep +1) if sleep < 60 else None
        account = {
        'total':balance['balance'],
        'used':float(balance['balance']) - float(balance['available_funds']),
        'free':balance['available_funds'],
        'base': currency
        }
        try:
            time.sleep(settings.INTERVAL)
            params = {"currency": currency, "kind": "future"}
            positions = self.execute_ws("private_get_get_positions",[params])
        except:
            logger.info("sleeping could not get private_get_get_positions")
            time.sleep(sleep)
            return self.get_account(currency = currency, sleep = sleep +1)     
        time.sleep(1)
        symbols = self.db.get_exchange_symbols(self.cat_ex_id)
        pos = []
        positions = {} if not positions else positions
        for s in symbols:
            if s[0].startswith(currency):
                free,used,total = [0,0,0]
                this = None
                if 'result' in positions.keys():
                    for p in positions['result']:
                        if p['instrument_name'] == s[0]:
                            total = p['size']
                            used = 0
                            free = total-used
                            this = {'symbol':s[0],'free':free,'used':used,'total':total}
                if not this:
                   this = {'symbol':s[0],'free':0,'used':0,'total':0}
                pos.append(this)
        account['positions'] = pos
        return (account)


       

    def fetch_my_trades(self, symbol = None, since = None, limit = None, params = {}):
        if limit == None:
            limit = 300
        if since == None:
            since = 0 #1420000000
        #print("since....",since)
        if len(str(since)) == 12:
            since = since * 10
        if len(str(since)) == 11:
            since = since * 100
        #self.ws.verbose = True
        trades = self.execute_ws("fetch_my_trades",[symbol, since, limit, params,])
        
        #sys.exit()
        #if trades:
        #    print(trades[-1])

        """
        if len(trades) < 5:
            print (trades)
        else:
            print("ttooo big how")
            print(trades[:-1])
        """
        ret_trades = []
        for t in trades:
            #print(t)
            #print("---------------")
            cost = float(t['amount']) / float (t['price'])
            date = t['datetime']
            t = t['info']
            ret_trades.append({'id':t['trade_id'],'order':t['order_id'],'side':t['direction'].capitalize(),'takerOrMaker':t['order_type'],
                'type':t['order_type'],'amount':t['amount'],'fee':{'cost':t['fee'],'currency':t['fee_currency']},
                'cost':cost,'price':t['price'],'datetime':date,'symbol':symbol,'isUSDBased':True})
        return ret_trades


    def get_my_trades_from(self, symbol, from_id=None, from_date=None):
        ts = round (arrow.get(from_date).float_timestamp, 3)
        ts = int(str(ts).replace('.', ''))
        #ts = None #nothing seems to work on deribit for now.. maybe api2
        return self.fetch_my_trades(symbol = symbol, since=ts)
        
    def get_open_orders(self, symbol = None, since = None, limit = None, params={}):
        ret_orders={}
        
        deribit_params={
            "instrument_name": symbol,
            "type": "any"
        }
        
        web_orders = self.execute_ws("private_get_get_open_orders_by_instrument',",[deribit_params])  # 'get_open_orders_by_instrument',
        for o in web_orders['result']:
            oid =  str(o['order_id'])
            ret_orders[oid] = 'Open'
        return ret_orders #,open_orders  

    def cancel_all_orders(self, symbol):
        params = {"instrument_name":symbol}
        order = self.execute_ws("private_get_cancel_all_by_instrument",[params])
        return order


    def set_ideal_fomo_price(self, signal, ticker, symbol):
        if symbol == "BTC-PERPETUAL":
            if signal == "Buy":
                return ticker-.5
            elif signal == "Sell":
                return ticker+.5 
        elif symbol == "ETH-PERPETUAL":
            if signal == "Buy":
                return ticker-.05
            elif signal == "Sell":
                return ticker+.05 
        else:
            if signal == "Buy":
                factor=-1
            elif signal == "Sell":
                factor=1 
            if not self.precision:
                print ("I may fail here")
                self.get_market(symbol=symbol)
            tick_size=1/(10**self.precision)
            return ticker+(tick_size*factor)  


    def entry(self, symbol, leverage = 1 , price = None,  pct = 1):  
        if not price:
            price = self.cache.get_price(symbol=symbol)        
        if "BTC" in symbol:
            totfunds = self.cache.get_full_account(uid = self.uid, ex_id = self.ex_id, currency = "BTC").base_total
            entry = round(pct * totfunds / 100 * price / self.contract * leverage)
            entry = round(entry/10,0)*10
            return  entry
        elif "ETH" in symbol:  #this is because eth/usd in bitmex
            totfunds = self.cache.get_full_account(uid = self.uid, ex_id = self.ex_id, currency = "ETH").base_total
            allowedfunds = pct * totfunds / 100
            return round(allowedfunds * price  * leverage) 
        return 0       


    def create_stop_order(self, symbol, side, volume, price, params):
        params = {
           'stopPx': price,  # your stop price
            'type': 'stop_market',
            "time_in_force": "good_till_cancel",
            "execInst": "last_price"
        }
        return self.execute_ws("create_order",[symbol, 'market', side, volume, price, params])
     
    def create_stop_limit_order(self, symbol, side, volume, price, plimit, params):
        params = {
           'stopPx': plimit,  # your stop price
            'type': 'stop_limit',
            "time_in_force": "good_till_cancel",
            "execInst": "last_price"
        }
        return self.execute_ws("create_order",[symbol, 'limit', side, volume, price, params])
