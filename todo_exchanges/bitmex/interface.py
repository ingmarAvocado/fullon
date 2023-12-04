import sys
import time
from exchanges.ccxt.interface import Interface
from libs import settings, log
import arrow


logger = log.fullon_logger(__name__)


#this is the interface for bitmex

class Interface(Interface):
    
    def __init__(self, exchange, db, db_ohlcv, params, dry_run=False):
        super().__init__(exchange, db, db_ohlcv, params)
        self.short = True
        self.tradehistory = True
        self.ws.verbose = False



    def get_all_tickers(self):
        time.sleep(settings.INTERVAL)
        markets = self.execute_ws("fetch_markets")
        tickers = {}
        if markets:
            for market in markets:
                if market['active']  == True:
                    #print (market['info']['timestamp'])
                    #print ( arrow.get(market['info']['timestamp']).format() )
                    #sys.exit()
                    #sys.exit()
                    tickers.update({market['id']:{'symbol':market['symbol'],'datetime':arrow.get(market['info']['timestamp']).format(),'openPrice':market['info']['prevClosePrice'],'highPrice':market['info']['highPrice'],'lowPrice':market['info']['lowPrice'],'close':market['info']['lastPrice'],'volume':market['info']['volume']}})
        return tickers
    
    def set_ideal_fomo_price(self, signal, ticker, symbol):
        if symbol=="BTC/USD":
            if signal == "Buy":
                return ticker-.5
            elif signal == "Sell":
                return ticker+.5 
        elif symbol=="ETH/USD":
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

    def check_bitmex_rules(self, price, signal, symbol):
        if symbol=="BTC/USD":
            if signal == "Buy":
                return int(price)
            elif signal == "Sell":
                return round(price) 
        elif symbol=="ETH/USD":
            if signal == "Buy":
                return int(pirce)
            elif signal == "Sell":
                return round(price)
        else:
            return price
    
    def set_leverage(self, symbol, leverage):
        self.leverage = leverage
        return None
        symbol = self.replace_symbol(symbol)
        response = self.execute_ws("private_get_position",[{'filter':'{"symbol": "'+symbol+'"}','columns':'leverage'}])
        if not response:
            self.leverage = leverage
            return None
        ex_leverage = response[0]['leverage']
        if int(leverage) != int(ex_leverage):
            time.sleep(0.5)
            self.ws.verbose = True
            self.execute_ws("private_post_position_leverage",[{'symbol':symbol,'leverage':leverage}])   
            return self.set_leverage(symbol=symbol, leverage=leverage)
        self.leverage = leverage
        return None
    
          
    def get_exchange_funds(self):
        return self.execute_ws("private_get_user_wallet")['amount']/100000000
        
    def ticker_data(self,symbol):
        if symbol == 'BTC/USD':
            symbol='XBTUSD'
            params={'symbol':symbol,'count':1,'reverse':'True','columns':'price'}
            time.sleep(settings.INTERVAL)
            ticker=self.ws.public_get_trade(params)
            return ticker[0]['price']
        else:
            return super().ticker_data(symbol)
            
    def get_total_user_account(self):
        balance = self.execute_ws("fetch_balance")
        if not balance:
            time.sleep(3)
            return self.get_total_user_account()
        account = {'total':balance['total']['BTC'],'used':balance['used']['BTC'],'free':balance['free']['BTC'],'base':'BTC'}
        positions = self.execute_ws("private_get_position")
        if not positions:
            time.sleep(3)
            return self.get_total_user_account()
        symbols = self.db.get_exchange_symbols(self.cat_ex_id)
        pos = []
        for s in symbols:
            free,used,total=[0,0,0]
            for p in positions:
                if p['symbol']=="XBTUSD":
                    p['symbol']="BTC/USD"
                if p['symbol']=="ETHXBT":
                    p['symbol']="ETH/BTC"
                if p['symbol']=="ETHUSD":
                    p['symbol']="ETH/USD"
                if p['symbol'] == s[0]:
                    total=p['currentQty']
                    used=p['openOrderSellQty']+p['openOrderBuyQty']
                    free=total-used
                pos.append({'symbol':s[0],'free':free,'used':used,'total':total})
            if not positions:
                pos.append({'symbol':s[0],'free':0,'used':0,'total':0})
        account['positions']=pos
        return ([account])

    def replace_symbol(self,symbol):
        if symbol=="BTC/USD":
            symbol="XBTUSD"
        if symbol=="ETH/BTC":
            symbol="ETHBTC"
        if symbol=="ETH/USD":
            symbol="ETHUSD"
        return symbol
        
        

    def get_open_orders(self, symbol = None, since = None, limit = None, params={}):
#    def get_orders(self, symbol = None, since = None, limit = None, params={}):
        ret_orders={}
        ws_params={'reverse':'true'}
        if limit == None:
            limit = 300        
        ws_params['count'] = limit
        if symbol:
            symbol = self.replace_symbol(symbol)
            ws_params['symbol'] = symbol
        if since:
            since=arrow.get(since).shift(days =-3).format('YYYY-MM-DDTHH:mm:ss')+".000Z"
            ws_params['startTime'] = since
        orders=self.execute_ws("private_get_order",[ws_params])
        for order in orders:
            status=order['ordStatus']
            if status == 'New':
                ret_orders[str(order['orderID'])] = 'Open'
        return ret_orders #,open_orders





    def cancel_all_orders(self, symbol):
        symbol = self.replace_symbol(symbol)
        orders = self.execute_ws("private_delete_order_all",[{'symbol':symbol},])
        #print ("a ver si las cancela:", orders)
        return None
        


    def fetch_my_trades(self, symbol = None, since = None, limit = None, params = {}):
        if limit == None:
            limit=300
        if since == None:
            since="2015-01-01T00:00:00.00Z"
        since=arrow.get(since).format('YYYY-MM-DDTHH:mm:ss')+".000Z"
        trades=self.execute_ws("private_get_execution_tradehistory",[{'symbol':self.replace_symbol(symbol), 'startTime':since, 'count':limit}]) 
        ret_trades=[]
        time.sleep(1)
        for t in trades:
            if t['side'] !="":
                cost=t['lastQty']/t['avgPx']
                fee=t['commission']*cost
                trade={'id':t['execID'],'order':t['orderID'],'side':t['side'],'type':t['ordType'],'amount':t['lastQty'],'fee':{'cost':fee,'currency':'BTC'},'cost':cost,'price':t['lastPx'],'datetime':t['timestamp'],'symbol':symbol,'isUSDBased':True}
                ret_trades.append(trade)
        return ret_trades   
            
        
    def get_my_trades_from(self, symbol, from_id=None, from_date=None):
        return self.fetch_my_trades(symbol = symbol, since = from_date)


        
    def create_stop_order(self, symbol, side, volume, price, params):
        price = self.check_bitmex_rules(price = price, signal=side, symbol = symbol)
        if 'linkedOrder' in params:
            newparams={'ordType':'Stop','orderQty': volume, 'side': side, 'stopPx': price, 'clOrdLinkID':params['linkedOrder'],'contingencyType':"OneCancelsTheOther"}
        else:
            #if not order:
            newparams={'ordType':'Stop','orderQty': volume, 'side': side, 'stopPx': price}
        #print (newparams)
        newparams.update(params)   
        order=self.execute_ws("create_order",[symbol, 'market', side, volume, None, newparams])
        return order

    def create_stop_limit_order(self, symbol, side, volume, price, plimit, params):
        price = self.check_bitmex_rules(price = price, signal=side, symbol = symbol)
        plimit = self.check_bitmex_rules(price = plimit, signal=side, symbol = symbol)
        if 'linkedOrder' in params:
            newparams={'ordType':'StopLimit','orderQty': volume, 'side': side, 'stopPx': plimit, 'price':price, 'clOrdLinkID':params['linkedOrder'],'contingencyType':"OneCancelsTheOther"}
        else:
            #if not order:
            newparams={'ordType':'StopLimit','orderQty': volume, 'side': side, 'stopPx': plimit , 'price': price}
        newparams.update(params)
        order=self.execute_ws("create_order",[symbol, 'limit', side, volume, None, newparams])
        return order
       

    def entry(self, symbol, price=None):        
        if not price:
            price = self.cache.get_price(symbol=symbol)
        totfunds = self.cache.get_full_account(uid=self.uid, ex_id=self.ex_id, currency="BTC").base_total
        #get localleverage
        if symbol.startswith("BTC"):
            return  round(self.pct * totfunds / 100 * price * self.leverage)
        else:  #this is because eth/usd in bitmex
            allowedfunds = self.pct * totfunds / 100
            contract_size = 0.000001 * price
            return round(allowedfunds / contract_size * self.leverage)

