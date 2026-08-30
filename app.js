const byId = (id) => document.getElementById(id);
const ledger = [];
const pct = (x) => (x * 100).toFixed(1) + '%';

byId('valueForm').addEventListener('submit', (e) => {
  e.preventDefault();
  const odds = Number(byId('odds').value);
  const fair = Number(byId('prob').value) / 100;
  const implied = 1 / odds;
  const edge = fair - implied;
  const ev = fair * odds - 1;
  const qualifies = ev >= 0.025 && edge >= 0.02;
  const item = {
    event: byId('event').value,
    market: byId('market').value,
    odds,
    fair,
    edge,
    ev,
    status: qualifies ? 'PAPER' : 'AFVIS'
  };
  ledger.unshift(item);
  renderResult(item);
  renderLedger();
});

function renderResult(x) {
  byId('bankroll').textContent = Number(byId('bank').value).toLocaleString('da-DK') + ' kr.';
  byId('result').className = 'result ' + (x.status === 'PAPER' ? 'pass' : 'fail');
  byId('result').innerHTML = `<strong>${x.status === 'PAPER' ? 'Paper-kandidat' : 'Ingen kandidat'}</strong><div class="resultGrid"><span>Implied: <b>${pct(1 / x.odds)}</b></span><span>Fair: <b>${pct(x.fair)}</b></span><span>Edge: <b>${pct(x.edge)}</b></span><span>Model-EV: <b>${pct(x.ev)}</b></span></div><small>Gate: mindst 2,0 procentpoint edge og 2,5% model-EV. Et modelsignal er ikke en garanti for profit.</small>`;
}

function renderLedger() {
  byId('betCount').textContent = ledger.length;
  byId('ledger').innerHTML = ledger.map(x => `<tr><td>${safe(x.event)}</td><td>${safe(x.market)}</td><td>${x.odds.toFixed(2)}</td><td>${pct(x.fair)}</td><td>${pct(x.edge)}</td><td>Paper</td><td><span class="pill ${x.status === 'PAPER' ? 'ok' : 'no'}">${x.status}</span></td></tr>`).join('');
}

function safe(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}
