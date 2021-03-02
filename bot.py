import tqdm 
import pandas as pd
import numpy as np
import ccxt
pd.options.display.float_format = '{:.10f}'.format
pd.options.display.precision = 5

def get_high_vol_pairs(exchange, vol=100000):
    #print(vars(exchange))
    tickers = exchange.fetch_tickers()
    #print(tickers)
    for key, ticker in list(tickers.items()):
        if ticker["quoteVolume"] < vol:
            del tickers[key]
    
    return tickers

def	get_tickers_with_quote(symbol, tickers):
    quote = symbol.split('/')[1]
    print("Getting pairs that can be bought with: " + quote)
    for ticker in tickers.values():
        if ticker["symbol"].split('/')[0] is quote:
            #print(ticker["symbol"])
            tickers.append(ticker) 

    #print(tickers)
    return tickers

def get_tickers_with_base(symbol, tickers):
    tickers_with_base = {}
    base = symbol.split('/')[0]
    print("Getting pairs that can be bought with: " + base)
    for ticker in tickers.values():
        if ticker["symbol"].split('/')[1] == base:
            print("Found pair: " + ticker["symbol"] + " can be bought with this base: " + base)
            tickers_with_base[ticker['symbol']] = ticker

    return tickers_with_base

def get_tickers_with_curr(curr, tickers, origin_to_exclude):
    # origin needs to be excluded so that this does not return the first ticker which the curr is found in
    # returns ticker pairs that are curr/x or x/curr
    tickers_with_curr = {}
    print("Getting pairs that can be bought with: " + curr)
    for ticker in tickers.values():
        if (curr == ticker["symbol"].split('/')[0] or curr == ticker["symbol"].split('/')[1]) and origin_to_exclude != ticker["symbol"] :
            print("Found pair: " + ticker["symbol"] + " contains this currency: " + curr)
            tickers_with_curr[ticker['symbol']] = ticker

    return tickers_with_curr

def get_route_margin(tickers, trade_actions, fee_per_trade):
    origin_amount = 1
    amount = origin_amount
    #print(trade_actions)
    for count, ticker in enumerate(tickers):
        #print(*ticker.values())
        if trade_actions[count] == True and not ticker['ask'] <= 0:
            
            # buy
            amount = amount / (ticker['ask'] - (ticker["ask"] * fee_per_trade)) # divide by ask so that the bid(buy order) gets filled instantly
        elif not ticker['bid'] <= 0:
            # sell
            amount = amount * (ticker["bid"] - (ticker["bid"] * fee_per_trade)) # multiply by bid so that the ask(sell order) gets filled instantly     

    return amount / origin_amount

def identify_arbi(tickers, exchange, amount_of_origin, vol_safety_thresh=0.1, profit_margin=0.005):
    # amount of origin = amount of the first quote currency(origin) that will be traded 
    # vol_safety_tresh = additional percentage of an ask's amount that acts as a threshold in an effort to prevent slippage
    # where the quote symbol is the key
    fee_per_trade = 0.0075
    cross_rate = 0
    arbi_routes = []
    trade_action, trade_action_2, trade_action_3 = True, True, True

    for ticker in tickers.values():
        if float(ticker['info']['bidPrice']) <= 0.00000000:
            continue
        origin = ticker["symbol"]
        print("Finding routes for " + ticker["symbol"])
        trade_action = True
        for ticker_2 in get_tickers_with_curr(ticker["symbol"].split('/')[0], tickers, origin).values():
            if float(ticker_2['info']['bidPrice']) <= 0.00000000:
                print('corrupted ticker')
                continue
            if ticker_2["symbol"].split('/')[1] == ticker["symbol"].split('/')[0]:
                trade_action_2 = True
            elif ticker_2["symbol"].split('/')[0] == ticker["symbol"].split('/')[0]:            
                trade_action_2 = False
            #print("route: {}:{} -> {}:{} ->".format(ticker["symbol"], trade_action, ticker_2["symbol"], trade_action))
            if(ticker["symbol"].split('/')[0] != ticker_2["symbol"].split('/')[0]):
                try:
                    ticker_3 = exchange.fetch_ticker(ticker["symbol"].split('/')[1] + '/' + ticker_2["symbol"].split('/')[0])
                    trade_action_3 = True
                except:
                    try: 
                        ticker_3 = exchange.fetch_ticker( ticker_2["symbol"].split('/')[0] + '/' + ticker["symbol"].split('/')[1])
                        trade_action_3 = False
                    except:
                        continue
            elif(ticker["symbol"].split('/')[0] != ticker_2["symbol"].split('/')[1]):
                try:
                    ticker_3 = exchange.fetch_ticker(ticker["symbol"].split('/')[1] + '/' + ticker_2["symbol"].split('/')[1])
                    trade_action_3 = True
                except:
                    try:
                        ticker_3 = exchange.fetch_ticker(ticker_2["symbol"].split('/')[1] + '/' + ticker["symbol"].split('/')[1])
                        trade_action_3 = False
                    except:
                        continue
            else:
                continue

            if float(ticker_2['info']['bidPrice']) <= 0.00000000:
                continue
            #print("route: {}:{} -> {}:{} -> {}:{}".format(ticker["symbol"], trade_action, ticker_2["symbol"], trade_action_2, ticker_3["symbol"], trade_action_3))
            route = [ticker, ticker_2, ticker_3]
            trade_actions = [trade_action, trade_action_2, trade_action_3]
            margin = get_route_margin(route, trade_actions, fee_per_trade)    
            print("route: {}:{} -> {}:{} -> {}:{} || margin = {}".format(ticker["symbol"], trade_action, ticker_2["symbol"], trade_action_2, ticker_3["symbol"], trade_action_3, margin))
            if margin >= 1 + (1 * profit_margin) and not margin >= 2:
                print("Adding to arbi_routes")
                arbi_routes.append((route, trade_actions, margin))

                if len(arbi_routes) % 10 == 0:
                    #for route in sorted(arbi_routes, key=lambda x: x[2]):
                    for route in arbi_routes[-10:]:
                        if route[0][0]["symbol"].split('/')[1] != 'BTC':
                            continue
                        print("trying route")
                        try_route(route, exchange, profit_margin)

def convert_amount(order, quote_amount):
    # converts the quote amount into the base currency amount
    base_amount = quote_amount * order[0]
    return base_amount

#def get_vol_by_price(ticker, symbol_1_vol):

def try_route(route, exchange, profit_margin):
    vol_safety_thresh = 0.20
    margin_lost = False
    trade_amount_aud = 0.001 # amount, in aud, of the first trade. Will be converted to btc below
    for idx, order in enumerate(exchange.fetch_order_book('BTC/AUD')['asks']):
        convert_amount(order, trade_amount_aud)
        # if the order's ask is less than the trade_amount_aud, continue loop with the next ask price
        # To summarise, this statement checks to see if the order at this price does not have enough volume, and thus,
        # is lower in value than the desired amount set in trade_amount_aud 
        order_value = order[0] * order[1]
        if order[0] * order[1] < trade_amount_aud:
            continue
        else:
            btc_amount = order
    # recalculate current cross rate for higher accuracy
    recalc = False
    actions = []

    # depending on the trade action, retrieve orderbook that contains asks or bids
    for action in route[1]:
        if action == True:
            actions.append("asks")
        else:
            actions.append("bids")
    
    price = [3]
    volume = [3]

    # loop over each orderbook in the route, checking if there is enough volume to safely execute the tade
    for idx, order in enumerate(exchange.fetch_order_book(route[0][0]["symbol"])[actions[0]]):
        print('hi')
        convert_amount(order, )
        if order[1] <= (order[1] + order[1]*vol_safety_thresh): # check if enough volume exists to make the arbi
            print("Not enough volume at " + str(order[1]))
            continue
        price[0] = order[0]
        volume[0] = order[1]
        for idx_2, order_2 in enumerate(exchange.fetch_order_book(route[0][1]["symbol"])[actions[1]]):
            print('hi2')
            if order_2[1] <= (order_2[1] + order_2[1]*vol_safety_thresh):
                print("Not enough volume at " + str(order_2[1]))
                continue
            price[1] = order_2[0]
            volume[1] = order_2[1]
            for idx_3, order_3 in enumerate(exchange.fetch_order_book(route[0][2]["symbol"])[actions[2]]):
                print('hi3')
                if order_3[1] <= (order_3[1] + order_3[1]*vol_safety_thresh):
                    print("Not enough volume at " + str(order_3[1]))
                    continue
                price[2] = order_3[0]
                volume[2] = order_3[1]
                # check if margin is enough
                margin = get_route_margin(route[0], trade_actions, fee_per_trade)
                print(margin)
                if margin >= 1 + (1 * profit_margin) and not margin >= 2:
                    #arbi_routes.append((route, trade_actions, margin))
                    trade_amount_aud = 0.0001
                    btc_aud = exchange.fetch_ticker('BTC/AUD') # btc/aud
                    trade_amount_btc = trade_amount_aud * btc_aud['bid']
                    tickers = (ticker["symbol"], ticker_2["symbol"], ticker_3["symbol"])
                    for i in range(len(tickers)):
                        print(exchange.fetch_order_book(tickers[i]["symbol"]))
                        if trade_actions[i] == True:
                            print("placing a buy order for " + trade_amount_btc + " btc at: " + price[i])
                            #exchange.create_limit_buy_order(tickers[i]["symbol"], trade_amount_btc, price[i])
                        else: 
                            print("placing a sell order for " + trade_amount_btc + " btc at: " + price[i])
                            #exchange.create_limit_sell_order(tickers[i]["symbol"], trade_amount_btc, price[i])
                    print("executing_trade")

                    #execute_trade(())
                else: 
                    print("Margin not sufficient for : route: {}:{} -> {}:{} -> {}:{} || margin = {}".format(ticker["symbol"], trade_actions[0], ticker_2["symbol"], trade_actions[1], ticker_3["symbol"], trade_actions[2], margin))
                    return


exchange_id = 'binance'
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    'apiKey': 'mEW9rhCUsabhAoHEBr7IbHAQPC9xRlVsKIofMR9kJlua5dT4UUTyrdzgErJAQdT5',
    'secret': 'ow8hKxmPI9SDFrU3YYj5YZ3gGtYycsbQhetlua0vGZsCvbni7SWYPQA8ltJ9cuuA',
    'timeout': 30000,
    'enableRateLimit': True,
    })
t_frame = '1m'
header = ['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
symb = 'ETH/BTC'
filename = '{}-{}2020.csv'.format(symb.replace('/','-'),t_frame)
markets = exchange.load_markets()

print(exchange.has['fetchTickers'])
high_vol_pairs = get_high_vol_pairs(exchange, vol = 10000)
identify_arbi(high_vol_pairs, exchange, 1)


