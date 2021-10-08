#!/usr/bin/python3 -u

import pyotp
from config import config

print( "Current OTP:", pyotp.TOTP( config[ 'bot' ][ 'totp' ] ).now() )
