const ingestBtn = document.getElementById('ingestBtn');
const ingestOut = document.getElementById('ingestOut');
const chatBox   = document.getElementById('chat');
const msgEl     = document.getElementById('msg');
const sendBtn   = document.getElementById('sendBtn');

// --- Helper: add chat bubbles ---
function addBubble(text, who = "bot") {
  const div = document.createElement("div");
  div.className = `bubble ${who}`;
  div.textContent = text;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

// --- Helper: add sources as small meta bubble ---
function addSources(sources = []) {
  if (!sources || sources.length === 0) return;
  const div = document.createElement("div");
  div.className = "bubble bot meta";
  div.innerHTML = `<strong>Sources:</strong><br>${sources.map(s => `• ${s}`).join("<br>")}`;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

// --- Ingest documents ---
ingestBtn.onclick = async () => {
  ingestOut.textContent = "Ingesting...";
  const res = await fetch("/api/ingest", { method: "POST" });
  const json = await res.json();
  ingestOut.textContent = JSON.stringify(json, null, 2);
};

// --- Send message ---
async function send() {
  const text = msgEl.value.trim();
  if (!text) return;

  // Show user bubble
  addBubble(text, "user");
  msgEl.value = "";

  // Show bot typing indicator
  addBubble("…", "bot");
  const typingBubble = chatBox.lastChild;

  // Call backend
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: text })
  });
  const json = await res.json();

  // Replace typing bubble with real answer
  typingBubble.textContent = json.answer || "(no answer)";
  addSources(json.sources);
}

sendBtn.onclick = send;
msgEl.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    send();
  }
});
