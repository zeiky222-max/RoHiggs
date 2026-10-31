import os
ALLOWED_OPS = {"AddPart", "SetTimeOfDay", "AddTrees", "AddSpawn"}

def higgsfield_configured():
    return bool(os.environ.get("HIGGSFIELD_API_KEY"))

def generate(feature, prompt):
    """DEMO generator. No Higgsfield endpoint is bundled (none is invented);
    add real calls here once you have official API access."""
    prompt = prompt.strip()[:500]
    if feature == "script":
        text = ("-- DEMO script\nlocal part = script.Parent\npart.Touched:Connect(function(hit)\n"
                "  print(hit.Name .. ' touched me!')\nend)\n-- Idea: " + prompt)
    else:
        text = "Demo result for: " + prompt
    return {"demo": True, "text": text, "note": "Demo mode: no real AI service is connected."}

def plan_studio_ops(prompt):
    p = prompt.lower(); ops = []
    if "tree" in p or "forest" in p: ops.append({"op": "AddTrees", "count": 8})
    if "night" in p: ops.append({"op": "SetTimeOfDay", "time": "00:00:00"})
    if "spawn" in p: ops.append({"op": "AddSpawn"})
    if any(w in p for w in ("house", "mansion", "pool", "bigger", "castle", "city", "map", "room")):
        ops.append({"op": "AddPart", "name": "Floor", "size": [40, 1, 40], "position": [0, 0.5, 0], "color": [0, 230, 92]})
        ops.append({"op": "AddPart", "name": "Wall", "size": [40, 12, 2], "position": [0, 6, -20], "color": [200, 200, 200]})
    return validate_ops(ops)

def validate_ops(ops):
    """Only whitelisted operations ever reach the plugin."""
    return [o for o in ops[:20] if isinstance(o, dict) and o.get("op") in ALLOWED_OPS]

def describe(ops):
    if not ops:
        return "I can't turn that into Studio changes yet. Try 'Add trees' or 'Create a modern house'."
    return "Here is what I will do: " + ", ".join(o["op"] for o in ops) + "."
