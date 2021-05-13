#!/usr/bin/python3 -u

from config import config
import robin_stocks as rh

for c in [ 'username', 'password' ]:
    try:
        config[ 'bot' ][ c ]
    except:
        config[ 'bot' ][ c ] = ''

try:
    rh_response = rh.login( config[ 'bot' ][ 'username' ], config[ 'bot' ][ 'password' ] )
except:
    print( 'Got exception while attempting to log into Robinhood.' )
    exit()

print( "Authentication complete. You can start using the bot now.\n\nAccess Token:" )
print( rh_response[ 'access_token' ] + "\n" )