const PALETTE = ['#c1272d','#e08e45','#4a7c8c','#8f1c21','#d9a441','#6b8f71','#a35d6a','#3f6b8f'];

let DATA, SUBJECTS;

async function loadData() {
  const [reportRes, subjectsRes] = await Promise.all([
    fetch('data/report_data.json'),
    fetch('data/soggetti_index.json'),
  ]);
  if (!reportRes.ok || !subjectsRes.ok) {
    throw new Error(`Errore caricamento dati (report: ${reportRes.status}, soggetti: ${subjectsRes.status})`);
  }
  DATA = await reportRes.json();
  SUBJECTS = await subjectsRes.json();
}

function renderSintesiGenerale() {
  document.getElementById('heroSubtitle').textContent =
    `${DATA.meta.totale_audizioni.toLocaleString('it-IT')} audizioni analizzate su ${DATA.meta.totale_commissioni} organi`;

  document.getElementById('metaWarning').innerHTML =
    `<strong>Nota sulla copertura dei dati:</strong> ${DATA.meta.nota_senato} Analisi limitata alla Camera dei Deputati.`;

  // KPI cards
  const kpis = [
    ['Audizioni totali', DATA.meta.totale_audizioni.toLocaleString('it-IT')],
    ['Organi/Commissioni coinvolti', DATA.meta.totale_commissioni],
    ['Audizioni con atto collegato', DATA.meta.audizioni_con_atto_collegato.toLocaleString('it-IT')],
    ['Provvedimenti distinti arricchiti', DATA.meta.atti_distinti_arricchiti],
  ];
  document.getElementById('kpiRow').innerHTML = kpis.map(([label, value]) => `
    <div class="col-6 col-lg-3">
      <div class="card kpi-card p-3 text-center h-100">
        <div class="kpi-value">${value}</div>
        <div class="text-muted small">${label}</div>
      </div>
    </div>`).join('');

  // Top commissioni
  const topCommittees = DATA.ranking_commissioni.slice(0, 10);
  new Chart(document.getElementById('chartTopCommittees'), {
    type: 'bar',
    data: {
      labels: topCommittees.map(c => c[0].length > 38 ? c[0].slice(0,36)+'…' : c[0]),
      datasets: [{ label: 'Audizioni', data: topCommittees.map(c => c[1]), backgroundColor: PALETTE[0] }]
    },
    options: { indexAxis: 'y', plugins: { legend: { display:false } }, scales: { x: { beginAtZero:true } } }
  });

  // Categorie
  const catEntries = Object.entries(DATA.sintesi_generale.categorie).sort((a,b)=>b[1]-a[1]);
  new Chart(document.getElementById('chartCategories'), {
    type: 'bar',
    data: {
      labels: catEntries.map(c=>c[0]),
      datasets: [{ label:'Audizioni', data: catEntries.map(c=>c[1]), backgroundColor: PALETTE[1] }]
    },
    options: { indexAxis:'y', plugins:{legend:{display:false}}, scales:{ x:{ beginAtZero:true } } }
  });

  // Top soggetti
  const topSubj = DATA.sintesi_generale.top_soggetti.slice(0, 15);
  new Chart(document.getElementById('chartTopSubjects'), {
    type: 'bar',
    data: {
      labels: topSubj.map(s=>s[0]),
      datasets: [{ label:'Audizioni', data: topSubj.map(s=>s[1]), backgroundColor: PALETTE[2] }]
    },
    options: { indexAxis:'y', plugins:{legend:{display:false}}, scales:{ x:{ beginAtZero:true } } }
  });

  // Timeline
  const timeline = DATA.sintesi_generale.andamento_mensile;
  new Chart(document.getElementById('chartTimeline'), {
    type: 'line',
    data: {
      labels: timeline.map(t=>t[0]),
      datasets: [{ label:'Audizioni/mese', data: timeline.map(t=>t[1]), borderColor: PALETTE[3], backgroundColor: PALETTE[3]+'33', fill:true, tension:.25 }]
    },
    options: { plugins:{legend:{display:false}}, scales:{ x:{ ticks:{ maxTicksLimit: 12 } } } }
  });

  // Tipologia atti
  const tipologia = Object.entries(DATA.sintesi_generale.tipologia_atti);
  new Chart(document.getElementById('chartTipologia'), {
    type: 'doughnut',
    data: { labels: tipologia.map(t=>t[0]), datasets:[{ data: tipologia.map(t=>t[1]), backgroundColor: PALETTE }] },
  });

  // Fase iter
  const fase = Object.entries(DATA.sintesi_generale.fase_iter);
  new Chart(document.getElementById('chartFaseIter'), {
    type: 'doughnut',
    data: { labels: fase.map(t=>t[0]), datasets:[{ data: fase.map(t=>t[1]), backgroundColor: PALETTE.slice().reverse() }] },
  });
}

function renderCommissioni() {
  const listEl = document.getElementById('committeeList');
  const committeesSorted = DATA.ranking_commissioni.map(([name]) => name);

  function committeeCardHtml(name, idx) {
    const d = DATA.per_commissione[name];
    const catRows = Object.entries(d.categorie).filter(([,v])=>v>0).sort((a,b)=>b[1]-a[1])
      .map(([k,v]) => `<tr><td>${k}</td><td class="text-end">${v}</td></tr>`).join('');
    const tipRows = Object.entries(d.tipologia_atti)
      .map(([k,v]) => `<tr><td>${k}</td><td class="text-end">${v}</td></tr>`).join('') || '<tr><td colspan="2" class="text-muted">Nessun atto legislativo collegato</td></tr>';
    const faseRows = Object.entries(d.fase_iter)
      .map(([k,v]) => `<tr><td>${k}</td><td class="text-end">${v}</td></tr>`).join('') || '<tr><td colspan="2" class="text-muted">—</td></tr>';
    const topPills = d.top_soggetti.map(([n,v]) => `<span class="top-soggetto-pill">${n} · ${v}</span>`).join(' ') || '<span class="text-muted">Nessuna entità nota riconosciuta</span>';

    return `
    <div class="card committee-card mb-2" data-name="${name.toLowerCase()}">
      <div class="card-header d-flex justify-content-between align-items-center" data-bs-toggle="collapse" data-bs-target="#coll${idx}">
        <span><strong>${name}</strong></span>
        <span class="badge bg-danger rounded-pill">${d.totale_audizioni} audizioni</span>
      </div>
      <div class="collapse" id="coll${idx}">
        <div class="card-body">
          <div class="row g-3">
            <div class="col-md-4">
              <h6 class="small text-uppercase text-muted">Categoria soggetti auditi</h6>
              <table class="table table-sm">${catRows}</table>
            </div>
            <div class="col-md-4">
              <h6 class="small text-uppercase text-muted">Tipologia atti collegati</h6>
              <table class="table table-sm">${tipRows}</table>
              <h6 class="small text-uppercase text-muted mt-3">Fase iter</h6>
              <table class="table table-sm">${faseRows}</table>
            </div>
            <div class="col-md-4">
              <h6 class="small text-uppercase text-muted">Soggetti più auditi (entità riconosciute)</h6>
              <div>${topPills}</div>
              <p class="small text-muted mt-2 mb-0">Atti legislativi distinti collegati: ${d.n_atti_distinti}</p>
            </div>
          </div>
        </div>
      </div>
    </div>`;
  }

  listEl.innerHTML = committeesSorted.map(committeeCardHtml).join('');

  document.getElementById('committeeSearch').addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase();
    document.querySelectorAll('.committee-card').forEach(card => {
      card.style.display = card.dataset.name.includes(q) ? '' : 'none';
    });
  });
}

// ==================== Soggetti auditi: ranking, ricerca, dettaglio ====================

let ALL_SUBJECTS, SUBJECTS_BY_SLUG;
let detailChart = null;

function normalizeText(s) {
  return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
}

function typeBadge(type) {
  return type === 'organization'
    ? '<span class="badge bg-danger">Organizzazione</span>'
    : '<span class="badge bg-secondary">Persona</span>';
}

const RANKING_CHUNK_SIZE = 40;

function attachSubjectRowHandlers(rows) {
  rows.forEach(row => {
    row.addEventListener('click', () => {
      window.location.hash = `soggetto=${row.dataset.type}:${row.dataset.slug}`;
    });
  });
}

function setupInfiniteRanking({ items, type, bodyId, sentinelId, rowHtml }) {
  const body = document.getElementById(bodyId);
  let rendered = 0;

  function renderNextChunk() {
    const next = items.slice(rendered, rendered + RANKING_CHUNK_SIZE);
    if (!next.length) return;

    const sentinel = document.getElementById(sentinelId);
    const rowsHtml = next.map((s, i) => rowHtml(s, rendered + i)).join('');
    sentinel.insertAdjacentHTML('beforebegin', rowsHtml);
    attachSubjectRowHandlers(Array.from(body.querySelectorAll('.subject-row')).slice(rendered));
    rendered += next.length;

    if (rendered >= items.length) {
      sentinel.remove();
      observer.disconnect();
    }
  }

  body.innerHTML = `<tr id="${sentinelId}"><td colspan="4" class="p-0 border-0"></td></tr>`;
  const sentinel = document.getElementById(sentinelId);
  const scrollContainer = body.closest('.table-responsive');

  const observer = new IntersectionObserver((entries) => {
    if (entries.some(e => e.isIntersecting)) renderNextChunk();
  }, { root: scrollContainer, rootMargin: '200px' });

  observer.observe(sentinel);
  renderNextChunk();
}

function renderRankings() {
  setupInfiniteRanking({
    items: SUBJECTS.organizzazioni,
    type: 'organization',
    bodyId: 'orgRankingBody',
    sentinelId: 'orgRankingSentinel',
    rowHtml: (s, i) => `
    <tr class="subject-row" role="button" data-type="organization" data-slug="${s.slug}">
      <td>${i + 1}</td><td>${s.name}</td>
      <td><span class="small text-muted">${s.category || ''}</span></td>
      <td class="text-end">${s.count}</td>
    </tr>`,
  });

  setupInfiniteRanking({
    items: SUBJECTS.persone,
    type: 'person',
    bodyId: 'personRankingBody',
    sentinelId: 'personRankingSentinel',
    rowHtml: (s, i) => `
    <tr class="subject-row" role="button" data-type="person" data-slug="${s.slug}">
      <td>${i + 1}</td><td>${s.name}</td>
      <td class="text-end">${s.count}</td>
    </tr>`,
  });
}

function renderDropdown(dropdown, matches) {
  let activeIdx = -1;
  if (!matches.length) { dropdown.style.display = 'none'; dropdown.innerHTML = ''; return; }
  dropdown.innerHTML = matches.map((s, i) => `
    <button type="button" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"
            data-type="${s.type}" data-slug="${s.slug}" data-idx="${i}">
      <span>${s.name} ${typeBadge(s.type)}</span>
      <span class="badge bg-light text-dark border">${s.count}</span>
    </button>`).join('');
  dropdown.style.display = 'block';
  dropdown.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('click', () => {
      window.location.hash = `soggetto=${btn.dataset.type}:${btn.dataset.slug}`;
      dropdown.style.display = 'none';
    });
  });
}

function setupSearch() {
  const searchInput = document.getElementById('subjectSearch');
  const dropdown = document.getElementById('subjectDropdown');
  let activeIdx = -1;

  searchInput.addEventListener('input', (e) => {
    const q = normalizeText(e.target.value.trim());
    if (q.length < 3) { renderDropdown(dropdown, []); return; }
    const matches = ALL_SUBJECTS
      .filter(s => normalizeText(s.name).includes(q))
      .sort((a, b) => b.count - a.count)
      .slice(0, 20);
    renderDropdown(dropdown, matches);
    activeIdx = -1;
  });

  searchInput.addEventListener('keydown', (e) => {
    const items = dropdown.querySelectorAll('button');
    if (!items.length) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); activeIdx = Math.min(activeIdx + 1, items.length - 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); activeIdx = Math.max(activeIdx - 1, 0); }
    else if (e.key === 'Enter') { if (activeIdx >= 0) items[activeIdx].click(); return; }
    else if (e.key === 'Escape') { dropdown.style.display = 'none'; return; }
    else return;
    items.forEach(el => el.classList.remove('active'));
    items[activeIdx].classList.add('active');
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('#subjectSearch') && !e.target.closest('#subjectDropdown')) {
      dropdown.style.display = 'none';
    }
  });
}

function renderSubjectDetail(subject) {
  const panel = document.getElementById('subjectDetail');
  const committeeRows = subject.committees.map(([name, n]) =>
    `<tr><td>${name}</td><td class="text-end">${n}</td></tr>`).join('');
  const audizioniRows = subject.audizioni.map(a => `
    <tr>
      <td class="text-nowrap">${a.date || '—'}</td>
      <td>${a.committee}</td>
      <td>${a.title}</td>
      <td>${a.bulletin_url ? `<a href="${a.bulletin_url}" target="_blank" rel="noopener">bollettino</a>` : ''}</td>
    </tr>`).join('');

  panel.innerHTML = `
    <div class="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-3">
      <div>
        <h4 class="fw-bold mb-1">${subject.name} ${typeBadge(subject.type)}</h4>
        ${subject.category ? `<span class="badge badge-cat">${subject.category}</span>` : ''}
      </div>
      <a href="#" class="btn btn-outline-secondary btn-sm" id="closeDetailBtn">← Torna all'elenco</a>
    </div>
    <div class="row g-3 mb-3">
      <div class="col-6 col-lg-3"><div class="card kpi-card p-3 text-center h-100">
        <div class="kpi-value">${subject.count}</div><div class="text-muted small">Audizioni totali</div></div></div>
      <div class="col-6 col-lg-3"><div class="card kpi-card p-3 text-center h-100">
        <div class="kpi-value">${subject.committees.length}</div><div class="text-muted small">Commissioni coinvolte</div></div></div>
      <div class="col-6 col-lg-3"><div class="card kpi-card p-3 text-center h-100">
        <div class="kpi-value" style="font-size:1.1rem;">${subject.date_min || '—'}</div><div class="text-muted small">Prima audizione</div></div></div>
      <div class="col-6 col-lg-3"><div class="card kpi-card p-3 text-center h-100">
        <div class="kpi-value" style="font-size:1.1rem;">${subject.date_max || '—'}</div><div class="text-muted small">Ultima audizione</div></div></div>
    </div>
    <div class="row g-3">
      <div class="col-lg-5">
        <h6 class="fw-bold">Audizioni per commissione</h6>
        <canvas id="subjectDetailChart" height="220"></canvas>
        <table class="table table-sm mt-2">${committeeRows}</table>
      </div>
      <div class="col-lg-7">
        <h6 class="fw-bold">Cronologia audizioni</h6>
        <div class="table-responsive" style="max-height:420px; overflow-y:auto;">
          <table class="table table-sm table-hover">
            <thead><tr><th>Data</th><th>Commissione</th><th>Titolo</th><th></th></tr></thead>
            <tbody>${audizioniRows}</tbody>
          </table>
        </div>
      </div>
    </div>`;

  panel.style.display = 'block';
  document.getElementById('subjectRankings').style.display = 'none';
  document.getElementById('closeDetailBtn').addEventListener('click', (e) => {
    e.preventDefault();
    window.location.hash = '';
  });

  if (detailChart) detailChart.destroy();
  const top = subject.committees.slice(0, 8);
  detailChart = new Chart(document.getElementById('subjectDetailChart'), {
    type: 'bar',
    data: { labels: top.map(c => c[0].length > 28 ? c[0].slice(0,26)+'…' : c[0]),
             datasets: [{ data: top.map(c => c[1]), backgroundColor: PALETTE[0] }] },
    options: { indexAxis:'y', plugins:{legend:{display:false}}, scales:{x:{beginAtZero:true}} }
  });

  panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function handleHashChange() {
  const m = window.location.hash.match(/^#soggetto=(person|organization):(.+)$/);
  const panel = document.getElementById('subjectDetail');
  if (!m) {
    panel.style.display = 'none';
    document.getElementById('subjectRankings').style.display = '';
    return;
  }
  const subject = SUBJECTS_BY_SLUG[`${m[1]}:${decodeURIComponent(m[2])}`];
  if (!subject) { panel.style.display = 'none'; document.getElementById('subjectRankings').style.display = ''; return; }
  renderSubjectDetail(subject);
}

function renderSoggettiAuditi() {
  ALL_SUBJECTS = [
    ...SUBJECTS.persone.map(s => ({...s})),
    ...SUBJECTS.organizzazioni.map(s => ({...s})),
  ];
  SUBJECTS_BY_SLUG = Object.fromEntries(ALL_SUBJECTS.map(s => [`${s.type}:${s.slug}`, s]));

  document.getElementById('subjectsMeta').textContent =
    `${SUBJECTS.persone.length.toLocaleString('it-IT')} persone, ${SUBJECTS.organizzazioni.length.toLocaleString('it-IT')} organizzazioni`;
  document.getElementById('orgRankCount').textContent = `${SUBJECTS.organizzazioni.length} totali`;
  document.getElementById('personRankCount').textContent = `${SUBJECTS.persone.length} totali`;

  renderRankings();
  setupSearch();

  window.addEventListener('hashchange', handleHashChange);
  handleHashChange();
}

async function main() {
  try {
    await loadData();
  } catch (err) {
    document.getElementById('metaWarning').innerHTML =
      `<strong>Errore nel caricamento dei dati:</strong> ${err.message}. Se hai aperto questo file direttamente dal filesystem (file://), apri invece il progetto tramite un server locale (es. <code>python3 -m http.server</code>) o consultalo online: i dati sono caricati con <code>fetch()</code> da <code>data/report_data.json</code> e <code>data/soggetti_index.json</code>, bloccato dai browser per i file locali.`;
    return;
  }
  renderSintesiGenerale();
  renderCommissioni();
  renderSoggettiAuditi();
}

main();
