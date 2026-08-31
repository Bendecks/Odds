const byId = id => document.getElementById(id);
const pct = x => Number.isFinite(Number(x)) ? (Number(x) * 100).toFixed(1) + '%' : '-';

function safe(s) {
  const d = document.createElement('div');
  d.textContent = String(s ?? '');
  return d.innerHTML;
}

function num(v, digits = 2) {
  const n = Number(v);
  return Number.isFinite(n) ? n.toFixed(digits) : '-';
}

function age(ts) {
  if (!ts) return '';
  const t = new Date(ts).getTime();
  if (!Number.isFinite(t)) return 'Tidspunkt ukendt';
  const m = Math.max(0, Math.round((Date.now() - t) / 60000));
  return `${m} min. gammel`;
}

function when(ts) {
  if (!ts) return '-';
  const d = new Date(ts);
  return Number.isFinite(d.getTime()) ? d.toLocaleString('da-DK', { dateStyle: 'short', timeStyle: 'short' }) : '-';
}

async function loadDecision() {
  try {
    const r = await fetch('output/latest_decision.json?' + Date.now());
    if (!r.ok) throw new Error('decision unavailable');
    const d = await r.json();
    byId('bankroll').textContent = Number(d.bankroll || 50).toLocaleString('da-DK') + ' kr.';
    byId('mode').textContent = d.mode === 'LIVE' ? 'LIVE' : 'PAPER';
    const box = byId('result');
    const pick = d.decision === 'PLAY' || d.decision === 'PAPER PICK';
    if (pick) {
      const stakeLabel = d.decision === 'PLAY' ? 'Indsats' : 'Paper indsats';
      box.className = 'result ' + (d.decision === 'PLAY' ? 'pass' : 'paper');
      box.innerHTML = `<strong>${safe(d.decision)}</strong><h2>${safe(d.event)}</h2><h1>${safe(d.pick)}</h1><div class="resultGrid"><span>Bet365 odds <b>${num(d.odds)}</b></span><span>Minimum <b>${num(d.minimum_odds)}</b></span><span>${stakeLabel} <b>${num(d.stake)} kr.</b></span><span>Edge <b>${pct(d.edge)}</b></span></div><small>${safe(age(d.price_timestamp))}</small>`;
    } else {
      box.className = 'result fail';
      box.innerHTML = `<strong>NO BET</strong><p>${safe(d.reason || 'Ingen kvalificeret value lige nu.')}</p>`;
    }
  } catch (e) {
    byId('result').className = 'result muted';
    byId('result').textContent = 'Ingen aktuel beslutning tilgængelig.';
  }
}

async function loadOperational() {
  try {
    const r = await fetch('output/operational_status.json?' + Date.now());
    if (!r.ok) throw new Error('operational unavailable');
    const d = await r.json();
    const f = d.funnel || {};
    const p = d.provider || {};
    byId('funnel-bottleneck').textContent = d.bottleneck || 'Driftsstatus er klar.';
    byId('funnel-candidates').textContent = Number(f.candidate_rows || 0);
    byId('funnel-fair').textContent = Number(f.fair_probability_rows || 0);
    byId('funnel-exact').textContent = Number(f.exact_bet365_rows || 0);
    byId('funnel-fresh').textContent = Number(f.fresh_exact_bet365_rows || 0);
    byId('funnel-depth').textContent = Number(f.reference_depth_ready_rows || 0);
    byId('funnel-edge').textContent = Number(f.positive_edge_rows || 0);
    byId('funnel-ev').textContent = Number(f.ev_ready_rows || 0);
    byId('funnel-qualified').textContent = Number(f.qualified_now_rows || 0);
    byId('provider-events').textContent = `Bet365 events: ${p.bet365_events_available ?? '-'} / queried ${p.events_queried ?? '-'}`;
    const callParts = [
      p.provider_call_attempts != null ? `${p.provider_call_attempts} forsøg` : null,
      p.odds_multi_calls != null ? `${p.odds_multi_calls} multi` : null,
      p.fallback_odds_calls != null ? `${p.fallback_odds_calls} fallback` : null
    ].filter(Boolean);
    byId('provider-calls').textContent = `API calls: ${callParts.join(' · ') || '-'}`;
    byId('provider-markets').textContent = `Markets: ${p.unique_markets ?? '-'} · observations ${p.raw_market_observations ?? '-'}`;
  } catch (e) {
    byId('funnel-bottleneck').textContent = 'Driftsstatus er midlertidigt utilgængelig.';
  }
}

async function loadPaperHistory() {
  try {
    const r = await fetch('output/paper_pick_history.json?' + Date.now());
    if (!r.ok) throw new Error('history unavailable');
    const d = await r.json();
    byId('paper-count').textContent = Number(d.paper_picks || 0);
    byId('paper-open').textContent = Number(d.open_picks || 0);
    byId('paper-profit').textContent = d.decisive_picks ? `${num(d.profit_dkk)} kr.` : '-';
    byId('paper-roi').textContent = d.roi_pct == null ? '-' : num(d.roi_pct, 1) + '%';
    const box = byId('paper-history');
    const rows = Array.isArray(d.rows) ? d.rows : [];
    if (!rows.length) {
      box.className = 'history muted';
      box.textContent = 'Ingen paper picks endnu.';
      return;
    }
    box.className = 'history';
    box.innerHTML = rows.map(x => {
      const state = x.result === 'open' ? 'ÅBEN' : String(x.result || '').toUpperCase();
      const profit = x.profit_dkk == null ? '-' : `${Number(x.profit_dkk) >= 0 ? '+' : ''}${num(x.profit_dkk)} kr.`;
      const clv = x.clv_pct == null ? '-' : `${num(x.clv_pct, 2)}%`;
      return `<article class="pickRow"><div><small>${safe(when(x.recorded_at))} · ${safe(state)}</small><strong>${safe(x.event)}</strong><span>${safe(x.pick)} @ ${num(x.odds)} · ${num(x.stake_dkk)} kr.</span></div><div class="pickMetrics"><span>Edge <b>${pct(x.edge)}</b></span><span>CLV <b>${clv}</b></span><span>P/L <b>${profit}</b></span></div></article>`;
    }).join('');
  } catch (e) {
    byId('paper-history').className = 'history muted';
    byId('paper-history').textContent = 'Paper-historikken er midlertidigt utilgængelig.';
  }
}

async function loadValidation() {
  try {
    const r = await fetch('output/model_validation_readiness.json?' + Date.now());
    if (!r.ok) throw new Error('validation unavailable');
    const d = await r.json();
    const n = Number(d.settled_decisive_bets || 0);
    byId('settled').textContent = `${n} / 300`;
    byId('roi').textContent = d.roi_pct == null ? '-' : num(d.roi_pct, 1) + '%';
    byId('clv').textContent = d.mean_clv_pct == null ? '-' : num(d.mean_clv_pct, 2) + '%';
    byId('calibration').textContent = d.brier_score == null ? '-' : 'Brier ' + num(d.brier_score, 3);
    const ci = d.roi_bootstrap_95_pct;
    byId('validation-note').textContent = Array.isArray(ci) ? `95% bootstrap ROI: ${num(ci[0], 1)}% til ${num(ci[1], 1)}%. PAPER fortsætter indtil dokumentationen er stærk nok.` : 'PAPER fortsætter, mens modellen samler dokumentation.';
  } catch (e) {
    byId('validation-note').textContent = 'Valideringsstatus er midlertidigt utilgængelig.';
  }
}

function refresh() {
  loadDecision();
  loadOperational();
  loadPaperHistory();
  loadValidation();
}

refresh();
setInterval(refresh, 60000);
