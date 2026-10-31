import os, sqlite3, json, time, secrets
from flask import Flask, g, jsonify, request, session, render_template, redirect
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from integrations import ai_service, roblox_service, token_service

BASE = os.path.dirname(os.path.abspath(__file__))
ON_VERCEL = bool(os.environ.get("VERCEL"))
# Vercel's disk is read-only except /tmp (temporary: data resets).
DB = "/tmp/rohiggs.db" if ON_VERCEL else os.path.join(BASE, "database", "rohiggs.db")
app = Flask(__name__, static_folder="public", static_url_path="")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=ON_VERCEL, MAX_CONTENT_LENGTH=2 * 1024 * 1024)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, pw_hash TEXT, tokens INTEGER DEFAULT 100,
 roblox_id TEXT, roblox_name TEXT, roblox_time TEXT, pair_code TEXT, studio_connected INTEGER DEFAULT 0, plugin_token TEXT);
CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, type TEXT, content TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY, user_id INTEGER, amount INTEGER, reason TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS commands(id INTEGER PRIMARY KEY, user_id INTEGER, prompt TEXT, ops TEXT, status TEXT DEFAULT 'preview', created TEXT DEFAULT CURRENT_TIMESTAMP);
"""

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB); g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close(_):
    d = g.pop("db", None)
    if d: d.commit(); d.close()

def init_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB); c.executescript(SCHEMA); c.commit(); c.close()

def me():
    """Every visitor gets a private guest account on first visit (100 demo RoTokens)."""
    uid = session.get("uid")
    row = db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone() if uid else None
    if not row:
        name = "guest-" + secrets.token_hex(3)
        cur = db().execute("INSERT INTO users(username) VALUES(?)", (name,))
        session["uid"] = cur.lastrowid
        row = db().execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
    return row

_hits = {}
def limited(uid, n=10, per=60):
    now = time.time(); h = [t for t in _hits.get(uid, []) if now - t < per]
    if len(h) >= n: return True
    h.append(now); _hits[uid] = h; return False

@app.route("/")
def index(): return render_template("index.html")

@app.get("/api/state")
def state():
    u = me(); d = db()
    return jsonify(username=u["username"], guest=u["username"].startswith("guest-"), tokens=u["tokens"],
        costs=token_service.COSTS, packages=token_service.PACKAGES,
        roblox={"status": "Connected" if u["roblox_id"] else "Not Connected", "name": u["roblox_name"], "time": u["roblox_time"],
                "oauth_ready": roblox_service.configured()},
        studio=bool(u["studio_connected"]), higgsfield_ready=ai_service.higgsfield_configured(),
        projects=[dict(r) for r in d.execute("SELECT id,name,type,content,created FROM projects WHERE user_id=? ORDER BY id DESC", (u["id"],))],
        history=[dict(r) for r in d.execute("SELECT amount,reason,created FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT 8", (u["id"],))])

@app.post("/api/generate")
def generate():
    u = me(); j = request.get_json(force=True); f = j.get("feature"); p = (j.get("prompt") or "").strip()
    if f not in token_service.COSTS or f == "studio": return jsonify(error="Unknown tool."), 400
    if not p or len(p) > 500: return jsonify(error="Type what you want to create (up to 500 letters)."), 400
    if not j.get("confirm"): return jsonify(error="Please confirm the RoToken cost first."), 400
    if limited(u["id"]): return jsonify(error="Slow down a little and try again in a minute."), 429
    if not token_service.charge(db(), u["id"], f): return jsonify(error="Not enough RoTokens? Get more to continue creating!"), 402
    try:
        res = ai_service.generate(f, p)
    except Exception:
        token_service.refund(db(), u["id"], f); return jsonify(error="That didn't work. You were not charged."), 500
    return jsonify(res)

@app.route("/api/projects", methods=["POST"])
def save_project():
    u = me(); j = request.get_json(force=True)
    db().execute("INSERT INTO projects(user_id,name,type,content) VALUES(?,?,?,?)",
        (u["id"], (j.get("name") or "Untitled")[:60], (j.get("type") or "idea")[:20], (j.get("content") or "")[:5000]))
    return jsonify(ok=True)

@app.delete("/api/projects/<int:pid>")
def del_project(pid):
    db().execute("DELETE FROM projects WHERE id=? AND user_id=?", (pid, me()["id"])); return jsonify(ok=True)

@app.post("/api/tokens/demo-buy")
def demo_buy():
    pkg = (request.get_json(force=True).get("package"))
    if pkg not in token_service.PACKAGES: return jsonify(error="Unknown package."), 400
    token_service.add_demo_package(db(), me()["id"], pkg); return jsonify(ok=True, demo=True)

# ---------- Roblox account linking (official OAuth only) ----------
@app.get("/api/roblox/link")
def roblox_link():
    if not roblox_service.configured():
        return jsonify(error="Account linking is not set up on this server yet. Add ROBLOX_CLIENT_ID and ROBLOX_CLIENT_SECRET (see README). Nothing was connected."), 501
    me(); session["oauth_state"] = secrets.token_urlsafe(16)
    return jsonify(url=roblox_service.auth_url(request.host_url.rstrip("/") + "/api/roblox/callback", session["oauth_state"]))

@app.get("/api/roblox/callback")
def roblox_callback():
    if not request.args.get("state") or request.args.get("state") != session.pop("oauth_state", None):
        return redirect("/?roblox=error")
    try:
        info = roblox_service.exchange(request.args.get("code", ""), request.host_url.rstrip("/") + "/api/roblox/callback")
    except Exception:
        return redirect("/?roblox=error")
    old = db().execute("SELECT id FROM users WHERE roblox_id=?", (info["id"],)).fetchone()
    if old: session["uid"] = old["id"]   # linking Roblox again brings your RoTokens and projects back
    db().execute("UPDATE users SET roblox_id=?, roblox_name=?, roblox_time=datetime('now') WHERE id=?", (info["id"], info["name"], me()["id"]))
    return redirect("/?roblox=ok#binding")

@app.post("/api/roblox/disconnect")
def roblox_disconnect():
    db().execute("UPDATE users SET roblox_id=NULL, roblox_name=NULL, roblox_time=NULL, studio_connected=0, plugin_token=NULL WHERE id=?", (me()["id"],))
    return jsonify(ok=True)

# ---------- Studio plugin bridge ----------
@app.post("/api/studio/pair-code")
def pair_code():
    c = roblox_service.pair_code()
    db().execute("UPDATE users SET pair_code=? WHERE id=?", (c, me()["id"])); return jsonify(code=c)

@app.post("/api/plugin/pair")
def plugin_pair():
    code = (request.get_json(force=True).get("code") or "").upper()
    r = db().execute("SELECT id FROM users WHERE pair_code=? AND pair_code IS NOT NULL", (code,)).fetchone()
    if not r: return jsonify(error="Bad code"), 400
    tok = secrets.token_hex(24)
    db().execute("UPDATE users SET plugin_token=?, studio_connected=1, pair_code=NULL WHERE id=?", (tok, r["id"]))
    return jsonify(token=tok)

def plugin_user():
    t = request.headers.get("X-Plugin-Token", "")
    return db().execute("SELECT * FROM users WHERE plugin_token=? AND plugin_token IS NOT NULL", (t,)).fetchone() if t else None

@app.get("/api/plugin/pending")
def plugin_pending():
    u = plugin_user()
    if not u: return jsonify(error="unauthorized"), 401
    rows = db().execute("SELECT id,ops FROM commands WHERE user_id=? AND status='queued' ORDER BY id", (u["id"],)).fetchall()
    return jsonify(commands=[{"id": r["id"], "ops": ai_service.validate_ops(json.loads(r["ops"]))} for r in rows])

@app.post("/api/plugin/done/<int:cid>")
def plugin_done(cid):
    u = plugin_user()
    if not u: return jsonify(error="unauthorized"), 401
    db().execute("UPDATE commands SET status='applied' WHERE id=? AND user_id=?", (cid, u["id"])); return jsonify(ok=True)

@app.post("/api/studio/preview")
def studio_preview():
    u = me(); p = (request.get_json(force=True).get("prompt") or "").strip()[:300]
    if not p: return jsonify(error="Tell RoHiggs what to build first."), 400
    if limited(u["id"]): return jsonify(error="Slow down a little and try again in a minute."), 429
    ops = ai_service.plan_studio_ops(p)
    cid = db().execute("INSERT INTO commands(user_id,prompt,ops) VALUES(?,?,?)", (u["id"], p, json.dumps(ops))).lastrowid
    return jsonify(id=cid, ops=ops, message=ai_service.describe(ops), cost=token_service.COSTS["studio"], demo=True)

@app.post("/api/studio/apply/<int:cid>")
def studio_apply(cid):
    u = me(); c = db().execute("SELECT * FROM commands WHERE id=? AND user_id=? AND status='preview'", (cid, u["id"])).fetchone()
    if not c or not json.loads(c["ops"]): return jsonify(error="Nothing to apply. Preview a change first."), 400
    if not u["studio_connected"]: return jsonify(error="Roblox Studio isn't connected. Install the plugin and enter your pairing code first. You were not charged."), 409
    if not token_service.charge(db(), u["id"], "studio"): return jsonify(error="Not enough RoTokens? Get more to continue creating!"), 402
    db().execute("UPDATE commands SET status='queued' WHERE id=?", (cid,))
    return jsonify(ok=True, message="Sent! Click Apply in the RoHiggs plugin inside Studio to approve it.")

init_db()
if __name__ == "__main__":
    app.run(port=5000)
