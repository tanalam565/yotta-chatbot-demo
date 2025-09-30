const chat = document.getElementById('chat');
const form = document.getElementById('f');
const q = document.getElementById('q');
const ingestBtn = document.getElementById('ingest');

ingestBtn.addEventListener('click', async () => {
  ingestBtn.disabled = true;
  ingestBtn.textContent = 'Ingesting...';
  try {
    const r = await fetch('/api/ingest', { method: 'POST' });
    const data = await r.json();
    alert(`Ingested ${data.ingested_chunks} chunks`);
  } catch (e) {
    alert('Ingest failed. Check server logs.');
  } finally {
    ingestBtn.disabled = false;
    ingestBtn.textContent = 'Ingest sample docs';
  }
});

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const user = q.value.trim();
  if (!user) return;
  chat.insertAdjacentHTML('beforeend', `<div class="user">${escapeHtml(user)}</div>`);
  q.value = '';
  const r = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: user })
  });
  const data = await r.json();
  const sources = data.sources?.map(s => s.path || 'N/A').join('<br>') || '—';
  chat.insertAdjacentHTML('beforeend', `<div class="bot">${escapeHtml(data.answer)}<div style="font-size:12px;opacity:.7;margin-top:.25rem">Sources:<br>${sources}</div></div>`);
  chat.scrollTop = chat.scrollHeight;
});

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
