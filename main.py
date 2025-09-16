import os
import time
import requests
import pyotp
from SmartApi import SmartConnect

def smartapi_login():
    api_key = os.getenv("SMARTAPI_API_KEY")
    api_secret = os.getenv("SMARTAPI_API_SECRET")
    client_code = os.getenv("SMARTAPI_CLIENT_CODE")
    mpin = os.getenv("SMARTAPI_MPIN")
    password = os.getenv("SMARTAPI_PASSWORD")
    totp_secret = os.getenv("SMARTAPI_TOTP_SECRET")

    obj = SmartConnect(api_key=api_key)

    # If MPIN login
    if mpin:
        print("[SmartAPI] Attempting MPIN login...")
        try:
            data = obj.generateSession(client_code, mpin)
            print("[SmartAPI] MPIN login success")
            return obj, data
        except Exception as e:
            print("[SmartAPI] MPIN login failed:", e)
            return None, None

    # Else Password+TOTP login
    elif password and totp_secret:
        print("[SmartAPI] Attempting Password+TOTP login...")
        try:
            otp = pyotp.TOTP(totp_secret).now()
            data = obj.generateSession(client_code, password, otp)
            print("[SmartAPI] Password+TOTP login success")
            return obj, data
        except Exception as e:
            print("[SmartAPI] Password+TOTP login failed:", e)
            return None, None
    else:
        print("[SmartAPI] Credentials missing. Check .env")
        return None, None

if __name__ == "__main__":
    smartapi_login()
