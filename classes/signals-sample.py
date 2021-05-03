from config import config
from math import isnan

# Signal functions are defined in alphabetical order and return a boolean value
# indicating if a given asset should be traded based on certain conditions

class signals:
    def buy_ema_crossover_rsi( self, ticker, data ):
        # Exponential Moving Average Crossover with RSI Filter
        # Buy when Fast-EMA crosses Slow-EMA from below, and RSI > buy threshold (50 suggested)
        #
        # Params: rsi_threshold

        return(        
            # Make sure the data is valid
            not isnan( data.iloc[ -1 ][ ticker + '_EMA_F' ] ) and
            not isnan( data.iloc[ -2 ][ ticker + '_EMA_F' ] ) and
            not isnan( data.iloc[ -1 ][ ticker + '_EMA_S' ] ) and
            not isnan( data.iloc[ -2 ][ ticker + '_EMA_S' ] ) and
            not isnan( data.iloc[ -1 ][ ticker + '_RSI' ] ) and

            # Fast-EMA crossed Slow-EMA from below
            data.iloc[ -2 ][ ticker + '_EMA_F' ] < data.iloc[ -2 ][ ticker + '_EMA_S' ]  and
            data.iloc[ -1 ][ ticker + '_EMA_F' ] >= data.iloc[ -1 ][ ticker + '_EMA_S' ]  and
            
            # RSI above threshold
            data.iloc[ -1 ][ ticker + '_RSI' ] > config[ 'trade_signals' ][ 'buy' ][ 'params' ][ 'rsi_threshold' ]
        )

    def buy_sma_crossover_rsi( self, ticker, data ):
        # Simple Moving Average Crossover with RSI Filter
        # Credits: https://trader.autochartist.com/moving-average-crossover-with-rsi-filter/
        # Buy when Fast-SMA crosses Slow-SMA from below, and RSI > buy threshold (50 suggested)
        #
        # Params: rsi_threshold

        return(        
            # Make sure the data is valid
            not isnan( data.iloc[ -1 ][ ticker + '_SMA_F' ] ) and
            not isnan( data.iloc[ -2 ][ ticker + '_SMA_F' ] ) and
            not isnan( data.iloc[ -1 ][ ticker + '_SMA_S' ] ) and
            not isnan( data.iloc[ -2 ][ ticker + '_SMA_S' ] ) and
            not isnan( data.iloc[ -1 ][ ticker + '_RSI' ] ) and

            # Fast-SMA crossed Slow-SMA from below
            data.iloc[ -2 ][ ticker + '_SMA_F' ] < data.iloc[ -2 ][ ticker + '_SMA_S' ]  and
            data.iloc[ -1 ][ ticker + '_SMA_F' ] >= data.iloc[ -1 ][ ticker + '_SMA_S' ]  and
            
            # RSI above threshold
            data.iloc[ -1 ][ ticker + '_RSI' ] > config[ 'trade_signals' ][ 'buy' ][ 'params' ][ 'rsi_threshold' ]
        )

    def buy_sma_rsi_threshold( self, ticker, data ):
        # Simple Moving Average and RSI
        # Credits: https://medium.com/swlh/a-full-crypto-trading-bot-in-python-aafba122bc4e
        # Buy when price is below Fast-SMA and RSI is below threshold
        #
        # Params: buy_below_moving_average, rsi_threshold
        
        return (
            not isnan( data.iloc[ -1 ][ ticker + '_SMA_F' ] ) and
            not isnan( data.iloc[ -1 ][ ticker + '_RSI' ] ) and

            # Is the current price below the Fast-SMA by the percentage defined in the config file?
            data.iloc[ -1 ][ ticker ] <= data.iloc[ -1 ][ ticker + '_SMA_F' ] - ( data.iloc[ -1 ][ ticker + '_SMA_F' ] * config[ 'trade_signals' ][ 'buy' ][ 'params' ][ 'buy_below_moving_average' ] ) and

            # RSI below the threshold
            data.iloc[ -1 ][ ticker + '_RSI' ] <= config[ 'trade_signals' ][ 'buy' ][ 'params' ][ 'rsi_threshold' ]
        )

    def sell_above_buy( self, asset, data ):
        # Simple profit percentage
        #
        # Params: profit_percentage
        
        return (
            data.iloc[ -1 ][ asset.ticker ] > asset.price + ( asset.price * config[ 'trade_signals' ][ 'sell' ][ 'params' ][ 'profit_percentage' ] )
        )

    def sell_ema_crossover_rsi( self, asset, data ):
        # Exponential Moving Average Crossover with RSI Filter
        #
        # Params: profit_percentage, rsi_threshold

        return(
            # Make sure the data is valid
            not isnan( data.iloc[ -1 ][ asset.ticker + '_EMA_F' ] ) and
            not isnan( data.iloc[ -2 ][ asset.ticker + '_EMA_F' ] ) and
            not isnan( data.iloc[ -1 ][ asset.ticker + '_EMA_S' ] ) and
            not isnan( data.iloc[ -2 ][ asset.ticker + '_EMA_S' ] ) and
            not isnan( data.iloc[ -1 ][ asset.ticker + '_RSI' ] ) and

            # Fast-EMA crossed Slow-EMA from above
            data.iloc[ -2 ][ asset.ticker + '_EMA_F' ] > data.iloc[ -2 ][ asset.ticker + '_EMA_S' ]  and
            data.iloc[ -1 ][ asset.ticker + '_EMA_F' ] <= data.iloc[ -1 ][ asset.ticker + '_EMA_S' ]  and
            
            # RSI below threshold
            data.iloc[ -1 ][ asset.ticker + '_RSI' ] <= config[ 'trade_signals' ][ 'sell' ][ 'params' ][ 'rsi_threshold' ] and

            # Price is higher than purchase price by at least profit percentage
            data.iloc[ -1 ][ asset.ticker ] >= asset.price + (  asset.price * config[ 'trade_signals' ][ 'sell' ][ 'params' ][ 'profit_percentage' ] )
        )

    def sell_price_ema_crossover_rsi( self, asset, data ):
        # Exponential Moving Average Crossover with RSI Filter
        #
        # Params: profit_percentage, rsi_threshold

        return(        
            # Make sure the data is valid
            not isnan( data.iloc[ -1 ][ asset.ticker + '_EMA_S' ] ) and
            not isnan( data.iloc[ -2 ][ asset.ticker + '_EMA_S' ] ) and
            not isnan( data.iloc[ -1 ][ asset.ticker + '_RSI' ] ) and

            # Price crossed Slow-EMA from above
            data.iloc[ -2 ][ asset.ticker ] > data.iloc[ -2 ][ asset.ticker + '_EMA_S' ]  and
            data.iloc[ -1 ][ asset.ticker ] <= data.iloc[ -1 ][ asset.ticker + '_EMA_S' ]  and
            
            # RSI below threshold
            data.iloc[ -1 ][ asset.ticker + '_RSI' ] <= config[ 'trade_signals' ][ 'sell' ][ 'params' ][ 'rsi_threshold' ] and

            # Price is higher than purchase price by at least profit percentage
            data.iloc[ -1 ][ asset.ticker ] >= asset.price + (  asset.price * config[ 'trade_signals' ][ 'sell' ][ 'params' ][ 'profit_percentage' ] )
        )

    def sell_sma_crossover_rsi( self, asset, data ):
        # Simple Moving Average Crossover with RSI Filter
        # Credits: https://trader.autochartist.com/moving-average-crossover-with-rsi-filter/
        #
        # Params: profit_percentage, rsi_threshold

        return(        
            # Make sure the data is valid
            not isnan( data.iloc[ -1 ][ asset.ticker + '_SMA_F' ] ) and
            not isnan( data.iloc[ -2 ][ asset.ticker + '_SMA_F' ] ) and
            not isnan( data.iloc[ -1 ][ asset.ticker + '_SMA_S' ] ) and
            not isnan( data.iloc[ -2 ][ asset.ticker + '_SMA_S' ] ) and
            not isnan( data.iloc[ -1 ][ asset.ticker + '_RSI' ] ) and

            # Fast-SMA crossed Slow-SMA from above
            data.iloc[ -2 ][ asset.ticker + '_SMA_F' ] > data.iloc[ -2 ][ asset.ticker + '_SMA_S' ]  and
            data.iloc[ -1 ][ asset.ticker + '_SMA_F' ] <= data.iloc[ -1 ][ asset.ticker + '_SMA_S' ]  and
            
            # RSI below threshold
            data.iloc[ -1 ][ asset.ticker + '_RSI' ] <= config[ 'trade_signals' ][ 'sell' ][ 'params' ][ 'rsi_threshold' ] and

            # Price is higher than purchase price by at least profit percentage
            data.iloc[ -1 ][ asset.ticker ] >= asset.price + (  asset.price * config[ 'trade_signals' ][ 'sell' ][ 'params' ][ 'profit_percentage' ] )
        )

    def sell_trailing_stop_loss( self, asset, data ):
        # Trailing Stop Loss
        # Sell an asset when its price dips below the trailing stop loss threshold
        #
        # Params: profit_percentage, tsl_percentage

        return( 
            data.iloc[ -1 ][ asset.ticker ] < data.loc[ data.timestamp > asset.timestamp ][ asset.ticker ].max() * ( 1 - config[ 'trade_signals' ][ 'sell' ][ 'params' ][ 'tsl_percentage' ] ) and
            data.iloc[ -1 ][ asset.ticker ] >= asset.price + (  asset.price * config[ 'trade_signals' ][ 'sell' ][ 'params' ][ 'profit_percentage' ] )
        )