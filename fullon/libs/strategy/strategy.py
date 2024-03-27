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
        ('stop_signal', None)
    )

    name = ""
    pos = {}
    pos_price = {}
    price_pct = {}
    anypos = 0
    tick = {}
    curtime = {}
    curtime_prev = {}
    cash = {}
    totalfunds = {}
    last_candle_date = {}
    new_candle = {}
    orders = {}
    bot_vars = {}
    entry_signal = {}
    take_profit = {}
    stop_loss = {}
    timeout = {}
    feed_timeout = {}
    lastclose = {}
    closed_this_loop = {}
    order_placed = False
    indicators_df: pandas.DataFrame = pandas.DataFrame()
    open_trade: Dict = {}
    indicators: object = indicators()
    size: dict = {}

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
        self.last_candle_date = {}
        self.dbase = Database()
        self.helper = self.p.helper
        self.dry_run = self.helper.dry_run
        self.first = True
        self.order_cmd = "process_now"
        self.on_exchange = False

        if len(self.datas) < self.p.feeds:
            logger.error("Bot %s doesnt have enough feeds, needs %s has %s ",
                         self.helper.id, self.p.feeds, len(self.datas))
            exit()

        for param in ['take_profit', 'stop_loss', 'trailing_stop', 'timeout']:
            if getattr(self.p, param) == 'false':
                setattr(self.p, param, False)
        if self.p.trailing_stop:
            self.p.stop_loss = self.p.trailing_stop

        """
        each feed should have its own bot_vars variable according to its feed parameters
        """

        self.take_profit = {n: None for n in range(len(self.datas))}
        self.stop_loss = {n: None for n in range(len(self.datas))}
        self.timeout = {n: None for n in range(len(self.datas))}
        self.size = {n: self.p.size for n in range(len(self.datas))}
        self.bot_vars = {n: ['time', 'status', 'take_profit', 'timeout'] for n in range(len(self.datas))}
        for n in self.bot_vars:
            if self.p.stop_loss:
                self.bot_vars[n].extend(['stop_loss', 'rolling_loss'])

        # Handle trading attribute for feeds
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
        self.exectype = bt.Order.Limit if int(self.params.mktorder) == 0 else bt.Order.Market
        self.nextstart_done = False
        self.local_init()
        self.entry_signal = [None] * len(self.datas)
        self.open_trade = {num: TradeStruct for num, data in enumerate(self.datas) if data.timeframe == bt.TimeFrame.Ticks}
        if not self.p.size_pct and not self.p.size:
            msg = f"Parameters size({self.p.size}) or size_pct {self.p.size_pct} not set"
            logger.error(msg)
            self.cerebro.runstop()
        logger.info("Bot %s completed init sequence", self.helper.id)

    def __del__(self):
        """ description """
        return None

    def set_indicators_df(self):
        pass

    def feeds_have_futures(self):
        """ check if a trading feed supports futures """
        for _, data in enumerate(self.datas):
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

    def _check_datas_lengths(self):
        lengths = []
        for num, _ in enumerate(self.datas):
            if self.datas[num].timeframe == bt.TimeFrame.Ticks:
                lengths.append(len(self.datas[num].result))
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
        return self.datas[0].params.fromdate

    def _state_variables(self) -> None:
        """
        Sets various state variables based on the current position and data feed.

        Returns:
            None
        """
        any_pos: int = 0
        for num, datas in enumerate(self.datas):
            if self.datas[num].feed.trading:
                self.closed_this_loop[num] = False
                position = self.getposition(datas)
                self.pos[num] = position.size
                self.pos_price[num] = position.price
                self.tick[num] = datas.close[0]
                self.price_pct[num] = None
                if self.pos[num] > 0:
                    self.price_pct[num] = round((self.tick[num] - self.pos_price[num]) / self.pos_price[num] * 100, 2)  # if long
                elif self.pos[num] < 0:
                    self.price_pct[num] = round((self.pos_price[num] - self.tick[num]) / self.pos_price[num] * 100, 2)  # if short

                self.cash[num] = self.broker.getcash()
                self.totalfunds[num] = self.get_value(num=num)
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

    def get_value(self, num: Optional[int] = None):
        """
        returns how much value there is in an exchange
        """
        return self.broker.getvalue()

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

    def _print_position_variables(self, feed: int) -> None:
        """
        Prints the current position variables for a given data feed.

        Args:
            feed (int): The index of the data feed.

        Returns:
            None
        """
        print("----------------------------")
        print(f"Feed: {feed}, Exchange: {self.datas[feed].feed.exchange_name} symbol: {self.datas[feed].symbol}")
        print(f"Loop: {self.datas[0].buflen()}")
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
        for num, datas in enumerate(self.datas):
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
        current_date = self.datas[feed].datetime[0]

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

    def handle_open_pos(self, datas_num: int, is_buy: bool, tick: Optional[float] = None) -> Any:
        """
        Handles opening position for both buy and sell operations
        """
        if not tick:
            tick = self.tick[datas_num]
        is_positive = is_buy
        if is_buy:
            order = self.open_long(datas_num)
        else:
            order = self.open_short(datas_num)

        if self.p.take_profit:
            self.take_profit[datas_num] = self.calculate_trade_variable(
                tick=tick,
                percentage=self.p.take_profit,
                is_positive=is_positive  # true for long, false for short
            )
        if self.p.stop_loss:
            self.stop_loss[datas_num] = self.calculate_trade_variable(
                tick=tick,
                percentage=self.p.stop_loss,
                is_positive=not is_positive  # false for long, true for short
            )
        return order

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

        # if its not blocked, lets block ---> the problem is that the bot_status_could be a problem, 
        # specially if its a like a long order no?

        # if bot not blocked
        # then block using a new key,, say bot is opening position
        if self.datas[0].last_moments is True:
            return False
        if self.entry_signal[datas_num] == "Buy":
            order = self.handle_open_pos(datas_num, is_buy=True)
        elif self.entry_signal[datas_num] == "Sell":
            order = self.handle_open_pos(datas_num, is_buy=False)
        else:
            logger.info("Can't open a position if no signal is set")
            return False
        if self.p.timeout:
            self.timeout[datas_num] = self.curtime[datas_num].shift(minutes=self.p.timeout)
        if order:
            self.save_log(order=order, num=datas_num)
            if self.verbose:
                print(
                    "------------OPEN  feed(" + str(datas_num) + ")----------" +
                    "\nopening on: " + str(self.curtime[0].format()) +
                    "\nsignal: " + str(self.entry_signal[datas_num]) +
                    "\ntick: " + str(self.tick[datas_num]) +
                    "\nstop loss: " + str(self.stop_loss[datas_num]) +
                    "\ntake_profit: " + str(self.take_profit[datas_num]) +
                    "\n------------------\n"
                )
        else:
            logger.warning("Could not open order")
        return True

    def close_position(self, feed: int = 0, reason: str = "No reason", otype=None) -> bool:
        """ description """
        datas = self.datas[feed]
        if self.pos[feed] is None:
            logger.error("problem here", feed)
            return False
        if self.closed_this_loop[feed] is True:
            logger.warning("Already had closed this position during loop")
            return False
        self.take_profit[feed] = None
        self.stop_loss[feed] = None
        self.datas[feed].event_timeout = None
        order = None
        kwargs = {'reason': reason}
        self.lastclose[feed] = reason
        signal = ''
        if self.pos[feed] < 0:
            signal = "Buy"
        elif self.pos[feed] > 0:
            signal = "Sell"
        order = self.place_order(signal=signal,
                                 otype=otype,
                                 entry=self.pos[feed],
                                 datas=datas,
                                 reason=reason)
        self.save_log(order=order, num=feed)
        self.closed_this_loop[feed] = True
        if self.verbose:
            msg = (f"--------- CLOSED ------------\nPosition closed on:\n{self.curtime[0].format()}\nwith signal: {signal}\n--------------\n\n")
            #logger.warning(msg)
            print(msg)
        return True

    def entry(self, datas_num: int, price: Optional[float] = None) -> float:
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
            price = self.tick[datas_num]
        if self.size[datas_num]:
            entry = (self.size[datas_num] / price * self.p.leverage)
        else:
            # Get the cash available for the dataset
            available_cash = self.cash[datas_num]
            # Calculate the total cash to be used for the trade
            cash_for_trade = available_cash * (self.p.size_pct / 100)
            # Apply leverage
            cash_with_leverage = cash_for_trade * self.p.leverage
            # Calculate entry size
            entry = cash_with_leverage / price
        return entry

    def kill_orders(self):
        """ description """
        if self.dry_run:
            orders = self.broker.get_orders_open(self.datas[0])
            for order in orders:
                self.broker.cancel(order)

    def place_stop_order(self, size, price, datas=None) -> bt.Order:
        """ description """
        self.order_placed = True
        datas = self.datas[0] if not datas else datas
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

    def place_stop_limit_order(self, size, price, plimit, datas=None) -> bt.Order:
        """ description """
        self.order_placed = True
        datas = self.datas[0] if not datas else datas
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

    def place_order(self, signal, entry, otype=None, datas=None, reason=None) -> Optional[bt.Order]:
        """ description """
        self.order_placed = True
        if otype is None:
            otype = self.exectype
        datas = self.datas[0] if not datas else datas
        kwargs = {'reason': reason}
        if entry is None or entry == 0:
            print("entry size is cero", entry)
            exit()
        # maybe here save bot_vars
        if signal == "Buy":
            return self.buy(datas,
                            exectype=otype,
                            size=entry,
                            command=self.order_cmd,
                            **kwargs)
        if signal == "Sell":
            return self.sell(datas,
                             exectype=otype,
                             size=entry,
                             command=self.order_cmd,
                             **kwargs)
        return None

    def open_long(self, datas_num=0, otype=None) -> bt.Order:
        """ description """
        entry_size = self.entry(datas_num=datas_num,
                                price=self.tick[datas_num])
        self.lastclose[datas_num] = 'Open'
        return self.place_order(signal="Buy",
                                otype=otype,
                                entry=entry_size,
                                datas=self.datas[datas_num],
                                reason='Open')

    def open_short(self, datas_num=0, otype=None) -> Optional[bt.Order]:
        """ description """
        self.lastclose[datas_num] = 'Open'
        if self.datas[datas_num].feed.futures:
            entry_size = self.entry(datas_num=datas_num,
                                    price=self.tick[datas_num]) 
            return self.place_order(signal="Sell",
                                    otype=otype,
                                    entry=entry_size,
                                    datas=self.datas[datas_num],
                                    reason='Open')
        return None

    def notify_order(self, order):
        """ description """
        pass

    def notify_trade(self, trade):
        pass

    def time_to_next_bar(self, feed: int) -> arrow.Arrow:
        """
        Calculates the number of minutes until the next period/bar in the OHLCV data.

        Args:
            feed (int): The index of the feed for which time to next bar is calculated.

        Returns:
            int: Number of minutes until the next bar.
        """
        current_time = self.curtime[feed]
        compression = self.datas[feed].compression
        # Depending on the timeframe, calculate the time to the next bar
        match self.datas[feed].timeframe:
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
