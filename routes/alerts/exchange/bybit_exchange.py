import os
from dotenv import load_dotenv
from pybit.unified_trading import HTTP
import json
import requests
import pybit
from decimal import Decimal, ROUND_DOWN
import datetime as dt
import sys
import time
from routes.db_query_manager import execute_query
from decimal import Decimal

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





testnet_url_bybit = "https://api-testnet.bybit.com"
main_url_bybit = "https://api.bybit.com"


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
        "title": "Zeppotrade Bybit Successfully Executed Alert",  
        "body": str(response_text),
        "isError" : "false",
    }


    response = requests.post( website_url + "/api/sendPushNotification/" + str( user_id), data=data)
    print(response.text)


def create_alert_log(e, api_key, error_code, is_error ):
    now = dt.datetime.now()
    today = now.strftime("%Y-%m-%d %H:%M:%S")
    error_message = str(e)

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
        "title": "Zeppotrade Bybit Alert Error",  
        "body": str(error_message),
        "isError" : "true",
    }


    response = requests.post( website_url + "/api/sendPushNotification/" + str( user_id), data=data)
    print(response.text)



def truncate_to_step_size(quantity, symbol, session):
    exchange_info = session.get_instruments_info(category="linear", symbol=symbol)
    symbol_info = next((s for s in exchange_info['result']['list'] if s['symbol'] == symbol), None)
    if symbol_info:
        for filter in symbol_info['lotSizeFilter']:
            if filter == "qtyStep":
                step_size = Decimal(symbol_info['lotSizeFilter'][filter])
                quantity_decimal = Decimal(str(quantity))
                truncated_quantity = (quantity_decimal / step_size).quantize(0, rounding=ROUND_DOWN) * step_size
                return float(truncated_quantity)

def truncate_to_step_size_spot(quantity, symbol, session,api_key, quantity_in_usd = False):
    ##baseprecision is for btc and quoteprecision is for usd
    try:
        exchange_info = session.get_instruments_info(category="spot", symbol=symbol)
        quote_precision = exchange_info['result']['list'][0]['lotSizeFilter']['quotePrecision']
        base_precision = exchange_info['result']['list'][0]['lotSizeFilter']['basePrecision']
    except Exception as e:
        print(e)
        create_alert_log("Couldn't get symbol information from exchange", api_key, "error_1", 1)


    if(quantity_in_usd == False):
        step_size = base_precision
    else:
        step_size = quote_precision

    step_size_decimal = Decimal(str(step_size))
    quantity_decimal = Decimal(str(quantity))
    truncated_quantity = (quantity_decimal / step_size_decimal).quantize(0, rounding=ROUND_DOWN) * step_size_decimal
    return float(truncated_quantity)
            
def get_btc_price(symbol, bybit_api_url):
    url = f"{bybit_api_url}/v5/market/tickers"
    params = {"symbol": symbol, "category" : "linear" }
    response = requests.get(url, params=params)
    data = response.json()
    btc_data = next((item for item in data["result"]["list"] if item.get("symbol") == symbol), None)
    btc_price = btc_data.get("lastPrice")
    return btc_price

def get_spot_btc_price(symbol, bybit_api_url):
    url = f"{bybit_api_url}/v5/market/tickers"
    params = {"symbol": symbol, "category" : "spot" }
    response = requests.get(url, params=params)
    data = response.json()
    btc_data = next((item for item in data["result"]["list"] if item.get("symbol") == symbol), None)
    btc_price = btc_data.get("lastPrice")
    return btc_price

def get_symbol_info(symbol, is_futures = False):

    if(is_futures == False):
        base_url = "https://api.bybit.com/spot/v1/symbols"
    else:
        base_url = "https://api.bybit.com/v2/public/symbols"

    response = requests.get(base_url)
    exchange_info = response.json()

    for pair in exchange_info['result']:
        if pair['name'] == symbol:
            return pair

    return None

def spot_split_symbol(symbol_info):
    #this is only for spot for futures it is base_currency quote_currency
    base_asset = symbol_info['baseCurrency']
    quote_asset = symbol_info['quoteCurrency']
    return base_asset, quote_asset

def truncate_price_spot(quantity, symbol, session):
    ##baseprecision is for btc and quoteprecision is for usd
    exchange_info = session.get_instruments_info(category="spot", symbol=symbol)
    quote_precision = exchange_info['result']['list'][0]['priceFilter']['tickSize']
    step_size_decimal = Decimal(str(quote_precision))
    quantity_decimal = Decimal(str(quantity))
    truncated_quantity = (quantity_decimal / step_size_decimal).quantize(0, rounding=ROUND_DOWN) * step_size_decimal
    return truncated_quantity

def close_futures_position(symbol, close_size, session, positions):
    open_positions = positions['result']['list']
    if not open_positions:
        print("No open positions found.")
        return

    for position in open_positions:
        size = float(position['size'])
        if size > 0:
            if('%' in str(close_size)):
                close_size = float(close_size.rstrip('%'))
                close_size = size * (close_size / 100)  # Calculate the size to close

            if position['side'] == 'Buy':
                orderSide = 'Sell'
            else:
                orderSide = 'Buy'

            close_size = truncate_to_step_size(close_size, symbol, session)
            response = session.place_order(
                category="linear",
                symbol=symbol,
                side=orderSide,  # Close position on the opposite side
                order_type='Market',
                qty=close_size,
                reduce_only=True  # Ensure this order only reduces the position
            )
            if response['retCode'] == 0:
                print(response)
                print(f"Closed {close_size} of position in {symbol}.")
            else:
                print(f"Error closing position: {response['retMsg']}")

def open_spot_order(PriceType, OrderSide,bybit_api_url, symbol, session, PriceNum, OrderQty,is_usd_quantity, account_type, api_key ):

    quantity_in_usd = False
    if(is_usd_quantity == False):
        if(PriceType == 'MARKET' and '%' not in OrderQty):
            if OrderSide == "Buy":
           
                try:
                      spot_price = get_spot_btc_price(symbol, bybit_api_url)
                except Exception as e:
                    error_message = "Symbol not available"
                    create_alert_log(error_message, api_key, "error_1", 1)
                    sys.exit()
                
                OrderQty = float(OrderQty) * float(spot_price)
                quantity_in_usd = True
    
        if('%' in str(OrderQty)):
            symbol_info = get_symbol_info(symbol)
            base_asset, quote_asset = spot_split_symbol(symbol_info)
            print(base_asset)
            if(OrderSide == "Buy"):
                wallet_coin = quote_asset
            else:
                wallet_coin = base_asset
            qty_in_perc = float(OrderQty.rstrip('%')) / 100

            try:
                get_bybit_balance = session.get_wallet_balance(
                    accountType=account_type.upper(),
                    coin=wallet_coin,
                )
            except pybit.exceptions.InvalidRequestError as e:
                e_msg = str(e)
                error_message = e_msg.split('\n')[0]
                create_alert_log(error_message, api_key, "error_1", 1)
            balance = get_bybit_balance['result']['list'][0]['coin'][0]['availableToWithdraw'] 
            btc_price = get_spot_btc_price(symbol, bybit_api_url)
            

            #if limit quantity is in btc
            if(OrderSide == "Buy" and PriceType != 'MARKET'):
                #convert usd to btc
                OrderQty = float(balance) / float(btc_price) * qty_in_perc
                quantity_in_usd = False

            elif OrderSide == "Buy" and PriceType == 'MARKET' :
                OrderQty = float(balance)  * qty_in_perc
                quantity_in_usd = True

            elif OrderSide == "Sell":
                OrderQty = float(balance)  * qty_in_perc
                quantity_in_usd = False
                
    else:
        quantity_in_usd = True


    if(quantity_in_usd == True):
        print("rounding usd")
        OrderQty = truncate_to_step_size_spot(OrderQty,symbol, session,api_key, True )
    else:
        OrderQty = truncate_to_step_size_spot(OrderQty,symbol, session, api_key,False )

    print(OrderQty)
    if(OrderQty == 0):
        print("quantity cannot be 0")
    else:
        try:
            if(PriceType == 'MARKET'):
                order = session.place_order(
                    category="spot",
                    symbol=symbol,
                    side=OrderSide,
                    orderType="Market",
                    qty=OrderQty,
                    orderFilter="Order",
                )
                print(order)
                create_success_log(order, api_key, "success", 0)
            else:
                PriceNum = truncate_price_spot(PriceNum,symbol, session)
                print(PriceNum)
                order = session.place_order(
                    category="spot",
                    symbol=symbol,
                    side=OrderSide,
                    orderType="Limit",
                    qty=OrderQty,
                    price=PriceNum,
                    timeInForce="PostOnly",
                    orderFilter="Order",
                    
                )
                print(order)
                create_success_log(order, api_key, "success", 0)
        except pybit.exceptions.InvalidRequestError as e:
                print(e)
                e_msg = str(e)
                error_message = e_msg.split('\n')[0]
                create_alert_log(error_message, api_key, "error_1", 1)
  
def open_trailing_stop(lowercase_data, session, bybit_api_url):
    if("symbol" in lowercase_data):
        symbol= lowercase_data['symbol']

    symbol= lowercase_data['symbol']
    retracement = lowercase_data['retracement']

    if('%' in retracement):
        retracement = float(retracement.rstrip('%')) / 100
        if('activationprice' in lowercase_data):
            coin_price = lowercase_data['activationprice']
        else:
            coin_price = get_btc_price(symbol.upper(), bybit_api_url)
            print(coin_price)

        retracement = float(coin_price) * float(retracement)
        retracement = str(retracement)

    if('activationprice' in lowercase_data):
        activation_price = lowercase_data['activationprice']
        print(session.set_trading_stop(
            category="linear",
            symbol=symbol.upper(),
            trailingStop=retracement,
            activePrice=activation_price,
            positionIdx=0,
        ))
    else:
        print(session.set_trading_stop(
            category="linear",
            symbol=symbol.upper(),
            trailingStop=retracement,
            positionIdx=0,
        ))

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

def open_futures_position(quantity, session, PriceType, symbol, OrderSide, PriceNum, sl, tp, api_key , lowercase_data,bybit_api_url):
    print(quantity)
    if(PriceType == 'MARKET'):
        order = session.place_order(
            category="linear",
            symbol=symbol,
            side=OrderSide,
            orderType="Market",
            qty=quantity,
            orderFilter="Order",
            
        )

        print(order)
        create_success_log(order, api_key, "success", 0)

        if OrderSide.upper() == 'BUY':
            is_long_position = True
        elif OrderSide.upper() == 'SELL':
            is_long_position = False

        coin_price = None
        if tp is not None:
            if(coin_price == None):
                coin_price = float(get_btc_price(symbol,bybit_api_url))

            if('%' in tp):  
                print(coin_price)
                tp = caculate_tp_in_perc(tp, is_long_position, coin_price)

            try:
                response = session.set_trading_stop(
                        category="linear",
                        symbol=symbol,
                        takeProfit=tp,
                        tpTriggerBy="MarkPrice",
                        positionIdx=0
                )
            except pybit.exceptions.InvalidRequestError as e:
                    print(e)
                    e_msg = str(e)
                    error_message = e_msg.split('\n')[0]
                    create_alert_log(error_message, api_key, "error_1", 1)

        if sl is not None:
            if(coin_price == None):
                coin_price = float(get_btc_price(symbol,bybit_api_url))

            if('%' in sl):
                sl = caculate_sl_in_perc(sl, is_long_position, coin_price)

            try:
                print(session.set_trading_stop(
                    category="linear",
                    symbol=symbol,
                    stopLoss=sl,
                    slTriggerBy="MarkPrice",
                    positionIdx=0
                ))
            except pybit.exceptions.InvalidRequestError as e:
                    print(e)
                    e_msg = str(e)
                    error_message = e_msg.split('\n')[0]
                    create_alert_log(error_message, api_key, "error_1", 1)
        
    else:
        order = session.place_order(
            category="linear",
            symbol=symbol,
            side=OrderSide,
            orderType="Limit",
            qty=quantity,
            price=PriceNum,
            timeInForce="PostOnly",
            orderFilter="Order",
            
        )

        print(order)
        create_success_log(order, api_key, "success", 0)


        if OrderSide.upper() == 'BUY':
            is_long_position = True
        elif OrderSide.upper() == 'SELL':
            is_long_position = False

        coin_price = None
        if tp is not None:
            if(coin_price == None):
                coin_price = float(get_btc_price(symbol,bybit_api_url))

            if('%' in tp):  
                print(coin_price)
                tp = caculate_tp_in_perc(tp, is_long_position, coin_price)

            try:
                response = session.set_trading_stop(
                        category="linear",
                        symbol=symbol,
                        takeProfit=tp,
                        tpTriggerBy="MarkPrice",
                        positionIdx=0
                )
            except pybit.exceptions.InvalidRequestError as e:
                    print(e)
                    e_msg = str(e)
                    error_message = e_msg.split('\n')[0]
                    create_alert_log(error_message, api_key, "error_1", 1)

        if sl is not None:
            if(coin_price == None):
                coin_price = float(get_btc_price(symbol,bybit_api_url))

            if('%' in sl):
                sl = caculate_sl_in_perc(sl, is_long_position, coin_price)

            try:
                print(session.set_trading_stop(
                    category="linear",
                    symbol=symbol,
                    stopLoss=sl,
                    slTriggerBy="MarkPrice",
                    positionIdx=0
                ))
            except pybit.exceptions.InvalidRequestError as e:
                    print(e)
                    e_msg = str(e)
                    error_message = e_msg.split('\n')[0]
                    create_alert_log(error_message, api_key, "error_1", 1)

    if("retracement" in lowercase_data):
        open_trailing_stop(lowercase_data, session, bybit_api_url)

def caculate_futures_quantity(quantity, session, leverage, symbol, tries_counter, tp, sl, OrderSide, PriceType, PriceNum, bybit_api_url,  account_type, api_key,  lowercase_data):
    if('%' in quantity):
        quantity = float(quantity.rstrip('%')) / 100
        qty_in_perc = quantity
        #GET ACCOUNT BALANCE
        try:
            get_bybit_balance = session.get_wallet_balance(
                accountType=account_type.upper(),
                coin="USDT",
            )
        except pybit.exceptions.InvalidRequestError as e:
            e_msg = str(e)
            error_message = e_msg.split('\n')[0]
            create_alert_log(error_message, api_key, "error_1", 1)
        print(get_bybit_balance)
        balance = get_bybit_balance['result']['list'][0]['coin'][0]['availableToWithdraw'] 
        print(balance)
        #convert balance to coin
        btc_price = get_btc_price(symbol, bybit_api_url)

        while tries_counter < 11:
                try:
                    quantity = float(balance) / float(btc_price) * float(leverage) * qty_in_perc
                    quantity = truncate_to_step_size(quantity, symbol, session)
                    open_futures_position(quantity, session, PriceType, symbol, OrderSide, PriceNum, sl, tp, api_key, lowercase_data, bybit_api_url)
                    break
                    
                except pybit.exceptions.InvalidRequestError as e:
                    error_message = str(e)
                    if "Insufficient available balance" in error_message or "110007" in error_message and tries_counter < 10:
                        qty_in_perc= qty_in_perc - 0.01
                        tries_counter += 1
                    else:
                        create_alert_log(error_message, api_key, "error_1", 1)
                        break
                    
    else:
        try:
            quantity = truncate_to_step_size(quantity, symbol, session)
            open_futures_position(quantity, session, PriceType, symbol, OrderSide, PriceNum, sl, tp, api_key, lowercase_data, bybit_api_url)
        except pybit.exceptions.InvalidRequestError as e:
            print(e)
            create_alert_log(e, api_key, "error_1", 1)

def send_bybit(json_data, api_key, snippet=None):

    query = "SELECT bybit_api_key, bybit_api_secret, testnet FROM bybit_alerts WHERE api_key_id = (SELECT id FROM api_keys WHERE api_key = :api_key);"
    values = {"api_key": api_key}

    results = execute_query(query, values)
    bybit_api_key = results[0][0]
    bybit_api_secret = results[0][1]
    is_testnet = results[0][2]
    is_testnet = (is_testnet == 1)

    check_syntax = True

    if(is_testnet == True):
        bybit_api_url = testnet_url_bybit
    else:
        bybit_api_url = main_url_bybit

    session = HTTP(
            testnet=is_testnet,
            api_key=bybit_api_key,
            api_secret=bybit_api_secret,
    )
    

    print(api_key)
    tp = None
    sl = None
    positions = None

    lowercase_data = {key.lower(): value.lower() if isinstance(value, str) else value for key, value in json_data.items()}

    if lowercase_data.get('version') == '2':
        check_syntax = False
        alert_symbol = lowercase_data['symbol']
        alert_side = lowercase_data['side']
        alert_price = lowercase_data['price']

        if('strategyquantity' in lowercase_data):
            alert_quantity = Decimal(lowercase_data['strategyquantity'])
        else:
            alert_quantity = None

        if('positionsize' in lowercase_data):
            alert_positionSize = Decimal(lowercase_data['positionsize'])
        else:
            alert_positionSize = None

        lowercase_data.clear()  # Remove all previous values


        query = "SELECT accountType, settings FROM alert_configurations WHERE api_key_id = (SELECT id FROM api_keys WHERE api_key = :api_key);"
        values = {"api_key": api_key}

        results = execute_query(query, values)
        alertconf_accountType = results[0][0]
        alertconf_settings = results[0][1]
        alertconf_settings = json.loads(alertconf_settings)

        lowercase_data.update({'symbol': alert_symbol})




        if(alertconf_accountType == "spot"):
            lowercase_data.update({'account': 'spot'})
            lowercase_data.update({'side': alert_side})
            if(alert_side == "buy"):
                if(alertconf_settings["spot"]["BuyOrderType"] == "limit"):
                    lowercase_data.update({'price': alert_price})

                if(alertconf_settings['spot']['BuyQuantityType'] == "coin"):
                    lowercase_data.update({'quantity': alertconf_settings['spot']['BuyQuantity']})

                if(alertconf_settings['spot']['BuyQuantityType'] == "percentage"):
                    lowercase_data.update({'quantity': str(alertconf_settings['spot']['BuyQuantity']) + "%"})

                if(alertconf_settings['spot']['BuyQuantityType'] == "usdt"):
                    lowercase_data.update({'quantity': float(alertconf_settings['spot']['BuyQuantity']) / float(alert_price)})

                if(alertconf_settings['spot']['BuyQuantityType'] == "strategy"):
                    quantity_in_perc =  float(alertconf_settings['spot']['BuyQuantity']) / 100
                    lowercase_data.update({'quantity':   float(alert_quantity) *  quantity_in_perc })

                lowercase_data['quantity'] = str(lowercase_data['quantity'])

            if(alert_side == "sell"):
                if(alertconf_settings['spot']['SellOrderType'] == "limit"):
                    lowercase_data.update({'price': alert_price})

                if(alertconf_settings['spot']['SellQuantityType'] == "coin"):
                    lowercase_data.update({'quantity': alertconf_settings['spot']['SellQuantity']})

                if(alertconf_settings['spot']['SellQuantityType'] == "percentage"):
                    lowercase_data.update({'quantity': str(alertconf_settings['spot']['SellQuantity']) + "%"})

                if(alertconf_settings['spot']['SellQuantityType'] == "usdt"):
                    lowercase_data.update({'quantity': float(alertconf_settings['spot']['SellQuantity']) / float(alert_price)})

                if(alertconf_settings['spot']['SellQuantityType'] == "strategy"):
                    quantity_in_perc =  float(alertconf_settings['spot']['SellQuantity']) / 100
                    lowercase_data.update({'quantity':   float(alert_quantity) *  quantity_in_perc })

                lowercase_data['quantity'] = str(lowercase_data['quantity'])
            
        if(alertconf_accountType == "futures"):
            lowercase_data.update({'account': 'futures'})
            lowercase_data.update({'leverage': alertconf_settings['futures']['Leverage']})
            lowercase_data.update({'margin': alertconf_settings['futures']['MarginType']})

            print(alert_positionSize)
            print(alert_side)
            if (alert_positionSize != 0) and (alert_side != "exit"):
                lowercase_data.update({'side': alert_side})
                if(alert_side == "buy"):
                    if(alertconf_settings["futures"]["LongOrderType"] == "limit"):
                        lowercase_data.update({'price': alert_price})

                    if(alertconf_settings['futures']['LongQuantityType'] == "coin"):
                        lowercase_data.update({'quantity': alertconf_settings['futures']['LongQuantity']})

                    if(alertconf_settings['futures']['LongQuantityType'] == "percentage"):
                        lowercase_data.update({'quantity': str(alertconf_settings['futures']['LongQuantity']) + "%"})

                    if(alertconf_settings['futures']['LongQuantityType'] == "usdt"):
                        lowercase_data.update({'quantity': float(alertconf_settings['futures']['LongQuantity']) / float(alert_price)})

                    if(alertconf_settings['futures']['LongQuantityType'] == "strategy"):
                        quantity_in_perc =  float(alertconf_settings['futures']['LongQuantity']) / 100
                        lowercase_data.update({'quantity':   float(alert_quantity) *  quantity_in_perc })

                    


                    if(alertconf_settings["futures"]["advancedLongSettingsEnabled"] == "on"):
                        if(alertconf_settings['futures']['advancedLongSettings']['LongTPValue'] != ""):
                            if(alertconf_settings['futures']['advancedLongSettings']['LongTPType'] == "percentage"):
                                lowercase_data.update({'tp': str(alertconf_settings['futures']['advancedLongSettings']['LongTPValue']) + "%"})

                            if(alertconf_settings['futures']['advancedLongSettings']['LongTPType'] == "fixed"):
                                lowercase_data.update({'tp': alertconf_settings['futures']['advancedLongSettings']['LongTPValue']})

                            if(alertconf_settings['futures']['advancedLongSettings']['LongTPType'] == "deviation"):
                                lowercase_data.update({'tp': float(alertconf_settings['futures']['advancedLongSettings']['LongTPValue']) + float(alert_price)})

                        if(alertconf_settings['futures']['advancedLongSettings']['LongSLValue'] != ""):
                            if(alertconf_settings['futures']['advancedLongSettings']['LongSLType'] == "percentage"):
                                lowercase_data.update({'sl': str(alertconf_settings['futures']['advancedLongSettings']['LongSLValue']) + "%"})

                            if(alertconf_settings['futures']['advancedLongSettings']['LongSLType'] == "fixed"):
                                lowercase_data.update({'sl': alertconf_settings['futures']['advancedLongSettings']['LongSLValue']})

                            if(alertconf_settings['futures']['advancedLongSettings']['LongSLType'] == "deviation"):
                                lowercase_data.update({'sl': float(alert_price) - float(alertconf_settings['futures']['advancedLongSettings']['LongSLValue'])})


                        if(alertconf_settings['futures']['advancedLongSettings']['TSRetracementRate'] != "0" and alertconf_settings['futures']['advancedLongSettings']['TSRetracementRate'] != "" and alertconf_settings['futures']['advancedLongSettings']['TSRetracementType'] == "rate"):
                            lowercase_data.update({'retracement': str(alertconf_settings['futures']['advancedLongSettings']['TSRetracementRate']) + "%"})

                        if(alertconf_settings['futures']['advancedLongSettings']['TSRetracementValue'] != "0" and alertconf_settings['futures']['advancedLongSettings']['TSRetracementValue'] != "" and alertconf_settings['futures']['advancedLongSettings']['TSRetracementType'] == "value"):
                            lowercase_data.update({'retracement': str(alertconf_settings['futures']['advancedLongSettings']['TSRetracementValue'])})

                        if(alertconf_settings['futures']['advancedLongSettings']['ActivationPriceEnabled'] == "on"):
                            if(alertconf_settings['futures']['advancedLongSettings']['ActivationalPriceType'] == "percentage" and  alertconf_settings['futures']['advancedLongSettings']['ActivationalPriceValue'] != "0" and  alertconf_settings['futures']['advancedLongSettings']['ActivationalPriceValue'] != ""):
                                in_perc =  float(alertconf_settings['futures']['advancedLongSettings']['ActivationalPriceValue']) / 100
                                lowercase_data.update({'activationprice': float(alert_price) * float(in_perc) + float(alert_price)})

                            if(alertconf_settings['futures']['advancedLongSettings']['ActivationalPriceType'] == "fixed" and  alertconf_settings['futures']['advancedLongSettings']['ActivationalPriceValue'] != "0" and  alertconf_settings['futures']['advancedLongSettings']['ActivationalPriceValue'] != ""):
                                lowercase_data.update({'activationprice': float(alert_price) + float(alertconf_settings['futures']['advancedLongSettings']['ActivationalPriceValue'])})

                    lowercase_data['quantity'] = str(lowercase_data['quantity'])

                        

                if(alert_side == "sell"):
                    if(alertconf_settings['futures']['ShortOrderType'] == "limit"):
                        lowercase_data.update({'price': alert_price})

                    if(alertconf_settings['futures']['ShortQuantityType'] == "coin"):
                        lowercase_data.update({'quantity': alertconf_settings['futures']['ShortQuantity']})

                    if(alertconf_settings['futures']['ShortQuantityType'] == "percentage"):
                        lowercase_data.update({'quantity': str(alertconf_settings['futures']['ShortQuantity']) + "%"})

                    if(alertconf_settings['futures']['ShortQuantityType'] == "usdt"):
                        lowercase_data.update({'quantity': float(alertconf_settings['futures']['ShortQuantity']) / float(alert_price)})

                    if(alertconf_settings['futures']['ShortQuantityType'] == "strategy"):
                        quantity_in_perc =  float(alertconf_settings['futures']['ShortQuantity']) / 100
                        lowercase_data.update({'quantity':   float(alert_quantity) *  quantity_in_perc })


                    if(alertconf_settings["futures"]["advancedShortSettingsEnabled"] == "on"):
                        if(alertconf_settings['futures']['advancedShortSettings']['ShortTPValue'] != ""):
                            if(alertconf_settings['futures']['advancedShortSettings']['ShortTPType'] == "percentage"):
                                lowercase_data.update({'tp': str(alertconf_settings['futures']['advancedShortSettings']['ShortTPValue']) + "%"})

                            if(alertconf_settings['futures']['advancedShortSettings']['ShortTPType'] == "fixed"):
                                lowercase_data.update({'tp': alertconf_settings['futures']['advancedShortSettings']['ShortTPValue']})

                            if(alertconf_settings['futures']['advancedShortSettings']['ShortTPType'] == "deviation"):
                                lowercase_data.update({'tp': float(alert_price) - float(alertconf_settings['futures']['advancedShortSettings']['ShortTPValue'])})

                        if(alertconf_settings['futures']['advancedShortSettings']['ShortSLValue'] != ""):
                            if(alertconf_settings['futures']['advancedShortSettings']['ShortSLType'] == "percentage"):
                                lowercase_data.update({'sl': str(alertconf_settings['futures']['advancedShortSettings']['ShortSLValue']) + "%"})

                            if(alertconf_settings['futures']['advancedShortSettings']['ShortSLType'] == "fixed"):
                                lowercase_data.update({'sl': alertconf_settings['futures']['advancedShortSettings']['ShortSLValue']})

                            if(alertconf_settings['futures']['advancedShortSettings']['ShortSLType'] == "deviation"):
                                lowercase_data.update({'sl': float(alert_price) + float(alertconf_settings['futures']['advancedShortSettings']['ShortSLValue'])})

                    lowercase_data['quantity'] = str(lowercase_data['quantity'])
            else:
                ##close position
               
                if(alertconf_settings['futures']['exitCloseAllTPSL'] == "on"):
                     lowercase_data.update({'tp':  'cancel'})
                     lowercase_data.update({'sl':  'cancel'})

                if(alertconf_settings['futures']['ExitQuantityType'] == "coin"):
                        lowercase_data.update({'close': alertconf_settings['futures']['ExitQuantity']})

                if(alertconf_settings['futures']['ExitQuantityType'] == "percentage"):
                        lowercase_data.update({'close': str(alertconf_settings['futures']['ExitQuantity']) + "%"})

                if(alertconf_settings['futures']['ExitQuantityType'] == "usdt"):
                        lowercase_data.update({'close': float(alertconf_settings['futures']['ExitQuantity']) / float(alert_price)})

                if(alertconf_settings['futures']['ExitQuantityType'] == "strategy"):
                        quantity_in_perc =  float(alertconf_settings['futures']['ExitQuantity']) / 100
                        lowercase_data.update({'close':   float(alert_quantity) *  quantity_in_perc })


        
    print(lowercase_data)


    
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

    if 'wait' in lowercase_data:
        time_to_wait = lowercase_data['wait']
        time.sleep(float(time_to_wait))

    print(snippet)

    #validate tradingview message syntax
    missing_keywords = []

    if('cancel' in lowercase_data):
        position_symbol =  lowercase_data['cancel']
    else:
        if("symbol" in lowercase_data):
            position_symbol =  lowercase_data['symbol']
        else:
            create_alert_log("Parameter symbol  missing in tradingview alert", api_key, "error_1", 1)
            sys.exit()

    if 'account' in lowercase_data:
        if(lowercase_data['account'] == 'futures'):
            account_is_futures = True
        else:
            account_is_futures = False
    
    if 'account' not in lowercase_data or account_is_futures:
        if positions is None:  # Fetch only if not already fetched
            positions = session.get_positions(
                category="linear",
                symbol=position_symbol.upper(),
            )
        for position in positions['result']['list']:
            position_side = position['side'].upper()
            if position_side.upper() == 'BUY':
                is_long_position = True
            elif position_side.upper() == 'SELL':
                is_long_position = False

   

    #run this if there is open position
    if ('retracement' in lowercase_data and position_side != "" and "account" not in lowercase_data):
        open_trailing_stop(lowercase_data, session,bybit_api_url)
        check_syntax = False

    if ('cancel' in lowercase_data or 'sl' in lowercase_data or 'tp' in lowercase_data) and position_side not in ("", "NONE"):
        print("RUNNING THIS")
        check_syntax = False
        if('cancel' in lowercase_data):
            if positions is None:  # Fetch only if not already fetched
                positions = session.get_positions(
                    category="linear",
                    symbol=position_symbol.upper(),
                )
            for position in positions['result']['list']:
                position_side = position['side']
                if position_side == "Buy":
                    position_side = "Sell"
                else:
                    position_side = "Buy"

                try:
                    print(session.place_order(
                        category="linear",
                        symbol=position_symbol.upper(),
                        side=position_side,
                        orderType="Market",
                        qty="0",
                        reduceOnly="true",
                        
                    ))
                except Exception as e:
                    1 == 1

            try:
                print(session.cancel_all_orders(
                    category="linear",
                    symbol=position_symbol.upper()
                ))
            except Exception as e:
                1 == 1
            
                    
        coin_price = None

        if('sl' in lowercase_data):
            if(lowercase_data['sl'] == "cancel"):
                sl_price = 0
            else:
                sl_price = lowercase_data['sl']
                symbol = lowercase_data['symbol'].upper()
                if(coin_price == None):
                    coin_price = float(get_btc_price(symbol,bybit_api_url))

                if('%' in sl_price):  
                    print(coin_price)
                    sl_price = caculate_sl_in_perc(sl_price, is_long_position, coin_price)

            try:
                print(session.set_trading_stop(
                    category="linear",
                    symbol=lowercase_data['symbol'].upper(),
                    stopLoss=sl_price,
                    positionIdx=0,
                ))
            except Exception as e:
                print(e)



        if('tp' in lowercase_data):
            if(lowercase_data['tp'] == "cancel"):
                tp_price = 0
            else:
                tp_price = lowercase_data['tp']
                symbol = lowercase_data['symbol'].upper()
                if(coin_price == None):
                    coin_price = float(get_btc_price(symbol,bybit_api_url))

                if('%' in tp_price):  
                    print(coin_price)
                    tp_price = caculate_tp_in_perc(tp_price, is_long_position, coin_price)

            try:
                print(session.set_trading_stop(
                    category="linear",
                    symbol=lowercase_data['symbol'].upper(),
                    takeProfit=tp_price,
                    positionIdx=0,
                ))
            except Exception as e:
                print(e)

    if('close' in lowercase_data and 'symbol' in lowercase_data  and position_side not in ("", "NONE")):
        check_syntax = False
        closeQty = lowercase_data['close']

        if positions is None:  # Fetch only if not already fetched
            positions = session.get_positions(
                category="linear",
                symbol=position_symbol.upper(),
            )
        close_futures_position(lowercase_data['symbol'].upper(), closeQty, session, positions )

    if check_syntax == True:
        if 'account' not in lowercase_data:
            missing_keywords.append('account')

        if 'side' not in lowercase_data:
            missing_keywords.append('side')

        if 'symbol' not in lowercase_data:
            missing_keywords.append('symbol')


        if missing_keywords:
            create_alert_log(f"Missing parameters in tradingview message: {', '.join(missing_keywords)}" + ". Please read setup guide.", api_key, "error_1", 1)
            #print(f"Missing parameters in tradingview message: {', '.join(missing_keywords)}" + ". Please read setup guide.")
            # Perform additional actions if needed
        else:
            # All keywords are present, perform your main actions here
            1 == 1
           # print("All keywords present. Perform main actions.")


    if 'account' in lowercase_data:
        
        account = lowercase_data['account']
        print("account:", account)

    else:
        print("'account' key does not exist in the JSON.")
    OrderType=''
    if account in ['spot', 'futures'] and  'side' in lowercase_data and 'symbol' in lowercase_data:
        
        PriceNum = None
        if 'price' in lowercase_data:
            if lowercase_data['price'] == 'market' :
                PriceType = lowercase_data['price'].upper()
            else:
                PriceType = 'LIMIT'
                PriceNum = lowercase_data['price']
        else:
                PriceType = 'MARKET'


        
        if('quantity' in lowercase_data):
                OrderQty= lowercase_data['quantity']
                if "-" in OrderQty:
                     OrderQty = OrderQty.replace("-", "")
        symbol = lowercase_data['symbol'].upper()
        
         
        OrderSide = lowercase_data['side']
        if(OrderSide == "long" or OrderSide == "buy"):
            OrderSide = "Buy"
        elif OrderSide == "short" or OrderSide == "sell":
            OrderSide =  "Sell"

        if 'accounttype' in lowercase_data:
            account_type =lowercase_data['accounttype']
        else:
            account_type = "UNIFIED"


        if account == 'futures':

            if('usdquantity' in lowercase_data):
                create_alert_log("Usdquantity is only available in spot for buying.", api_key, "error_1", 1)
                sys.exit()

            if 'leverage' in lowercase_data:
                leverage=lowercase_data['leverage']
            else:
                #default leverage
                leverage=10

        
            if 'margin' in lowercase_data:
                if lowercase_data['margin'] == 'cross' or lowercase_data['margin'] == 'crossed':
                    IsIsolated = 0
                else:
                    IsIsolated = 1
            else:
                    IsIsolated = 1
        

            if('type' in lowercase_data):
                if 'take_profit_market' == lowercase_data['type'] or 'stop_market' == lowercase_data['type']:
                    OrderType = lowercase_data['type'].upper()
            else:
                if 'tp' in lowercase_data:
                    tp =lowercase_data['tp']
                if 'sl' in lowercase_data:
                    sl =lowercase_data['sl']


      
            try:
                print(session.switch_margin_mode(
                    category="linear",
                    symbol=symbol,
                    tradeMode=IsIsolated,
                    buyLeverage=str(leverage),
                    sellLeverage=str(leverage),
                ))
            except Exception as e:
                 1 == 1
            try:
                print(session.set_leverage(
                    category="linear",
                    symbol=symbol,
                    buyLeverage=str(leverage),
                    sellLeverage=str(leverage),
                ))
            except Exception as e:
                1 == 1


            tries_counter = 0
            caculate_futures_quantity(OrderQty, session, leverage, symbol, tries_counter, tp, sl, OrderSide, PriceType, PriceNum, bybit_api_url, account_type, api_key, lowercase_data)

        elif account == 'spot':
            if('usdquantity' in lowercase_data):
                OrderQty = lowercase_data['usdquantity']
                if "-" in OrderQty:
                     OrderQty = OrderQty.replace("-", "")
                is_usd_quantity = True
                if(OrderSide == "Sell"):
                    create_alert_log("Usdquantity is only available in spot for buying not selling.", api_key, "error_1", 1)
                    sys.exit()
            else:
                is_usd_quantity = False
            open_spot_order(PriceType, OrderSide,bybit_api_url, symbol, session, PriceNum, OrderQty, is_usd_quantity, account_type, api_key )



    else:
        print("request invalid, missing parms")




 
