from datetime import datetime

class asset:
    ticker = ''
    quantity = 0.0
    price = 0.0
    order_id = ''
    timestamp = 0
    status = 'PB'
    profit = 0.0

    def __init__( self, ticker = '', quantity = 0.0, price = 0.0, order_id = '', status = 'PB', profit = 0.0, timestamp = 0 ):
        self.ticker = ticker
        self.quantity = float( quantity )
        self.price = float( price )
        self.order_id = order_id
        self.timestamp = datetime.now()
        self.status = 'PB'
        self.profit = float( profit )