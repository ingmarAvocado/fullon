import time
from libs import log, settings
from libs.cache import Cache
from libs.structs.trade_struct import TradeStruct
from libs.structs.order_struct import OrderStruct
from exchanges.ccxt.interface import Interface as Ccxt_Interface
from exchanges.bitmex import websockets
from typing import Dict, Any, Union, List, Optional
from  ccxt.base.errors import RequestTimeout

logger = log.fullon_logger(__name__)


#this is the interface for bitmex

class Interface(Ccxt_Interface):

    def __init__(self, exchange, params, dry_run=False):
        super().__init__(exchange, params)
        self.exchange = exchange
        self.params = params
        self.ws.verbose = False
        self.short = True
        self.delete_trades = False
        self._sleep = float(settings.BITMEX_TIMEOUT)
        self._load_markets()
        '''
        if not self.currencies:
            self.set_currencies()
        if not self.pairs:
            self.set_pairs()
        self._markets = self._markets_dict()
        self._ws_pre_check()
        self.start_token_refresh_thread()
        '''
        self.no_sleep.extend(['start_ticker_socket',
                              'start_trade_socket',
                              'start_my_trades_socket',
                              'my_open_orders_socket',
                              'create_order',
                              'cancel_order'])

    def _load_markets(self, retries=5):
        """
        load markets and if time out try every 5 seconds unitl 2 hours.
        Define the end time of the loop (2 hours from now)
        """
        end_time = time.time() + 2 * 60 * 60  # 2 hours in seconds
        end_time = time.time() + 1  # minute hours in seconds

        while time.time() < end_time:
            try:
                # Attempt to load markets if they are not loaded
                if not self.ws.markets:
                    self.ws.load_markets()
                break  # If load_markets succeeds, break out of the loop
            except RequestTimeout:
                # Sleep for some time before retrying (e.g., 1 second)
                logger.error("Cann't connect to Bitmex, seems connection has been timedout")
                time.sleep(5)
            except Exception as e:
                if 'request has expired' in str(e):
                    time.sleep(1)
                    if retries > 0:
                        self._load_markets(retries=retries-1)
                    else:
                        raise e
                raise e  # or log the error, etc.
        else:
            pass

    def get_markets(self) -> Dict[str, Dict[str, str]]:
        """
        This method retrieves market data from the WebSocket instance, processes it,
        and returns a dictionary containing the relevant information for each market.
        """
        # Get the markets dictionary from the WebSocket instance
        markets_dict = self.ws.markets
        # Initialize an empty dictionary to store the processed market data
        result = {}
        # Iterate over the markets in the markets_dict
        for market in markets_dict.values():
            # Add the extracted information to the result dictionary
            result[market['symbol']] = {
                'symbol': market['id'],
                'wsname': 'bitmex',
                'base': market['base'],
                'cost_decimals': 4,
                'pair_decimals': 4
            }

        # Return the processed result dictionary
        return result

    def replace_symbol(self, symbol):
        """
        """
        match symbol:
            case 'BTC/USD':
                return 'XBTUSD'
        return symbol.replace("/", "")

    def get_tickers(self, sleep: int = 1) -> Dict[str, Dict[str, Union[str, float]]]:
        """
        Retrieve ticker information for all available markets.

        :param sleep: Sleep interval between ticker updates, default is 1 second.
        :return: A dictionary with ticker symbols as keys and ticker information as values.
        """
        markets = self.execute_ws("fetch_tickers")
        if not markets:
            return {}

        tickers = {}
        for m in markets:
            market = markets[m]
            tickers.update(
                {
                    market['symbol']: {
                        'symbol': market['symbol'],
                        'datetime':  market['close'],
                        'openPrice': market['close'],
                        'highPrice': market['close'],
                        'lowPrice': market['close'],
                        'close': market['close'],
                        'volume': 0
                    }
                }
            )
        return tickers

    def connect_websocket(self) -> bool:
        """
        Establishes a connection to the WebSocket and sets the `websocket_connected` attribute to True.

        Returns:
        bool: True if the WebSocket connection was successfully established, False otherwise.
        """
        if not self._socket:
            key, secret = self.get_user_key(ex_id=self.params.ex_id)
            self._socket = websockets.WebSocket(ex_id=self.params.ex_id, api_key=key, api_secret=secret, markets={})
            self._socket.connect()
            if self._socket.started is False:
                self._socket = None
                return self.connect_websocket()
            logger.info(f"Bitmex WebSocket initiated ex_id {self.params.ex_id}")
            self._ws_subscriptions['tickers'] = []
            self._ws_subscriptions['trades'] = []
            self._ws_subscriptions['ownTrades'] = False
            self._ws_subscriptions['openOrders'] = False
            return True
        return False

    def start_trade_socket(self, tickers: list) -> bool:
        """
        Subscribes to trade updates
        Args:
        tickers (list): A list of trading pairs to subscribe to.
        Returns:
        bool: True if the subscription was successfully created, False otherwise.
        """
        self._ws_pre_check()
        logger.info("Starting BitMEX trade websockets")
        # Apply symbol replacement and remove duplicates
        tickers = list(set(self.replace_symbol(ticker) for ticker in tickers))
        # Clear existing tickers from cache
        if not self._socket.subscribe_trades(tickers=tickers):
            logger.error("Failed to initiate trade subscription")
            return False
        # Wait for subscriptions to be confirmed
        max_attempts = 20
        attempt = 0
        while attempt < max_attempts:
            subscribed_tickers = set()
            for subscription in self._socket.subscriptions:
                for ticker in tickers:
                    if f"trade:{ticker}" in subscription:
                        subscribed_tickers.add(ticker)
            if len(subscribed_tickers) == len(tickers):
                # All tickers have been subscribed
                self._ws_subscriptions['trades'].extend(tickers)
                logger.info(f"Successfully subscribed to trade feeds for: {', '.join(tickers)}")
                return True
            time.sleep(0.5)  # Wait for 0.5 seconds before checking again
            attempt += 1
        # If we've reached this point, not all tickers were subscribed
        logger.error(f"Timed out waiting for trade subscriptions. Subscribed: {len(subscribed_tickers)}/{len(tickers)}")
        return False

    def stop_trade_socket(self) -> bool:
        """
        Subscribes to ticker updates

        Args:
        tickers (list): A list of trading pairs to subscribe to.

        Returns:
        bool: True if the subscription was successfully closed, False otherwise.
        """
        self._ws_pre_check()
        return self._socket.unsubscribe_trades()

    def start_ticker_socket(self, tickers: List[str]) -> bool:
        """
        Subscribes to ticker updates for specified trading pairs.

        Args:
        tickers (List[str]): A list of trading pairs to subscribe to.

        Returns:
        bool: True if the subscription was successfully created for all tickers, False otherwise.
        """
        self._ws_pre_check()
        logger.info("Starting BitMEX ticker websockets")
        # Apply symbol replacement and remove duplicates
        tickers = list(set(self.replace_symbol(ticker) for ticker in tickers))
        # Clear existing tickers from cache
        with Cache() as cache:
            cache.del_exchange_ticker('bitmex')
        # Subscribe to tickers
        if not self._socket.subscribe_tickers(tickers=tickers):
            logger.error("Failed to initiate ticker subscription")
            return False
        # Wait for subscriptions to be confirmed
        timeout = 40  # 40 seconds total timeout
        interval = 2  # Check every 2 seconds
        for _ in range(timeout // interval):
            with Cache() as cache:
                subscribed_tickers = cache.get_tickers(exchange='bitmex')
                if len(subscribed_tickers) == len(tickers):
                    logger.info(f"Successfully started BitMEX ticker websockets for {len(tickers)} pairs")
                    self._ws_subscriptions['tickers'].extend(tickers)
                    return True
            time.sleep(interval)
        logger.warning(f"Timed out waiting for all ticker subscriptions. "
                       f"Subscribed to {len(subscribed_tickers)} out of {len(tickers)} tickers")
        return False

    def stop_ticker_socket(self) -> bool:
        """
        Subscribes to ticker updates

        Args:
        tickers (list): A list of trading pairs to subscribe to.

        Returns:
        bool: True if the subscription was successfully closed, False otherwise.
        """
        logger.info("Stopped websockets bitmex tickers")
        return self._socket.unsubscribe_tickers()

    def start_my_trades_socket(self) -> bool:
        """
        Subscribes to user's trades.

        Returns:
        bool: True if the subscription was successfully created, False otherwise.
        """
        return True
        try:
            if 'ownTrades' in self._socket.subscriptions:
                return True
        except AttributeError:
            pass
        self._ws_pre_check()
        if self._socket.subscribe_private(
                subscription={'name': 'ownTrades', 'token': self._ws_token},
                callback=self._socket.on_my_trade):
            count = 0
            while 'ownTrades' not in self._socket.subscriptions or count > 20:
                time.sleep(0.5)
                count += 1
            if count > 20:
                return False
            self._ws_subscriptions['ownTrades'] = True
            return True
        return False

    def start_candle_socket(self, tickers: List[str]) -> bool:
        """
        Subscribes to ticker updates for specified trading pairs.

        Args:
        tickers (List[str]): A list of trading pairs to subscribe to.

        Returns:
        bool: True if the subscription was successfully created for all tickers, False otherwise.
        """
        self._ws_pre_check()
        logger.info("Starting BitMEX candles websockets")
        # Apply symbol replacement and remove duplicates
        tickers = list(set(self.replace_symbol(ticker) for ticker in tickers))
        if not self._socket.subscribe_candles(tickers=tickers):
            logger.error("Failed to initiate candle subscription")
            return False
        # Wait for subscriptions to be confirmed
        '''
        timeout = 40  # 40 seconds total timeout
        interval = 2  # Check every 2 seconds
        for _ in range(timeout // interval):
            with Cache() as cache:
                subscribed_tickers = cache.get_tickers(exchange='bitmex')
                if len(subscribed_tickers) == len(tickers):
                    logger.info(f"Successfully started BitMEX ticker websockets for {len(tickers)} pairs")
                    self._ws_subscriptions['tickers'].extend(tickers)
                    return True
            time.sleep(interval)
        logger.warning(f"Timed out waiting for all ticker subscriptions. "
                       f"Subscribed to {len(subscribed_tickers)} out of {len(tickers)} tickers")
        '''
        return False

    def stop_candles_socket(self) -> bool:
        """
        Subscribes to ticker updates

        Args:
        tickers (list): A list of trading pairs to subscribe to.

        Returns:
        bool: True if the subscription was successfully closed, False otherwise.
        """
        logger.info("Stopped websockets bitmex candles")
        return self._socket.unsubscribe_candles()

    def _ws_pre_check(self):
        """
        Perform pre-subscription checks and setup.
        """
        try:
            if not self._socket.is_connected():
                logger.info("WebSocket not connected. Attempting to connect...")
                self._socket.connect()
                time.sleep(1)  # Give it a moment to establish connection
            if not self._socket.is_connected():
                raise ConnectionError("Failed to establish WebSocket connection")
                return False
        except AttributeError as error:
            if 'is_connected' in str(error):
                if self.connect_websocket():
                    return True
            logger.error("Websocket has not been initialized, have you run connect_websocket()")
            return False
        return True


    '''

    def get_tickers(self):
        markets = self.execute_ws("fetch_markets")
        tickers = {}
        if markets:
            for market in markets:
                if market['active']is True:
                    #print (market['info']['timestamp'])
                    #print ( arrow.get(market['info']['timestamp']).format() )
                    #sys.exit()
                    #sys.exit()
                    tickers.update({market['id']:{'symbol':market['symbol'],'datetime':arrow.get(market['info']['timestamp']).format(),'openPrice':market['info']['prevClosePrice'],'highPrice':market['info']['highPrice'],'lowPrice':market['info']['lowPrice'],'close':market['info']['lastPrice'],'volume':market['info']['volume']}})
        return tickers
    '''
    
    '''    
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
    '''