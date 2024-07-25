from fastapi import Request
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse as jsonify
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from typing import List
import os
import sys
from datetime import datetime
import threading
import asyncio
from metaapi_cloud_sdk import MetaApi
from datetime import datetime, timedelta
import smtplib
import ssl
import json
import requests
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.svm import SVR
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_squared_error
from sklearn.linear_model import LinearRegression
#from sklearn.ensemble import GradientBoostingRegressor

import yfinance as yf
import traceback
import pandas as pd

from db import create_main_db, get_connection, log_db, return_visits_count, create_dir_db, return_direction_date, update_clients,update_direction, update_deploy, log_clients, return_clients, return_the_clients, log_visits, return_direction, increase_visits, clean_db, check_db

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

trader = None
lastreset = f'{datetime.now().hour}:{datetime.now().minute}:{datetime.now().second}'

# ----------------------------------------------------------------------------------------------------- EMAILER

import smtplib
import ssl

smtp_server = 'smtp.gmail.com'
smtp_port = 465

from_address = 'ALERT'
to_address = [f'YOURADDRESS']

username = 'email'
password = 'password'

subject = '⚠️ PYTHON TRADING SERVER ONLINE ⚠️'
body = '''\
Hi, your Python Trading Server has started.

Best regards,
YOU
'''

async def sendemail(subject, body):
    global from_address
    global to_address

    await smtp_client.connect()
    await smtp_client.send_email(from_address, to_address, subject, body)

class SMTPClient:
    def __init__(self, smtp_server, smtp_port, username, password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.server = None

    async def connect(self):
        context = ssl.create_default_context()
        self.server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context)
        self.server.set_debuglevel(1)
        self.server.login(self.username, self.password)
        print("SMTP server connected and logged in.")

    async def send_email(self, from_address, to_address, subject, body):
        if self.server is None:
            raise Exception("SMTP server is not connected.")
        message = f'From: {from_address}\r\nSubject: {subject}\r\nTo: {to_address}\r\n\r\n{body}'
        self.server.sendmail(from_address, to_address, message.encode())
        print("Email sent successfully.")

    async def close(self):
        if self.server:
            self.server.quit()
            self.server = None
            print("SMTP server connection closed.")

smtp_client = SMTPClient(smtp_server, smtp_port, username, password)

# ----------------------------------------------------------------------------------------------------- TRADING

ma1 = 0
ma2 = 0
ma3 = 0

direction = -1
hema_dir = -1
hema_color = None 
latest_hema = 0

import pandas as pd
import numpy as np
import yfinance as yf
import ta

async def get_direction(length_MA1=50, length_MA2=200):

    btc = yf.Ticker("BTC-USD")

    try:
        data = btc.history(period="5d", interval="1m")

        _close = data['Close']

        #---- EMA 1 code start ----#
        MA1 = ta.trend.EMAIndicator(close=_close, window=length_MA1).ema_indicator()
        #---- EMA 1 code end ----#

        #---- EMA 2 code start ----#
        MA2 = ta.trend.EMAIndicator(close=_close, window=length_MA2).ema_indicator()

        MA3 = ta.trend.EMAIndicator(close=_close, window=36).ema_indicator()
        #---- EMA 2 code end ----#

        # Access the latest value of MA1
        latest_ma1 = MA1.iloc[-1]
        latest_ma2 = MA2.iloc[-1]
        latest_ma3 = MA3.iloc[-1]
        #await sendemail(f"{latest_ma1} {latest_ma2}", f"{latest_ma1} {latest_ma2}")

        global ma1
        global ma2
        global ma3
        ma1 = latest_ma1
        ma2 = latest_ma2
        ma3 = latest_ma3
        ready = False 
        instances = []
        if ready:
            #---- Direction ----#
            global direction
            if (latest_ma1 > latest_ma2):
                direction = 1
                for instance in instances:
                    if instance.strategy == 1:
                        await instance.close_positions("SELL")
                await update_direction(1)
            elif (latest_ma1 < latest_ma2):
                direction == 0
                for instance in instances:
                    if instance.strategy == 1:
                        await instance.close_positions("BUY")
                await update_direction(0)
            
        return direction
    except Exception as err:
        await sendemail('Failed fetching direction on Get_Direction.', err)
        return -1

    results = pd.DataFrame({
        'CLS': CLS,
        'MA1': MA1,
        'MA2': MA2,
        'RSI': RSI,
        'MACDV': MACDV,
        'SignalV': SignalV,
        'stringmacdv': stringmacdv,
        'stringmomentum': stringmomentum,
        'direction': direction
    })

    return results

import aiohttp
apiCount = 0

async def fetch_historical_data(timeframe):
    keys = ["KEYSOBTAINEDFROMFINANCIALMODELINGPREP"]
    asset = "BTCUSD"
    success = False
    global apiCount
    apiCount += 1

    async with aiohttp.ClientSession() as session:
        for keyNr, key in enumerate(keys, start=1):
            try:
                if timeframe in ["1d", "daily", "Daily"]:
                    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{asset}?apikey={key}"
                else:
                    url = f"https://financialmodelingprep.com/api/v3/historical-chart/{timeframe}/{asset}?apikey={key}"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        print(f"Response from apikey {keyNr}.")
                        success = True
                        usedKey = key
                        data = await response.json()
                        break
                    else:
                        print(f"Failed with apikey {keyNr} {response.status}.")
            except Exception as e:
                print(f"Error with apikey {keyNr}: {e}")

        if not success:
            await sendemail('MAX API CALLS USED', 'Please check.')
            return False, 0, 0

        slbuy, slsell = await auto_sl()

        if timeframe in ["daily", "Daily", "1d"]:
            historical_data = data["historical"]
            historical_data.reverse()
            df = pd.DataFrame(historical_data)
        else:
            data.reverse()
            df = pd.DataFrame(data)

    return df, slbuy, slsell

# Feel free to use any of the features already present to further the code yourself
async def add_features(df):
    df['SMA_5'] = df['close'].rolling(window=5).mean()
    df['SMA_10'] = df['close'].rolling(window=10).mean()
    df['EMA_5'] = ta.trend.ema_indicator(df['close'], window=5)
    df['EMA_10'] = ta.trend.ema_indicator(df['close'], window=10)
    df['RSI'] = ta.momentum.rsi(df['close'], window=14)
    df['MACD'] = ta.trend.macd_diff(df['close'])
    df.dropna(inplace=True)
    return df

async def prepare_data(df):
    features = ['close', 'SMA_5', 'SMA_10', 'EMA_5', 'EMA_10', 'RSI', 'MACD']
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(df[features])
    
    X = scaled_data[:-1]
    y = scaled_data[1:, 0]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    return X_train, X_test, y_train, y_test, scaler, scaled_data

async def auto_predict(timeframe):
    df, slbuy, slsell = await fetch_historical_data(timeframe)

    if df is None:
        print("Failed to fetch historical data.")
        return False, None, None

    df = await add_features(df)
    X_train, X_test, y_train, y_test, scaler, scaled_data = await prepare_data(df)
    
    model = LinearRegression()
    model.fit(X_train, y_train)

    next_data_point = X_test[-1].reshape(1, -1)
    predicted_data_point = model.predict(next_data_point)

    last_scaled_close = scaled_data[-1, 0]
    predicted_value = scaler.inverse_transform([[predicted_data_point[0], last_scaled_close, last_scaled_close, last_scaled_close, last_scaled_close, last_scaled_close, last_scaled_close]])[0][0]

    worked_value = f"{predicted_value:.2f}"

    return worked_value, slbuy, slsell

async def auto_sl(percentage=0.02):

    bid, ask = await trader.get_price()

    current_closePRE = (float(bid) + float(ask)) / 2
    current_close = float(current_closePRE)

    sl_margin = current_close * percentage

    buy_stop_loss = current_close - sl_margin
    sell_stop_loss = current_close + sl_margin

    worked_buy_value = "%.2f" % buy_stop_loss
    worked_sell_value = "%.2f" % sell_stop_loss

    slbuy = float(worked_buy_value)
    slsell = float(worked_sell_value)

    return slbuy, slsell

async def predict(timeframe):
    asset = "BTCUSD"
    worked_value, slbuy, slsell = await auto_predict(timeframe)

    if worked_value:
        result = {'info': f"Predicted {asset} {timeframe} Close is {worked_value}", "tp_value": float(worked_value) ,"slbuy": slbuy, "slsell" :slsell }
        return result
    else:
        result = {'info': f"Info gathering failed.", "tp_value": None ,"slbuy": 0, "slsell" : 0 }
        return result

# ----------------------------------------------------------------------------------------------------- TRADING CLASS

class Trader:   
    def __init__(self, token, login, password, server_name, deployed, timeframe, strategy):
        self.token = token
        self.login = login
        self.password = password
        self.server_name = server_name
        self.deployed = deployed
        self.account = None
        self.connection = None
        self.terminal_state = None
        self.timeframe = timeframe
        self.strategy = strategy

    @classmethod
    async def create(cls, token, login, password, server_name, deployed, timeframe, strategy):
        self = cls(token, login, password, server_name, deployed, timeframe, strategy)
        self.api = MetaApi(token)
        accounts = await self.api.metatrader_account_api.get_accounts_with_infinite_scroll_pagination()
        
        for item in accounts:
            if item.login == self.login and item.type.startswith('cloud'):
                self.account = item

                update = {
                    "metaapitoken": self.token,
                    "brokerlogin" : self.login,
                    "brokerpass" : self.password,
                    "brokerserver" : self.server_name, 
                    "deployed" : True,
                    "timeframe" : self.timeframe,
                    "strategy" : self.strategy
                }

                if not await update_deploy(self.token, update):
                    self.deployed = True
                break

        if not self.account and not self.deployed:
            print('Adding MT5 account to MetaApi')
            self.account = await self.api.metatrader_account_api.create_account({
                'name': 'MULTI Account',
                'type': 'cloud',
                'login': self.login,
                'password': self.password,
                'server': self.server_name,
                'platform': 'mt5',
                'application': 'MetaApi',
                'magic': 1000,
            })

            # wait until account is deployed and connected to broker
            print('Deploying account')
            await self.account.deploy()
        else:
            print('MT5 account already added to MetaApi')
        
        print('Waiting for API server to connect to broker (may take couple of minutes)')
        await self.account.wait_connected()

        self.connection = self.account.get_streaming_connection()
        await self.connection.connect()

        print('Waiting for SDK to synchronize to terminal state (may take some time depending on your history size)')
        await self.connection.wait_synchronized()
        self.terminal_state = self.connection.terminal_state
        
        await self.connection.subscribe_to_market_data('BTCUSD')
        print(f"Account {self.login} connected.")

        return self

    async def get_price(self):
        if not self.connection:
            await self.create(self.token, self.login, password, self.server_name)

        bid = self.terminal_state.price('BTCUSD')['bid']
        ask = self.terminal_state.price('BTCUSD')['ask']

        return bid, ask
    
    async def open_order(self, side, lot):
        if not self.connection:
            print("NO CONNECTION, RE-CREATING.")
            await self.create(self.token, self.login, password, self.server_name)

        if side == "BUY":
            try:
                print("OPENING ORDER N/L")
                await self.connection.create_market_buy_order('BTCUSD', lot, 0, 0,
                    options={'comment': 'ILLCLOUD-V2-MELVA'})
            except Exception as err:
                await sendemail("Error on open order N/L", self.api.format_error(err))
                print(self.api.format_error(err))
        elif side == "SELL":
            try:
                print("OPENING ORDER N/L")
                await self.connection.create_market_sell_order('BTCUSD', lot, 0, 0,
                    options={'comment': 'ILLCLOUD-V2-MELVA'})
            except Exception as err:
                await sendemail("Error on open order N/L", self.api.format_error(err))
                print(self.api.format_error(err))
        
    async def open_order_tp(self, side, lot, tp):
        if side == "BUY":
            try:
                print("OPENING ORDER TPO")
                await self.connection.create_market_buy_order('BTCUSD', lot, 0, tp,
                    options={'comment': 'ILLCLOUD-V2-MELVA'})
            except Exception as err:
                await sendemail("Error on open order TPO", self.api.format_error(err))
                print(self.api.format_error(err))
        elif side == "SELL":
            try:
                print("OPENING ORDER TPO")
                await self.connection.create_market_sell_order('BTCUSD', lot, 0, tp,
                    options={'comment': 'ILLCLOUD-V2-MELVA'})
            except Exception as err:
                await sendemail("Error on open order TPO", self.api.format_error(err))
                print(self.api.format_error(err))
    
    async def open_order_sl(self, side, lot, sl):
        if side == "BUY":
            try:
                print("OPENING ORDER SLO")
                await self.connection.create_market_buy_order('BTCUSD', lot, sl, 0,
                    options={'comment': 'ILLCLOUD-V2-MELVA'})
            except Exception as err:
                await sendemail("Error on open order SLO", self.api.format_error(err))
                print(self.api.format_error(err))
        elif side == "SELL":
            try:
                print("OPENING ORDER SLO")
                await self.connection.create_market_sell_order('BTCUSD', lot, sl, 0,
                    options={'comment': 'ILLCLOUD-V2-MELVA'})
            except Exception as err:
                await sendemail("Error on open order SLO", self.api.format_error(err))
                print(self.api.format_error(err))

    async def open_order_both(self, side, lot, tp, sl, comment):
        if side == "BUY":
            try:
                print("OPENING ORDER W/L")
                await self.connection.create_market_buy_order('BTCUSD', lot, sl, tp,
                    options={'comment': comment})
            except Exception as err:
                await sendemail("Error on open order W/L", self.api.format_error(err))
                print(self.api.format_error(err))
        elif side == "SELL":
            try:
                print("OPENING ORDER W/L")
                await self.connection.create_market_sell_order('BTCUSD', lot, sl, tp,
                    options={'comment': comment})
            except Exception as err:
                await sendemail("Error on open order W/L", self.api.format_error(err))
                print(self.api.format_error(err))

    async def modify_order(self, id, sl, tp):
        try:
            print("MODIFYING ORDER")
            await self.connection.modify_position(id, sl, tp)
        except Exception as err:
            await sendemail("Error while modifying order", self.api.format_error(err))
            print(self.api.format_error(err))

    async def get_orders(self):
        orders = self.terminal_state.positions

        if len(orders) < 1:
            #print("Orders len: ", len(orders))
            return 0
        else: 
            #print("Orders len:", len(orders))
            return len(orders)
        
    async def get_orders_info(self):
        orders = self.terminal_state.positions
        #print("Orders returned:", orders)
        return
        
    async def get_orders_full(self):
        orders = self.terminal_state.positions
        #print("Orders returned:", orders)
        return orders
    
    async def close_position(self, id):
        self.connection.close_position(f'{int(id)}')
                
    async def close_order(self, id):
        try:
            self.connection.close_position(id)
            print(f"Closed order with id: {id}")
        except Exception as err:
            print("Error closing position.", err)
    async def close_positions(self, side):
        orders = await self.get_orders_full()
        for order in orders:
            fullside = "POSITION_TYPE_" + side
            if fullside == order.get('type'):
                id = order.get('id')
                await self.connection.close_position(id)

# ----------------------------------------------------------------------------------------------------- TRADING CLASS STARTER

#trader = asyncio.run(Trader(token, login, password, server_name, deployed).create(token, login, password, server_name, deployed))

# ----------------------------------------------------------------------------------------------------- INTERVAL +

lastminute = -1
intervalCounter = 0
move = "Nan"
runningTimer = False

timeframe_list = {
    "1hour": [1],
    "15min": [3, 18, 33, 48],
    "5min": [1, 6, 11, 16, 21, 26, 31, 36, 41, 46, 51, 56]
}

previsions_list = {
    "5min" : 0,
    "15min" : 0,
    "5slb" : 0,
    "5sls" : 0,
    "15slb" : 0,
    "15sls" : 0
}

async def update_previsions(order):
    if order:
        prediction, slbuy, slsell = await auto_predict('15min')
        previsions_list['15min'] = prediction
        previsions_list['15sls'] = slsell
        previsions_list['15slb'] = slbuy
        print(f"15min prevision updated.")

        prediction2, slbuy2, slsell2 = await auto_predict('5min')
        previsions_list['5min'] = prediction2
        previsions_list['5sls'] = slsell2
        previsions_list['5slb'] = slbuy2
        print(f"5min prevision updated.")
        return

    else:
        current_minute = datetime.now().minute

        if current_minute in timeframe_list.get('15min'):
            prediction, slbuy, slsell = await auto_predict('15min')
            previsions_list['15min'] = prediction
            previsions_list['15sls'] = slsell
            previsions_list['15slb'] = slbuy
            print(f"15min prevision updated.")

        if current_minute in timeframe_list.get('5min'):
            prediction, slbuy, slsell = await auto_predict('5min')
            previsions_list['5min'] = prediction
            previsions_list['5sls'] = slsell
            previsions_list['5slb'] = slbuy
            print(f"5min prevision updated.")
        return

async def checkTime():
    global lastminute, trader, intervalCounter, move, runningTimer, instances, previsions_list, timeframe_list, ma1, ma2, ma3

    intervalCounter += 1
    runningTimer = True

    global direction
    global apiCount

    allInfo = {
        "Current direction": direction,
        "DB direction": await return_direction(),
        "Instances Logged": len(instances),
        "Instances full": instances,
        "Total clients": await log_clients(),
        "Previsions List": previsions_list,
        "ShortMA": ma1,
        "LongMA": ma2,
        "midMA": ma3,
        "ApiCallCount": apiCount,
        "Interval Nr": intervalCounter,
        "VisitsCount": await return_visits_count()
    }

    # Print each field and value separated by a ":"
    for key, value in allInfo.items():
        print(f"{key} : {value}")

    direction = await get_direction()

    current_minute = datetime.now().minute
    current_hour = datetime.now().hour

    for instance in instances:
        timeframe = instance.timeframe
    
        if timeframe in ["1min", "5min", "15min", "1hour", "4hour", "daily"]:
            predefined_minutes = timeframe_list[timeframe]
            cant_hours = [20, 21, 22, 23, 0, 1, 2, 3]
            cant_days = [ 5, 6 ]
            daynow = datetime.now().weekday()
            #await sendemail(f"Weekday: {daynow}", "Nan")

            if current_minute in predefined_minutes and current_hour not in cant_hours and not daynow in cant_days:
                if lastminute != current_minute:

                    try:
                        await update_previsions(False)
                    except Exception as err:
                        print('Error updating previsions: ', err, 'Error updating previsions.')
                        
                    try:
                        trader = instances[0]
                        bidPRE, askPRE = await trader.get_price()

                        bid = float(bidPRE)
                        ask = float(askPRE)

                        if timeframe == "15min":
                            prediction = previsions_list[timeframe]
                            stops = [previsions_list.get('15slb'), previsions_list.get('15sls')]
                            slbuy = stops[0]
                            slsell = stops[1]
                        elif timeframe == "5min":
                            prediction = previsions_list[timeframe]
                            stops = [previsions_list.get('5slb'), previsions_list.get('5sls')]
                            slbuy = stops[0]
                            slsell = stops[1]

                        else:
                            prediction, slbuy, slsell = await auto_predict(timeframe)

                        if prediction:
                            totalOrders = await instance.get_orders() or 0
                            if totalOrders >= 10:
                                await sendemail('Max orders reached.', "Nan")
                                continue

                            try:
                                mid_price = (float(bid) + float(ask)) / 2
                                prediction = float(prediction)
                                direction = int(direction)
                                diff = abs(prediction - mid_price)

                                if int(instance.strategy) == 1:
                                    if direction == 1:
                                        if prediction > mid_price and diff > 25:
                                            await instance.open_order_both("BUY", 0.01, prediction, slbuy, "str1-dir1-normal")
                                            move = "BUY"
                                            await sendemail(f'{instance.login} STR: {instance.strategy} Order info:', f'Normal 1 buy: {prediction}, {slbuy}, {diff}')
                                        elif prediction < mid_price and diff > 25:
                                            target = float(bid) + diff
                                            await instance.open_order_both("BUY", 0.01, target, slbuy, "str1-dir1-reverse")
                                            move = "BUY-R"
                                            await sendemail(f'{instance.login} STR: {instance.strategy} Order info:', f'Reverse 1 buy: {target}, {slbuy}, {diff}')
                                        else:
                                            await sendemail("Diff too small", instance.login)
                                    elif direction == 0:
                                        if prediction > mid_price and diff > 25:
                                            target = float(bid) - diff
                                            await instance.open_order_both("SELL", 0.01, target, slsell, "str1-dir0-reverse")
                                            move = "SELL-R"
                                            await sendemail(f'{instance.login} Order info:', f'Reverse 0 sell: {target}, {slsell}, {diff}')
                                        elif prediction < mid_price and diff > 25:
                                            await instance.open_order_both("SELL", 0.01, prediction, slsell, "str1-dir0-normal")
                                            move = "SELL"
                                            await sendemail(f'{instance.login} STR: {instance.strategy} Order info:', f'Normal 0 sell: {prediction}, {slsell}, {diff}')
                                        else:
                                            await sendemail('Diff too small', instance.login)
                                    elif direction == -1:
                                        if prediction > mid_price and diff > 25:
                                            await instance.open_order_both("BUY", 0.01, prediction, slbuy, "str1-dir-min1-normal")
                                            move = "BUY"
                                            await sendemail(f'{instance.login} STR: {instance.strategy} Order info:', f'Normal -1 buy: {prediction}, {slbuy}, {diff}')
                                        elif prediction < mid_price and diff > 25:
                                            await instance.open_order_both("SELL", 0.01, prediction, slsell, "str1-dir-min1-normal")
                                            move = "SELL"
                                            await sendemail(f'{instance.login} STR: {instance.strategy} Order info:', f'Normal -1 sell: {prediction}, {slsell}, {diff}')
                                        else:
                                            await sendemail("Diff too small", instance.login)
                                # STRATEGY 0
                                else:
                                    if prediction > mid_price and diff > 25:
                                        await instance.open_order_both("BUY", 0.01, prediction, slbuy, "ILLCLOUD")
                                        move = "BUY"
                                        await sendemail(f'{instance.login} STR: {instance.strategy} Order info:', f'Normal 0 buy: {prediction}, {slbuy}, {diff} Mid: {mid_price}')
                                    elif prediction < mid_price and diff > 25:
                                        await instance.open_order_both("SELL", 0.01, prediction, slsell, "ILLCLOUD")
                                        move = "SELL"
                                        await sendemail(f'{instance.login} STR: {instance.strategy} Order info:', f'Normal 0 sell: {prediction}, {slsell}, {diff} Mid: {mid_price}')
                                    else:
                                        await sendemail("Diff too small", instance.login)

                            except ValueError as e:
                                await sendemail('ValueError Caught (2nd try)', str(e))
                            except Exception as e:
                                await sendemail('Error Caught (2nd try)', str(e))
                        else:
                            await sendemail("Failed prediction!CheckTime", "Nan")
                    except Exception as err:
                        print("Error opening automatically after prediction on interval.", err)
                        traceback.print_exc()

    lastminute = current_minute

# ----------------------------------------------------------------------------------------------------- SCRIPT RUNNER
instances = []
    
new_template = { "service": "infinipyv2", "clients": [], "visits": 0 }
direction_template = { "service": "infinipyv2-direction-template", "direction": -1, "direction_date": None }

account1 = {
    "metaapitoken": "meta_api_token",
    "brokerlogin" : "account_login",
    "brokerpass" : "account_password",
    "brokerserver" : "server_name", 
    "deployed" : "BOOL",
    "timeframe": "INT",
    "strategy" : 2
}

manager = None

mainCounter = 0
async def tradingLogin():
    global mainCounter
    global from_address
    global to_address
    global subject
    global body
    global instances
    global direction
    global new_template, main, main2, leandro

    mainCounter += 1

    await get_connection()
    await clean_db()

    print("Database creation..")
    await create_main_db(new_template)
    #a.run(create_dir_db(direction_template))
    print("Waiting 3 seconds for database update.")
    await asyncio.sleep(3)
    print("Adding clients to database.")
    await update_clients(main)
    print("Client one added.")
    await update_clients(main2)
    print("Client two added.")
    #await update_clients(hema)
    #print("Client three added.")

    #------------- DATABASE LOG
    #log_db()
    #await sendemail("Clients:", await log_clients())
    #increase_visits()
    #log_visits()

    ready = True
    if ready:
        clients = await return_the_clients()

        for client in clients:
            instance = await Trader.create(client.get("metaapitoken"), client.get("brokerlogin"), client.get("brokerpass"), client.get('brokerserver'), client.get('deployed'), client.get('timeframe'), client.get('strategy'))
            instances.append(instance)
        
        global trader
        trader = instances[0]
        await sendemail(f"Instances logged: {len(instances)}", "Info on title.")
        
    if not runningTimer:
        interval = 15
        asyncio.create_task(schedule_checkTime(interval))

    await smtp_client.connect()
    await smtp_client.send_email(from_address, to_address, subject, body)

    global direction
    await sendemail("Fetching direction", "Nan")
    direction = await return_direction()
    await sendemail(f"Direction fetched: {direction}", "Nan")

    await update_previsions(True)
    #global manager
    #manager = ConnectionManager()

# ----------------------------------------------------------------------------------------------------- INTERVAL_FUNCTIONS

def start_event_loop(loop):
    if not runningTimer:
        asyncio.set_event_loop(loop)
        loop.run_forever()

async def schedule_checkTime(interval):
    while True:
        await checkTime()
        await asyncio.sleep(interval) 

if not runningTimer:
    loop = asyncio.new_event_loop()
    threading.Thread(target=start_event_loop, args=(loop,), daemon=True).start()
    asyncio.run_coroutine_threadsafe(tradingLogin(), loop)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(app, port=port)

# 2024 - ILLIMITEDANDCOMPANY


    
    


    
