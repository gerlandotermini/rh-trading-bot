#!/usr/bin/python3 -u

# Crypto Trading Bot
# Version: 1.5.4
# Credits: https://github.com/JasonRBowling/cryptoTradingBot/

from config import config
from classes.asset import asset
from classes.signals import signals

from datetime import datetime
from math import floor
import matplotlib.pyplot as plt
import numpy as np
from os import path, makedirs
import pandas as pd
import pickle
from random import randint
from requests import get as get_json
import robin_stocks as rh
import signal
from talib import EMA, RSI, MACD
from threading import Timer
from time import sleep

class bot:
    default_config = {
        'username': '',
        'password': '',
        'trades_enabled': False,
        'simulate_api_calls': False,
        'data_source': 'robinhood',
        'ticker_list': {
            'XETHZUSD': 'ETH'
        },
        'trade_signals': {
            'buy': 'sma_rsi_threshold',
            'sell': 'above_buy'
        },
        'buy_below_moving_average': 0.0075,
        'profit_percentage': 0.01,
        'buy_amount_per_trade': {
            0.0,
            0.0
        },
        'moving_average_periods': {
            'sma_fast': 48, # 12 data points per hour, 4 hours worth of data
            'sma_slow': 192,
            'macd_fast': 48,
            'macd_slow': 104, # MACD 12/26 -> 48/104
            'macd_signal': 28
        },
        'rsi_period': 48,
        'rsi_threshold': 39.5,
        'reserve': 0.0,
        'stop_loss_threshold': 0.3,
        'minutes_between_updates': 5,
        'cancel_pending_after_minutes': 20,
        'save_charts': True,
        'max_data_rows': 10000
    }
    data = pd.DataFrame()
    orders = {}

    min_share_increments = {}  # the smallest increment of a coin you can buy/sell
    min_price_increments = {}   # the smallest fraction of a dollar you can buy/sell a coin with
    api_error_counter = 0 # stop the bot if the API calls keep returning errors
    
    available_cash = 0

    signal = signals()

    def __init__( self ):
        # Set Pandas to output all columns in the dataframe
        pd.set_option( 'display.max_columns', None )
        pd.set_option( 'display.width', 300 )

        print( '-- Configuration ------------------------' )
        for c in self.default_config:
            isDefined = config.get( c )
            if not isDefined:
                config[ c ] = self.default_config[ c ]
        
        for a_key, a_value in config.items():
            if ( a_key == 'username' or a_key == 'password' ):
                continue

            print( a_key.replace( '_', ' ' ).capitalize(), ': ', a_value, sep='' )

        print( '-- Init Environment ---------------------' )

        # Initialize folders where to store data and charts
        if not path.exists( 'pickle' ):
            makedirs( 'pickle' )

        if not path.exists( 'charts' ):
            makedirs( 'charts' )

        if path.exists( 'pickle/orders.pickle' ):
            # Load state
            print( 'Loading saved orders' )
            with open( 'pickle/orders.pickle', 'rb' ) as f:
                self.orders = pickle.load( f )
        else:
            # Start from scratch
            print( 'No state saved, starting from scratch' )

        # Load data points
        if path.exists( 'pickle/dataframe.pickle' ):
            print( 'Loading saved dataset' )
            self.data = pd.read_pickle( 'pickle/dataframe.pickle' )

        # Connect to Robinhood
        if not config[ 'simulate_api_calls' ]:
            try:
                print( 'Logging in to Robinhood' )
                rh_response = rh.login( config[ 'username' ], config[ 'password' ],  )
            except:
                print( 'Got exception while attempting to log into Robinhood.' )
                exit()

        # Download Robinhood parameters
        for a_robinhood_ticker in config[ 'ticker_list' ].values():
            if not config[ 'simulate_api_calls' ]:
                try:
                    result = rh.get_crypto_info( a_robinhood_ticker )
                    self.min_share_increments.update( { a_robinhood_ticker: float( result[ 'min_order_quantity_increment' ] ) } )
                    self.min_price_increments.update( { a_robinhood_ticker: float( result[ 'min_order_price_increment' ] ) } )
                    self.api_error_counter = 0
                except:
                    print( 'Failed to get increments from RobinHood.' )
                    exit()
            else:
                self.min_share_increments.update( { a_robinhood_ticker: 0.0001 } )
                self.min_price_increments.update( { a_robinhood_ticker: 0.0001 } )

        # How much cash do we have?
        self.update_available_cash()

        # Install signal handlers
        signal.signal( signal.SIGTERM, self.handle_exit )
        signal.signal( signal.SIGINT, self.handle_exit )

        print( 'Bot Ready' )

        return

    def run( self ):
        # If we've had more than 5 consecutive exceptions, something is wrong (authentication expired?): abort
        if self.api_error_counter > 5:
            exit()

        now = datetime.now()

        # We don't have enough consecutive data points to decide what to do
        is_trading_locked = not self.get_new_data( now )
        
        if len( self.orders ) > 0:
            print( '-- Assets -------------------------------' )

            # Is any of our orders not filled? (swing/miss)
            pending_orders = []
            is_table_header_printed = False
            for a_asset in self.orders.values():
                if a_asset.status in [ 'PB', 'PS' ]:
                    print( 'Checking pending orders' )

                    # Retrieve the list of pending orders, if we haven't already
                    if len( pending_orders ) == 0 and config[ 'trades_enabled' ] and not config[ 'simulate_api_calls' ]:
                        try:
                            pending_orders = rh.get_all_open_crypto_orders()
                            self.api_error_counter = 0
                        except:
                            print( 'An exception occurred while retrieving list of pending orders.' )
                            self.api_error_counter += 1
                            pending_orders = []

                    # Is this order still pending?
                    for a_order in pending_orders:
                        if a_order[ 'id' ] == a_asset.order_id:
                            # Mark this order as cancelled so that we can remove it during garbage collection
                            a_asset.status = 'C' + str( a_asset.status )

                    # Was this asset marked as "to be cancelled?"
                    timediff = now - a_asset.timestamp
                    if a_asset.status in [ 'CPB', 'CPS' ] and timediff.seconds > config[ 'cancel_pending_after_minutes' ] * 60:
                        self.cancel_order( a_asset.order_id )
                    else:
                        # If it wasn't marked as 'to be cancelled', the order can be confirmed (remove the 'P' in front of the status)
                        # If it's not time to cancel it yet, remove the 'C' in front of the status
                        a_asset.status = a_asset.status[1:]

                        # If we confirmed that this asset was sold, we can update the available cash balance
                        if a_asset.status == 'S':
                            self.update_available_cash()

                # Print a summary of all confirmed assets
                if a_asset.status in [ 'B', 'PB', 'PS' ]:
                    if not is_table_header_printed:
                        print( "{:<16}  {:<6}  {:<12}  {:<12}  {:<12}  {:<12}".format( 'Date/Time', 'Ticker', 'Quantity', 'Price', 'Cost', 'Value' ) )
                        is_table_header_printed = True

                    try:
                        print( "{:<16}  {:<6}  {:<12}  {:<12}  {:<12}  {:<12}".format( a_asset.timestamp.strftime( '%Y-%m-%d %H:%M' ), str( a_asset.ticker ), str( a_asset.quantity ), str( a_asset.price ), str( round( a_asset.price * a_asset.quantity, 3 ) ), str( round( self.data.iloc[ -1 ][ a_asset.ticker ] * a_asset.quantity, 3 ) ) ) )
                    except IndexError:
                        print( "{:<16}  {:<6}  {:<12}  {:<12}  {:<12}  {:<12}".format( a_asset.timestamp.strftime( '%Y-%m-%d %H:%M' ), str( a_asset.ticker ), str( a_asset.quantity ), str( a_asset.price ), str( round( a_asset.price * a_asset.quantity, 3 ) ), 'N/A' ) )

                if a_asset.status == 'B':
                    # Is it time to sell this asset? ( Stop-loss: is the current price below the purchase price by the percentage defined in the config file? )
                    if not is_trading_locked and ( getattr( self.signal, 'sell_' + str(  config[ 'trade_signals' ][ 'sell' ] ) )( a_asset, self.data ) or self.data.iloc[ -1 ][ a_asset.ticker ] < a_asset.price - ( a_asset.price * config[ 'stop_loss_threshold' ] ) ):
                        self.sell( a_asset )
                        # During the following iteration we will confirm if this limit order was actually executed, and update the available cash balance accordingly

            if not is_table_header_printed:
                print( 'No assets found.')

        # Is it time to buy something?
        for a_robinhood_ticker in config[ 'ticker_list' ].values():
            if not is_trading_locked and getattr( self.signal, 'buy_' + str(  config[ 'trade_signals' ][ 'buy' ] ) )( a_robinhood_ticker, self.data ) and self.buy( a_robinhood_ticker ):
                self.update_available_cash()              

        # Only track up to a fixed amount of data points
        self.data = self.data.tail( config[ 'max_data_rows' ] )

        # Final status for this iteration
        print( '-- Bot Status ---------------------------' )
        print( 'Iteration completed on ' +str( datetime.now().strftime( '%Y-%m-%d %H:%M' ) ) )
        print( 'Buying power: $' + str( self.available_cash ) )
        print( '-- Data Snapshot ------------------------' )
        print( self.data.tail() )

        # Save state
        with open( 'pickle/orders.pickle', 'wb' ) as f:
            pickle.dump( self.orders, f )

        self.data.to_pickle( 'pickle/dataframe.pickle' )

        # Schedule the next iteration
        timer_handle = Timer( config[ 'minutes_between_updates' ] * 60, self.run )
        timer_handle.daemon = True
        timer_handle.start()
        timer_handle.join()

    def buy( self, ticker ):
        if self.available_cash == 0 or self.available_cash < config[ 'buy_amount_per_trade' ][ 'min' ] or ( config[ 'buy_amount_per_trade' ][ 'max' ] > 0 and self.available_cash > config[ 'buy_amount_per_trade' ][ 'max' ] ):
            return False
        
        # Retrieve the actual ask price from Robinhood
        if not config[ 'simulate_api_calls' ]:
            try:
                quote = rh.get_crypto_quote( ticker )
                price = float( quote[ 'ask_price' ] )
                self.api_error_counter = 0
            except:
                print( 'Could not retrieve ask price from Robinhood. Using most recent value.' )
                self.api_error_counter += 1
                price = self.data.iloc[ -1 ][ ticker ]
        else:
            price = self.data.iloc[ -1 ][ ticker ]

        # Values need to be specified to no more precision than listed in min_price_increments.
        # Truncate to 7 decimal places to avoid floating point problems way out at the precision limit
        price_precision = round( floor( price / self.min_price_increments[ ticker ] ) * self.min_price_increments[ ticker ], 7 )
        
        # How much to buy depends on the configuration
        quantity = ( self.available_cash if ( config[ 'buy_amount_per_trade' ][ 'max' ] == 0 ) else config[ 'buy_amount_per_trade' ][ 'max' ] ) / price_precision
        quantity = round( floor( quantity / self.min_share_increments[ ticker ] ) * self.min_share_increments[ ticker ], 7 )

        if config[ 'trades_enabled' ] and not config[ 'simulate_api_calls' ]:
            try:
                buy_info = rh.order_buy_crypto_limit( str( ticker ), quantity, price_precision )

                # Add this new asset to our orders
                self.orders[ buy_info[ 'id' ] ] = asset( ticker, quantity, price_precision, buy_info[ 'id' ], 'PB' )

                print( '## Submitted order to buy ' +  str( quantity ) + ' ' + str( ticker ) + ' at $' + str( price_precision ) )
                
                if ( price != self.data.iloc[ -1 ][ ticker ] ):
                    print( '## Price Difference: Mark $' + str( self.data.iloc[ -1 ][ ticker ] ) + ', Ask $' + str( price ) )

                self.api_error_counter = 0
            except:
                print( 'An exception occurred while trying to buy.' )
                self.api_error_counter += 1
                return False
        else:
            print( '## Would have bought ' + str( ticker ) + ' ' + str( quantity ) + ' at $' + str( price_precision ) + ', if trades were enabled' )
            return False

        return True

    def sell( self, asset ):
        # Retrieve the actual bid price from Robinhood
        if not config[ 'simulate_api_calls' ]:
            try:
                quote = rh.get_crypto_quote( asset.ticker )
                price = float( quote[ 'bid_price' ] )
                self.api_error_counter = 0
            except:
                print( 'Could not retrieve bid price from Robinhood. Using most recent value.' )
                self.api_error_counter += 1
                price = self.data.iloc[ -1 ][ asset.ticker ]
        else:
            price = self.data.iloc[ -1 ][ asset.ticker ]

        # Values needs to be specified to no more precision than listed in min_price_increments. 
        # Truncate to 7 decimal places to avoid floating point problems way out at the precision limit
        price_precision = round( floor( price / self.min_price_increments[ asset.ticker ] ) * self.min_price_increments[ asset.ticker ], 7 )
        profit = round( ( asset.quantity * price_precision ) - ( asset.quantity * asset.price ), 3 )

        if config[ 'trades_enabled' ] and not config[ 'simulate_api_calls' ]:
            try:
                sell_info = rh.order_sell_crypto_limit( str( asset.ticker ), asset.quantity, price_precision )

                # Mark this asset as pending sold
                self.orders[ asset.order_id ].status = 'PS'
                self.orders[ asset.order_id ].profit = profit

                print( '## Submitted order to sell ' + str( asset.quantity ) + ' ' + str( asset.ticker ) + ' at $' + str( price_precision ) + ' (estimated profit: $' + str( profit ) + ')' )
            
                if ( price != self.data.iloc[ -1 ][ asset.ticker ] ):
                    print( '## Price Difference: Mark $' + str( self.data.iloc[ -1 ][ asset.ticker ] ) + ', Bid $' + str( price ) )
            
                self.api_error_counter = 0
            except:
                print( 'An exception occurred while trying to sell.' )
                self.api_error_counter += 1
                return False
        else:
            print( '## Would have sold ' + str( asset.ticker ) + ' ' + str( asset.quantity ) + ' at $' + str( price_precision ) + ', if trades were enabled' )
            return False

        return True

    def data_has_gaps( self, now ):
        if self.data.shape[ 0 ] <= 1:
            return True

        # Check for break between now and last sample
        timediff = now - datetime.strptime( self.data.iloc[ -1 ][ 'timestamp' ], '%Y-%m-%d %H:%M' )

        # Not enough data points available or it's been too long since we recorded any data
        if timediff.seconds > ( config[ 'minutes_between_updates' ] + 1 ) * 120:
            return True

        # Check for break in sequence of samples to minimum consecutive sample number
        position = len( self.data ) - 1
        min_consecutive_samples = max( config[ 'rsi_period' ], config[ 'moving_average_periods' ][ 'sma_fast' ] )

        if position >= min_consecutive_samples:
            for x in range( 0, min_consecutive_samples ):
                timediff = datetime.strptime( self.data.iloc[ position - x ][ 'timestamp' ], '%Y-%m-%d %H:%M' ) - datetime.strptime( self.data.iloc[ position - ( x + 1 ) ][ 'timestamp' ], '%Y-%m-%d %H:%M' ) 

                if timediff.seconds > ( config[ 'minutes_between_updates' ] + 1 ) * 120:
                    return True

        return False

    def init_data( self ):
        print( 'Starting with a fresh dataset.' )

        # Download historical data from Kraken
        column_names = [ 'timestamp' ]

        for a_robinhood_ticker in config[ 'ticker_list' ].values():
            column_names.append( a_robinhood_ticker )

        self.data = pd.DataFrame( columns = column_names )

        for a_kraken_ticker, a_robinhood_ticker in config[ 'ticker_list' ].items():
            try:
                result = get_json( 'https://api.kraken.com/0/public/OHLC?interval=' + str( config[ 'minutes_between_updates' ] ) + '&pair=' + a_kraken_ticker ).json()
                historical_data = pd.DataFrame( result[ 'result' ][ a_kraken_ticker ] )
                historical_data = historical_data[ [ 0, 1 ] ]
                self.api_error_counter = 0

                # Be nice to the Kraken API
                sleep( 3 )
            except:
                print( 'An exception occurred retrieving historical data from Kraken.' )
                self.api_error_counter += 1
                return False

            # Convert timestamps
            self.data[ 'timestamp' ] = [ datetime.fromtimestamp( x ).strftime( "%Y-%m-%d %H:%M" ) for x in historical_data[ 0 ] ] 

            # Copy the data
            self.data[ a_robinhood_ticker ] = [ round( float( x ), 3 ) for x in historical_data[ 1 ] ]

            # Calculate the indicators
            self.data[ a_robinhood_ticker + '_SMA_F' ] = self.data[ a_robinhood_ticker ].shift( 1 ).rolling( window = config[ 'moving_average_periods' ][ 'sma_fast' ] ).mean()
            self.data[ a_robinhood_ticker + '_SMA_S' ] = self.data[ a_robinhood_ticker ].shift( 1 ).rolling( window = config[ 'moving_average_periods' ][ 'sma_slow' ] ).mean()
            self.data[ a_robinhood_ticker + '_EMA_F' ] = self.data[ a_robinhood_ticker ].ewm( span = config[ 'moving_average_periods' ][ 'ema_fast' ], adjust = False, min_periods = config[ 'moving_average_periods' ][ 'ema_fast' ]).mean()
            self.data[ a_robinhood_ticker + '_EMA_S' ] = self.data[ a_robinhood_ticker ].ewm( span = config[ 'moving_average_periods' ][ 'ema_slow' ], adjust = False, min_periods = config[ 'moving_average_periods' ][ 'ema_slow' ]).mean()
            self.data[ a_robinhood_ticker + '_RSI' ] = RSI( self.data[ a_robinhood_ticker ].values, timeperiod = config[ 'rsi_period' ] )
            self.data[ a_robinhood_ticker + '_MACD' ], self.data[ a_robinhood_ticker + '_MACD_S' ], macd_hist = MACD( self.data[ a_robinhood_ticker ].values, fastperiod = config[ 'moving_average_periods' ][ 'macd_fast' ], slowperiod = config[ 'moving_average_periods' ][ 'macd_slow' ], signalperiod = config[ 'moving_average_periods' ][ 'macd_signal' ] )

    def get_new_data( self, now ):
        # If the current dataset has gaps in it, we refresh it from Kraken
        if self.data_has_gaps( now ) and not self.init_data():
            return False

        new_row = { 'timestamp': now.strftime( "%Y-%m-%d %H:%M" ) }

        # Calculate moving averages and RSI values
        for a_kraken_ticker, a_robinhood_ticker in config[ 'ticker_list' ].items():
            if not config[ 'simulate_api_calls' ]:
                if config[ 'data_source' ] == 'kraken':
                    try:
                        result = get_json( 'https://api.kraken.com/0/public/Ticker?pair=' + str( a_kraken_ticker ) ).json()

                        if len( result[ 'error' ] ) == 0:
                            new_row[ a_robinhood_ticker ] = round( float( result[ 'result' ][ a_kraken_ticker ][ 'a' ][ 0 ] ), 3 )

                        self.api_error_counter = 0
                    except:
                        print( 'An exception occurred retrieving prices from Kraken.' )
                        self.api_error_counter += 1
                        return False
                else:
                    try:
                        result = rh.get_crypto_quote( a_robinhood_ticker )
                        new_row[ a_robinhood_ticker ] = round( float( result[ 'mark_price' ] ), 3 )
                        self.api_error_counter = 0
                    except:
                        print( 'An exception occurred retrieving prices from Robinhood.' )
                        self.api_error_counter += 1
                        return False
            else:
                new_row[ a_robinhood_ticker ] = round( float( randint( 400000, 500000 ) ), 3 )

            # If the new price is more than 40% lower/higher than the previous reading, assume it's an error somewhere
            percent_diff = ( abs( new_row[ a_robinhood_ticker ] - self.data.iloc[ -1 ][ a_robinhood_ticker ] ) / self.data.iloc[ -1 ][ a_robinhood_ticker ] ) * 100
            if percent_diff > 30:
                print( 'Error: new price ($' + str( new_row[ a_robinhood_ticker ] ) + ') differs ' + str( round( percent_diff, 2 ) ) + '% from previous value, ignoring.' )
                return False

            self.data = self.data.append( new_row, ignore_index = True )

            # If the API is overloaded, it keeps returning the same value
            if ( self.data.tail( 4 )[ a_robinhood_ticker ].to_numpy()[ -1 ] == self.data.tail( 4 )[ a_robinhood_ticker ].to_numpy() ).all():
                print( 'Repeating values detected for ' + str( a_robinhood_ticker ) + '. Ignoring data point.' )
                self.data = self.data[:-1]
                return False

            elif self.data.shape[ 0 ] > 0:
                self.data[ a_robinhood_ticker + '_SMA_F' ] = self.data[ a_robinhood_ticker ].rolling( window = config[ 'moving_average_periods' ][ 'sma_fast' ] ).mean()
                self.data[ a_robinhood_ticker + '_SMA_S' ] = self.data[ a_robinhood_ticker ].rolling( window = config[ 'moving_average_periods' ][ 'sma_slow' ] ).mean()
                self.data[ a_robinhood_ticker + '_SMA_S' ] = self.data[ a_robinhood_ticker ].rolling( window = config[ 'moving_average_periods' ][ 'sma_slow' ] ).mean()
                self.data[ a_robinhood_ticker + '_EMA_F' ] = self.data[ a_robinhood_ticker ].ewm( span = config[ 'moving_average_periods' ][ 'ema_fast' ], adjust = False, min_periods = config[ 'moving_average_periods' ][ 'ema_fast' ]).mean()
                self.data[ a_robinhood_ticker + '_EMA_S' ] = self.data[ a_robinhood_ticker ].ewm( span = config[ 'moving_average_periods' ][ 'ema_slow' ], adjust = False, min_periods = config[ 'moving_average_periods' ][ 'ema_slow' ]).mean()
                self.data[ a_robinhood_ticker + '_RSI' ] = RSI( self.data[ a_robinhood_ticker ].values, timeperiod = config[ 'rsi_period' ] )
                self.data[ a_robinhood_ticker + '_MACD' ], self.data[ a_robinhood_ticker + '_MACD_S' ], macd_hist = MACD( self.data[ a_robinhood_ticker ].values, fastperiod = config[ 'moving_average_periods' ][ 'macd_fast' ], slowperiod = config[ 'moving_average_periods' ][ 'macd_slow' ], signalperiod = config[ 'moving_average_periods' ][ 'macd_signal' ] )

            if config[ 'save_charts' ] == True:
                self.save_chart( [ a_robinhood_ticker, str( a_robinhood_ticker ) + '_SMA_F', str( a_robinhood_ticker ) + '_SMA_S' ], str( a_robinhood_ticker ) + '_sma' )
                self.save_chart( [ a_robinhood_ticker, str( a_robinhood_ticker ) + '_EMA_F', str( a_robinhood_ticker ) + '_EMA_S' ], str( a_robinhood_ticker ) + '_ema' )
                self.save_chart_rescale( [ a_robinhood_ticker, str( a_robinhood_ticker ) + '_RSI' ], str( a_robinhood_ticker ) + '_rsi' )
                self.save_chart_rescale( [ a_robinhood_ticker, str( a_robinhood_ticker ) + '_MACD', str( a_robinhood_ticker ) + '_MACD_S' ], str( a_robinhood_ticker ) + '_macd' )

        return True

    def update_available_cash( self ):
        if not config[ 'simulate_api_calls' ]:
            try:
                me = rh.account.load_phoenix_account( info=None )
                self.available_cash = max( 0, round( float( me[ 'crypto_buying_power' ][ 'amount' ] ) - config[ 'reserve' ], 3 ) )
                self.api_error_counter = 0
            except:
                print( 'An exception occurred while reading available cash amount.' )
                self.api_error_counter += 1
                return False
        else:
            self.available_cash = randint( 400000, 500000 ) + config[ 'reserve' ]

        return True

    def cancel_order( self, order_id ):
        if not config[ 'simulate_api_calls' ]:
            try:
                cancelResult = rh.cancel_crypto_order( order_id )
                self.orders[ order_id ].status = 'C'
                print( 'Cancelled order #' + str( order_id ) + '.' )
                self.api_error_counter = 0
            except:
                print( 'An exception occurred while attempting to cancel order #' + str( order_id ) + '.')
                self.api_error_counter += 1
                return False

        # Let Robinhood process this transaction
        sleep( 10 )

        # No profit on this order
        self.orders[ order_id ].profit = 0

        return True

    def save_chart( self, columns, label ):
        if len( columns ) < 1:
            return False

        slice = self.data.loc[:, [ 'timestamp' ] + columns ]
        slice[ 'timestamp' ] = [ datetime.strptime( x, '%Y-%m-%d %H:%M').strftime( "%d@%H:%M" ) for x in slice[ 'timestamp' ] ]
        fig = slice.plot( x = 'timestamp', xlabel = 'Time', ylabel = '', figsize = ( 15, 5 ), fontsize = 13, linewidth = 0.8, alpha = 0.6 )
        fig.set_yticks( np.arange( min( slice[ columns[ 0 ] ] ), max( slice[ columns[ 0 ] ] ), int( ( max( slice[ columns[ 0 ] ] ) - min( slice[ columns[ 0 ] ] ) ) / 20 ) ) )
        fig.yaxis.set_tick_params( labelright = 'on' )
        fig.lines[ 0 ].set_alpha( 1 )
        fig.grid( linestyle = 'dotted', linewidth = '0.5' )
        fig = fig.get_figure()
        fig.savefig( 'charts/chart_' + str( label ).lower() + '.png', dpi = 300 )
        plt.close( fig )

    def save_chart_rescale( self, columns, label ):
        if len( columns ) < 1:
            return False

        ax = {}
        slice = self.data.loc[:, [ 'timestamp' ] + columns ]
        slice[ 'timestamp' ] = [ datetime.strptime( x, '%Y-%m-%d %H:%M').strftime( "%d@%H:%M" ) for x in slice[ 'timestamp' ] ]

        fig = plt.figure( figsize = ( 15, 5 ), dpi = 300 )
        fig.subplots_adjust( right = 1 - ( len( columns ) * 0.1 ) )
        ax[ 0 ] = fig.add_subplot()
        slice[ columns[ 0 ] ].plot( x = 'timestamp', xlabel = '', ylabel = columns[ 0 ], ax=ax[ 0 ], fontsize = 13, linewidth = 0.8 )
        for idx in range( 1, len( columns ) ):
            ax[ idx + 1 ] = ax[ 0 ].twinx()
            ax[ idx + 1 ].spines[ 'right' ].set_position(( 'axes', 1 + idx * 0.1 ) )
            slice[ columns[ idx ] ].plot( x = 'timestamp', xlabel = '', ylabel = columns[ idx ], ax=ax[ idx + 1 ], fontsize = 13, linewidth = 0.8, color = 'C' + str( idx ) )

        plt.savefig( 'charts/chart_' + str( label ).lower() + '.png' )
        plt.close( fig )

    def handle_exit( self, signum, frame ):
        with open( 'pickle/orders.pickle', 'wb' ) as f:
            pickle.dump( self.orders, f )

        self.data.to_pickle( 'pickle/dataframe.pickle' )
        
        print( 'Shutdown signal received. Saving state.' )
        exit()

if __name__ == "__main__":
    b = bot()
    b.run()