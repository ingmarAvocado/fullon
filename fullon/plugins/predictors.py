import psycopg2 
import sys
#import urllib, json
import arrow
from libs import settings
from libs import log
from libs import database_helpers as dbhelpers 

logger = log.setup_custom_logger('database_predictors',settings.DBLOG)



class database_predictors:
    
    def __init__(self):
        self.con = ""
        self.connect_db()
        return None


    def __del__(self):
        try:
            self.con.close()
            del (self.con)
        except:
            pass


    def error_print(self, error, method, query):
        error = "Error: " +str(error)
        error = error + "\nMethod "+method
        error = error + "\nQuery " +query
        return error
   

    def valiate_prediction(self, predictor):
        sql = f"SELECT * FROM {predictor}  limit 1"
        try:  
            cur = self.con.cursor()
            cur.execute(sql)
            r = cur.fetchall() 
            cur.close()
            return True
        except (Exception, psycopg2.errors.UndefinedTable):
            cur.close()
            return False
        return False

        
    def connect_db(self):
        con=""
        try:
            if settings.DBPORT != "":
                self.con = psycopg2.connect(dbname=settings.DBNAME+"_predictions", user=settings.DBUSER, host=settings.DBHOST, port=settings.DBPORT, password=settings.DBPASSWD)
            else:
                self.con = psycopg2.connect(dbname=settings.DBNAME+"_predictions", user=settings.DBUSER, host=settings.DBHOST,  password=settings.DBPASSWD)                
        except (Exception, psycopg2.DatabaseError) as error:
            error="Error cant connect database, postgres says: " +str(error)
            logger.info(error)
            raise
        #return None
        try:
            sql = "SET TIME ZONE 'UTC'"
            cur = self.con.cursor()
            cur.execute(sql)
            cur.close()
        except:
            pass

    def get_prediction(self, predictor, ma = None, date = None, return_ma = False, limit = 5):
        if return_ma:
            sql = f"SELECT AVG(prediction) OVER(ORDER BY timestamp ROWS BETWEEN {ma} PRECEDING AND CURRENT ROW) AS prediction FROM {predictor} order by timestamp desc limit {limit}"
        else:
            date = date if date else arrow.utcnow().format('YYYY-MM-DD HH:mm:ss') 
            sql = f"SELECT * FROM {predictor} WHERE timestamp = '{date}' limit {limit}"  
        try:    
            cur = self.con.cursor()
            cur.execute(sql)
            rows = []
            for row in cur.fetchall() :
                rows.append(dbhelpers.reg(cur,row))
            cur.close()
            if ma and rows and not return_ma: return self.get_prediction(predictor = predictor, ma = ma, date = date, return_ma = True, limit = limit)               
            return rows
        except (Exception, psycopg2.errors.UndefinedTable):
            cur.close()
            logger.error(f"Table {predictor} does not exist")
            return None
        except (Exception, psycopg2.DatabaseError) as error:
            cur.close()
            error="Error cant get_my_symbols postgres says: " +str(error)
            logger.error(error)                        
            raise
            return None

