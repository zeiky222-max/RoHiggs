import os, secrets, urllib.parse
import requests
AUTH = "https://apis.roblox.com/oauth/v1/authorize"
TOKEN = "https://apis.roblox.com/oauth/v1/token"
USERINFO = "https://apis.roblox.com/oauth/v1/userinfo"

def configured():
    return bool(os.environ.get("ROBLOX_CLIENT_ID") and os.environ.get("ROBLOX_CLIENT_SECRET"))

def auth_url(redirect_uri, state):
    q = {"client_id": os.environ["ROBLOX_CLIENT_ID"], "redirect_uri": redirect_uri,
         "scope": "openid profile", "response_type": "code", "state": state}
    return AUTH + "?" + urllib.parse.urlencode(q)

def exchange(code, redirect_uri):
    """Official Roblox OAuth 2.0: trade the code for the verified Roblox profile."""
    r = requests.post(TOKEN, data={"grant_type": "authorization_code", "code": code,
        "client_id": os.environ["ROBLOX_CLIENT_ID"], "client_secret": os.environ["ROBLOX_CLIENT_SECRET"],
        "redirect_uri": redirect_uri}, timeout=15)
    r.raise_for_status()
    u = requests.get(USERINFO, headers={"Authorization": "Bearer " + r.json()["access_token"]}, timeout=15)
    u.raise_for_status(); i = u.json()
    return {"id": i.get("sub"), "name": i.get("preferred_username") or i.get("name")}

def pair_code():
    return secrets.token_hex(3).upper()
