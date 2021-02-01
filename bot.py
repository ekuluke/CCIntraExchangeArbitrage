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
			if (margin / 1) >= profit_margin and not margin >= 2:
				print("Adding to arbi_routes")
				arbi_routes.append((route, trade_actions, margin))
				if len(arbi_routes) > 10:
					for route in sorted(arbi_routes, key=lambda x: x[2]):
						if route[0][0]["symbol"].split('/')[1] != 'BTC':
							continue
						try_route(route)

def aud_to_ticker(aud_amount, ticker):
	btc_aud = exchange.fetch_ticker('BTC/AUD') # btc/aud
	trade_amount_btc = trade_amount_aud * btc_aud['bid']
	trade_amount_ticker = 0 # 0.0001 aud to the quote symbol on the first ticker
	try:
		get_tickers_with_curr(route[0][0]["symbol"].split('/')[1])
	except:
		pass

def try_route(route, amount_to_trade):
	vol_safety_thresh = 0.20
	margin_lost = False
	trade_amount_aud = 0.0001
	btc_aud = exchange.fetch_ticker('BTC/AUD') # btc/aud
	trade_amount_btc = trade_amount_aud * btc_aud['bid']
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
	for idx, ask in enumerate(exchange.fetch_order_book(route[0][0]["symbol"])[action[0]]):
		if margin_lost:
			break
		if ask[1] <= (ask[1] + ask[1]*vol_safety_thresh): # check if enough volume exists to make the arbi
			print("Not enough volume at " + str(ask[1]))
			continue
		price[0] = ask[0]
		for idx_2, ask_2 in enumerate(exchange.fetch_order_book(route[0][1]["symbol"])[action[1]]):
			if margin_lost:
				break
			if ask_2[1] <= (ask_2[1] + ask_2[1]*vol_safety_thresh):
				continue
			price[1] = ask[1]
			for idx_3, ask_3 in enumerate(exchange.fetch_order_book(route[0][2]["symbol"])[action[2]]):
				if margin_lost:
					break
				if ask_3[1] <= (ask_3[1] + ask_3[1]*vol_safety_thresh):
					continue
				if route[0][3]["ask"] != ask_3[0]:
					route[0][3]["ask"] = ask_3[0]
					recalc = True	

				if recalc == True:
					margin = get_route_margin(route[0], trade_actions, fee_per_trade)	
					print("route: {}:{} -> {}:{} -> {}:{} || margin = {}".format(ticker["symbol"], trade_actions[0], ticker_2["symbol"], trade_actions[1], ticker_3["symbol"], trade_actions[2], margin))
					if (margin / 1) >= profit_margin:
						#arbi_routes.append((route, trade_actions, margin))
						print("executing_trade")
						#execute_trade(())
					else: 
						print("Margin lost when recalculating, moving to next route")
						margin_lost = True
						break



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


