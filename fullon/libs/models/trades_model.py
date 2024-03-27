import psycopg2
from libs import log
from libs.models import orders_model as database
from libs.structs.trade_struct import TradeStruct
from typing import List, Any, Optional


logger = log.fullon_logger(__name__)


class Database(database.Database):

    def save_dry_trade(self, bot_id: str, trade: TradeStruct, reason: str) -> bool:
        """
        Save a dry trade to the database.

        Args:
            bot_id (str): The ID of the bot.
            trade (TradeStruct): The trade information.
            reason (str): The reason for the trade

        Returns:
            bool: True if the trade is successfully saved, False otherwise.
        """
        # SQL query for inserting a new dry trade
        sql = """
            INSERT INTO dry_trades (bot_id, uid, ex_id, symbol, side, volume, price, cost, fee, roi, roi_pct, reason, closingtrade)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # Extract values from the TradeStruct object
        values = (
            bot_id,
            trade.uid,
            trade.ex_id,
            trade.symbol,
            trade.side,
            trade.volume,
            trade.price,
            trade.cost,
            trade.fee,
            trade.roi,
            trade.roi_pct,
            reason,
            trade.closingtrade
        )

        try:
            # Execute the SQL query
            with self.con.cursor() as cur:
                cur.execute(sql, values)
                self.con.commit()
            return True
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.error(f"Error saving dry trade: {error}")
            return False

    def delete_dry_trades(self, bot_id):
        try:
            sql="delete from dry_trades where bot_id='%s'" %(bot_id)
            cur = self.con.cursor()
            cur.execute(sql)
            self.con.commit()
            cur.close()
            return True
        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(self.error_print(error = error, method = "delete_dry_trades", query = sql))   
            if cur:         
                cur.close()
        return None

    def get_last_dry_trade(self, bot_id: str, symbol: str, ex_id: str) -> Optional[TradeStruct]:
        """
        Retrieve the last dry trade from the database based on the given parameters.

        Args:
            bot_id (str): Bot ID.
            symbol (str): Symbol.
            ex_id (str): Exchange ID.

        Returns:
            Optional[TradeStruct]: The last TradeStruct object containing trade data, or None if not found.
        """
        sql = "SELECT * FROM dry_trades WHERE bot_id = %s AND symbol = %s AND ex_id = %s ORDER BY timestamp DESC LIMIT 1"
        params = (bot_id, symbol, ex_id)

        try:
            with self.con.cursor() as cur:
                cur.execute(sql, params)
                row = cur.fetchone()

            if row:
                # Get column names from cursor description
                column_names = [desc[0] for desc in cur.description]

                # Build a dictionary where keys are column names and values are data from the row
                trade_dict = dict(zip(column_names, row))

                # Use the dictionary to create a TradeStruct
                return TradeStruct(**trade_dict)
            else:
                return None

        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(self.error_print(error=error, method="get_last_dry_trade", query=sql))
            raise

    def save_trades(self, trades: List[TradeStruct]) -> bool:
        """
        Save trade information to the database.

        :param trades: List of trade information dictionaries.
        :return: True if all trades are successfully saved, False otherwise.
        """
        sql = (
            "INSERT INTO TRADES "
            "(ex_trade_id, ex_order_id, uid, ex_id, symbol, order_type, "
            "side, volume, price, cost, fee, leverage, time) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (ex_trade_id, ex_order_id) DO NOTHING"
        )
        data = []
        try:
            for trade in trades:
                data.append((
                    trade.ex_trade_id,
                    trade.ex_order_id,
                    trade.uid,
                    trade.ex_id,
                    trade.symbol,
                    trade.order_type,
                    trade.side.capitalize(),
                    trade.volume,
                    trade.price,
                    trade.cost,
                    f'{trade.fee:.8f}',
                    trade.leverage,
                    trade.time,
                ))
        except AttributeError:
            return False
        try:
            cur = self.con.cursor()
            cur.executemany(sql, data)
            self.con.commit()
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            if cur:
                cur.close()
            logger.error(f"Error can't save_trade, postgres says: {error}")
            return False
        finally:
            return True

    def delete_trade(self, trade_id: int) -> bool:
        """
        Delete a trade from the database.

        :param trade_id: The ID of the trade to delete.
        :return: True if the trade was successfully deleted, False otherwise.
        """
        sql = "DELETE FROM TRADES WHERE trade_id = %s"

        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (trade_id,))
                self.con.commit()
            return True
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.error(f"Error: can't delete trade, postgres says: {error}")
            return False

    def update_trade(self, trade_id: int, cur: Optional[Any] = None, rois: Optional[Any] = None) -> Optional[None]:
        """
        Update the trade information in the database.

        :param trade_id: The trade ID to be updated.
        :param cur: An object containing current trade information, defaults to None.
        :param rois: An object containing ROI information, defaults to None.
        :return: None
        """
        if cur:
            # Add check for values being close to zero
            cur_volume = 0 if abs(cur.volume - 0) < 1e-10 else cur.volume
            cur_avg_price = 0 if abs(cur.avg_price - 0) < 1e-10 else cur.avg_price
            cur_avg_cost = 0 if abs(cur.avg_cost - 0) < 1e-10 else cur.avg_cost
            cur_fee = 0 if abs(cur.fee - 0) < 1e-10 else cur.fee

            sql = """UPDATE TRADES SET cur_volume = %s, cur_avg_price = %s, cur_avg_cost = %s, cur_fee = %s
                     WHERE trade_id = %s"""
            params = (cur_volume, cur_avg_price, cur_avg_cost, cur_fee, trade_id)
        elif rois:
            # Similarly, add checks here if required
            sql = """UPDATE TRADES SET roi = %s, roi_pct = %s, total_fee = %s
                     WHERE trade_id = %s"""
            params = (round(rois.roi,3), rois.pct, rois.fee, trade_id)
        else:
            return None

        try:
            with self.con.cursor() as cur:
                cur.execute(sql, params)
                self.con.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            error_message = f"Error cant update_trade, postgres says: {error} for query ({sql})"
            logger.warning(error_message)
        return None

    def update_dry_trade(self, trade_id, changes):
        sql="UPDATE DRY_TRADES SET roi=%s, roi_usd=%s, roi_pct=%s where trade_id=%s" %(changes['roi'], changes['roi_usd'] ,changes['roi_pct'], trade_id)
        try:
            cur = self.con.cursor()
            cur.execute(sql)
            self.con.commit()
            cur.close()
            return True
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.info(error)
            raise

    def get_trades(self,
                   ex_id: int,
                   last: bool = False,
                   uncalculated: bool = False,
                   symbol: Optional[str] = None) -> List[TradeStruct]:
        """
        Retrieve trades from the database based on the given parameters.

        :param ex_id: Exchange ID.
        :param last: Whether to retrieve only the last trade, default is False.
        :param uncalculated: Whether to retrieve trades with uncalculated current quantities, default is False.
        :param symbol: Symbol to filter trades, default is None (no filtering).
        :raises: Exception, psycopg2.DatabaseError
        :return: A list of TradeStruct objects containing trade data.
        """

        base_sql = "SELECT * FROM trades WHERE ex_id=%(ex_id)s"
        params = {'ex_id': ex_id}
        if symbol:
            base_sql += " AND symbol=%(symbol)s"
            params['symbol'] = symbol
        if last:
            base_sql += " ORDER BY TIME DESC LIMIT 1"
        else:
            if uncalculated:
                base_sql += " AND cur_volume IS NULL"
            base_sql += " ORDER BY symbol ASC, time ASC, volume DESC"
        try:
            with self.con.cursor() as cur:
                cur.execute(base_sql, params)
                trades = [TradeStruct(*row) for row in cur.fetchall()]
        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(self.error_print(error=error, method="get_trades", query=base_sql))
            raise
        return trades