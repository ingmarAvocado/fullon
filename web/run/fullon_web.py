from multiprocessing import set_start_method
import cherrypy
from cherrypy.lib import auth_digest
import os, os.path
import sys
import time
from libs import log
from libs import database as database
from libs import cache as cache
from mako.template import Template
from libs import settings
import xmlrpc.client
import arrow
import json
from munch import Munch



rpc = xmlrpc.client.ServerProxy('http://%s:%s' %(settings.XMLRPC_HOST, settings.XMLRPC_PORT))



class FullonWebServer(object):
    
    def __init__(self):
        self.db = database.database()
        self.cache = self.db.cache
 
    def toytest(self, n):
        return n+1
    
    @cherrypy.expose
    def index(self):
        return  self.head()+self.landing()+self.foot()  

    @cherrypy.expose  
    def trades(self, tempkey):
        return self.head()+self.trades_detail(tempkey)+self.foot()

    @cherrypy.expose  
    def detail(self, tempkey):
        return self.head()+self.bot_detail(tempkey)+self.foot()

    @cherrypy.expose  
    def bots(self):
        return self.head()+self.bots_table()+self.foot()

    @cherrypy.expose  
    def log(self, tempkey, feed):
        return self.head()+self.bot_log(tempkey, feed)+self.foot()

    @cherrypy.expose  
    def accounts(self):
        return self.head()+self.accounts_table()+self.foot()

    @cherrypy.expose  
    def account(self, key, currency):
        return self.head()+self.account_detail(key = key, currency = currency)+self.foot()

    @cherrypy.expose  
    def btcprice(self, _ = None):
        try:
            price = rpc.btc_ticker()
        except ConnectionRefusedError:
            raise
            return ("no connection with rpc server")
            time.sleep(1)
            return self.btcprice()
        pct = round(self.get_change(current = price[0], previous = price[1]),2)
        css = "text-success" if pct > 0 else "text-warning"
        string = "XBT %s (%s&#37;)" %(price[0], pct)
        string = '<font class="%s">%s</font>' %(css, string)
        return  string

    @cherrypy.expose  
    def procs(self, _ = None):
        try:
            procs = rpc.get_proc_overview()
        except:
            time.sleep(1)
            return self.procs()

        procs = Munch(procs)
        retjson = """
                {
              "data": [
                [
                  "%s",
                  "%s",
                  "%s",
                  "%s",
                  "%s"
                ]
              ]
            }""" %(procs.total, procs.free, procs.rss, procs.time, procs.count)
        return retjson


    @cherrypy.expose  
    def get_bots(self, _ = None):
        tmpbots = self.cache.get_bot_status()
        bots = []
        n = 0
        for bot in tmpbots:
            bots.append(self.append_bot_details(bot = bot, n = n))
            n +=1
        bots = self.nicely_format_bots(bots)
        retjson = """
                {
              "data": [
                """
        prev_bot_id = ""
        for bot in bots:
            if bot.live == "Yes":
                bot.live = "<font class='text-success'>Yes</font>"
            bot.pos_pct = round(bot.pos_pct,2)
            if bot.pos_pct > 0:
                bot.pos_pct ="<font class='text-success'>%s</font>" %(bot.pos_pct)
            elif bot.pos_pct < 0:
                bot.pos_pct ="<font class='text-warning'>%s</font>" %(bot.pos_pct)
            ts = arrow.get(bot.timestamp)
            now = int(float(arrow.utcnow().format('X')))
            lateness = now - int(float(ts.format('X')))
            if lateness > 180:
                bot.timestamp = "<font class='text-warning'>%s</font>" %(ts.format('YYYY-MM-DD HH:mm:ss'))
            else:
                bot.timestamp = "<font class='text-success'>%s</font>" %(ts.format('YYYY-MM-DD HH:mm:ss'))

            if prev_bot_id != bot.bot_id:
                bot_name = f"<a href='/detail?tempkey={bot.bot_id}'>{bot.bot_name}</a>"
                bot_live = bot.live
                bot_strategy = bot.strategy
            else:
                bot_name = ''
                bot_live = ''
                bot_strategy = ''
            retjson = retjson + f"""
                [
                  "{bot_name}",
                  "{bot_live}",
                  "{bot_strategy}",
                  "{bot.symbol}",
                  "{bot.exchange}",
                  "{bot.base}",
                  "{bot.tick}",
                  "{bot.pos}",
                  "{bot.pos_price}",
                  "{bot.pos_roi}",
                  "{bot.pos_pct}",
                  "{bot.timestamp}"
                ],""" 
            prev_bot_id = bot.bot_id
        retjson = retjson.rstrip(',')
        retjson = retjson + """
                ]
            }"""
        return retjson
      


    def head(self):
        mytemplate = Template(filename='views/head.mako')
        timestamp = arrow.utcnow().format('YYYY-MM-DD HH:mm:ss')
        return mytemplate.render(timestamp = timestamp, btcprice = self.btcprice())            


    def get_change(self, current, previous):
        current = float(current)
        previous = float(previous)
        if current == previous:
            return 0
        try:
            return ((current - previous) / previous) * 100.0
        except ZeroDivisionError:
            return float('inf')

    def accounts_table(self):
        mytemplate = Template(filename='views/exchanges.mako')
        uid = self.db.get_uid(email = settings.TESTACCOUNT)
        accounts = self.db.get_exchanges(uid = uid)
        for account in accounts:
            value = account.last - account.first
            value = f'{value:.8f}'
            setattr(account, 'diff', value)
            value = self.get_change(current = account.last, previous = account.first)
            if account.last < 0 and account.first < 0:
                value = value * -1 
            value = round(value,2)
            setattr(account, 'change', value)
        title = "Exchange  Account Overview"
        now = arrow.utcnow()
        return mytemplate.render(accounts = accounts, title = title, now = now)

    def account_detail(self, key, currency):
        mytemplate = Template(filename='views/account.mako')
        bots = self.db.get_bot_detail(ex_id = key, currency = currency)
        title = "Account Overview"
        data = self.db.get_exchange_history(period = 'week', ex_id = key, currency = currency)
        chartdata = ""
        for record in data:
            chartdata += "{ week: '%s', balance: %s }," %(record.ts, record.balance)
        chartdata = chartdata.rstrip(',')
        overview = self.db.get_exchange_overview(ex_id = key, currency = currency)[0]
        setattr(overview, "roi", self.get_change(current = overview.last, previous = overview.first))
        overview.roi = round(overview.roi, 2)
        if overview.last < 0 and overview.first < 0:
            overview.roi = overview.roi * -1 
        now = arrow.utcnow()
        return mytemplate.render(bots = bots, title = title, chart = chartdata, ov = overview)




    def bots_table(self):
        mytemplate = Template(filename='views/bots.mako')
        tmpbots = self.cache.get_bot_status()
        bots = []
        n = 0
        for bot in tmpbots:
            print(bot, n)
            bots.append(self.append_bot_details(bot = bot, n = n))
            n +=1
        bots = self.nicely_format_bots(bots)
        title="Bot Overview"
        now = arrow.utcnow()
        return mytemplate.render(bots = bots, title = title, now = now)


    def landing(self):
        mytemplate = Template(filename='views/landing.mako')
        title="Fullon Dashboard"
        now = arrow.utcnow()
        statuses = self.cache.get_mini_top()
        return mytemplate.render(title = title, now = now, statuses = statuses)


    def get_str_params(self, bot_id):
        params = []
        try:
            for key, value in json.loads(self.cache.get_user_strategy_params(bot_id = bot_id)).items():
                b = Munch()
                b.name = key
                b.value = value
                params.append(b)
            return params
        except:
            return params

    def get_str_vars(self, bot_id):
        variables = self.cache.get_bot_vars(bot_id = bot_id)
        #print(variables)
        if variables:
            var_dict=[]
            variables = json.loads(variables)
            for key, value in variables.items():
                b = Munch()
                b.name = key
                if isinstance(value,float):
                    value = round(value,4)
                if key == "time":
                    value = arrow.get(value).format('YYYY-MM-DD HH:mm:ss')
                b.value = value
                var_dict.append(b)
            return var_dict
        else:
            return []


    def bot_log(self, bot_id, feed):
        mytemplate = Template(filename='views/bot_log.mako')
        logs = self.db.get_bot_log(bot_id = bot_id, feed = feed)
        bot_view = self.db.get_bot_detail(bot_id = bot_id)
        bot = self.nicely_format_bots(self.cache.get_bot_status(bot_id = bot_id))

        if bot:
            bot =  bot[0]
            try:
                if bot.ex_base:
                    setattr(bot,'market',bot.ex_base)
                else:
                    setattr(bot,'market',bot.base)
            except:
                setattr(bot,'market',bot.base)   
        i = 0
        if logs:
            for log in logs:
                #print(log.message)
                try:
                    messages = []
                    for key, value in json.loads(log.message).items():
                        b = Munch()
                        b.name = key
                        b.value = value
                        messages.append(b)                        
                except:
                    pass
                logs[i].message = messages
                i += 1
        
        return mytemplate.render(logs = logs, bot_view = bot_view, bot = bot)
     


    
    def trades_detail(self, bot_id):
        mytemplate = Template(filename='views/trades_detail.mako')
        bot_view = self.db.get_bot_detail(bot_id = bot_id)
        bot = self.nicely_format_bots(self.cache.get_bot_status(bot_id = bot_id))
        if bot:
            bot =  bot[0]
            try:
                if bot.ex_base:
                    setattr(bot,'market',bot.ex_base)
                else:
                    setattr(bot,'market',bot.base)
            except:
                setattr(bot,'market',bot.base)    
        if bot_view.dry_run:
            setattr(bot, 'live', 'No')
        else:
            setattr(bot, 'live', 'Yes')
        totals = self.db.get_bot_totals(bot_id = bot_id, dry=bot_view.dry_run)
        trades = self.db.get_trades(bot_id = bot_id, dry = bot_view.dry_run, limit = 100)
        return mytemplate.render(bot_view = bot_view, bot = bot, trades = trades, totals=totals)
     


    def nicely_format_bots(self, bots):
        n = 0
        for bot in bots:
            if bot.pos_price  < 10:
                bot.pos_price =  f'{bot.pos_price:.8f}'
                bot.pos_roi =  f'{bot.pos_roi:.6f}'
            else:
                bot.pos_price =  f'{bot.pos_price:.2f}'
                bot.pos_roi =  f'{bot.pos_roi:.6f}'
            if bot.pos > 1 :
                bot.pos =  round(bot.pos, 2)
            elif bot.pos == 0:
                bot.pos_price =  0
                bot.pos_roi =  0
            else:
                bot.pos =  f'{bot.pos:.4f}'
            if bot.totfunds > 100:
                bot.totfunds = round (bot.totfunds, 2)
                bot.funds = round (bot.funds, 2)
            else:
                bot.totfunds = round(bot.totfunds, 4)
                bot.funds = round(bot.funds, 4)
            if bot.tick < 1:
                bot.tick = f'{bot.tick:.8f}'
            try:
                bot = self.append_bot_details(bot, n)
                if bot.tot_roi ==  None:
                    bot.tot_roi = 0;
                if 'USD' in bot.base:
                    bot.tot_roi =  round(bot.tot_roi, 4)
                else:
                    bot.tot_roi =  round(bot.tot_roi, 4)
            except:
                raise
            n +=1
        return bots

    def append_bot_details(self, bot, n):
        dry = True
        if bot.live == "Yes":
            dry = False 
        totals = self.db.get_bot_totals(bot_id = bot.bot_id, dry=dry)
        setattr(bot, 'tot_roi', totals.roi)
        setattr(bot, 'tot_pct', " ")
        setattr(bot, 'feed', n)
        return bot

    
    def bot_detail(self, bot_id):
        mytemplate = Template(filename='views/bot_detail.mako')
        bot_view = self.db.get_bot_detail(bot_id = bot_id)
        bots = self.nicely_format_bots(self.cache.get_bot_status(bot_id = bot_id))
        totals = self.db.get_bot_totals(bot_id = bot_id, dry = bot_view.dry_run)
        rois = self.db.get_bot_rois(bot_id = bot_id, dry = bot_view.dry_run)
        now = arrow.utcnow()
        str_params = self.get_str_params(bot_id = bot_id)
        str_vars = self.get_str_vars(bot_id = bot_id)
        trades = self.db.get_trades(bot_id = bot_id, dry = bot_view.dry_run)
        overview = Munch()
        overview.trades = 0
        overview.a = 0
        overview.b = 0
        overview.x = 0
        overview.y = 0
        chartdata = ""
        roi = 0
        if trades:
            trades.reverse()
            trade_reset = 1
            for t in trades:  

                if trade_reset and t.roi_pct != None:
                    trade_reset = 0
                    roi = roi + t.roi
                    chartdata += "{ date: '%s', roi: %s }," %(t.timestamp, roi)
                    overview.trades += 1
                    if t.roi_pct >= 5:
                        overview.b += 1
                    elif t.roi_pct >= 0 and t.roi_pct < 5:
                        overview.a += 1                    
                    elif t.roi_pct < 0 and t.roi_pct > -5:
                        overview.x += 1
                    elif t.roi_pct <= -5:
                        overview.y += 1
                elif not t.roi_pct:
                    trade_reset = 1
        chartdata = chartdata.rstrip(',')
        print (chartdata)


        #return mytemplate.render(bot_view = bot_view, bots = bots, now=now,  totals=totals)
        return mytemplate.render(bot_view = bot_view, bots = bots, now=now, ov=overview, totals=totals, rois=rois, str_params=str_params, str_vars=str_vars, chart=chartdata)
     
    def foot(self):
        with open('views/foot.mako', 'r') as content_file:
            content = content_file.read()
        content = content.replace('REVISION','0.8')
        return content
    


    


class FullonWeb(object):
    
        def __init__(self):
            return None
        


        def start(self):
            USERS = {'avalon':'boomnights'}

            conf = {
                
                    '/static': {
                    'tools.staticdir.on': True,
                    'tools.staticdir.dir': './public'
                },
                
                '/': {
                    'tools.sessions.on': True,
                    'tools.staticdir.root': os.path.abspath(os.getcwd()),
                    'tools.auth_digest.on': True,
                    'tools.auth_digest.realm': 'localhost',
                    'tools.auth_digest.get_ha1': auth_digest.get_ha1_dict_plain(USERS),
                    'tools.auth_digest.key': '5a65c27146791cbf',
                    'tools.auth_digest.accept_charset': 'UTF-8',    
                }
            }
            cherrypy.server.socket_host = '0.0.0.0'
            cherrypy.server.socket_port= 8089
            cherrypy.quickstart(FullonWebServer(), '/', conf)
        """
        def start(self):
            USERS = {'avalon':'boomnights'}

            conf = {
                
                    '/static': {
                    'tools.staticdir.on': True,
                    'tools.staticdir.dir': './public'
                },
                
                '/': {
                    'tools.sessions.on': True,
                    'tools.staticdir.root': os.path.abspath(os.getcwd())
                }
            }
            cherrypy.server.socket_host = '0.0.0.0'
            cherrypy.server.socket_port= 8089
            cherrypy.quickstart(FullonWebServer(), '/', conf)
        """
            
