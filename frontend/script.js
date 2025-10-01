const ingestBtn = document.getElementById('ingestBtn');
const ingestOut = document.getElementById('ingestOut');
const askBtn = document.getElementById('askBtn');
const queryEl = document.getElementById('query');
const answerEl = document.getElementById('answer');
const sourcesEl = document.getElementById('sources');


ingestBtn.onclick = async () => {
  ingestOut.textContent = 'Ingesting...';
  const res = await fetch('/api/ingest', { method: 'POST' });
  const json = await res.json();
  ingestOut.textContent = JSON.stringify(json, null, 2);
};


askBtn.onclick = async () => {
  const query = queryEl.value.trim();
  if (!query) return;
  answerEl.textContent = 'Thinking...';
  sourcesEl.innerHTML = '';
  const res = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query }) });
  const json = await res.json();
  answerEl.textContent = json.answer || '(no answer)';
  (json.sources || []).forEach(s => {
    const li = document.createElement('li');
    li.textContent = s;
    sourcesEl.appendChild(li);
  });
};