// YottaReal Chat – lightweight client
(function () {
  const API_URL = window.API_URL || "/api/chat"; // override if needed
  const chat = document.getElementById("chat");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("user-input");
  const yearEl = document.getElementById("year");
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  // Persist a session id so follow-ups keep context
  const SESSION_KEY = "yotta_session_id";
  let sessionId = localStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId = (crypto.randomUUID && crypto.randomUUID()) || String(Date.now());
    localStorage.setItem(SESSION_KEY, sessionId);
  }

  function sanitize(s) {
    const div = document.createElement("div");
    div.innerText = s == null ? "" : String(s);
    return div.innerHTML;
  }

  function addMessage(role, text, citations = []) {
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
      const list = citations
        .map((c) => `<a href="#" title="From local docs">${sanitize(c.source || c.id)}</a>`)
        .join(" • ");
      cites.innerHTML = `<strong>Sources:</strong> ${list}`;
      bubble.appendChild(cites);
    }

    wrap.appendChild(bubble);
    chat.appendChild(wrap);
    chat.scrollTop = chat.scrollHeight;
  }

  // Replace the last bot "Thinking…" bubble with the real response
  function replaceLastBot(text, citations) {
    for (let i = chat.children.length - 1; i >= 0; i--) {
      const node = chat.children[i];
      if (node.classList.contains("bot")) {
        chat.removeChild(node);
        break;
      }
    }
    addMessage("bot", text, citations);
  }

  // Send question to backend
  async function send(question) {
    // show user + thinking
    addMessage("user", question);
    addMessage("bot", "Thinking…");

    try {
      // NOTE: Most FastAPI examples in your repo expect {session_id, question, top_k}
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, question, top_k: 4 })
      });

      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || `HTTP ${res.status}`);
      }
      const data = await res.json();
      replaceLastBot(
        (data && data.answer) || "I don’t know based on the available documents.",
        (data && data.citations) || []
      );
    } catch (err) {
      console.error(err);
      replaceLastBot("Sorry — something went wrong.");
    }
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = (input.value || "").trim();
    if (!q) return;
    input.value = "";
    send(q);
  });

  // Friendly welcome
  addMessage("bot", "Hi! I’m Yotta - your property management assistant. Ask me about leases, fees, maintenance, or policies.");
})();
