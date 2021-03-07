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
        return (route.margin >= 1 + (1 * profit_margin) and not route.margin >= 2)

    def visualize(self):
        print("Visualizing Route")
        route_viz = []
        route_viz.append("Route: ")
        for idx, ticker in enumerate(self.tickers):
           route_viz.append("{}:{} ".format(ticker['symbol'], self.sides[idx]))

        route_viz.append("|| margin = {}".format(self.margin))
        print(*route_viz)
 
    
    def refresh(self):
        for idx, order in enumerate(self.exchange.fetch_order_book('BTC/AUD')['asks']):
            # if the order's ask is less than the trade_amount_aud, continue loop with the next ask price
            # To summarise, this statement checks to see if the order at this price does not have enough volume, and thus,
            # is lower in value than the desired amount set in trade_amount_aud. 
            origin_amount = self.starting_amount/order[0]
            if origin_amount < order[1] + order[1] * self.vol_safety_thresh:
                break

        book_sides = []
        # depending on the side of the trade, retrieve orderbook that contains asks or bids
        for side in self.sides:
            if side == "buy":
                book_sides.append("asks")
            else:
                book_sides.append("bids")


       # to calculate the margin, the actual amount received(above) and the amount received after fees must be kept seperate
        # check if enough origin 
        

        # Series of loops that iterate over each pair in the arbitrage route to calculate the best price avaliable while still having enough volume
        # to fill the trades.
        for pair_idx, pair in enumerate(self.tickers):
            # iterate over order book
            for idx, order in enumerate(self.exchange.fetch_order_book(self.tickers[pair_idx]['symbol'])[book_sides[pair_idx]]): 
                if pair_idx == 0:
                    self.amounts_rec[pair_idx] = self.starting_amount
                else:
                    self.amounts_rec[pair_idx] = self.amounts_rec[pair_idx-1]
                if self.sides[pair_idx] == 'buy':
                    # use the coin received in the previous ticker to buy the other coin in the current ticker
                    self.amounts_rec[pair_idx] = self.amounts_rec[pair_idx]/order[0]
                else:
                    # sell the coin received in the previous ticker to receive the other coin in the current ticker
                    self.amounts_rec[pair_idx] = self.amounts_rec[pair_idx]*order[0]

                # apply fee
                self.amounts_rec_after_fees[pair_idx] = self.amounts_rec[pair_idx]
                #print(self.amounts_rec_after_fees[pair_idx])
                self.amounts_rec_after_fees[pair_idx] -= self.amounts_rec_after_fees[pair_idx] * self.fee_per_trade
                if order[1] > (self.amounts_rec[pair_idx] + self.amounts_rec[pair_idx]*self.vol_safety_thresh):
                    self.prices[pair_idx] = order[0]
                    self.volumes[pair_idx] = order[1]
                    #print(self.amounts_rec_after_fees[pair_idx])
                    break

                else:
                    print("Not enough volume at " + str(order_2[1]))
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
