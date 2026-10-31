-- RoHiggs Studio plugin. Save in Studio's Plugins folder. Enable "Allow HTTP Requests" for the game.
-- Safe by design: it only runs the 4 whitelisted operations below, and only after YOU click the button.
local HttpService = game:GetService("HttpService")
local History = game:GetService("ChangeHistoryService")
local BASE = "http://127.0.0.1:5000"   -- change to your server address
local token = plugin:GetSetting("rohiggs_token")

local toolbar = plugin:CreateToolbar("RoHiggs")
local pairBtn = toolbar:CreateButton("Pair", "Enter your code from the website", "")
local applyBtn = toolbar:CreateButton("Apply", "Approve and apply pending changes", "")

local function call(method, path, body, auth)
	local headers = {["Content-Type"] = "application/json"}
	if auth then headers["X-Plugin-Token"] = token end
	return HttpService:RequestAsync({Url = BASE .. path, Method = method, Headers = headers, Body = body and HttpService:JSONEncode(body) or nil})
end

local ops = {}
function ops.AddPart(o)
	local p = Instance.new("Part"); p.Anchored = true; p.Name = tostring(o.name or "Part")
	p.Size = Vector3.new(table.unpack(o.size)); p.Position = Vector3.new(table.unpack(o.position))
	p.Color = Color3.fromRGB(table.unpack(o.color)); p.Parent = workspace
end
function ops.SetTimeOfDay(o) game:GetService("Lighting").TimeOfDay = tostring(o.time) end
function ops.AddSpawn(o) local s = Instance.new("SpawnLocation"); s.Position = Vector3.new(0, 3, 0); s.Parent = workspace end
function ops.AddTrees(o)
	for i = 1, math.clamp(tonumber(o.count) or 5, 1, 20) do
		local t = Instance.new("Part"); t.Name = "Tree"; t.Anchored = true; t.Size = Vector3.new(2, 10, 2)
		t.Color = Color3.fromRGB(100, 70, 40); t.Position = Vector3.new(math.random(-60, 60), 5, math.random(-60, 60)); t.Parent = workspace
	end
end

pairBtn.Click:Connect(function()
	local code = plugin:GetSetting("rohiggs_code_input")
	warn("RoHiggs: set your code with plugin:SetSetting in the command bar, e.g. paste: ")
end)

applyBtn.Click:Connect(function()
	if not token then warn("RoHiggs: not paired yet. Run the pair step first."); return end
	local r = call("GET", "/api/plugin/pending", nil, true)
	if not r.Success then warn("RoHiggs: could not reach server"); return end
	for _, c in ipairs(HttpService:JSONDecode(r.Body).commands) do
		local rec = History:TryBeginRecording("RoHiggs change")   -- one Ctrl+Z undoes it
		for _, o in ipairs(c.ops) do
			local f = ops[o.op]; if f then pcall(f, o) end
		end
		if rec then History:FinishRecording(rec, Enum.FinishRecordingOperation.Commit) end
		call("POST", "/api/plugin/done/" .. c.id, {}, true)
	end
end)

-- Run once from the Studio command bar to pair:  RoHiggsPair("ABC123")
_G.RoHiggsPair = function(code)
	local r = call("POST", "/api/plugin/pair", {code = code})
	if r.Success then token = HttpService:JSONDecode(r.Body).token; plugin:SetSetting("rohiggs_token", token); print("RoHiggs paired!") else warn("Wrong code") end
end
