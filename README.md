# Fullon Trading Bot

Need to write the instrucitons better...

To install one needs to setup envirment with poetry or requirements.txt

Then you need google secrets, so you need to go to google cloud, create a .json that has can use your secret database.

Then you need to set your secrets (exchange api keys) with fullon_secrets

The one needs to setup the database  (create an account with create database permissions) and configure conf/fullon.conf 

then you need to install the databae fullon_install.py --help

then you need to run fullon_dameon.py to start ohlcv, ticket and account fetchers

then fullon_ctl to manage the daemon...

