class Route:

    def __init__(self, tickers, sides, exchange, profit_margin, fee_per_trade):
        self.tickers = tickers
        self.sides = sides
        self.exchange = exchange
        self.profit_margin = profit_margin
        self.fee_per_trade = fee_per_trade
        self.margin = 0
        self.prices = [0]*len(tickers)
        self.volumes = [0]*len(tickers)
        self.amounts_rec = [0]*len(tickers) # amount of coin received that would be received from executing the n'th trade
        self.amounts_rec_after_fees = [0]*len(tickers) # above but after fees are applied. When using BNB, fees are not subtracted from the amount of the coin received and thus
        self.vol_safety_thresh = 0.20
        self.starting_amount = 15.0 # of US StableCoin e.g USDT, USDC, BUSD 
        #self.margin = margin

        #self.prices = prices
        #self.amount_rec = amount_rec
        #self.amount_rec_after_fees = amount_rec_after_fees
        #self.volumes = volumes
        #self.profit
    @property
    def profitable(self):
        return (self.margin >= 1 + (1 * profit_margin) and not self.margin >= 2)

    def visualize(self):
        print("Visualizing Route")
        route_viz = []
        route_viz.append("Route: ")
        for idx, ticker in enumerate(self.tickers):
           route_viz.append("{}:{} ".format(ticker['symbol'], self.sides[idx]))

        route_viz.append("|| margin = {}".format(self.margin))
        print(*route_viz)
 
    
    def refresh(self):



       # to calculate the margin, the actual amount received(above) and the amount received after fees must be kept seperate
        # check if enough origin 
        

        # Series of loops that iterate over each pair in the arbitrage route to calculate the best price avaliable while still having enough volume
        # to fill the trades.
        #print(*self.tickers)
        anchor_coins = ['BUSD', 'USDT', 'USDC']
        buys = []
        sells = []
        if not any(x in self.tickers[0]['symbol'] for x in anchor_coins):
            print("First ticker does not contain any anchor coins: " + " || ".join(anchor_coins))
            for anchor in anchor_coins:
                symbol_buy = self.tickers[0]['symbol'].split('/')[1] + '/' + anchor
                symbol_sell = anchor + '/' + self.tickers[0]['symbol'].split('/')[1]
                try:
                    buy_ticker = self.exchange.fetch_ticker(symbol_buy)
                    print(buy_ticker['symbol'])
                    # check if tickers valid
                    if float(buy_ticker['info']['bidPrice']) > 0.00000000 and int(buy_ticker['info']['count']) > 5:
                        buys.append(buy_ticker)

                except:
                    sell_ticker = self.exchange.fetch_ticker(symbol_sell)
                    print(sell_ticker['symbol'])
                    if float(sell_ticker['info']['bidPrice']) > 0.00000000 and int(sell_ticker['info']['count']) > 5:
                        sells.append(sell_ticker)

            try:
                lowest_ask = buys[0]
                for ticker in buys:
                    print(ticker['symbol'])
                    if not ticker == None:
                        if ticker['ask'] < lowest_ask['ask']:
                            lowest_ask = ticker

                if lowest_ask is not None:
                    print("Adding anchor conversion: " + lowest_ask['symbol'])
                    # Insert the anchor to original origin conversion ticker
                    self.tickers.insert(0, lowest_ask)
                    self.sides.insert(0, 'buy')
                    
                    # On the new last ticker, sell the original ending coin for the new origin anchor coin by flipping the side of the anchor conversion ticker
                    self.tickers.append(lowest_ask)
                    self.sides.append('sell')


            except:
                try:
                    highest_bid = sells[0]
                    for ticker in sells:
                        print(ticker['symbol'])
                        if not ticker == None:
                            if ticker['bid'] > highest_bid['bid']:
                                highest_bid = ticker

                    print("Adding anchor conversion: " + highest_bid['symbol'])
                    # Insert the anchor to original origin conversion ticker
                    self.tickers.insert(0, highest_bid)
                    self.sides.insert(0, 'sell')
                    
                    # On the new last ticker, sell the original ending coin for the new origin anchor coin by flipping the side of the anchor conversion ticker
                    self.tickers.append(highest_bid)
                    self.sides.append('buy')


                
                except:
                    print("ERROR: No route from an anchor coin could be found")
                    return

            # visualise modified route
            self.visualize()
        else:
            for anchor in anchor_coins:
                # ticker[0] always set to buy even if it is the base of a pair and should be sold
                if self.tickers[0]['symbol'].split('/')[0] == anchor:
                    self.sides[0] = 'sell'
                    print("Switching 1st ticker to sell")
        
        book_sides = []
        # depending on the side of the trade, retrieve orderbook that contains asks or bids
        for side in self.sides:
            if side == "buy":
                book_sides.append("asks")
            else:
                book_sides.append("bids")
        
        self.prices = [0]*len(self.tickers)
        self.volumes = [0]*len(self.tickers)
        self.amounts_rec = [0]*len(self.tickers) # amount of coin received from executing the n'th trade, actual coin determined by either side of ticker
        self.amounts_rec_after_fees = [0]*len(self.tickers) # above but after fees are applied. When using BNB, fees are not subtracted from the amount of the coin received and thus

        for pair_idx, pair in enumerate(self.tickers):
            # iterate over order book
            for idx, order in enumerate(self.exchange.fetch_order_book(self.tickers[pair_idx]['symbol'])[book_sides[pair_idx]]): 
                if pair_idx == 0:
                    self.amounts_rec[pair_idx] = self.starting_amount
                else:
                    self.amounts_rec[pair_idx] = self.amounts_rec[pair_idx-1]
                if self.sides[pair_idx] == 'buy':
                    # use the coin received in the previous ticker to buy the other coin in the current ticker
                    # selling quote, buying base
                    self.amounts_rec[pair_idx] = self.amounts_rec[pair_idx]/order[0]
                else:
                    # sell the coin received in the previous ticker to receive the other coin in the current ticker
                    # buying quote, selling base
                    self.amounts_rec[pair_idx] = self.amounts_rec[pair_idx]*order[0]

                # apply fee
                self.amounts_rec_after_fees[pair_idx] = self.amounts_rec[pair_idx]
                #print(self.amounts_rec_after_fees[pair_idx])
                print("Applying Fee")
                self.amounts_rec_after_fees[pair_idx] -= self.amounts_rec_after_fees[pair_idx] * self.fee_per_trade

                # The coin in the order[1] and the coin in amounts_rec are the same
                if self.sides[pair_idx] == 'buy':
                    if order[1] > (self.amounts_rec[pair_idx] + self.amounts_rec[pair_idx]*self.vol_safety_thresh):
                        self.prices[pair_idx] = order[0]
                        self.volumes[pair_idx] = order[1]
                        #print(self.amounts_rec_after_fees[pair_idx])
                        break

                    else:
                        print("{} Not enough volume: This order has an amount of: {} which is less than the threshold of: {}"
                              .format(pair['symbol'], str(order[1]), self.amounts_rec[pair_idx] + self.amounts_rec[pair_idx]*self.vol_safety_thresh))
                        continue
                
                # The coin in the order[1] and the coin in amounts_rec are NOT the same
                else:
                    # Convert order amount in the base currency to the order amount equivalent in the quote currency
                    # This is because amounts_rec is in the quote currency.
                    converted_amount = (order[0]*order[1])
                    if converted_amount > (self.amounts_rec[pair_idx] + self.amounts_rec[pair_idx]*self.vol_safety_thresh):
                        self.prices[pair_idx] = order[0]
                        self.volumes[pair_idx] = order[1]
                        #print(self.amounts_rec_after_fees[pair_idx])
                        break

                    else:
                        print("{} Not enough volume: This order has an amount of: {} which is less than the threshold of: {}"
                              .format(pair['symbol'], converted_amount, self.amounts_rec[pair_idx] + self.amounts_rec[pair_idx]*self.vol_safety_thresh))
                        continue


 
                       
        self.margin = self.amounts_rec_after_fees.pop()/self.starting_amount
        return


    def execute(self):
        self.refresh()
        if profitable:
            for i in range(len(route.tickers)):
                ticker = route.tickers[i]
                # if trade_action == buy
                if route.sides[i] == 'buy':
                    continue
                    exchange.create_limit_buy_order(ticker['symbol'], route.amounts_rec[i], price[i])
                else: 
                    continue
                    exchange.create_limit_sell_order(ticker['symbol'], trade_amount_btc, price[i])
        else:
            print("EXECUTION ERROR: NO LONGER PROFITABLE")
