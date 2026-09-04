let docs = [], idx;

fetch('data/documents.json')
  .then(r => r.json())
  .then(async data => {
    docs = data;
    for (const d of docs) {
      try {
        d.text = await (await fetch('text/' + d.filename.replace('.pdf', '.txt'))).text();
      } catch { d.text = ''; }
    }
    idx = lunr(function () {
      this.ref('id');
      this.field('title', { boost: 10 });
      this.field('agency', { boost: 5 });
      this.field('author', { boost: 5 });
      this.field('topic', { boost: 5 });
      this.field('notes');
      this.field('text');
      docs.forEach(d => this.add(d));
    });
    fillFilter('agency');
    fillFilter('topic');
    render(docs);
  });

function fillFilter(field) {
  const sel = document.getElementById(field);
  [...new Set(docs.map(d => d[field]).filter(Boolean))].sort()
    .forEach(v => sel.add(new Option(v, v)));
  sel.onchange = run;
}

document.getElementById('search').oninput = run;

function run() {
  const q = document.getElementById('search').value.trim();
  const ag = document.getElementById('agency').value;
  const tp = document.getElementById('topic').value;
  let hits = q ? idx.search(q).map(h => docs.find(d => d.id === h.ref)) : docs;
  if (ag) hits = hits.filter(d => d.agency === ag);
  if (tp) hits = hits.filter(d => d.topic === tp);
  render(hits, q);
}

function render(list, q) {
  document.getElementById('count').textContent = list.length + ' documents';
  document.getElementById('results').innerHTML = list.map(d => `
    <div class="result">
      <h3><a href="${d.url}" target="_blank">${d.title}</a></h3>
      <div class="meta">${d.date} · ${d.agency} · ${d.topic} · ${d.status}</div>
      <div class="snippet">${snippet(d.text, q)}</div>
    </div>`).join('');
}

function snippet(text, q) {
  if (!q || !text) return '';
  const i = text.toLowerCase().indexOf(q.toLowerCase().split(' ')[0]);
  if (i < 0) return '';
  return '…' + text.slice(Math.max(0, i - 120), i + 180).replace(/\s+/g, ' ') + '…';
}