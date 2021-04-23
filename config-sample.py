config = {
    'username': "", # Robinhood credentials. If you don't want to keep them stored here, launch "./2fa.py" to setup the access token interactively
    'password': "",
    'trades_enabled': False, # if False, just collect data
    'simulate_api_calls': False, # if enabled, just pretend to connect to Robinhood
    'data_source': 'robinhood', # which platform to use to track prices: kraken or robinhood

    'ticker_list': { # list of coin ticker pairs Kraken/Robinhood (XETHZUSD/ETH, etc) - https://api.kraken.com/0/public/AssetPairs
        'XETHZUSD': 'ETH'
    }, 
    'trade_signals': { # select which strategies to use (buy, sell); see classes/signals.py for more info
        'buy': 'sma_rsi_threshold',
        'sell': 'above_buy'
    },
    'moving_average_periods': { # data points needed to calculate SMA fast, SMA slow, MACD fast, MACD slow, MACD signal
        'sma_fast': 12, # 12 data points per hour 
        'sma_slow': 48,
        'ema_fast': 12,
        'ema_slow': 48,
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 7
    },
    'rsi_period': 48, # data points for RSI
    'rsi_threshold': { # RSI thresholds to trigger a buy or a sell order
        'buy': 39.5,
        'sell': 60
    },
    'buy_below_moving_average': 0.0075, # buy if price drops below Fast_MA by this percentage (0.75%)
    'profit_percentage': 0.01, # sell if price raises above purchase price by this percentage (1%)
    'buy_amount_per_trade': { # if greater than zero, buy no less/no more than this amount of coin, otherwise use all the cash in the account
        'min': 0.0, 
        'max': 0.0 
    },
    'reserve': 0.0, # tell the bot if you don't want it to use all of the available cash in your account
    'stop_loss_threshold': 0.3,   # sell if the price drops at least 30% below the purchase price

    'minutes_between_updates': 5, # 1 (default), 5, 15, 30, 60, 240, 1440, 10080, 21600
    'cancel_pending_after_minutes': 20, # how long to wait before cancelling an order that hasn't been filled
    'save_charts': True,
    'max_data_rows': 2000
}
