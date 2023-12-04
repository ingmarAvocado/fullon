import sys
import time
from libs import settings
from run import system_manager
from libs import log
import arrow


class install_exchange():
    
    def __init__(self):
        return None
        
    def install(self):
        return True
        
        
    def get_params(self):
        params=[]
        param={'name':'SIMUL_FUNDS','type':'int','default':1}
        params.append(param)
        param={'name':'SIMUL_LIMITFEE','type':'float','default':.01}
        params.append(param)
        param={'name':'SIMUL_MKTFEE','type':'bool','default':.01}
        params.append(param)
        return params
        
