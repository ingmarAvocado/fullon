"""
This class manages user accounts from exchanges.
Gets the trades, account totals, etc.
"""
import time
import threading
import arrow
from libs import settings
from libs.database import Database
from libs import exchange, cache, log
from libs.structs.trade_struct import TradeStruct
from typing import List, Any, Dict, Union, Optional
from decimal import Decimal, getcontext
getcontext().prec = 20

logger = log.fullon_logger(__name__)


class Reg:
    """ helper class"""
    roi: Decimal
    pct: Decimal
    fee: Decimal
    roi: Decimal
    pct: Decimal
    side: str
    cost: Decimal
    cur_avg_cost: Decimal
    cur_fee: Decimal
    volume: Decimal
    cur_volume: Decimal


class TradeCalculator:
    """ main account class"""

    started: bool = False

    def _init_(self):
        """ description """
        # logger.info("Initializing Account Update Manager")
        self.lastrecord = ""
        self.stop_signals = {}
        self.thread_lock = threading.Lock()
        self.threads = {}

    def _del_(self):
        self.stop_all()

    def stop(self):
        """
        Stops the tick data collection loop for the specified exchange.
        """
        with self.thread_lock:  # Acquire the lock before accessing shared resources
            if exchange_name in self.stop_signals:
                self.stop_signals[exchange_name].set()
                try:
                    # Wait for the thread to finish with a timeout
                    self.threads[exchange_name].join(timeout=10)
                except Exception as e:
                    logger.error(
                        f"Error stopping ticker for exchange {exchange_name}: {e}")
                else:
                    logger.info(f"Stopped ticker for exchange {exchange_name}")

                del self.stop_signals[exchange_name]
                del self.threads[exchange_name]
            else:
                logger.info(
                    f"No running ticker found for exchange {exchange_name}")

    def stop_all(self):
        pass

    def position_array(self,
                       prev: List[Any],
                       current: List[Any],
                       my_symbols: List[Any],
                       futures: bool
                       ) -> Dict[str, Dict[str, Union[str, Any]]]:
        """
        Create a dictionary representing the positions of symbols for the given parameters.

        :param prev: A list of previous trade information.
        :param current: A list of current trade information.
        :param my_symbols: A list of user's symbols.
        :param futures: A boolean indicating whether the trade is a futures trade.
        :return: A dictionary with positions of symbols.
        """
        if not my_symbols:
            return {}

        positions = {}

        for my_symbol in my_symbols:
            symbol = my_symbol.symbol
            if not futures:
                symbol = symbol.split('/')[0]
            positions[symbol] = {'prev': '',
                                 'current': '',
                                 'symbol': my_symbol.symbol}
        for item in prev:
            if item.symbol in positions:
                positions[item.symbol]['prev'] = item.total

        for item in current:
            if item.symbol in positions:
                positions[item.symbol]['current'] = item.total

        return positions

    def _classify_cur(self, volume: Decimal, avg_price: Decimal, avg_cost: Decimal, fee: Decimal) -> Any:
        """
        Classify the current trade information.

        :param volume: The trade volume.
        :param avg_price: The average trade price.
        :param avg_cost: The average trade cost.
        :param fee: The trade fee.
        :return: A Reg object with the trade information.
        """
        cur = Reg()
        setattr(cur, "volume", volume)
        setattr(cur, "avg_price", avg_price)
        setattr(cur, "avg_cost", avg_cost)
        setattr(cur, "fee", fee)
        return cur

    def _get_rois(self, trade: Any, cur: Any, prev: Any) -> Any:
        """
        Calculate the return on investment (ROI) for a trade.

        :param trade: Trade information.
        :param cur: Current trade information.
        :param prev: Previous trade information.
        :return: ROI object.
        """
        if trade.fee is None:
            trade.fee = 0
        rois = Reg()
        previous_cost = Decimal(trade.volume) * Decimal(prev.cur_avg_price)
        previous_fee = Decimal(prev.cur_fee) * (Decimal(trade.volume) / Decimal(prev.cur_volume))
        if trade.side == "Sell":
            roi = (Decimal(trade.cost) + Decimal(trade.fee)) - (previous_cost + previous_fee)
            roi_pct = round(Decimal(100) * (roi / (previous_cost + previous_fee)), 2)
            rois.fee = Decimal(trade.fee) + (previous_fee * (Decimal(prev.cur_volume) - Decimal(cur.volume)) / Decimal(prev.cur_volume))
        else:  # trade.side == "Buy"
            roi = (previous_cost + previous_fee) - (Decimal(trade.cost) + Decimal(trade.fee))
            roi_pct = round(Decimal(100) * (roi / (Decimal(trade.cost) + Decimal(trade.fee))), 2)
            rois.fee = Decimal(trade.fee) + (previous_fee * (Decimal(prev.cur_volume) - Decimal(cur.volume)) / Decimal(prev.cur_volume))

        rois.roi = roi
        rois.pct = roi_pct
        return rois

    def _determine_cost(self, trade: Any, prev: Any, cur_qty: Decimal) -> Decimal:
        """
        Determine the cost based on the trade, previous trade, and current volume.

        :param trade: Trade information.
        :param prev: Previous trade information.
        :param cur_qty: Current volume.
        :return: The determined cost.
        """
        if cur_qty < 0:
            cur_qty *= -1

        if trade.volume * trade.price == trade.cost:
            result = cur_qty * Decimal(prev.cur_avg_price)
        else:
            result = cur_qty / Decimal(prev.cur_avg_price)

        return result

    def _increase_position(
            self,
            trade: TradeStruct,
            cur_qty: Decimal,
            prev_trade: Optional[TradeStruct] = None) -> Any:
        """
        Increase the position for a given trade.

        :param trade: The trade for which the position is to be increased.
        :param cur_qty: The current volume of the trade, defaults to None.
        :param prev_trade: The previous trade, defaults to None.
        :return: True if the trade update is successful, False otherwise.
        """
        if trade.fee is None:
            trade.fee = 0
        if not prev_trade:
            if trade.side == 'Sell':
                trade.volume *= -1
            current_values = self._classify_cur(
                volume=Decimal(trade.volume),
                avg_price=Decimal(trade.price),
                avg_cost=Decimal(trade.cost),
                fee=Decimal(trade.fee))
        else:
            current_values = self._classify_cur(
                volume=cur_qty,
                avg_price=Decimal(trade.price),
                avg_cost=Decimal(trade.cost) + Decimal(prev_trade.cur_avg_cost),
                fee=Decimal(trade.fee) + Decimal(prev_trade.cur_fee))
        with Database() as dbase:
            update_result = dbase.update_trade(
                trade_id=trade.trade_id, cur=current_values)
        return self._return_trade(trade=trade, cur=current_values)

    def _position_reduced(self, trade: Any, prev: Any, cur_qty: Decimal) -> bool:
        """
        Check if the position is reduced.

        :param trade: Trade information.
        :param prev: Previous trade information.
        :param cur_qty: Current volume.
        :return: True if the position is reduced, False otherwise.
        """
        if trade.side == "Sell" and cur_qty > 0:
            if cur_qty < prev.cur_volume:
                return True
        elif trade.side == "Buy" and cur_qty < 0:
            if cur_qty > prev.cur_volume:
                return True
        return False

    def _reduce_position(self, trade: Any, cur_qty: Decimal, prev: Any) -> None:
        """
        Reduce the position.

        :param trade: Trade information.
        :param cur_qty: Current volume.
        :param prev: Previous trade information.
        :return: None
        """
        fee = Decimal(prev.cur_fee) - (Decimal(prev.cur_fee) * cur_qty / Decimal(prev.cur_volume))
        cur = self._classify_cur(
            volume=cur_qty,
            avg_price=prev.cur_avg_price,
            avg_cost=self._determine_cost(
                trade=trade,
                prev=prev,
                cur_qty=cur_qty),
            fee=fee)
        with Database() as dbase:
            dbase.update_trade(trade_id=trade.trade_id, cur=cur)
            rois = self._get_rois(trade=trade, cur=cur, prev=prev)
            dbase.update_trade(trade_id=trade.trade_id, rois=rois)
        return self._return_trade(trade=trade, cur=cur)

    @staticmethod
    def _return_trade(trade: Any, cur: Any) -> Any:
        """
        Update the trade object with the current trade information.

        :param trade: Trade object to be updated.
        :param cur: Current trade information.
        :return: The updated trade object.
        """
        trade.cur_volume = cur.volume
        trade.cur_avg_price = cur.avg_price
        trade.cur_avg_cost = cur.avg_cost
        trade.cur_fee = cur.fee
        return trade

    def _calc_increase_position(self, cur_qty: Decimal, trade: Any, prev: Any) -> Any:
        """
        Calculate the increased position.

        :param cur_qty: The current volume of the trade.
        :param trade: The trade object.
        :param prev: The previous trade object.
        """
        if cur_qty == 0:
            cur = self._classify_cur(volume=cur_qty,
                                     avg_price=0,
                                     avg_cost=0,
                                     fee=0)
            with Database() as dbase:
                dbase.update_trade(trade_id=trade.trade_id, cur=cur)
                rois = self._get_rois(trade=trade, cur=cur, prev=prev)
                dbase.update_trade(trade_id=trade.trade_id, rois=rois)
            return self._return_trade(trade=trade, cur=cur)
        else:
            if self._position_reduced(trade=trade, prev=prev, cur_qty=cur_qty):
                return self._reduce_position(trade=trade, cur_qty=cur_qty, prev=prev)
            else:
                return self._increase_position(trade=trade, cur_qty=cur_qty, prev_trade=prev)

    def _calc_reduce_position(self, cur_qty: Decimal, trade: Any, prev: Any) -> Any:
        """
        Calculate the reduction in position for a trade.

        :param cur_qty: Current volume.
        :param trade: Trade information.
        :param prev: Previous trade information.
        """
        if cur_qty == 0:  # Fully closing a trade
            cur = self._classify_cur(volume=cur_qty,
                                     avg_price=0,
                                     avg_cost=0,
                                     fee=0)
            with Database() as dbase:
                dbase.update_trade(trade_id=trade.trade_id, cur=cur)
                rois = self._get_rois(trade=trade, cur=cur, prev=prev)
                dbase.update_trade(trade_id=trade.trade_id, rois=rois)
            return self._return_trade(trade=trade, cur=cur)
        # Partial close
        elif self._position_reduced(trade=trade, prev=prev, cur_qty=cur_qty):
            return self._reduce_position(trade=trade, cur_qty=cur_qty, prev=prev)
        else:
            return self._increase_position(trade=trade, cur_qty=cur_qty, prev_trade=prev)

    def update_trade_calcs(self, exch: object) -> None:
        """
        Update trade calculations for a user's exchange, including calculating
        the current volume, ROI, and other relevant metrics for uncalculated trades.

        :param exch: The UserExchange object containing the user's exchange information.
        :return: None
        """
        # Fetch all trades for the given bot ID
        with Database() as dbase:
            all_trades: List[TradeStruct] = dbase.get_trades(ex_id=exch.ex_id)

        if not all_trades:
            return

        # Create a dictionary mapping trade timestamps to their index in the all_trades list
        trade_timestamp_to_index = {trade.timestamp: i for i, trade in enumerate(all_trades)}

        # Filter out uncalculated trades
        uncalculated_trades: List[TradeStruct] = [
            trade for trade in all_trades if trade.cur_volume is None]

        if not uncalculated_trades:
            return

        prev_trade = None
        for trade in uncalculated_trades:
            current_trade_index = trade_timestamp_to_index[trade.timestamp]
            if prev_trade and trade.symbol != prev_trade.symbol:
                # If symbols don't match, reset prev_trade to None
                prev_trade = None
            if prev_trade:
                # Calculate the current volume
                if trade.side == "Buy":
                    cur_qty = Decimal(prev_trade.cur_volume) + Decimal(trade.volume)
                else:
                    cur_qty = Decimal(prev_trade.cur_volume) - Decimal(trade.volume)
                cur_qty = cur_qty.quantize(Decimal('0.000000001'))
                if trade.side == prev_trade.side:
                    prev_trade = self._calc_increase_position(
                                cur_qty=cur_qty, trade=trade, prev=prev_trade)
                else:
                    prev_trade = self._calc_reduce_position(
                                cur_qty=cur_qty, trade=trade, prev=prev_trade)
            else:
                try:
                    cur = Decimal(trade.cur_volume)
                except TypeError:
                    cur = Decimal(0)
                prev_trade = self._increase_position(
                        trade=trade,
                        cur_qty=cur,
                        prev_trade=None)

    def calculate_user_trades(self) -> None:
        """
        Run account loop to start threads for each user's active exchanges.

        The method retrieves the list of users and their active exchanges, then starts a thread for each
        exchange, storing the thread in the 'threads' dictionary. Sets the 'started' attribute to True
        when completed.
        """
        with cache.Cache() as store:
            exchanges = store.get_exchanges()
        for exch in exchanges:
            self.update_trade_calcs(exch=exch)
