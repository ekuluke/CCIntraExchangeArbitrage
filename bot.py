import tqdm 
import pandas as pd
import numpy as np
import ccxt
pd.options.display.float_format = '{:.10f}'.format
pd.options.display.precision = 5

# GLOBALS

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
            
            # buy, convert amount
            amount = amount / ticker['ask'] # divide by ask so that the bid(buy order) gets filled instantly
            # apply fee to new amount 
            amount = amount - amount * fee_per_trade
        elif not ticker['bid'] <= 0:
            # sell
            amount = amount * ticker["bid"]  # multiply by bid so that the ask(sell order) gets filled instantly     
            amount = amount - amount * fee_per_trade 

        #print(amount)
    

    #print("profit margin: {}".format(amount/origin_amount))
    return amount / origin_amount

def identify_arbi(tickers, exchange, amount_of_origin, vol_safety_thresh=0.1, profit_margin=0.0005):
    # amount of origin = amount of the first quote currency(origin) that will be traded 
    # vol_safety_tresh = additional percentage of an ask's amount that acts as a threshold in an effort to prevent slippage
    # where the quote symbol is the key
    cross_rate = 0
    # TODO: CALCULATE BEFORE RELEASE
    fee_per_trade = 0.00075
    arbi_routes = []
    trade_action, trade_action_2, trade_action_3 = True, True, True

    for ticker in tickers.values():
        if ticker["symbol"].split('/')[1] != 'BTC':
            #continue
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
            if margin > 1:
                print("route: {}:{} -> {}:{} -> {}:{} || margin = {}".format(ticker["symbol"], trade_action, ticker_2["symbol"], trade_action_2, ticker_3["symbol"], trade_action_3, margin))
            if margin >= 1 + (1 * profit_margin) and not margin >= 2:
                print("Adding to arbi_routes")
                #TODO: Refactor route into a class for much greater readability
                arbi_routes.append((route, trade_actions, margin))

            if len(arbi_routes) % 10 == 0:
                #for route in sorted(arbi_routes, key=lambda x: x[2]):
                for route in arbi_routes[-10:]:
                    if route[0][0]["symbol"].split('/')[1] != 'BTC':
                        continue
                    print("trying route")
                    try_route(route, exchange, profit_margin, fee_per_trade)

#def get_vol_by_price(ticker, symbol_1_vol):

def try_route(route, exchange, profit_margin, fee_per_trade):
    vol_safety_thresh = 0.20
    margin_lost = False
    trade_amount_aud = 0.001 # amount, in aud, of the first trade. Will be converted to btc below
    for idx, order in enumerate(exchange.fetch_order_book('BTC/AUD')['asks']):
        # if the order's ask is less than the trade_amount_aud, continue loop with the next ask price
        # To summarise, this statement checks to see if the order at this price does not have enough volume, and thus,
        # is lower in value than the desired amount set in trade_amount_aud. 
        origin_amount = trade_amount_aud/order[0]
        if origin_amount < order[1] + order[1] * vol_safety_thresh:
            break

    actions = []
    sides = []
    # depending on the trade action, retrieve orderbook that contains asks or bids
    for action in route[1]:
        if action == True:
            actions.append("asks")
        else:
            actions.append("bids")
    
    for action in route[1]:
        if action == True:
            sides.append("buy")
        else:
            sides.append("sell")


    price = [0]*3
    volume = [0]*3
    amount_rec = [0]*3 # amount of coin received that would be received from executing the n'th trade
    print(origin_amount)
    

    # Series of loops that iterate over each pair in the arbitrage route to calculate the best price avaliable while still having enough volume
    # to fill the trades.
    for idx, order in enumerate(exchange.fetch_order_book(route[0][0]["symbol"])[actions[0]]):
        amount_rec[0] = origin_amount/order[0]
        print(order[1])
        print(amount_rec[0] + amount_rec[0]*vol_safety_thresh)
        # if there is enough volume to make the arbi
        if order[1] > (amount_rec[0] + amount_rec[0]*vol_safety_thresh): 
            price[0] = order[0]
            volume[0] = order[1]
            # if not, go to the next closest price in the order book 
        else:
            print("Not enough volume at " + str(order[1]))
            continue

        for idx_2, order_2 in enumerate(exchange.fetch_order_book(route[0][1]["symbol"])[actions[1]]):
            if sides[1] == 'buy':
                # received coin on previous ticker becomes the quote coin on the this ticker
                amount_rec[1] = amount_rec[0]/order_2[0]
                if order_2[1] > (amount_rec[1] + amount_rec[1]*vol_safety_thresh):
                    price[1] = order_2[0]
                    volume[1] = order_2[1]

                else:
                    print("Not enough volume at " + str(order_2[1]))
                    continue
            # received coin on previous ticker becomes the base coin on the this ticker
            else:
                amount_rec[1] = amount_rec[0]*order_2[0]
                if order_2[1] > (amount_rec[1] + amount_rec[1]*vol_safety_thresh):
                    price[1] = order_2[0]
                    volume[1] = order_2[1]

                else:
                    print("Not enough volume at " + str(order_2[1]))
                    continue



            for idx_3, order_3 in enumerate(exchange.fetch_order_book(route[0][2]["symbol"])[actions[2]]):
                print('hi3')
                if sides[2] == 'buy':
                    amount_rec[2] = amount_rec[1]/order_3[0]
                    if order_3[1] > (amount_rec[2] + amount_rec[2]*vol_safety_thresh):
                        price[2] = order_3[0]
                        volume[2] = order_3[1]

                    else:
                        print("Not enough volume at " + str(order_3[1]))
                        continue
                else:
                    amount_rec[2] = amount_rec[1]*order_3[0]
                    if order_3[1] > (amount_rec[2] + amount_rec[2]*vol_safety_thresh):
                        price[2] = order_3[0]
                        volume[2] = order_3[1]

                    else:
                        print("Not enough volume at " + str(order_3[1]))
                        continue

                # check if margin is enough
                # pass in route tickers, route trade actions and fee_per_trade
                margin = get_route_margin(route[0], route[1], fee_per_trade)
                print(margin)
                if margin >= 1 + (1 * profit_margin) and not margin >= 2:
                    #arbi_routes.append((route, trade_actions, margin))
                    
                    # Print some info about the calculated trades in the route
                    print("Preparing to execute route: {}:{} -> {}:{} -> {}:{} || margin = {}".format(route[0][0]["symbol"], sides[0], route[0][1]["symbol"], sides[1], route[0][2]["symbol"], sides[2], margin))
                    print("starting with an origin amount of: {} {} ".format(origin_amount, route[0][0]['symbol'].split('/')[1]))
                    for i in range(len(sides)):
                        if i != 0:
                           quote_amount = amount_rec[i-1]

                        else:
                            quote_amount = origin_amount 

                        if sides[i] == 'buy':
                            print("Buying {} {} with {} {}".format(amount_rec[i], route[0][i]['symbol'].split('/')[0], quote_amount,
                                 route[0][i]['symbol'].split('/')[1]))
                            print("Buying 1 {} at a price of {} {}".format(route[0][i]['symbol'].split('/')[0], price[i], route[0][i]['symbol'].split('/')[1]))

                        else: 
                            print("Selling {} {} for {} {}".format(amount_rec[i], route[0][i]['symbol'].split('/')[0], quote_amount,
                                 route[0][i]['symbol'].split('/')[1]))
                            print("Selling 1 {} at a price of {} {}".format(route[0][i]['symbol'].split('/')[0], price[i], route[0][i]['symbol'].split('/')[1]))

                    # Iterate over tickers in route, executing trades
                    for i in range(len(route[0])):
                        ticker = route[0][i]
                        # if trade_action == buy
                        if route[1][i] == True:
                            print("place a buy order for " + ticker['symbol'] + 'with a base currency quantity of: ' +  str(amount_rec[i]) +
                                 "at a price of: " + str(price[i]) + '?')
                            #exchange.create_limit_buy_order(ticker['symbol'], amount_rec[i], price[i])
                        else: 
                            print("place a sell order for " + ticker['symbol'] + 'with a base currency quantity of: ' +  str(amount_rec[i]) +
                                 "at a price of: " + str(price[i]) + '?')
                            #exchange.create_limit_sell_order(ticker['symbol'], trade_amount_btc, price[i])
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


