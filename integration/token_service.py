COSTS = {"avatar": 10, "video": 25, "builder": 10, "script": 5, "studio": 20, "image": 10}
PACKAGES = {"starter": 100, "creator": 500, "pro": 1000, "ultimate": 5000}

def charge(db, uid, feature):
    """Atomic deduction. Returns True only if the user had enough tokens."""
    cost = COSTS[feature]
    cur = db.execute("UPDATE users SET tokens=tokens-? WHERE id=? AND tokens>=?", (cost, uid, cost))
    if cur.rowcount != 1:
        return False
    db.execute("INSERT INTO transactions(user_id,amount,reason) VALUES(?,?,?)", (uid, -cost, feature))
    return True

def refund(db, uid, feature):
    cost = COSTS[feature]
    db.execute("UPDATE users SET tokens=tokens+? WHERE id=?", (cost, uid))
    db.execute("INSERT INTO transactions(user_id,amount,reason) VALUES(?,?,?)", (uid, cost, "refund: " + feature))

def add_demo_package(db, uid, pkg):
    amt = PACKAGES[pkg]
    db.execute("UPDATE users SET tokens=tokens+? WHERE id=?", (amt, uid))
    db.execute("INSERT INTO transactions(user_id,amount,reason) VALUES(?,?,?)", (uid, amt, "demo package: " + pkg))
