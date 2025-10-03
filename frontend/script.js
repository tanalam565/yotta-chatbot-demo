const chat = document.getElementById("chat");
const form = document.getElementById("chat-form");
const input = document.getElementById("user-input");

const SESSION_KEY = "yotta_session_id";
let sessionId = localStorage.getItem(SESSION_KEY);
if (!sessionId) {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    sessionId = window.crypto.randomUUID();
  } else {
    // Fallback if randomUUID not available
    sessionId = "sess-" + Date.now() + "-" + Math.random().toString(36).slice(2, 10);
  }
  localStorage.setItem(SESSION_KEY, sessionId);
}

function addMessage(role, text, citations=[]) {
  const wrap = document.createElement("div");
  wrap.className = `message ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";

  const meta = document.createElement("div");
  meta.className = "meta";
  meta.textContent = role === "user" ? "You" : "Yotta";

  const content = document.createElement("div");
  content.className = "content";
  content.innerHTML = sanitize(text).replace(/\n/g, "<br/>");

  bubble.appendChild(meta);
  bubble.appendChild(content);

  if (role === "bot" && citations && citations.length) {
    const cites = document.createElement("div");
    cites.className = "citations";
    const list = citations.map(c => `<a href="#" title="From local docs">${sanitize(c.source)}</a>`).join(" • ");
    cites.innerHTML = `<strong>Citations:</strong> ${list}`;
    bubble.appendChild(cites);
  }

  wrap.appendChild(bubble);
  chat.appendChild(wrap);
  chat.scrollTop = chat.scrollHeight;
}

function sanitize(s){
  const div = document.createElement("div");
  div.innerText = s;
  return div.innerHTML;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = input.value.trim();
  if (!q) return;

  addMessage("user", q);
  input.value = "";
  addMessage("bot", "Thinking…");

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: q, session_id: sessionId })  
    });

    if (!res.ok) {
      let detail = res.statusText;
      try {
        const errJson = await res.json();
        detail = (errJson && (errJson.detail || errJson.message)) || detail;
      } catch {}
      throw new Error(detail || "Request failed");
    }

    const data = await res.json();
    chat.removeChild(chat.lastChild); // remove "Thinking…"
    addMessage("bot", data.answer, data.citations || []);
  } catch (err) {
    chat.removeChild(chat.lastChild);
    addMessage("bot", `Sorry — ${err.message || "something went wrong."}`);
    console.error(err);
  }
});
