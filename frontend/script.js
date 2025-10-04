const chat = document.getElementById("chat");
const form = document.getElementById("chat-form");
const input = document.getElementById("user-input");
const uploadBtn = document.getElementById("upload-btn");
const clearBtn = document.getElementById("clear-btn");
const fileInput = document.getElementById("file-input");
const uploadStatus = document.getElementById("upload-status");
const yearSpan = document.getElementById("year");
const uploadedFilesDiv = document.getElementById("uploaded-files");
const fileListDiv = document.getElementById("file-list");

// Set current year
yearSpan.textContent = new Date().getFullYear();

// USE sessionStorage instead of localStorage - clears when browser closes
const SESSION_KEY = "yotta_session_id";
let sessionId = sessionStorage.getItem(SESSION_KEY) || (function(){
  const id = (crypto && crypto.randomUUID) ? crypto.randomUUID() : ("sess-" + Date.now() + "-" + Math.random().toString(36).slice(2));
  sessionStorage.setItem(SESSION_KEY, id);  // Changed to sessionStorage
  return id;
})();

// Track uploaded files for this session
let uploadedFiles = [];

function displayUploadedFiles() {
  if (uploadedFiles.length === 0) {
    uploadedFilesDiv.style.display = 'none';
    return;
  }
  
  uploadedFilesDiv.style.display = 'block';
  fileListDiv.innerHTML = '';
  
  uploadedFiles.forEach((filename, index) => {
    const item = document.createElement('div');
    item.className = 'file-item';
    item.innerHTML = `
      <span>📄 ${sanitize(filename)}</span>
      <button class="remove-btn" data-index="${index}" title="Remove">×</button>
    `;
    fileListDiv.appendChild(item);
  });
  
  // Add remove handlers
  fileListDiv.querySelectorAll('.remove-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const index = parseInt(e.target.getAttribute('data-index'));
      uploadedFiles.splice(index, 1);
      displayUploadedFiles();
    });
  });
}

// AUTO-CLEANUP when browser/tab closes
window.addEventListener('beforeunload', () => {
  // Use sendBeacon for reliable cleanup during page unload
  const formData = new FormData();
  formData.append('session_id', sessionId);
  
  // sendBeacon is designed for cleanup tasks during page unload
  navigator.sendBeacon('/api/clear-session', formData);
});

// Handle file upload
uploadBtn.addEventListener("click", async () => {
  const files = fileInput.files;
  if (!files || files.length === 0) {
    uploadStatus.textContent = "No files selected";
    setTimeout(() => uploadStatus.textContent = "", 3000);
    return;
  }

  uploadStatus.textContent = `Uploading ${files.length} file(s)...`;

  try {
    const fd = new FormData();
    fd.append("session_id", sessionId);
    for (const f of files) fd.append("files", f);
    
    const res = await fetch("/api/upload", { 
      method: "POST", 
      body: fd 
    });

    if (!res.ok) {
      let detail = res.statusText;
      try { 
        const errJson = await res.json(); 
        detail = errJson.detail || errJson.message || detail; 
      } catch {}
      throw new Error(detail || "Upload failed");
    }

    const data = await res.json();
    
    // Add successfully uploaded files to the list
    if (data.saved && data.saved.length > 0) {
      uploadedFiles.push(...data.saved);
      displayUploadedFiles();
    }
    
    uploadStatus.textContent = `✓ ${data.saved.length} file(s) uploaded`;
    fileInput.value = "";
    
    setTimeout(() => {
      uploadStatus.textContent = "";
    }, 3000);
  } catch (err) {
    uploadStatus.textContent = `✗ Upload failed: ${err.message}`;
    console.error(err);
  }
});

// MANUAL clear session button
clearBtn.addEventListener("click", async () => {
  if (!confirm('This will clear all uploaded files and chat history. Continue?')) {
    return;
  }
  
  uploadStatus.textContent = "Clearing session...";
  
  try {
    const res = await fetch("/api/clear-session", {
      method: "POST",
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: `session_id=${sessionId}`
    });
    
    if (!res.ok) {
      throw new Error("Failed to clear session");
    }
    
    // Clear local state
    uploadedFiles = [];
    displayUploadedFiles();
    chat.innerHTML = '';
    
    uploadStatus.textContent = "✓ Session cleared";
    setTimeout(() => {
      uploadStatus.textContent = "";
    }, 3000);
  } catch (err) {
    uploadStatus.textContent = `✗ Clear failed: ${err.message}`;
    console.error(err);
  }
});

// Handle chat form submission
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
      body: JSON.stringify({ 
        message: q, 
        session_id: sessionId 
      })
    });

    if (!res.ok) {
      let detail = res.statusText;
      try { 
        const errJson = await res.json(); 
        detail = errJson.detail || errJson.message || detail; 
      } catch {}
      throw new Error(detail || "Request failed");
    }

    const data = await res.json();
    chat.removeChild(chat.lastChild);
    addMessage("bot", data.answer, data.citations || []);
  } catch (err) {
    chat.removeChild(chat.lastChild);
    addMessage("bot", `Sorry — ${err.message || "something went wrong."}`);
    console.error(err);
  }
});

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
  content.innerHTML = sanitize(text || "").replace(/\n/g, "<br/>");

  bubble.appendChild(meta);
  bubble.appendChild(content);

  if (role === "bot" && citations && citations.length) {
    const cites = document.createElement("div");
    cites.className = "citations";
    const list = citations.map(c => {
      const source = sanitize(c.source + (c.page ? ` (page ${c.page})` : c.ocr ? " (OCR)" : ""));
      return c.url ? `<a href="${sanitize(c.url)}" target="_blank">${source}</a>` : source;
    }).join(" • ");
    cites.innerHTML = `<strong>Citations:</strong> ${list}`;
    bubble.appendChild(cites);
  }

  wrap.appendChild(bubble);
  chat.appendChild(wrap);
  chat.scrollTop = chat.scrollHeight;
}

function sanitize(s) { 
  const d = document.createElement("div"); 
  d.innerText = s; 
  return d.innerHTML; 
}

// Initialize uploaded files display
displayUploadedFiles();