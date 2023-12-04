import psycopg2 
import sys
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sqlite3
#import urllib, json
import time
import arrow
from datetime import datetime
from libs import settings
from libs import log
from libs import cache 
from libs import database_helpers as dbhelpers 

logger=log.setup_custom_logger('database',settings.DBLOG)

class database:
    
    def __init__(self):
        self.con = self.connect_db()        
        self.cache = cache.Cache()
        
        
    def connect_db(self):
        con=""
        try:
            if settings.DBPORT != "":
                con = psycopg2.connect(dbname=settings.DBNAME, user=settings.DBUSER, host=settings.DBHOST, port=settings.DBPORT, password=settings.DBPASSWD)
            else:
                con = psycopg2.connect(dbname=settings.DBNAME, user=settings.DBUSER, host=settings.DBHOST, password=settings.DBPASSWD)
            return con
        except (Exception, psycopg2.DatabaseError) as error:
            error="Error cant connect database, postgres says: " +str(error)
            logger.info(error)
            raise


    def error_print(self, error, method, query):
        error = "Error: " +str(error)
        error = error + "\nMethod "+method
        error = error + "\nQuery " +query
        return logger.info(error)


    #returns the bot variables
    def get_bot_vars(self, bot_id):
        sql = "select message from bot_log where bot_id='%s' order by timestamp desc" %(bot_id)
        try:
            cur = self.con.cursor()
            cur.execute(sql)
            row = cur.fetchone() 
            cur.close()
            return row[0]
        except (Exception, psycopg2.DatabaseError) as error:
            error = "Error cant get user list postgres says: " +str(error)
            cur.close()
            return None
            #logger.info(error) 

   #returns the bot detail
    def get_bot_detail(self, bot_id):
        try:
            #sql = "select * from bots where bot_id='%s'" %(bot_id)
            sql = f"""SELECT
                    public.bots.name,
                    public.exchanges.name as ex_name,
                    public.symbols.symbol,
                    public.bot_exchanges.leverage,
                    public.bot_exchanges.pct,
                    public.symbols.base,
                    public.symbols.ex_base,
                    public.bots.dry_run,
                    public.bots.str_id,
                    public.bots.uid,
                    public.bots.active,
                    public.bots.timestamp
                FROM
                    public.bots
                    INNER JOIN public.bot_exchanges
                     ON public.bots.bot_id = public.bot_exchanges.bot_id
                    INNER JOIN public.exchanges
                     ON public.bot_exchanges.ex_id = public.exchanges.ex_id
                    INNER JOIN public.symbols
                     ON public.bot_exchanges.symbol_id = public.symbols.symbol_id
                 WHERE 
                    public.bots.bot_id = '{bot_id}'"""
            cur = self.con.cursor()
            cur.execute(sql)
            row = cur.fetchone() 
            row = dbhelpers.reg(cur,row)
            cur.close()
            return row
        except (Exception, psycopg2.DatabaseError) as error:
            error = "Error cant get user list postgres says: " +str(error)+sql
            if cur:
                cur.close()
            return None
            #logger.info(error)   
   

   #returns the bot detail
    def get_bot_log(self, bot_id, feed):
        try:
            sql = f"select * from bot_log where bot_id='{bot_id}'  and feed_num = '{feed}' order by timestamp desc limit 40" 
            print(sql)
            cur = self.con.cursor()
            cur.execute(sql)
            rows = []
            for row in cur.fetchall() :
                rows.append(dbhelpers.reg(cur,row))
            cur.close()
            return rows
        except (Exception, psycopg2.DatabaseError) as error:
            error = "Error cant get bot_log postgres says: " +str(error)
            if cur:
                cur.close()
            return None
   

    #returns the bot detail
    def get_bot_totals(self, bot_id, dry=False):
        if dry:
             sql = "select sum(roi) as roi, sum(fee) as fee, sum(roi_pct) as roi_pct, sum(cost) as flow from dry_trades where bot_id='%s'" %(bot_id)
        else:
             sql = "select sum(roi) as roi, sum(fee) as fee, sum(roi_pct) as roi_pct, sum(cost) as flow from trades where bot_id='%s'" %(bot_id)
        try:
            cur = self.con.cursor()
            cur.execute(sql)
            row = cur.fetchone() 
            if row[0] == None:
                row = (0,0,0,0)
            row = dbhelpers.reg(cur,row)
            cur.close()
            return row 
        except (Exception, psycopg2.DatabaseError) as error:
            error="Error cant get user list postgres says: " +str(error)
            cur.close()
            logger.info(error)  
            raise
 

    #returns the bot detail
    def get_bot_rois(self, bot_id, dry=False):
        table='trades'
        if dry:
            table='dry_trades'
        time1 = arrow.utcnow().shift(days=-7).format()
        time2 = arrow.utcnow().shift(days=-30).format()
        time3 = arrow.utcnow().shift(days=-90).format()
        sql =  """ 
        SELECT
        (select sum(roi)  from %s where bot_id='%s' and timestamp >'%s') as week, 
        (select sum(roi)  from %s where bot_id='%s' and timestamp >'%s') as month,
        (select sum(roi)  from %s where bot_id='%s' and timestamp >'%s') as trimonth 
        """  %(table, bot_id, time1, table, bot_id, time2, table, bot_id, time3)

        try:
            cur = self.con.cursor()
            cur.execute(sql)
            row = cur.fetchone() 
            row=dbhelpers.reg(cur,row)

            if row.week == None:
                row.week = 0 
            if row.month == None:
                row.month = 0
            if  row.trimonth == None:
                row.trimonth = 0

            cur.close()
            return row
        except (Exception, psycopg2.DatabaseError) as error:
            error="Error cant get user list postgres says: " +str(error)
            cur.close
            raise
            return None
            #logger.info(error) 
    

    def get_trades(self, bot_id, dry=False, last=False, since=None, limit=None):
        table = 'trades'
        if dry:
            table='dry_trades'
        if last:
            sql="""SELECT * from %s where bot_id='%s' order by timestamp DESC, trade_id DESC limit 1""" %(table, bot_id)
        elif since:
            sql="""SELECT * from %s where bot_id='%s' and timestamp > '%s' order by timestamp DESC, trade_id DESC limit 1""" %(table, bot_id, since)
        else:
            if limit:
                sql="""SELECT * from %s where bot_id='%s' order by timestamp DESC, trade_id  DESC limit %s """ %(table, bot_id, limit)
            else:
                sql="""SELECT * from %s where bot_id='%s' order by timestamp DESC, trade_id  DESC """ %(table, bot_id)
        try:          
            cur = self.con.cursor()
            cur.execute(sql)
            rows=[]
            for row in cur.fetchall() :
                rows.append(dbhelpers.reg(cur,row))
            cur.close()
            return rows
        except (Exception, psycopg2.DatabaseError) as error:
            error="Error cant get_trades postgres says: " +str(error)
            logger.info(error)            
            raise

    def get_strategy_id(self, bot_id):
        sql = "SELECT str_id from bots where bot_id = '%s' " %(bot_id) 
        try:          
            cur = self.con.cursor()
            cur.execute(sql)
            row = cur.fetchone() 
            cur.close()
            return row[0]
        except (Exception, psycopg2.DatabaseError) as error:
            error="Error cant get_strategy_id postgres says: " +str(error)
            logger.info(error)            
            raise
            
    def get_uid(self, email):
        sql = "SELECT uid from users where mail = '%s' " %(email) 
        try:          
            cur = self.con.cursor()
            cur.execute(sql)
            row = cur.fetchone() 
            cur.close()
            return row[0]
        except (Exception, psycopg2.DatabaseError) as error:
            self.error_print(error = error, method = "get_uid", query = sql)
            if cur:         
                cur.close()
        return None


    #gets exchanges read to be loaded to the bot
    def get_exchanges(self, uid = None):
        sql = """ SELECT
        exchanges.name,
        users.mail,
        users.uid,
        exchanges.ex_id,
        exchange_history.currency,
        first (exchange_history.balance) as first,
        first (exchange_history.timestamp) as fts,
        last    (exchange_history.balance) as last,
        last (exchange_history.timestamp) as lts
        FROM
            exchanges
            INNER JOIN exchange_history
            ON exchanges.ex_id = exchange_history.ex_id
            INNER JOIN users
            ON exchange_history.user_id = users.uid 
            group by exchanges.name, users.mail, users.uid, exchanges.ex_id, exchange_history.currency
            order by exchanges.name
            """         

        try:
            cur = self.con.cursor()
            cur.execute(sql)
            rows=[]
            for row in cur.fetchall() :
                if row[2] == uid:
                    rows.append(dbhelpers.reg(cur,row))
            cur.close()
            return rows
        except (Exception, psycopg2.DatabaseError) as error:
            self.error_print(error = str(error), method = "get_exchanges", query = sql)
            if cur:         
                cur.close()
        return None


    def get_exchange_overview(self, ex_id, currency):
        sql=""" SELECT
        exchanges.name,
        users.mail,
        users.uid,
        exchanges.ex_id,
        exchange_history.currency,
        first (exchange_history.balance) as first,
        first (exchange_history.timestamp) as fts,
        last    (exchange_history.balance) as last,
        last (exchange_history.timestamp) as lts
        FROM
            exchanges
            INNER JOIN exchange_history
            ON exchanges.ex_id = exchange_history.ex_id
            INNER JOIN users
            ON exchange_history.ex_id = '%s' AND exchange_history.currency = '%s'
            group by exchanges.name, users.mail, users.uid, exchanges.ex_id, exchange_history.currency
            order by exchanges.name
            """    %(ex_id, currency)

        try:
            cur = self.con.cursor()
            cur.execute(sql)
            rows=[]
            for row in cur.fetchall() :
                rows.append(dbhelpers.reg(cur,row))
            cur.close()
            return rows
        except (Exception, psycopg2.DatabaseError) as error:
            self.error_print(error = str(error), method = "get_exchanges", query = sql)
            if cur:         
                cur.close()
        return None


    #gets exchanges read to be loaded to the bot
    def get_exchange_history(self, ex_id, period, currency):
        if period == "weekly":
            period = 60 * 60 * 24  * 7
        else:
            period = 60 * 60 * 24  * 7
        sql=""" SELECT 
            to_timestamp(floor(EXTRACT(epoch from timestamp) / %s ) * %s   ) AT TIME ZONE 'UTC'  as ts,
            last (balance) as balance
            from exchange_history where ex_id = '%s' and currency = '%s' 
            group by ts order by ts asc
            """ %(period, period, ex_id, currency)         
        try:
            cur = self.con.cursor()
            cur.execute(sql)
            rows=[]
            for row in cur.fetchall() :
                rows.append(dbhelpers.reg(cur,row))
            cur.close()
            return rows
        except (Exception, psycopg2.DatabaseError) as error:
            self.error_print(error = str(error), method = "get_exchange_history", query = sql)
            if cur:         
                cur.close()
            raise
        return None


