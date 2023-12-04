import psycopg2
from libs import log
from libs.models import strategy_model as database


logger = log.fullon_logger(__name__)


class Database(database.Database):

    def update_order_status(self, oid, status, ex_order_id=None):
        if ex_order_id:
            sql="UPDATE ORDERS SET STATUS = '%s', EX_ORDER_ID = '%s' WHERE order_id='%s' " %(status, ex_order_id, oid)
        else:        
            sql="UPDATE ORDERS SET STATUS = '%s' WHERE order_id='%s' " %(status, oid)
        try:
            cur = self.con.cursor()
            #print (sql)
            cur.execute(sql)
            self.con.commit()
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            error="Error cant update executed orders says: " +str(error)
            logger.info(error)            
            raise
        return None

    def update_order_final_volume(self, order):
        try:
            cur = self.con.cursor()
            sql = "UPDATE ORDERS SET FINAL_QUANTITY = '%s' WHERE ORDER_ID='%s' " %(order.final_volume , order.order_id)
            cur.execute(sql)
            self.con.commit()
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            error="Error cant update executed orders says: " +str(error)
            logger.info(error)            
            raise
        return None

    #gets total money in btc
    def get_all_orders(self, uid=None, ex_id=None, status=None):
        if uid and ex_id:
            sql=("select * from orders where uid='%s' and  ex_id='%s' and status='Open'" %(uid, ex_id))
        elif status:
            sql=("select * from orders where status='%s'" %(status))
        else:
            return []
        try:
            cur = self.con.cursor()
            cur.execute(sql)
            rows =  []
            for row in cur.fetchall() :
                rows.append(dbhelpers.reg(cur,row))
            cur.close()
            if rows:
                return rows
            else:
                return []
        except (Exception, psycopg2.DatabaseError) as error:
            error="Error cant get_all_open_orders postgres says: " +str(error)
            logger.info(error)            
            raise

    def save_order(self, bot_id, uid, ex_id, exchange, cat_ex_id, symbol, order_type, side, amount, price=None, plimit=None, command=None, futures = None, reason = None):          
        if not price:
            price = 'NULL'
        if not plimit:
            plimit = 'NULL'
        tick = self.cache.get_ticker(exchange=exchange, symbol=symbol)
        tick = tick[0]
        cur = self.con.cursor()
        futures = 'f' if not futures else 't'
        sql = """INSERT INTO ORDERS(bot_id, uid, ex_id,  cat_ex_id, exchange, symbol, order_type, side, volume, price, plimit, tick, futures, status, command, reason) 
            VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', %s, %s, %s, %s, '%s' ,'New', '%s', '%s') """ %(bot_id, uid, ex_id, cat_ex_id, exchange, symbol, order_type, side, amount, price, plimit, tick, futures, command, reason)
        try:
            #print (sql)
            cur.execute(sql)
            #self.db_cache.commit()
            self.con.commit()
            cur.close()
            return True
        except (Exception, psycopg2.DatabaseError) as error:
            error="Error cant save order says: " +str(error)
            logger.info(error)            
            raise
        return None

    def get_order(self, ex_order_id=None):
        sql=("select * from orders where order_id = '%s'" %(ex_order_id))
        try:            
            cur = self.con.cursor()
            cur.execute(sql)
            row =  cur.fetchone()
            cur.close()
            if row:
                return row
            else:
                return []
        except (Exception, psycopg2.DatabaseError) as error:
            error="Error cant get_orger postgres says: " +str(error)
            logger.info(error)            
            raise
    
    def get_open_orders(self, uid=None, ex_id=None, bot_id=None):
        if uid and ex_id and not bot_id:
            sql=("select ex_order_id, order_type, volume, side, price, plimit from orders where uid='%s' and  ex_id='%s' and status='Open'" %(uid, ex_id))
        elif bot_id and not ex_id and not uid:
            sql=("select ex_order_id, order_type, volume, side, price, plimit from orders where bot_id='%s' and status='Open'" %(bot_id))
        else:
            logger.info("invalid parameters")
            return None
        try:            
            cur = self.con.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
            cur.close()
            if rows:
                return rows
            else:
                return []
        except (Exception, psycopg2.DatabaseError) as error:
            error="Error cant get open orders postgres says: " +str(error)
            logger.info(error)
            raise

    def update_orders_status(self, bot_id, status, restrict=None):
        sql="UPDATE ORDERS SET STATUS = '%s' WHERE bot_id='%s' AND status = '%s' " %(status, bot_id, restrict)
        try:
            cur = self.con.cursor()
            cur.execute(sql)
            self.con.commit()
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            error="Error cant update executed orders says: " +str(error)
            logger.info(error)            
            raise
        return None

    def get_last_order(self, bot_id):
        sql="""SELECT * from orders where bot_id='%s' order by order_id DESC limit 1""" %(bot_id)
        try:            
            cur = self.con.cursor()
            cur.execute(sql)
            row = cur.fetchone() 
            if row:
                row = dbhelpers.reg(cur, row)
                cur.close()
                return row
            else:
                cur.close()
                return None

        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(self.error_print(error=error, method="get_last_order", query=sql))
            raise