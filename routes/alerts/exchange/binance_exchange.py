import os
from dotenv import load_dotenv
import requests
from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException
import datetime as dt
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
import time
import json
import sys
from routes.db_query_manager import execute_query
load_dotenv()


website_url = os.getenv("WEBSITE_URL")
base_url = "http://127.0.0.1:8000"
APINAME = os.getenv("APINAME")
APIPASSWORD = os.getenv("APIPASSWORD")
auth = (APINAME, APIPASSWORD)

proxy = os.getenv("PROXY_URL")
os.environ['http_proxy'] = proxy
os.environ['HTTP_PROXY'] = proxy
os.environ['https_proxy'] = proxy
os.environ['HTTPS_PROXY'] = proxy




response = requests.get('https://fapi.binance.com/fapi/v1/exchangeInfo')
info = response.json()

def create_success_log(response_text, api_key, error_code, is_error):
    now = dt.datetime.now()
    today = now.strftime("%Y-%m-%d %H:%M:%S")

    query = "INSERT INTO alertlogs (api_key, error, alert, created_at, updated_at, is_error, snippet_message) SELECT id, :error, :alert, :created_at, :updated_at, :is_error, '' FROM api_keys WHERE api_key = :api_key"
    values = {"error": str(response_text), "alert": error_code, "created_at": today, "updated_at": today, "is_error": is_error, "api_key": api_key}

    results = execute_query(query, values)


    query = "SELECT user_id FROM api_keys WHERE api_key = :api_key"
    values = {"api_key": api_key}

    results = execute_query(query, values)

    user_id = results[0][0]
    data = {
        "private_key" : "alfj2847Gdjfzrb976dgshKAgsifgibcjouh2djeofaeif103854739879327uUUUuusuuuauoknbvwhpaue8Ahfiwj",
        "title": "Zeppotrade Binance Successfully Executed Alert",  
        "body": str(response_text),
        "isError" : "false",
    }


    #response = requests.post( website_url + "/api/sendPushNotification/" + str( user_id), data=data)
    #print(response.text)

def create_alert_log(e, api_key, error_code, is_error ):
    now = dt.datetime.now()
    today = now.strftime("%Y-%m-%d %H:%M:%S")
    error_message = str(e)
    if('code=-2019' in str(e)):
        error_message = "Insufficient funds to complete the order."
    if('code=-4164' in str(e)):
       error_message = "The quantity is below the minimum allowed amount."



    query = "INSERT INTO alertlogs (api_key, error, alert, created_at, updated_at, is_error, snippet_message) SELECT id, :error, :alert, :created_at, :updated_at, :is_error, '' FROM api_keys WHERE api_key = :api_key"
    values = {"error": str(error_message), "alert": error_code, "created_at": today, "updated_at": today, "is_error": is_error, "api_key": api_key}
    results = execute_query(query, values)


    #send notification

    query = "SELECT user_id FROM api_keys WHERE api_key = :api_key"
    values = {"api_key": api_key}

    results = execute_query(query, values)
    user_id = results[0][0]
    data = {
        "private_key" : "alfj2847Gdjfzrb976dgshKAgsifgibcjouh2djeofaeif103854739879327uUUUuusuuuauoknbvwhpaue8Ahfiwj",
        "title": "Zeppotrade Binance Alert Error",  
        "body": str(error_message),
        "isError" : "true",
    }


    #response = requests.post( website_url + "/api/sendPushNotification/" + str( user_id), data=data)
    #print(response.text)

def truncate_to_step_size(quantity, symbol, client):
    exchange_info = client.get_exchange_info()
    symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
    if symbol_info:
        for filter in symbol_info['filters']:
            filter_type = filter['filterType']
            if(filter_type == "LOT_SIZE"):
                step_size = filter['stepSize']
                quantity_decimal = Decimal(str(quantity))
                step_size_decimal = Decimal(str(step_size))
                truncated_quantity = (quantity_decimal / step_size_decimal).quantize(0, rounding=ROUND_DOWN) * step_size_decimal
                return float(truncated_quantity)

def get_symbol_info(symbol, is_futures = False, client = None):

    if(is_futures == True):
        try:
            exchange_info = client.futures_exchange_info()
            for pair in exchange_info['symbols']:
                if pair['symbol'] == symbol:
                    return pair
            
            print(f"Symbol '{symbol}' not found in futures exchange info.")
            return None
    
        except Exception as e:
            print(f"Failed to fetch symbol info for {symbol}: {e}")
            return None
    

    base_url = "https://api.binance.com/api/v3/exchangeInfo"
    response = requests.get(base_url)
    exchange_info = response.json()

    for pair in exchange_info['symbols']:
        if pair['symbol'] == symbol:
            return pair

    return None

def split_symbol(symbol_info):
    base_asset = symbol_info['baseAsset']
    quote_asset = symbol_info['quoteAsset']
    return base_asset, quote_asset

def open_spot_order(symbol, side, quantity, price_type, client, PriceNum,api_key, lowercase_data, account, OrderType):
    def open_order(symbol,side, quantity, price_type,client, PriceNum):
        if 'e' in str(quantity).lower():
            quantity = format(quantity, 'f')
            print(quantity)
        price_type = price_type.upper()
        try:

            if(price_type == 'MARKET'):
                order = client.create_order(
                    symbol=symbol,
                    side=side,
                    type=Client.ORDER_TYPE_MARKET,
                    quantity=quantity,
                    recvWindow=60000
                )
                print(order)
                create_success_log(order, api_key, "binance_success", 0)
            else:
                PriceNum = get_rounded_price(client, symbol, PriceNum, False)
                order = client.create_order(
                    symbol=symbol,
                    side=side,
                    price=PriceNum,
                    type=Client.ORDER_TYPE_LIMIT,
                    timeInForce=Client.TIME_IN_FORCE_GTC,
                    quantity=quantity,
                    recvWindow=60000
                )
                print(order)
                create_success_log(order, api_key, "binance_success", 0)

        except Exception as e:
                    if isinstance(e, BinanceAPIException):
                        create_alert_log(e, api_key, "binance_error", 1)
                
                        print(e)
                    else:
                        print("Non-Binance API error")
                        print(e)


    if('%' in str(quantity)):
        quantity = float(quantity.rstrip('%')) / 100
        symbol_info = get_symbol_info(symbol)
        account_info = client.get_account()
        if symbol_info:
            base_asset, quote_asset = split_symbol(symbol_info)

            #get account balance
            for balance in account_info['balances']:
                asset = balance['asset']
                free_balance = float(balance['free'])

                if(side == "BUY"):
                    order_asset = quote_asset
                    if(quantity > 0.97):
                        quantity = 0.97
                else:
                    order_asset = base_asset
                    
                if asset == order_asset:
                    print(f"Free Balance: {free_balance} {order_asset}")

                    if(side == "BUY"):
                        #get coin price
                        ticker = client.get_symbol_ticker(symbol=symbol)
                        coin_price = float(ticker['price'])
                        quantity = free_balance * quantity
                        quantity = quantity / coin_price 
                    else:
                        quantity = free_balance * quantity
                    
                 
                    quantity = truncate_to_step_size(quantity, symbol, client)
                    print(quantity)

                    open_order(symbol,side, quantity, price_type,client, PriceNum)

                            
            
                    break
            else:
                print(f"Asset {quote_asset} not found in the account.")
        else:
            print(f"Symbol {symbol} not found on Binance.")
    else:
        print(quantity)
        quantity = truncate_to_step_size(quantity, symbol, client)
        print(quantity)
        open_order(symbol,side, quantity, price_type,client, PriceNum)

def get_rounded_price(client, symbol: str, price: float, is_futures: bool = False) -> float:
    def round_step_size(quantity, step_size):
        if(step_size is not None):
            quantity = Decimal(str(quantity))
            return float(quantity - quantity % Decimal(str(step_size)))


    def get_tick_size(symbol: str) -> float:
        if(is_futures == True):
            info = client.futures_exchange_info()
            for symbol_info in info['symbols']: 
                if symbol_info['symbol'] == symbol:
                    for symbol_filter in symbol_info['filters']:
                        if symbol_filter['filterType'] == 'PRICE_FILTER':
                            return float(symbol_filter['tickSize'])
        else:
            info = client.get_symbol_info(symbol)
            filters = info['filters']
            for symbol_filter in filters:
                if symbol_filter['filterType'] == 'PRICE_FILTER':
                    return float(symbol_filter['tickSize'])


    return round_step_size(price, get_tick_size(symbol))

def caculate_sl_in_perc(sl, is_long_position, coin_price):
    sl = float(sl.strip('%')) / 100
    if(is_long_position == True):
        sl = coin_price - coin_price * sl
    else:
        sl = sl * coin_price + coin_price
    
    return sl

def caculate_tp_in_perc(tp, is_long_position, coin_price):
    tp = float(tp.strip('%')) / 100
    if(is_long_position == True):
        tp = tp * coin_price + coin_price
    else:
        tp = coin_price - coin_price * tp

    return tp

#futures precision quantity caculation
    
def truncate_to_step_size_FUTURES(symbol, quantity,client):
    exchange_info = client.futures_exchange_info()
    for pair in exchange_info['symbols']:
        if pair['symbol'] == symbol:
            filters = pair['filters']
            lot_size_filter = next((f for f in filters if f['filterType'] == 'LOT_SIZE'), None)

            if lot_size_filter:
                step_size = float(lot_size_filter['stepSize'])
                quantity_decimal = Decimal(str(quantity))
                step_size_decimal = Decimal(str(step_size))
                truncated_quantity = (quantity_decimal / step_size_decimal).quantize(0, rounding=ROUND_DOWN) * step_size_decimal
                return float(truncated_quantity)

            else:
                print(f"Lot size filter not found for {symbol}")
                return None
    
    print(f"Symbol {symbol} not found")
    return None

def get_available_balance(quote_asset, client):
    account_info = client.futures_account_balance()
    for asset in account_info:
        if 'asset' in asset and asset['asset'] == quote_asset and 'availableBalance' in asset:
            return float(asset['availableBalance'])


    return None

def caculate_quantity_futures(quantity, symbol, client, side, leverage, PriceType, OrderQty, OrderSide, api_key, tp, sl, PriceNum, OrderType, lowercase_data, account, is_hedge):
    if(is_hedge == None):
        position_mode = client.futures_get_position_mode()
        is_hedge = position_mode['dualSidePosition']


    if('%' in str(quantity)):
        tries_counter = 0
        closing_existing_position = None
        qty_in_perc = float(quantity.rstrip('%')) / 100
        symbol_info = get_symbol_info(symbol, True, client)
        base_asset, quote_asset = split_symbol(symbol_info)
    
        if(is_hedge == False):
            open_positions = client.futures_position_information(symbol=symbol)
            if open_positions:
                open_position_side = None
                print("Open BTC positions:")
                for position in open_positions:
                    position_amount = float(position['positionAmt'])
                    if(position_amount < 0) :
                        open_position_side = "SELL"
                    elif position_amount > 0:
                        open_position_side = "BUY"
                    print(open_position_side)

            
            else:
                closing_existing_position = False
        else:
            open_position_side = None
            closing_existing_position = False

        
        #if there is open position and if order side is opposite to alert side it means closing_existing-position = true

        if(open_position_side == None):
            closing_existing_position = False
        else:
            if(open_position_side == side):
                closing_existing_position = False
            else:
                available_balance = position['positionAmt']
                available_balance = available_balance.replace("-", "")
                closing_existing_position = True

        if(closing_existing_position == False):
            available_balance = get_available_balance(quote_asset, client)

            
            #print(f"Available Balance for {quote_asset}: {available_balance}")
            coin_price = client.futures_ticker(symbol=symbol)
        

        while tries_counter < 11:
            try:
                print(quantity)
                quantity = float(available_balance) * qty_in_perc
                if(closing_existing_position == False):
                    quantity = quantity / float(coin_price['lastPrice']) * float(leverage)

                quantity = truncate_to_step_size_FUTURES(symbol, quantity, client) 
                print(quantity)
                open_futures_position(symbol, client,PriceType, quantity, OrderSide, api_key, tp, sl, PriceNum, OrderType, is_hedge)
                break
                
            
            except BinanceAPIException as e:
                    if e.code == -2019 and tries_counter < 10:
                        qty_in_perc= qty_in_perc - 0.03
                        tries_counter += 1
                    else:
                        print(e)
                        create_alert_log(e, api_key, "binance_error", 1)
                        break
    else:
        try:
            quantity = truncate_to_step_size_FUTURES(symbol, quantity, client) 
            open_futures_position(symbol, client,PriceType, quantity, OrderSide, api_key, tp, sl, PriceNum, OrderType, is_hedge)

        except BinanceAPIException as e:
                print(e)
                create_alert_log(e, api_key, "binance_error", 1)
                  
def open_futures_position(symbol, client,PriceType, OrderQty, OrderSide, api_key, tp, sl, PriceNum, OrderType, is_hedge):
    if(PriceType == 'MARKET'):

        if is_hedge == False:
            order = client.futures_create_order(
                symbol=symbol,
                side=OrderSide.upper(),
                type=ORDER_TYPE_MARKET,
                quantity=OrderQty,
                recvWindow=100000000
            )
        else:
            order = client.futures_create_order(
                symbol=symbol,
                side=OrderSide.upper(),
                type=ORDER_TYPE_MARKET,
                quantity=OrderQty,
                recvWindow=100000000,
                positionSide='LONG' if OrderSide.upper() == 'BUY' else 'SHORT'
            )
        print(order)
        create_success_log(order, api_key, "binance_success", 0)

        
        if OrderSide.upper() == 'BUY':
            SP = 'SELL'
            is_long_position = True
        elif OrderSide.upper() == 'SELL':
            is_long_position = False
            SP = 'BUY'
   
        coin_price = None

        if tp is not None:
            if(coin_price == None):
                ticker = client.futures_symbol_ticker(symbol=symbol)
                coin_price = float(ticker['price'])

            if('%' in tp):  
                print(coin_price)
                tp = caculate_tp_in_perc(tp, is_long_position, coin_price)

 
            tp = get_rounded_price(client, symbol, tp, True)
            if is_hedge == False:
                order = client.futures_create_order(
                    symbol=symbol,
                    side=SP,
                    type='TAKE_PROFIT_MARKET',
                    stopPrice=tp,
                    closePosition='true',
                    recvWindow=100000000
                )
            else:
                order = client.futures_create_order(
                    symbol=symbol,
                    side=SP,
                    type='TAKE_PROFIT_MARKET',
                    stopPrice=tp,
                    closePosition='true',
                    recvWindow=100000000,
                    positionSide='LONG' if OrderSide.upper() == 'BUY' else 'SHORT'
                )

        if sl is not None:
            if(coin_price == None):
                ticker = client.futures_symbol_ticker(symbol=symbol)
                coin_price = float(ticker['price'])

            if('%' in sl):
                sl = caculate_sl_in_perc(sl, is_long_position, coin_price)
            sl = get_rounded_price(client, symbol, sl, True)
            if is_hedge == False:
                order = client.futures_create_order(
                    symbol=symbol,
                    side=SP,
                    type='STOP_MARKET',
                    stopPrice=sl,
                    closePosition='true',
                    recvWindow=100000000
                )
            else:
                order = client.futures_create_order(
                    symbol=symbol,
                    side=SP,
                    positionSide='LONG' if OrderSide.upper() == 'BUY' else 'SHORT',
                    type='STOP_MARKET',
                    stopPrice=sl,
                    closePosition='true',
                    recvWindow=100000000,
                    
                )
    elif(OrderType == 'TAKE_PROFIT_MARKET' or  OrderType == 'STOP_MARKET'):
        order = client.futures_create_order(
            symbol=symbol,
            side=OrderSide.upper(),
            type=OrderType,
            stopPrice=PriceNum,
            closePosition='true',
            recvWindow=100000000
        )
    else:
            PriceNum = get_rounded_price(client, symbol, PriceNum, True)
            if is_hedge == False:
                order = client.futures_create_order(
                    symbol=symbol,
                    side=OrderSide.upper(),
                    price=PriceNum,
                    type=Client.ORDER_TYPE_LIMIT,
                    timeInForce=Client.TIME_IN_FORCE_GTC,
                    quantity=OrderQty,
                    recvWindow=100000000,
                )
            else:
                order = client.futures_create_order(
                    symbol=symbol,
                    side=OrderSide.upper(),
                    price=PriceNum,
                    type=Client.ORDER_TYPE_LIMIT,
                    timeInForce=Client.TIME_IN_FORCE_GTC,
                    quantity=OrderQty,
                    recvWindow=100000000,
                    positionSide='LONG' if OrderSide.upper() == 'BUY' else 'SHORT'
                )
            print(order)
            create_success_log(order, api_key, "binance_success", 0)


            if OrderSide.upper() == 'BUY':
                SP = 'SELL'
                is_long_position = True
            elif OrderSide.upper() == 'SELL':
                is_long_position = False
                SP = 'BUY'

            coin_price = None

            if tp is not None:
                if(coin_price == None):
                    ticker = client.futures_symbol_ticker(symbol=symbol)
                    coin_price = float(ticker['price'])

                if('%' in tp):  
                    print(coin_price)
                    tp = caculate_tp_in_perc(tp, is_long_position, coin_price)

    
                tp = get_rounded_price(client, symbol, tp, True)
                if is_hedge == False:
                    order = client.futures_create_order(
                        symbol=symbol,
                        side=SP,
                        type='TAKE_PROFIT_MARKET',
                        stopPrice=tp,
                        closePosition='true',
                        recvWindow=100000000
                    )
                else:
                    order = client.futures_create_order(
                        symbol=symbol,
                        side=SP,
                        type='TAKE_PROFIT_MARKET',
                        stopPrice=tp,
                        closePosition='true',
                        recvWindow=100000000,
                        positionSide='LONG' if OrderSide.upper() == 'BUY' else 'SHORT'
                    )

            if sl is not None:
                if(coin_price == None):
                    ticker = client.futures_symbol_ticker(symbol=symbol)
                    coin_price = float(ticker['price'])

                if('%' in sl):
                    sl = caculate_sl_in_perc(sl, is_long_position, coin_price)
                sl = get_rounded_price(client, symbol, sl, True)
                if is_hedge == False:
                    order = client.futures_create_order(
                        symbol=symbol,
                        side=SP,
                        type='STOP_MARKET',
                        stopPrice=sl,
                        closePosition='true',
                        recvWindow=100000000
                    )
                else:
                    order = client.futures_create_order(
                        symbol=symbol,
                        side=SP,
                        positionSide='LONG' if OrderSide.upper() == 'BUY' else 'SHORT',
                        type='STOP_MARKET',
                        stopPrice=sl,
                        closePosition='true',
                        recvWindow=100000000,
                        
                    )
            
def open_trailing_stop(client,lowercase_data, api_key, is_hedge):

    missing_keywords = []

    if 'symbol' not in lowercase_data:
        missing_keywords.append('symbol')

    if 'account' not in lowercase_data:
        missing_keywords.append('account')

    if 'trailingside' not in lowercase_data:
        missing_keywords.append('trailingside')

    if 'callbackrate' not in lowercase_data:
        missing_keywords.append('callbackrate')
    
    if 'trailingquantity' not in lowercase_data:
        missing_keywords.append('trailingquantity')


    if missing_keywords:
        create_alert_log(f"Missing parameters in tradingview message: {', '.join(missing_keywords)}" + ". Please read setup guide.", api_key, "error_1", 1)
        print(f"Missing parameters in tradingview message: {', '.join(missing_keywords)}" + ". Please read setup guide.")
    else:

        symbol = lowercase_data['symbol']
        account = lowercase_data['account']
        side = lowercase_data['trailingside']
        quantity = lowercase_data['trailingquantity']
        callback_rate = lowercase_data['callbackrate']
        
        callback_rate = float(callback_rate.rstrip('%'))
        if('activationprice' in lowercase_data):
            activation_price = lowercase_data['activationprice']
            if(account == "usdm"):
                activation_price = get_rounded_price(client, symbol.upper(), activation_price, True)




        if(side == "long" or side == "buy"):
            side = "BUY"
            posSide= "LONG"
        elif side == "short" or  side == "sell":
            side =  "SELL"
            posSide= "short"

        
        
        quantity = truncate_to_step_size_FUTURES(symbol.upper(), quantity, client) 
        if(account == "usdm"):
            if(is_hedge == False):
                if('activationprice' in lowercase_data):
                    order = client.futures_create_order(
                        symbol=symbol,
                        side=side.upper(),
                        type='TRAILING_STOP_MARKET',
                        quantity=quantity,
                        callbackRate=callback_rate,
                        activationPrice=activation_price,
                    )
                else:
                    order = client.futures_create_order(
                        symbol=symbol,
                        side=side.upper(),
                        type='TRAILING_STOP_MARKET',
                        quantity=quantity,
                        callbackRate=callback_rate,
                    )
            else:
                if('activationprice' in lowercase_data):
                    order = client.futures_create_order(
                        symbol=symbol,
                        side=side.upper(),
                        type='TRAILING_STOP_MARKET',
                        quantity=quantity,
                        callbackRate=callback_rate,
                        activationPrice=activation_price,
                        positionSide=posSide
                    )
                else:
                    order = client.futures_create_order(
                        symbol=symbol,
                        side=side.upper(),
                        type='TRAILING_STOP_MARKET',
                        quantity=quantity,
                        callbackRate=callback_rate,
                        positionSide=posSide
                    )


        elif(account == "spot"):
            print("spot")

def send_binance(json_data, api_key, snippet):
    print("snipper is:" + snippet)
    query = "SELECT binance_api_key, binance_api_secret, testnet FROM binance_alerts WHERE api_key_id = (SELECT id FROM api_keys WHERE api_key = :api_key);"
    values = {"api_key": api_key}
    results = execute_query(query, values)
 


    binance_api_key = results[0][0]
    binance_api_secret = results[0][1]
    is_testnet = results[0][2]

    is_testnet = (is_testnet == 1)
    client = Client(binance_api_key, binance_api_secret,testnet=is_testnet)



 
    #print(api_key)
    tp = None
    sl = None
    is_hedge = None

    print(json_data)
    lowercase_data = {key.lower(): value.lower() if isinstance(value, str) else value for key, value in json_data.items()}

    if('sellquantity' in lowercase_data):
        if(lowercase_data['side'] == "sell" or lowercase_data['side'] == "short"):
            lowercase_data['quantity'] = lowercase_data['sellquantity']

    if('shortquantity' in lowercase_data):
        if(lowercase_data['side'] == "sell" or lowercase_data['side'] == "short"):
            lowercase_data['quantity'] = lowercase_data['shortquantity']

    if('buyquantity' in lowercase_data):
        if(lowercase_data['side'] == "buy" or lowercase_data['side'] == "long"):
            lowercase_data['quantity'] = lowercase_data['buyquantity']

    if('longquantity' in lowercase_data):
        if(lowercase_data['side'] == "sell" or lowercase_data['side'] == "long"):
            lowercase_data['quantity'] = lowercase_data['longquantity']


    if('side' in lowercase_data):
        if('{{strategy.order.action}}' in lowercase_data['side']):
            create_alert_log("You are most likely using an indicator, which doesn't support placeholders like {{strategy.order.action}}. To fix this, create two separate alerts: one for the buy condition and one for the sell condition. ", api_key, "binance_error", 1)
            sys.exit()
    if('quantity' in lowercase_data):
        if('{{strategy.market_position_size}}' in lowercase_data['quantity']):
            create_alert_log("Your strategy doesn't use {{strategy.market_position_size}}. Try using quantity={{strategy.order.contracts}} instead.", api_key, "binance_error", 1)
            sys.exit()

        if('{{strategy.order.contracts}}' in lowercase_data['quantity']):
            create_alert_log("Your strategy doesn't support {{strategy.order.contracts}} or you are using an indicator.", api_key, "binance_error", 1)
            sys.exit()
        
    if 'symbol' in lowercase_data:
        lowercase_data['symbol'] = lowercase_data['symbol'].rstrip('.pP')

    # Check if 'cancel' key exists and remove '.p' or '.P' from the end
    if 'cancel' in lowercase_data:
        lowercase_data['cancel'] = lowercase_data['cancel'].rstrip('.pP')




    if 'quantity' in lowercase_data:
        if "-" in lowercase_data['quantity']:
            lowercase_data['quantity'] = lowercase_data['quantity'].replace("-", "")

    if 'wait' in lowercase_data:
        time_to_wait = lowercase_data['wait']
        time.sleep(float(time_to_wait))

    


    #validate tradingview message syntax
    missing_keywords = []

    if('cancel' in lowercase_data):
        position_symbol =  lowercase_data['cancel']
    else:
        position_symbol =  lowercase_data['symbol']

    if 'account' in lowercase_data:
        if(lowercase_data['account'] == 'usdm'):
            account_is_futures = True
        else:
            account_is_futures = False

    if('callbackrate' in lowercase_data):
        position_mode = client.futures_get_position_mode()
        is_hedge = position_mode['dualSidePosition']
        try:
            open_trailing_stop(client, lowercase_data, api_key, is_hedge)
        except Exception as e:
            if isinstance(e, BinanceAPIException):
                create_alert_log(e, api_key, "binance_error", 1)
                print(e)
            else:
                print("Non-Binance API error")
                print(e)

    
    if 'account' not in lowercase_data or account_is_futures:
        if is_hedge == None:
            position_mode = client.futures_get_position_mode()
            is_hedge = position_mode['dualSidePosition']
        try:
            positions = client.futures_position_information(symbol=position_symbol.upper())
        except Exception as e:
            if isinstance(e, BinanceAPIException):
                create_alert_log(e, api_key, "binance_error", 1)
                print(e)
        for position in positions:
            position_amount = float(position['positionAmt'])
            print(position_amount)
            if(position_amount != 0):
                if position_amount > 0:
                    position_side = "SELL"
                    is_long_position = True
                    break

                elif position_amount < 0:
                    position_side = "BUY"
                    is_long_position = False
                    break
                else:
                    position_side = "NONE"
            else:
                    position_side = "NONE"
        

    if ('cancel' in lowercase_data or 'sl' in lowercase_data or 'tp' in lowercase_data):
        if('cancel' in lowercase_data):
            symbol_to_close = lowercase_data['cancel'].upper()
            futures_positions = client.futures_position_information()
                # Filter and print only BTCUSDT positions


            for position in futures_positions:
                if position['symbol'] == symbol_to_close:
                    position_amount = float(position['positionAmt'])
                    open_orders = client.futures_get_open_orders(symbol=symbol_to_close)
                    for order in open_orders:
                        client.futures_cancel_order(symbol=symbol_to_close, orderId=order['orderId'])
                        print(f"Cancelled order ID {order['orderId']} - Type: {order['type']}")
         
                    if position_amount != 0:
                        if(is_hedge == False):
                            order = client.futures_create_order(
                                symbol=symbol_to_close,
                                side='SELL' if position_amount > 0 else 'BUY',
                                type='MARKET',
                                quantity=abs(position_amount),
                            )
                            print(f"Closed position for {symbol_to_close}. Order ID: {order['orderId']}")
                        else:
                            order = client.futures_create_order(
                                symbol=symbol_to_close,
                                side='SELL' if position_amount > 0 else 'BUY',
                                type='MARKET',
                                quantity=abs(position_amount),
                                positionSide=position['positionSide']
                            )
                            print(f"Closed position for {symbol_to_close}. Order ID: {order['orderId']}")
                    print(position)
                    print(f"{symbol_to_close} position closed successfully.")
                      # Exit the loop after closing the specified position


        if(position_side != "NONE"):
            coin_price = None
            if('sl' in lowercase_data):
                #cancel sl
                symbol_to_close = lowercase_data['symbol'].upper()
                open_orders = client.futures_get_open_orders(symbol=symbol_to_close)
                for order in open_orders:
                    if order['type'] == 'STOP_MARKET':
                        client.futures_cancel_order(symbol=symbol_to_close, orderId=order['orderId'])

                if(lowercase_data['sl'] != "cancel"):
                    try:
                        sl = lowercase_data['sl']
                        symbol = lowercase_data['symbol'].upper()
                        if(coin_price == None):
                            ticker = client.futures_symbol_ticker(symbol=symbol)
                            coin_price = float(ticker['price'])
                  
                        if('%' in sl):  
                            sl = caculate_sl_in_perc(sl, is_long_position, coin_price)
                        
                        sl = get_rounded_price(client, lowercase_data['symbol'].upper(), sl, True)
                        if is_hedge == False:
                            order = client.futures_create_order(
                                symbol=lowercase_data['symbol'].upper(),
                                side=position_side,
                                type='STOP_MARKET',
                                stopPrice=sl,
                                closePosition='true',
                                recvWindow=100000000
                            )
                        else:

                            order = client.futures_create_order(
                                symbol=symbol,
                                side=position_side,
                                positionSide='SHORT' if position_side == 'BUY' else 'LONG',
                                type='STOP_MARKET',
                                stopPrice=sl,
                                closePosition='true',
                                recvWindow=100000000,
                                
                            )
        
                    except Exception as e:
                     if isinstance(e, BinanceAPIException):
                            create_alert_log(e, api_key, "binance_error", 1)
                            print(e)
            
            if('tp' in lowercase_data):
                #cancel sl
                symbol_to_close = lowercase_data['symbol'].upper()
                open_orders = client.futures_get_open_orders(symbol=symbol_to_close)
                for order in open_orders:
                    if order['type'] == 'TAKE_PROFIT_MARKET':
                        client.futures_cancel_order(symbol=symbol_to_close, orderId=order['orderId'])

                if(lowercase_data['tp'] != "cancel"):
                    try:
                        tp = lowercase_data['tp']
                        symbol = lowercase_data['symbol'].upper()
                        if(coin_price == None):
                            ticker = client.futures_symbol_ticker(symbol=symbol)
                            coin_price = float(ticker['price'])
                  
                        if('%' in tp):  
                            tp = caculate_tp_in_perc(tp, is_long_position, coin_price)
          

                        tp = get_rounded_price(client, lowercase_data['symbol'].upper(), tp, True)
                        if is_hedge == False:
                            order = client.futures_create_order(
                                symbol=lowercase_data['symbol'].upper(),
                                side=position_side,
                                type='TAKE_PROFIT_MARKET',
                                stopPrice=tp,
                                closePosition='true',
                                recvWindow=100000000
                            )
                        else:
                            order = client.futures_create_order(
                                symbol=symbol,
                                side=position_side,
                                type='TAKE_PROFIT_MARKET',
                                stopPrice=tp,
                                closePosition='true',
                                recvWindow=100000000,
                                positionSide='SHORT' if position_side == 'BUY' else 'LONG'
                            )

                    except Exception as e:
                        if isinstance(e, BinanceAPIException):
                            create_alert_log(e, api_key, "binance_error", 1)
                            print(e)
                            
    if('quantity' in lowercase_data):
        if 'account' not in lowercase_data:
            missing_keywords.append('account')

        if 'side' not in lowercase_data:
            missing_keywords.append('side')

        if 'symbol' not in lowercase_data:
            missing_keywords.append('symbol')

        if 'quantity' not in lowercase_data:
            missing_keywords.append('quantity')

        if missing_keywords:
            create_alert_log(f"Missing parameters in tradingview message: {', '.join(missing_keywords)}" + ". Please read setup guide.", api_key, "error_1", 1)
            print(f"Missing parameters in tradingview message: {', '.join(missing_keywords)}" + ". Please read setup guide.")
            # Perform additional actions if needed
        else:
            # All keywords are present, perform your main actions here
            print("All keywords present. Perform main actions.")


    if 'account' in lowercase_data:
        account = lowercase_data['account']
        print("account:", account)

    else:
        print("'account' key does not exist in the JSON.")
    OrderType=''
    if account in ['spot', 'coinm', 'usdm'] and  'side' in lowercase_data and 'symbol' in lowercase_data:
        



        if 'price' in lowercase_data:
            if lowercase_data['price'] == 'market' :
                PriceType = lowercase_data['price'].upper()
                PriceNum = None
            else:
                
                PriceType = 'LIMIT'
                PriceNum = lowercase_data['price']
        else:
                PriceType = 'MARKET'
                PriceNum = None
                print(PriceNum)


        
        if('quantity' in lowercase_data):
                OrderQty= lowercase_data['quantity']
        symbol = lowercase_data['symbol']
        
        OrderSide = lowercase_data['side']

        if(OrderSide == "long"):
            OrderSide = "BUY"
        elif OrderSide == "short":
            OrderSide =  "SELL"

        OrderSide = OrderSide.upper()






        symbol = symbol.upper()

        try:

            if account == 'usdm' or account =='coinm':

                if 'leverage' in lowercase_data:
                    leverage=lowercase_data['leverage']
                else:
                    #default leverage
                    leverage=10

                if 'margin' in lowercase_data:
                    if lowercase_data['margin'] == 'cross' or lowercase_data['margin'] == 'crossed':
                        IsIsolated = 'CROSSED'
                    else:
                        IsIsolated = 'ISOLATED'
                else:
                        IsIsolated = 'ISOLATED'

        

                if('type' in lowercase_data):
                    if 'take_profit_market' == lowercase_data['type'] or 'stop_market' == lowercase_data['type']:
                        OrderType = lowercase_data['type'].upper()
                

                if 'tp' in lowercase_data:
                    tp =lowercase_data['tp']
                if 'sl' in lowercase_data:
                    sl =lowercase_data['sl']

        

                client.futures_change_leverage(symbol=symbol, leverage=leverage, recvWindow=100000000)
                try:
                    client.futures_change_margin_type(symbol=symbol, marginType=IsIsolated,recvWindow=100000000)
                except Exception as e:
                    print()

                OrderQty = caculate_quantity_futures(OrderQty, symbol, client, OrderSide, leverage, PriceType, OrderQty, OrderSide, api_key, tp, sl, PriceNum, OrderType, lowercase_data, account, is_hedge)
                print(OrderQty)
  
        
            
            elif account == 'spot':
                open_spot_order(symbol, OrderSide.upper(), OrderQty, PriceType, client, PriceNum, api_key, lowercase_data ,account, OrderType)



        except Exception as e:
            if isinstance(e, BinanceAPIException):
                create_alert_log(e, api_key, "binance_error", 1)
        
                print(e)
            else:
                print("Non-Binance API error")
                print(e)

    else:
        print("request invalid, missing parms")




    
