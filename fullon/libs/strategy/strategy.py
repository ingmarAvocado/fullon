"""
description
"""
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals)
import backtrader as bt
import arrow
from libs import log
from libs.database import Database
from libs.structs.trade_struct import TradeStruct
import pandas
from typing import Optional, Dict, Any


logger = log.fullon_logger(__name__)


class indicators():
    pass


class Strategy(bt.Strategy):
    """ description """

    verbose = False
    cash = {}
    totalfunds = {}

    params = (
        ('helper', None),
        ('mktorder', True),
        ('take_profit', False),
        ('stop_loss', False),
        ('trailing_stop', False),
        ('timeout', False),
        ('size_pct', False),
        ('size', 0),
        ('size_currency', 'USD'),
        ('leverage', 1),
        ('pre_load_bars', 100),
        ('feeds', 2),
        ('pairs', False),
        ('stop_signal', None),
        ('str_id', None),
        ('cat_str_id', None),
        ('bot_id', None),
        ('uid', None),
        ('cat_name', None)
    )

    def __init__(self):
        """
        Initialize the class.

        Attributes:
            last_candle_date (dict): A dictionary to store the last candle date.
            dbase (Database): An instance of the Database class.
            helper (Helper): An instance of the Helper class.
            dry_run (bool): Whether to perform a dry run.
            first (bool): Initial flag.
            order_cmd (str): Command for order processing.
            on_exchange (bool): Status of the exchange.
            take_profit (dict): Details about take profit.
            stop_loss (dict): Details about stop loss.
            bot_vars (dict): Bot variables according to feed parameters.
            exectype (bt.Order): Type of order execution.
            nextstart_done (bool): Status of the next start process.
            entry_signal (list): List of entry signals.
            open_trade (dict): Details of open trades.
        """
        self._instance_variables()
        self._set_datafeeds()
        self.last_candle_date = {}
        self.dbase = Database()
        self.helper = self.p.helper
        self.dry_run = self.helper.dry_run
        self.first = True
        self.order_cmd = "process_now"
        self.on_exchange = False

        if len(self.str_feed) < self.p.feeds:
            logger.error("Bot %s doesnt have enough feeds, needs %s has %s ",
                         self.helper.id, self.p.feeds, len(self.str_feed))
            self.cerebro.runstop()

        for param in ['take_profit', 'stop_loss', 'trailing_stop', 'timeout']:
            if getattr(self.p, param) == 'false':
                setattr(self.p, param, False)
        if self.p.trailing_stop:
            self.p.stop_loss = self.p.trailing_stop
        """
        each feed should have its own bot_vars variable according to its feed parameters
        """
        self.take_profit = {n: None for n in range(len(self.str_feed))}
        self.stop_loss = {n: None for n in range(len(self.str_feed))}
        self.timeout = {n: None for n in range(len(self.str_feed))}
        self.size = {n: self.p.size for n in range(len(self.str_feed))}
        self.bot_vars = {n: ['time', 'status', 'take_profit', 'timeout'] for n in range(len(self.str_feed))}
        for n in self.bot_vars:
            if self.p.stop_loss:
                self.bot_vars[n].extend(['stop_loss', 'rolling_loss'])

        self.exectype = bt.Order.Limit if int(self.params.mktorder) == 0 else bt.Order.Market
        self.nextstart_done = False
        self.local_init()
        self.entry_signal = [None] * len(self.str_feed)
        self.open_trade = {num: TradeStruct for num, data in enumerate(self.str_feed) if data.timeframe == bt.TimeFrame.Ticks}
        if not self.p.size_pct and not self.p.size:
            msg = f"Parameters size({self.p.size}) or size_pct {self.p.size_pct} not set"
            logger.error(msg)
            self.cerebro.runstop()
        logger.info("Bot %s completed init sequence", self.helper.id)

    def __del__(self):
        """ description """
        return None

    def _instance_variables(self) -> None:
        """
        """
        self.name = ""
        self.pos = {}
        self.pos_price = {}
        self.price_pct = {}
        self.anypos = 0
        self.tick = {}
        self.curtime = {}
        self.last_candle_date = {}
        self.new_candle = {}
        self.orders = {}
        self.bot_vars = {}
        self.entry_signal: dict[Any, Any] = {}
        self.take_profit: dict[Any, Any] = {}
        self.stop_loss: dict[Any, Any] = {}
        self.timeout = {}
        self.feed_timeout = {}
        self.lastclose = {}
        self.closed_this_loop = {}
        self.order_placed = False
        self.indicators_df: pandas.DataFrame = pandas.DataFrame()
        self.open_trade: Dict = {}
        self.indicators: object = indicators()
        self.size: dict = {}
        self.str_feed: list = []
        self.post_message = False

    def _set_datafeeds(self):
        """
        Configures datafeeds in a bit more friendly way
        """
        for num, data in enumerate(self.datas):
            try:
                data.feed.trading
            except AttributeError:
                class feed:
                    trading = False
                setattr(data, "feed", feed)
                self.closed_this_loop[num] = False
                if data.dataframe.empty:
                    logger.error("Bot %s produces empty dataframe for feed %s and symbol %s",
                                 self.helper.id, num, data.symbol)
                    self.cerebro.runstop()
            if data.feed.str_id == self.p.str_id:
                self.str_feed.append(self.datas[num])
                self.datas[num]._name = str(len(self.str_feed)-1)

    def set_indicators_df(self):
        pass

    def feeds_have_futures(self):
        """ check if a trading feed supports futures """
        for _, data in enumerate(self.str_feed):
            if data.timeframe == bt.TimeFrame.Ticks:
                if not data.feed.futures:
                    return False
        return True

    def local_init(self):
        """ description """
        pass

    def nextstart(self):
        if not self._check_datas_lengths():
            logger.error("Check your feeds as they are not all equal in size")
            logger.info("Maybe you want to update ohlcv for the corresponding symbols")
            exit()

    def next(self):
        """ description """
        pass

    def _end_next(self):
        pass

    def local_nextstart(self):
        pass

    def local_next_event(self):
        pass

    def _check_datas_lengths(self):
        lengths = []
        for num, _ in enumerate(self.str_feed):
            if self.str_feed[num].timeframe == bt.TimeFrame.Ticks:
                lengths.append(len(self.str_feed[num].result))
        first_length = lengths[0]
        for length in lengths[1:]:
            if length != first_length:
                msg = "Lowest time frame (usually 1min) need to measure the same. Dont forget to remove pickle files "
                logger.error(msg)
                return False
        return True

    def _bar_start_date(self, compression: int, period: str):
        """
        Gets starting date of bot data feed
        """
        return self.str_feed[0].params.fromdate

    def _state_variables(self) -> None:
        """
        Sets various state variables based on the current position and data feed.

        Returns:
            None
        """
        any_pos: int = 0
        for num, datas in enumerate(self.str_feed):
            if self.str_feed[num].feed.trading:
                self.closed_this_loop[num] = False
                position = self.getposition(datas)
                self.pos[num] = position.size
                self.pos_price[num] = position.price
                self.tick[num] = datas.open[0]
                self.price_pct[num] = None
                if self.pos[num] > 0:
                    self.price_pct[num] = round((self.tick[num] - self.pos_price[num]) / self.pos_price[num] * 100, 2)  # if long
                elif self.pos[num] < 0:
                    self.price_pct[num] = round((self.pos_price[num] - self.tick[num]) / self.pos_price[num] * 100, 2)  # if short
                self.cash[num] = self.broker.getcash()
                self.totalfunds[num] = self.broker.getvalue()
                if position.size != 0:
                    self.update_trade_vars(feed=num)
                    any_pos = 1
                else:
                    self.take_profit[num] = None
                    self.stop_loss[num] = None
            curtime = arrow.get(bt.num2date(datas.datetime[0]))
            if datas.timeframe != bt.TimeFrame.Ticks:
                if curtime.microsecond > 999000:
                    curtime = curtime.ceil('minute').shift(microseconds=1)
            self.curtime[num] = curtime
            self.new_candle[num] = self._is_new_candle(feed=num)
        self.anypos = any_pos

    def set_indicator(self, name: str, value: Any) -> None:
        """
        sets object self.indicator with a new attribute name, with value value
        Args:
            name (str): Name of the attribute.
            value (str): value of the attribure
        """
        setattr(self.indicators, name, value)

    def _set_indicators(self):
        """
        """
        self._state_variables()
        self.udpate_indicators_df()
        if not self.indicators_df.empty:
            self.indicators_df = self.indicators_df.tail(self.params.pre_load_bars + 1)
            self.indicators_df.dropna(inplace=True)
        self.set_indicators()
        self.get_entry_signal()

    def set_indicators(self):
        pass

    def _this_indicators(self, current_time: arrow.Arrow, fields: list):
        """
        helps sets the indicators for a strategy, as self.indicator.[field]

        Args:
            current_time (arrow):  dataframe index time to get the indicator value
            fields  (list):  fields available in self.indicator_df to get
        """
        for indicator in fields:
            try:
                value = self.indicators_df.loc[current_time, indicator]
                self.set_indicator(indicator, value)
            except KeyError:
                self.set_indicator(indicator, None)

    def _print_position_variables(self, feed: int) -> None:
        """
        Prints the current position variables for a given data feed.

        Args:
            feed (int): The index of the data feed.

        Returns:
            None
        """
        print("----------------------------")
        print(f"Feed: {feed}, Exchange: {self.str_feed[feed].feed.exchange_name} symbol: {self.str_feed[feed].symbol}")
        print(f"Loop: {self.str_feed[0].buflen()}")
        print("Tick: ", self.tick[feed])
        print("Date: ", self.curtime[feed])
        print("Availabe Balance: ", self.cash[feed])
        print("Total Balance: ", self.totalfunds[feed])
        print("Pos: ", self.pos[feed])
        try:
            print("Entry Signal: ", self.entry_signal[feed])
        except (AttributeError, KeyError) as error:
            print("Entry Signal: ", "N/A for this feed")
        print("New Candle: ", self.new_candle[feed])
        if self.pos[feed]:
            try:
                print("Profit: ", self.take_profit[feed])
                print("Stop: ", self.stop_loss[feed])
                print(f"Rolling Stop: {self.p.trailing_stop}%")
            except KeyError:
                print("No stops for feed: ", feed)
            if feed in self.timeout:
                print("Timeout: ", self.timeout[feed])
        print("----------------------------")

    def check_input_params(self):
        """ description """
        params = dict(vars(self.p))
        del (params['timeout'])
        del (params['mktorder'])
        del (params['take_profit'])
        del (params['stop_loss'])
        del (params['trailing_stop'])
        try:
            del (params['helper'])
        except BaseException:
            pass
        for p in params:
            if params[p] == 0:
                logger.info(
                    "Input params contains at least a zero, program may or may not run")
                logger.info("Zero at: %s", p)
                return False
        return True

    def risk_management(self):
        pass

    def check_exit(self) -> bool:
        """ description """
        result = False
        for num, datas in enumerate(self.str_feed):
            if datas.feed.trading:
                if self.pos[num] != 0:
                    # If timeout reached, then get out.
                    if self.p.timeout and num in self.timeout:
                        if self.timeout[num] <= self.curtime[num]:
                            if self.close_position(feed=num, reason="timeout"):
                                result = True
                            continue
                    # if handling auto orders for risk management on exchange
                    if self.on_exchange:
                        pass
                        # will need to check with exchange
                        # if orders are set properly, good.
                        # if not set/reset them.
                    # if bot does not open orders, it will market buy/sell when
                    # targets reached.
                    else:
                        if self.pos[num] > 0:
                            if self._check_long(feed=num):
                                result = True
                            continue
                        else:
                            if self._check_short(feed=num):
                                result = True
                            continue
        return result

    def _check_long(self, feed: int) -> bool:
        """
        Manages risk for long positions by checking and applying various risk management
        techniques such as take profit, stop loss, and rolling stop.      
        Args:
            feed (int): The feed index to manage risk for.
        """
        # Check if take profit is enabled and if the current tick price has reached
        # or exceeded the take profit value, then close the position and return.
        if self.p.take_profit:
            if self.tick[feed] >= self.take_profit[feed]:
                self.close_position(feed=feed, reason="take_profit", )
                return True

        # Check if stop loss is enabled and if the current tick price has reached
        # or dropped below the stop loss value, then close the position and return.
        if self.p.stop_loss:
            if self.tick[feed] <= self.stop_loss[feed]:
                self.close_position(feed=feed, reason="stop_loss")
                return True
        return False

    def _check_short(self, feed: int) -> bool:
        """
        Manages risk for short positions by checking and applying various risk management
        techniques such as take profit, stop loss, and rolling stop.
        Args:
            feed (int): The feed index to manage risk for.
        """
        # Check if take profit is enabled and if the current tick price has reached
        # or dropped below the take profit value, then close the position and return.
        if self.p.take_profit:
            if self.tick[feed] <= self.take_profit[feed]:
                self.close_position(feed=feed, reason="take_profit")
                return True

        # Check if stop loss is enabled and if the current tick price has reached
        # or exceeded the stop loss value, then close the position and return.
        if self.p.stop_loss:
            if self.tick[feed] >= self.stop_loss[feed]:
                self.close_position(feed=feed, reason="stop_loss")
                return True
        return False

    def _is_new_candle(self, feed: int) -> bool:
        """
        Check if a new candle has been formed in the given data feed.

        Parameters:
        feed (int): Index of the data feed to check.

        Returns:
        bool: True if a new candle has been formed, False otherwise.
        """
        # Early exit for tick data
        if feed == 0:
            return False

        # Get the current date of the feed
        current_date = self.str_feed[feed].datetime[0]

        # Check if a new candle has been formed
        new_candle_formed = (
            feed not in self.last_candle_date or
            current_date > self.last_candle_date.get(feed, 0)
        )

        # Update the last candle date if a new candle has been formed
        if new_candle_formed:
            self.last_candle_date[feed] = current_date

        return new_candle_formed

    def save_log(self, order: bt.Order, num: int):
        """ description """
        return

    def get_entry_signal(self):
        """ description """
        return

    def _post_message(self, datas_num: int = 0, open_pos: bool = False, close_pos: bool = False):
        """
        Posts a message on X when a position happens
        """
        pass


    def update_trade_vars(self, feed: int = 0) -> None:
        """
        Update the dynamic trade variables (trailing_stop) for a specific feed.

        Args:
            feed (int, optional): The index of the feed for which trade variables
                                  are updated. Defaults to 0.
        """
        if self.pos[feed] == 0:
            return
        is_positive = self.pos[feed] > 0
        # Check if a trailing stop is defined for this strategy
        try:
            if self.p.trailing_stop:
                if is_positive:
                    stop_loss = self.calculate_trade_variable(self.tick[feed],
                                                              self.p.stop_loss,
                                                              False)

                    if self.stop_loss[feed] is None:
                        self.stop_loss[feed] = stop_loss
                    elif stop_loss > self.stop_loss[feed]:
                        self.stop_loss[feed] = stop_loss
                elif not is_positive:
                    stop_loss = self.calculate_trade_variable(self.tick[feed],
                                                              self.p.stop_loss,
                                                              True)
                    if self.stop_loss[feed] is None:
                        self.stop_loss[feed] = stop_loss
                    elif stop_loss < self.stop_loss[feed]:
                        self.stop_loss[feed] = stop_loss
        except TypeError:
            raise

    @staticmethod
    def calculate_trade_variable(tick: float,
                                 percentage: Optional[float],
                                 is_positive: bool) -> Optional[float]:
        """
        Calculate trading variables based on a percentage of tick value.

        Args:
            tick (float): The current tick value.
            percentage (Optional[float]): The desired percentage of the tick value.
            is_positive (bool): A flag indicating whether the result should be a positive or negative change.

        Returns:
            Optional[float]: The trading variable calculated as a percentage of the tick value. If the percentage is None,
            the function will return None as well.
        """
        if percentage is None:
            return None
        percentage = float(percentage)
        return tick + float(tick) * float(percentage) / 100 if is_positive else tick - tick * percentage / 100

    def open_pos(self,
                 datas_num: int = 0,
                 otype: Optional[str] = None) -> bool:
        """
        Open a position for a given feed.

        Args:
            datas_num (int, optional): The index of the data feed. Defaults to 0.
            otype (Optional[str], optional): The type of operation. Defaults to None.

        Returns:
            Optional[bool]: Returns True if the operation was successful, 
                           None if the operation was not successful (e.g., if it is the last moment).
        """
        if self.str_feed[0].last_moments is True:
            return False
        is_long = False
        signal = "Buy"
        if self.entry_signal[datas_num] == "Buy":
            is_long = True
        elif self.entry_signal[datas_num] == "Sell":
            signal = "Sell"
            is_long = False
        if is_long and not self.str_feed[datas_num].feed.futures:
            logger.error("Not allowed to open short on this exchange ")
            return False
        value = self.entry(datas_num=datas_num)
        self.lastclose[datas_num] = 'Open'
        order = self.place_order(signal=signal,
                                 size=value,
                                 datas_num=datas_num,
                                 otype=otype)

        if self.p.timeout:
            self.timeout[datas_num] = self.curtime[datas_num].shift(minutes=self.p.timeout)
        if order:
            if self.p.take_profit:
                self.take_profit[datas_num] = self.calculate_trade_variable(
                    tick=self.tick[datas_num],
                    percentage=self.p.take_profit,
                    is_positive=is_long  # true for long, false for short
                )
            if self.p.stop_loss:
                self.stop_loss[datas_num] = self.calculate_trade_variable(
                    tick=self.tick[datas_num],
                    percentage=self.p.stop_loss,
                    is_positive=not is_long  # false for long, true for short
                )
            self.save_log(order=order, num=datas_num)
            if self.verbose:
                print(
                    "------------Add pos  feed(" + str(datas_num) + ")----------" +
                    "\nDate: " + str(self.curtime[0].format()) +
                    "\nsignal: " + str(self.entry_signal[datas_num]) +
                    "\ntick: " + str(self.tick[datas_num]) +
                    "\nstop loss: " + str(self.stop_loss[datas_num]) +
                    "\ntake_profit: " + str(self.take_profit[datas_num]) +
                    "\n------------------\n"
                )
            self._post_message(datas_num=datas_num, go_long=is_long, open_pos=True)
        else:
            logger.warning("Could not open order")
        return True

    def close_position(self, feed: int = 0, reason: str = "No reason", otype=None) -> bool:
        """ description """
        if self.pos[feed] is None:
            logger.error("problem here", feed)
            return False
        if self.closed_this_loop[feed] is True:
            logger.warning("Already had closed this position during loop")
            return False
        self.take_profit[feed] = None
        self.stop_loss[feed] = None
        self.str_feed[feed].event_timeout = None
        order = None
        self.lastclose[feed] = reason
        signal = ''
        is_long = False
        if self.pos[feed] < 0:
            is_long = True
            signal = "Buy"
        elif self.pos[feed] > 0:
            signal = "Sell"
        order = self.place_order(signal=signal,
                                 otype=otype,
                                 size=self.pos[feed],
                                 datas_num=feed,
                                 reason=reason)
        self.save_log(order=order, num=feed)
        self.closed_this_loop[feed] = True
        if self.verbose:
            msg = ("--------- CLOSED ------------\nPosition closed on: " +
                   f"\n{self.curtime[0].format()}\nwith signal: {signal}\n" +
                   f"reason: {reason}\n--------------\n\n")
            print(msg)
        self._post_message(datas_num=datas_num, go_long=is_long, close_pos=True)
        return True

    def change_position(self,
                        size: float,
                        datas_num: int = 0,
                        otype: Optional[str] = None,
                        reason: Optional[str] = None) -> bool:
        """
        Changes a position for a given feed.

        Args:
            size (float): The amount to change the position
            datas_num (int, optional): The index of the data feed. Defaults to 0.
            otype (Optional[str], optional): The type of operation. Defaults to None.

        Returns:
            Optional[bool]: Returns True if the operation was successful, 
                           None if the operation was not successful (e.g., if it is the last moment).
        """

        # if its not blocked, lets block ---> the problem is that the bot_status_could be a problem, 
        # specially if its a like a long order no?

        # if bot not blocked
        # then block using a new key,, say bot is opening position
        if self.str_feed[0].last_moments is True:
            return False
        signal = "Sell"
        if size > 0:
            signal = "Buy"
        order = self.place_order(signal=signal,
                                 size=size,
                                 otype=otype,
                                 datas_num=datas_num,
                                 reason=reason)

        if order:
            self.save_log(order=order, num=datas_num)
            if self.verbose:
                print(
                    "------------Change pos  feed(" + str(datas_num) + ")----------" +
                    "\nDate: " + str(self.curtime[0].format()) +
                    "\ntick: " + str(self.tick[datas_num]) +
                    "\n------------------\n"
                )
        else:
            logger.warning("Could not open order")
        return True

    def entry(self, datas_num: int, price: Optional[float] = None) -> Optional[float]:
        """
        Compute the position size for trading, considering either a set position size,
        a percentage of available cash, or defaulting to the latest tick price.

        Args:
            datas_num (int): Index for data feed.
            price (Optional[float]): Price at which trading is considered. Defaults to the latest tick price.

        Returns:
            float: Computed position size for the trade.

        Note:
            This method uses `self.get_value(pair)` to ensure accuracy across varying collateral currencies.
        """
        # Defaulting to tick data if price not provided
        if not price:
            price = self.str_feed[datas_num].close[0]
        fee_pct = self.broker.getcommissioninfo(self.datas[0]).p.commission
        if self.size[datas_num]:
            cash_for_trade = self.size[datas_num] / (1 + fee_pct)
            entry = cash_for_trade / price
        else:
            buffered_size_pct = round(self.p.size_pct / (1 + fee_pct), 2)
            sizer = bt.sizers.PercentSizer(percents=buffered_size_pct)
            self.setsizer(sizer)
            entry = None
        return entry

    def kill_orders(self):
        """ description """
        if self.dry_run:
            orders = self.broker.get_orders_open(self.str_feed[0])
            for order in orders:
                self.broker.cancel(order)

    def place_stop_order(self, size, price, datas=None):
        """ description """
        self.order_placed = True
        datas = self.str_feed[0] if not datas else datas
        if size < 0:
            return self.buy(datas,
                            exectype=bt.Order.StopLimit,
                            size=size,
                            price=price)
        if size > 0:
            return self.sell(datas,
                             exectype=bt.Order.StopLimit,
                             size=size,
                             price=price)

    def place_stop_limit_order(self, size, price, plimit, datas=None):
        """ description """
        self.order_placed = True
        datas = self.str_feed[0] if not datas else datas
        if size < 0:
            return self.buy(datas,
                            exectype=bt.Order.StopLimit,
                            size=size,
                            price=price,
                            plimit=plimit)
        if size > 0:
            return self.sell(datas,
                             exectype=bt.Order.StopLimit,
                             size=size,
                             price=price,
                             plimit=plimit)

    def place_order(self,
                    size: float,
                    signal: str,
                    otype=None,
                    datas_num: int = 0,
                    reason=None) -> Optional[bt.Order]:
        """ Places an order in backtrader broker

         Args:
            size (float): The amount to change the position
            value (float): The amount to change the position
            datas_num (int, optional): The index of the data feed. Defaults to 0.
            otype (Optional[str], optional): The type of operation. Defaults to None.

        Returns:
            Optional[bool]: Returns True if the operation was successful, 
                           None if the operation was not successful (e.g., if it is the last moment).
        """
        '''
        if size and value:
            logger.info("Size and Value detected for trade, lets just use value")
            size = None
        elif not size and not value:
            logger.error("A size or value input value is necessary")
            return
        '''
        self.order_placed = True
        if otype is None:
            otype = self.exectype
        datas = self.str_feed[datas_num]
        kwargs = {'reason': reason}
        if signal == "Buy":
            return self.buy(datas, exectype=otype, size=size, command=self.order_cmd, **kwargs)
        if signal == "Sell":
            return self.sell(datas, exectype=otype, size=size, command=self.order_cmd, **kwargs)
        return None

    def time_to_next_bar(self, feed: int) -> arrow.Arrow:
        """
        Calculates the number of minutes until the next period/bar in the OHLCV data.

        Args:
            feed (int): The index of the feed for which time to next bar is calculated.

        Returns:
            int: Number of minutes until the next bar.
        """
        current_time = self.curtime[feed]
        compression = self.str_feed[feed].compression
        # Depending on the timeframe, calculate the time to the next bar
        match self.str_feed[feed].timeframe:
            case bt.TimeFrame.Minutes:
                next_bar_time = current_time.shift(minutes=compression)
            case bt.TimeFrame.Days:
                next_bar_time = current_time.shift(days=compression)
            case bt.TimeFrame.Weeks:
                next_bar_time = current_time.shift(weeks=compression)
            case bt.TimeFrame.Months:
                next_bar_time = current_time.shift(months=compression)
            case bt.TimeFrame.Years:
                next_bar_time = current_time.shift(years=compression)
            case _:
                raise ValueError("Unsupported timeframe")
        return next_bar_time
