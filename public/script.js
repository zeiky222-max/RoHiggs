const $ = s => document.querySelector(s);
const esc = t => String(t ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let S = null, pending = null;
const TOOLS = {
  avatar: {t: "AI Avatar Creator", i: "🧍", b: "CREATE AVATAR", q: "Describe how your avatar looks", ex: ["A ninja with green hair", "A space explorer"]},
  video: {t: "AI Video Generator", i: "🎬", b: "CREATE VIDEO", q: "Describe your video", ex: ["My avatar dancing in a neon city"]},
  builder: {t: "AI Roblox Builder", i: "🧱", b: "BUILD WITH AI", q: "What should we build?", ex: ["Build a modern mansion", "Create a racing game map", "Build a futuristic city", "Create a beautiful forest", "Make a fantasy castle"]},
  script: {t: "AI Script Assistant", i: "</>", b: "ASK AI", q: "What should the script do?", ex: ["Make a door that opens when touched", "Make an NPC that walks around"]},
};
const CHIPS = ["Create a modern gaming house.", "Add trees around my house.", "Change the lighting to nighttime.", "Create a futuristic racing map.", "Add a swimming pool.", "Create a spawn location."];
const api = async (url, body, method) => {
  const r = await fetch(url, {method: method || (body ? "POST" : "GET"), headers: {"Content-Type": "application/json"}, body: body ? JSON.stringify(body) : undefined});
  const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.error || "Something went wrong. Try again."); return j;
};
const modal = h => { $("#mbody").innerHTML = h; $("#modal").hidden = false; };
const closeModal = () => $("#modal").hidden = true;
const info = (t, p) => modal(`<h3>${esc(t)}</h3><p>${esc(p)}</p>`);
function help() { modal(`<h3>Help</h3><p><b>Create an avatar / video:</b> tap a card, describe it, confirm the cost.</p><p><b>RoTokens:</b> each tool costs a few. You always see the price first.</p><p><b>Connect Roblox:</b> press LINK MY ROBLOX ACCOUNT and approve on Roblox.</p><p><b>Install the plugin:</b> copy studio_plugin/RoHiggsPlugin.lua into Studio's Plugins folder, then type your Studio code.</p><p><b>Send AI commands:</b> type in "Tell RoHiggs What to Build!", preview, apply, then click Apply inside Studio.</p>`); }
$("#helpBtn").onclick = help;

async function load() {
  S = await api("/api/state");
  for (const el of document.querySelectorAll(".rbx-icon")) el.style.backgroundImage = `url("data:image/svg+xml;utf8,${encodeURIComponent(document.querySelector('#rbx').innerHTML)}")`;
  ["#bal", "#bal2"].forEach(s => $(s).textContent = S.tokens + " RoTokens"); $("#bal3").textContent = S.tokens;
  const R = S.roblox, ok = R.status === "Connected"; $("#bigIcon").classList.toggle("on", ok);
  $("#status").innerHTML = `<h3>Status: <b>${esc(R.status)}</b></h3>` + (ok
    ? `<p>Roblox username: <b>${esc(R.name)}</b><br>Last connected: ${esc(R.time)} (UTC)<br>Studio plugin: ${S.studio ? "Connected" : "Not connected yet"}</p><button class="btn alt" id="disc">DISCONNECT</button> <a class="btn alt" href="https://bloxlink.gr/verify?server=6836061804292720" target="https://bloxlink.gr/verify?server=6836061804292720" rel="noopener">OPEN ROBLOX</a>`
    : `<p>Your account is not linked yet.${R.oauth_ready ? "" : '<br><span class="err">This server has no Roblox login keys yet, so linking is off (see README).</span>'}</p>`);
  if ($("#disc")) $("#disc").onclick = async () => { await api("/api/roblox/disconnect", {}); load(); };
  $("#tools").innerHTML = Object.entries(TOOLS).map(([k, t]) => `<button class="card tool" data-k="${k}"><div class="ico">${t.i}</div><h3>${t.t}</h3><p>${S.costs[k]} RoTokens</p><span class="btn">${t.b}</span></button>`).join("");
  document.querySelectorAll(".tool").forEach(b => b.onclick = () => openTool(b.dataset.k));
  $("#grid").innerHTML = S.projects.length ? S.projects.map(p => `<div class="card"><div class="thumb">${p.type === "script" ? "</>" : "✨"}</div><b>${esc(p.name)}</b><p>${esc(p.type)} · ${esc(p.created.slice(0, 10))}</p><button class="btn alt" data-o="${p.id}">OPEN</button> <button class="ghost" data-d="${p.id}">DELETE</button></div>`).join("") : "<p>Nothing here yet. Make something and press SAVE!</p>";
  document.querySelectorAll("[data-d]").forEach(b => b.onclick = async () => { await api("/api/projects/" + b.dataset.d, null, "DELETE"); load(); });
  document.querySelectorAll("[data-o]").forEach(b => b.onclick = () => { const p = S.projects.find(x => x.id == b.dataset.o); modal(`<h3>${esc(p.name)}</h3><pre>${esc(p.content)}</pre>`); });
  const names = {starter: "Starter", creator: "Creator", pro: "Pro Creator", ultimate: "Ultimate Creator"};
  $("#pkgs").innerHTML = Object.entries(S.packages).map(([k, v]) => `<div class="card"><h3>${names[k]}</h3><p class="code" style="font-size:26px;letter-spacing:0">${v.toLocaleString()}</p><button class="btn alt" data-p="${k}">GET (DEMO)</button></div>`).join("");
  document.querySelectorAll("[data-p]").forEach(b => b.onclick = async () => { await api("/api/tokens/demo-buy", {package: b.dataset.p}); load(); });
  $("#costs").innerHTML = Object.entries({avatar: "Avatar Creation", video: "Video Generation", builder: "Roblox Building Ideas", script: "AI Script Generation", studio: "AI Studio Assistance", image: "Image Generation"}).map(([k, n]) => `<tr><td>${n}</td><td>${S.costs[k]}</td></tr>`).join("");
  $("#hist").innerHTML = S.history.map(h => `<tr><td>${esc(h.reason)}</td><td>${h.amount > 0 ? "+" : ""}${h.amount}</td></tr>`).join("") || "<tr><td>No activity yet</td></tr>";
  if (location.search.includes("roblox=error")) $("#status").insertAdjacentHTML("beforeend", '<p class="err">Connection Error: Roblox could not verify you. Please try again.</p>');
}

function openTool(k) {
  const t = TOOLS[k];
  modal(`<h3>${t.t}</h3><p>${t.q}</p><textarea id="tp" rows="3" maxlength="500"></textarea><div class="chips">${t.ex.map(e => `<button>${esc(e)}</button>`).join("")}</div><p>This costs <b>${S.costs[k]} RoTokens</b>. You have ${S.tokens}.</p><button class="btn" id="go">${t.b}</button><div id="out"></div>`);
  document.querySelectorAll("#mbody .chips button").forEach(b => b.onclick = () => $("#tp").value = b.textContent);
  $("#go").onclick = async () => {
    if (!confirm(`Spend ${S.costs[k]} RoTokens?`)) return; $("#out").textContent = "Working…";
    try {
      const r = await api("/api/generate", {feature: k, prompt: $("#tp").value, confirm: true});
      $("#out").innerHTML = `<p class="err">${esc(r.note)}</p><pre>${esc(r.text)}</pre><button class="btn alt" id="sv">SAVE TO MY CREATIONS</button>`;
      $("#sv").onclick = async () => { await api("/api/projects", {name: $("#tp").value.slice(0, 40), type: k, content: r.text}); closeModal(); load(); };
      load();
    } catch (e) { $("#out").innerHTML = `<p class="err">${esc(e.message)}</p>`; }
  };
}

const say = (c, t) => { const p = document.createElement("p"); p.className = c; p.textContent = t; $("#log").append(p); $("#log").scrollTop = 1e6; };
$("#chips").innerHTML = CHIPS.map(c => `<button>${esc(c)}</button>`).join("");
document.querySelectorAll("#chips button").forEach(b => b.onclick = () => { $("#cmd").value = b.textContent; });
$("#sendBtn").onclick = async () => {
  const p = $("#cmd").value.trim(); if (!p) return; say("me", p);
  try {
    pending = await api("/api/studio/preview", {prompt: p});
    say("ai", pending.message + " (Preview only. Nothing has changed in Studio.)");
    $("#cost").textContent = `Cost: ${pending.cost} RoTokens`; $("#applyRow").hidden = !pending.ops.length;
  } catch (e) { say("ai", e.message); }
};
$("#applyBtn").onclick = async () => {
  if (!pending || !confirm(`Spend ${pending.cost} RoTokens?`)) return;
  try { const r = await api("/api/studio/apply/" + pending.id, {}); say("ai", r.message); $("#applyRow").hidden = true; pending = null; load(); }
  catch (e) { say("ai", e.message); }
};
$("#cancelBtn").onclick = () => { pending = null; $("#applyRow").hidden = true; say("ai", "Cancelled. Nothing was changed."); };
$("#linkBtn").onclick = async () => { try { location.href = (await api("/api/roblox/link")).url; } catch (e) { $("#status").insertAdjacentHTML("beforeend", `<p class="err">${esc(e.message)}</p>`); } };
$("#pairBtn").onclick = async () => { $("#pairOut").textContent = (await api("/api/studio/pair-code", {})).code; };
$("#modal").onclick = e => { if (e.target.id === "modal") closeModal(); };
load();
