import arrow
import sys
from libs import log
import numpy as np
import pandas
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
import pandas as pd
import numpy as np
import time as time
from typing import List, Tuple


logger = log.fullon_logger(__name__)


class Xgb():

    data = pd.DataFrame

    '''

    def load_data(self, scale=True, shuffle=True, table=False):
        if self.data:
            return True
        df = self._pre_load_data(scale=scale, shuffle=shuffle, table=table)
        df.fillna(-99999, inplace=True)
        y = df['future']
        df.drop(columns=['future', 'target'], inplace = True)
        result = {}
        x_train, x_test, y_train, y_test = train_test_split(df, y, test_size = self.p.TEST_SIZE, shuffle = False)
        result['last_sequence'] = df.tail(self.p.LOOKUP_STEP).copy()
        result["X_train"], result["X_test"], result["y_train"], result["y_test"] = x_train, x_test, y_train, y_test
        self.data = result
        return True
    '''

    '''
    def create_model(self, test = False): 
        if not self.x:
            from xgboost import XGBRegressor
            model = XGBRegressor(objective="reg:squarederror", gamma =0.0, n_estimators=200, base_score=0.7, learning_rate=0.01, colsample_bytree=1)
            self.load_data()
            model = model.fit(self.data['X_train'], self.data['y_train'])
            self.x = model
            return model
        else:
            return self.x


    def train(self, test):
        return None



    def predict(self, test = False):
        model = self.create_model(test = test)
        y_predicted = model.predict(self.data['X_test'])
        return 1 if y_predicted[-1] > 0.5 else 0
        #y_predicted_binary = [1 if yp > 0.5 else 0 for yp in y_predicted]
        


    def plot(self, append="", test = False):
        return None


    def predictions(self, table  = False, test = False):
        if self.error:
            logger.error (f"Can't predict, we have error ({self.error})")
            return None
        model = self.create_model(test = test)      
        df = pd.DataFrame()
        predictions = model.predict(self.data['X_test'])
        predictions= [1 if p > 0.5 else 0 for p in predictions]
        df['prediction'] = predictions
        length = df['prediction'].shape[0]
        last_date = self.orig_df.at[self.orig_df.shape[0]-1, 'date']
        last_date = arrow.get(last_date)
        if self.p.FRAME == 'days':
            arr = np.array([last_date.shift(days = -self.p.PERIOD * i).format('YYYY-MM-DD') for i in range(0,length)])        
        if self.p.FRAME == 'weeks':
            arr = np.array([last_date.shift(weeks = -self.p.PERIOD * i).format('YYYY-MM-DD') for i in range(0,length)])
        if self.p.FRAME == 'months':
            arr = np.array([last_date.shift(months = -self.p.PERIOD * i).format('YYYY-MM-DD') for i in range(0,length)])
        elif self.p.FRAME =='minutes':
            arr = np.array([last_date.shift(minutes = -self.p.PERIOD * i).format('YYYY-MM-DD  HH:mm:SS') for i in range(0,length)])
        dates = arr[::-1]       
        df['timestamp'] = dates
        df['target'] = np.array(self.orig_df["target"].tail(df.shape[0])) 
        self.db.save_df(name = self.predictor_name, df = df, table = table)
        self.data = ""
        self.x=""
        self.predict_next(table = table, test = test)



    def predict_next(self, table  = False, test = False, count = 0):
        if self.error:
            logger.error (f"Cant predict_next, we have error ({self.error})")
            return None 
        """       
        if not self.date_validation(table = table) and not test:
            logger.info(f"Waiting for ohlcv data update, attempt {count}")
            count +=1
            time.sleep(5)
            self.data = None
            return self.predict_next(table = table, test = test, count = count) if count < 20 else False        
        """
        p = self.predict()       
        last_date = arrow.get(self.orig_df.at[self.orig_df.shape[0]-1, 'date'])                
        if self.p.FRAME == 'days': next_date = last_date.shift(days = self.p.PERIOD)
        elif self.p.FRAME =='minutes': next_date = last_date.shift(minutes = self.p.PERIOD)            
        elif self.p.FRAME == 'weeks':  next_date = last_date.shift(weeks = self.p.PERIOD)   
        elif self.p.FRAME == 'months': next_date = last_date.shift(months = self.p.PERIOD)   
        p = {'prediction':p, 'timestamp':next_date.format('YYYY-MM-DD HH:mm:SS'), 'close':None}
        return self.db.append_prediction(predictor = self.predictor_name, prediction = p, table = table)


    def plot_technical_indicators(self, dataset, set2=None, last_days = 500):
        return None

    def score(self, test = False):
        model = self.create_model(test = test)
        y_predicted = model.predict(self.data['X_test'])
        y_predicted_binary = [1 if yp > 0.5 else 0 for yp in y_predicted]
        accuracy = (accuracy_score(self.data['y_test'], y_predicted_binary))
        return f"Binary accuracy: {accuracy}%"

    '''
