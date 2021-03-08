import tqdm 
import pandas as pd
import numpy as np
import ccxt
import time
import multiprocessing as mp
from inputimeout import inputimeout, TimeoutOccurred
from route import Route
pd.options.display.float_format = '{:.10f}'.format
pd.options.display.precision = 5

def get_high_vol_pairs(exchange, vol=25):
    #print(vars(exchange))
    tickers = exchange.fetch_tickers()
    #print(tickers)
    for key, ticker in list(tickers.items()):
        if ticker["quoteVolume"] < vol:
            del tickers[key]
        elif ticker["baseVolume"] < vol:
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

def get_tickers_with_curr(curr,origin_to_exclude):
    # origin needs to be excluded so that this does not return the first ticker which the curr is found in
    # returns ticker pairs that are curr/x or x/curr
    tickers_with_curr = {}
    #print("Getting pairs that can be bought with: " + curr)
    for ticker in high_vol_tickers.values():
        if (curr == ticker["symbol"].split('/')[0] or curr == ticker["symbol"].split('/')[1]) and origin_to_exclude != ticker["symbol"] :
            #print("Found pair: " + ticker["symbol"] + " contains this currency: " + curr)
            tickers_with_curr[ticker['symbol']] = ticker

    return tickers_with_curr

def get_estimate_route_margin(tickers, trade_actions, fee_per_trade):
    origin_amount = 1
    amount = origin_amount
    #print(trade_actions)
    for count, ticker in enumerate(tickers):
        #print(*ticker.values())
        #if 'NGN' in ticker['symbol']:
        #    print(*ticker.values())
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


    # GLOBALS

def identify_arbi(exchange, amount_of_origin, vol_safety_thresh=0.1, profit_margin=0.002):
    # amount of origin = amount of the first quote currency(origin) that will be traded 
    # vol_safety_tresh = additional percentage of an ask's amount that acts as a threshold in an effort to prevent slippage
    # where the quote symbol is the key

    global processes_paused
    processes_paused = False
    cross_rate = 0
    # TODO: CALCULATE BEFORE RELEASE

    if __name__ ==  '__main__':
        with mp.Pool(8) as pool:
            event = mp.Event()
            pool.map(check_if_arbitrage_exists, high_vol_tickers.values())



def check_if_arbitrage_exists(ticker):
    while(processes_paused == True):
        time.sleep(1)
    fee_per_trade = 0.000750
    profit_margin = 0.0001
    trade_action, trade_action_2, trade_action_3 = True, True, True
    if float(ticker['info']['bidPrice']) <= 0.00000000 or int(ticker['info']['count']) < 5:
        #print('ERROR: corrupted ticker: ' + ticker['symbol'])
        return
    origin = ticker["symbol"]
    print("Finding routes for " + ticker["symbol"])
    trade_action = True
    for ticker_2 in get_tickers_with_curr(ticker["symbol"].split('/')[0], origin).values():
        if float(ticker_2['info']['bidPrice']) <= 0.00000000 or int(ticker_2['info']['count']) < 5:
            #print('ERROR: corrupted ticker: ' + ticker_2['symbol'])
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

        if float(ticker_3['info']['bidPrice']) <= 0.00000000 or int(ticker_3['info']['count']) < 5:
            #print('ERROR: corrupted ticker: ' + ticker_3['symbol'])
            continue

        #print("route: {}:{} -> {}:{} -> {}:{}".format(ticker["symbol"], trade_action, ticker_2["symbol"], trade_action_2, ticker_3["symbol"], trade_action_3))
        route_tickers = [ticker, ticker_2, ticker_3]
        trade_actions = [trade_action, trade_action_2, trade_action_3]
        margin = get_estimate_route_margin(route_tickers, trade_actions, fee_per_trade)
        if margin > 1:
            print("route: {}:{} -> {}:{} -> {}:{} || margin = {}".format(ticker["symbol"], trade_action, ticker_2["symbol"], trade_action_2, ticker_3["symbol"], trade_action_3, margin))
        if margin >= 1 + (1 * profit_margin) and not margin >= 2:
            #str_routes.append(("route: {}:{} -> {}:{} -> {}:{} || margin = {}".format(ticker["symbol"], trade_action, ticker_2["symbol"], trade_action_2, ticker_3["symbol"], trade_action_3, margin), route, trade_actions, margin))
            print("trying route")
            #for route in str_routes:
            #route = (route[0], route[1], route[2], get_estimate_route_margin(route[1],route[2], fee_per_trade))
            #str_routes.sort(key=lambda x: x[3], reverse=True) 
            #print(*str_routes[0])
            #TODO: Refactor route into a class for much greater readability
            #arbi_routes.append((route, trade_actions, margin))
            #route = (route_tickers, trade_actions, margin)
            sides = []
            for action in trade_actions:
                if action == True:
                    sides.append("buy")
                else:
                    sides.append("sell")

            route = Route(route_tickers, sides, exchange, profit_margin, fee_per_trade)
            try_route(route)
     
        
#def get_vol_by_price(ticker, symbol_1_vol):
    
def try_route(route):
    
    route.refresh()
    route.visualize()
    print("Profitable: " + str(route.profitable))
    if route.profitable == True:
        
        if processes_paused == False:
            processes_paused = True 
            # wait for processes to complete before asking for input
            time.sleep(3)

        #arbi_routes.append((route, trade_actions, margin))
        
        # Print some info about the calculated trades in the route
        
        # Visualize
        for i in range(len(route.tickers)):
            ticker = route.tickers[i]
            # if trade_action == buy
            if route.sides[i] == 'buy':
                print("place a buy order for " + ticker['symbol'] + 'with a base currency quantity of: ' +  str(route.amounts_rec[i]) +
                     "at a price of: " + str(route.prices[i]) + '?')
                #exchange.create_limit_buy_order(ticker['symbol'], route.amounts_rec[i], price[i])
            else: 
                print("place a sell order for " + ticker['symbol'] + 'with a base currency quantity of: ' +  str(route.amounts_rec[i]) +
                     "at a price of: " + str(route.prices[i]) + '?')
                #exchange.create_limit_sell_order(ticker['symbol'], trade_amount_btc, price[i])
        
        try:
            i = inputimeout("execute trades: y/n", 2)
        except TimeoutOccurred:
            try_route(route)

        if i == 'y':
            route.execute()

        else:
            print("Input was not y: skipping trade")


        # Resume Processes
        processes_paused = False
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
high_vol_tickers = get_high_vol_pairs(exchange)
identify_arbi(exchange,1)




