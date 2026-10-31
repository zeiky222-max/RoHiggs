# RoHiggs – Your Roblox World, Powered by AI
Flask + SQLite demo. Black/green UI using your background image.

## Run
```
pip install -r requirements.txt
python main.py        # open http://127.0.0.1:5000
```
Set `SECRET_KEY` in production.

## Put it on GitHub and Vercel
1. Upload this whole folder to a **public** GitHub repo (the `.gitignore` keeps the database and secrets out).
2. On vercel.com: **Add New Project** → import the repo. No build settings are needed (Vercel finds `main.py` and serves `public/`).
3. In **Settings → Environment Variables** add `SECRET_KEY` (any long random text). Optional: `ROBLOX_CLIENT_ID`, `ROBLOX_CLIENT_SECRET`; set the Roblox redirect URI to `https://YOUR-SITE.vercel.app/api/roblox/callback`.
4. **Important:** on Vercel the SQLite file lives in `/tmp`, so tokens, accounts and projects can reset at any time. That is fine for a demo. For real use, move the database to a hosted one (Postgres/Turso) or host on PythonAnywhere/Render.

## What is real and what is demo
- **Real:** sessions, password hashing, backend-validated RoTokens (atomic deduction, refunds on failure, history), projects, rate limits, Studio bridge (pair code, pending queue, whitelist validation).
- **Demo:** AI generation (`integrations/ai_service.py`) and token packages (no payments). No Higgsfield endpoint is included; add yours there when you have official API access.
- **Roblox account linking** uses official Roblox OAuth 2.0. It only works after you register an app at create.roblox.com and set `ROBLOX_CLIENT_ID` and `ROBLOX_CLIENT_SECRET` (redirect URI: `http://127.0.0.1:5000/api/roblox/callback`). Without keys the site says so and stays "Not Connected". RoHiggs never asks for Roblox passwords or cookies.

## Studio plugin
1. Copy `studio_plugin/RoHiggsPlugin.lua` to your Studio Plugins folder; enable HTTP requests.
2. On the site press GET MY STUDIO CODE, then in the Studio command bar run `_G.RoHiggsPair("CODE")`.
3. Preview in the website, press APPLY TO ROBLOX STUDIO, then click **Apply** in the plugin toolbar to approve. One Ctrl+Z undoes it.
