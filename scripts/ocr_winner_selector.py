import json
import os
import math
import pathlib
import re
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

ROOT = pathlib.Path('.')
OUT = ROOT / 'output'
ANALYSIS_JSON = OUT / 'ocr_possible_bets_analysis.json'
FINAL_PICKS_JSON = OUT / 'ocr_final_picks.json'
FINAL_PICKS_MD = OUT / 'ocr_final_picks.md'

MAX_PICKS = int(os.getenv('OCR_FINAL_MAX_PICKS', '25'))
MIN_ODDS = float(os.getenv('OCR_FINAL_MIN_ODDS', '1.55'))
MAX_ODDS = float(os.getenv('OCR_FINAL_MAX_ODDS', '2.10'))
SOON_HOURS = float(os.getenv('OCR_FINAL_SOON_HOURS', '12'))
MIN_START_MINUTES = float(os.getenv('OCR_FINAL_MIN_START_MINUTES', '5'))
REQUIRED_CONFIDENCE = os.getenv('OCR_FINAL_CONFIDENCE', 'high')
TIMEZONE_NAME = os.getenv('OCR_TIMEZONE', 'Europe/Copenhagen')

MIN_NORMALIZED_PROB = float(os.getenv('OCR_MIN_NORMALIZED_PROB', '0.44'))
MIN_TEAM_PROB_MARGIN = float(os.getenv('OCR_MIN_TEAM_PROB_MARGIN', '0.05'))
MIN_OVERROUND = float(os.getenv('OCR_MIN_OVERROUND', '1.00'))
MAX_OVERROUND = float(os.getenv('OCR_MAX_OVERROUND', '1.25'))
MAX_SECTION_EVENT_COUNT = int(os.getenv('OCR_MAX_SECTION_EVENT_COUNT', '3'))

DEFAULT_BANKROLL_DKK = float(os.getenv('OCR_BANKROLL_DKK', '100'))
MAX_TOTAL_STAKE_PCT = float(os.getenv('OCR_MAX_TOTAL_STAKE_PCT', '0.10'))
MIN_STAKE_DKK = float(os.getenv('OCR_MIN_STAKE_DKK', '1'))
MAX_STAKE_DKK = float(os.getenv('OCR_MAX_STAKE_DKK', '3'))

DAY_RE = r'(Man|Tir|Ons|Tor|Fre|Lør|Søn)'
TIME_RE = re.compile(rf'^{DAY_RE}\s+\d{{1,2}}:\d{{2}}(?:\s+\d+)?$', re.I)
DK_WEEKDAYS = {'Man': 0, 'Tir': 1, 'Ons': 2, 'Tor': 3, 'Fre': 4, 'Lør': 5, 'Søn': 6}


def parse_iso_utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def parse_visible_start(visible, reference_utc):
    if not visible:
        return None, None
    m = TIME_RE.fullmatch(str(visible).strip())
    if not m:
        return None, None
    day_name = m.group(1).title()
    clock = re.search(r'(\d{1,2}):(\d{2})', str(visible))
    if not clock or day_name not in DK_WEEKDAYS:
        return None, None
    hour, minute = int(clock.group(1)), int(clock.group(2))
    tz = ZoneInfo(TIMEZONE_NAME)
    ref_local = reference_utc.astimezone(tz)
    target_wd = DK_WEEKDAYS[day_name]
    delta_days = (target_wd - ref_local.weekday()) % 7
    candidate = (ref_local + timedelta(days=delta_days)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate < ref_local - timedelta(minutes=30):
        candidate += timedelta(days=7)
    hours_until = (candidate.astimezone(timezone.utc) - reference_utc).total_seconds() / 3600
    return candidate.isoformat(), round(hours_until, 2)


def load_analysis():
    if not ANALYSIS_JSON.exists():
        raise FileNotFoundError(f'Missing {ANALYSIS_JSON}')
    return json.loads(ANALYSIS_JSON.read_text(encoding='utf-8'))


def collect_candidates(analysis):
    rows = []
    for item in analysis.get('files', []):
        for c in item.get('candidates') or []:
            rows.append(dict(c))
    return rows


def event_key(c):
    return (c.get('event'), c.get('start_time_visible'), c.get('league'))


def implied_probability(odds):
    if odds is None or odds <= 1:
        return None
    return 1.0 / float(odds)


def enrich_market_probabilities(candidates):
    grouped = {}
    for c in candidates:
        grouped.setdefault(event_key(c), []).append(c)

    enriched = []
    for key, rows in grouped.items():
        market_rows = [r for r in rows if r.get('market') in {'1x2', 'moneyline'} and r.get('odds')]
        probs = []
        for r in market_rows:
            ip = implied_probability(r.get('odds'))
            if ip is not None:
                probs.append((r, ip))
        overround = sum(ip for _, ip in probs) if probs else None
        complete_1x2 = len([r for r in market_rows if r.get('line') in {'1', 'X', '2'}]) >= 3

        team_probs = []
        for r, ip in probs:
            nr = dict(r)
            nr['implied_probability'] = round(ip, 4)
            nr['market_overround'] = round(overround, 4) if overround else None
            nr['complete_1x2_market'] = bool(complete_1x2)
            nr['normalized_probability'] = round(ip / overround, 4) if overround else None
            if nr.get('line') != 'X':
                team_probs.append((nr.get('normalized_probability') or 0, nr.get('selection')))
            enriched.append(nr)

        ranked_team_probs = sorted(team_probs, reverse=True)
        best_prob = ranked_team_probs[0][0] if ranked_team_probs else None
        second_prob = ranked_team_probs[1][0] if len(ranked_team_probs) > 1 else 0
        for nr in enriched[-len(probs):] if probs else []:
            if nr.get('line') != 'X':
                nr['team_probability_rank'] = 1 if math.isclose(nr.get('normalized_probability') or 0, best_prob or -1, rel_tol=1e-9) else 2
                nr['team_probability_margin'] = round((nr.get('normalized_probability') or 0) - second_prob, 4) if nr['team_probability_rank'] == 1 else round((nr.get('normalized_probability') or 0) - (best_prob or 0), 4)

    return enriched


def reject_reason(c):
    odds = c.get('odds')
    hours = c.get('hours_until_start')
    section_count = c.get('section_event_count')
    overround = c.get('market_overround')
    norm_prob = c.get('normalized_probability')
    margin = c.get('team_probability_margin')

    if c.get('confidence') != REQUIRED_CONFIDENCE:
        return f'confidence_not_{REQUIRED_CONFIDENCE}'
    if c.get('market') not in {'1x2', 'moneyline'}:
        return 'unsupported_market'
    if c.get('line') == 'X':
        return 'draws_disabled'
    if odds is None or not (MIN_ODDS <= odds <= MAX_ODDS):
        return 'odds_outside_safe_range'
    if section_count is not None and section_count > MAX_SECTION_EVENT_COUNT:
        return 'section_too_large_for_safe_pick'
    if hours is None:
        return 'missing_or_unparsed_start_time'
    if hours < MIN_START_MINUTES / 60:
        return 'starts_too_soon_or_already_started'
    if hours > SOON_HOURS:
        return 'starts_too_late'
    if overround is None or not (MIN_OVERROUND <= overround <= MAX_OVERROUND):
        return 'market_overround_suspicious'
    if not c.get('complete_1x2_market'):
        return 'incomplete_1x2_market'
    if c.get('team_probability_rank') != 1:
        return 'not_market_favorite_team'
    if norm_prob is None or norm_prob < MIN_NORMALIZED_PROB:
        return 'normalized_probability_too_low'
    if margin is None or margin < MIN_TEAM_PROB_MARGIN:
        return 'favorite_margin_too_small'
    return None


def winner_score(c):
    # Conservative score: market-implied chance first, then parse safety and soon-start preference.
    norm = c.get('normalized_probability') or 0
    margin = c.get('team_probability_margin') or 0
    hours = c.get('hours_until_start') or 999
    odds = c.get('odds') or 0
    odds_safety = max(0, (MAX_ODDS - odds) / max(0.01, MAX_ODDS - MIN_ODDS))
    soon_bonus = max(0, (SOON_HOURS - min(hours, SOON_HOURS)) / SOON_HOURS)
    return round((norm * 100) + (margin * 50) + (odds_safety * 5) + (soon_bonus * 3), 2)


def stake_pct_for_pick(pick):
    odds = pick.get('odds') or 0
    norm = pick.get('normalized_probability') or 0
    margin = pick.get('team_probability_margin') or 0

    # Very conservative because this is still PDF/market-derived, not a full edge model.
    if norm >= 0.56 and margin >= 0.12 and odds <= 1.75:
        return 0.015
    if norm >= 0.50 and margin >= 0.08 and odds <= 1.90:
        return 0.010
    return 0.0075


def apply_stakes(picks, bankroll):
    if not picks:
        return picks
    total_cap = max(0, bankroll * MAX_TOTAL_STAKE_PCT)
    raw = []
    for p in picks:
        row = dict(p)
        pct = stake_pct_for_pick(row)
        stake = bankroll * pct
        stake = max(MIN_STAKE_DKK, min(MAX_STAKE_DKK, stake))
        row['stake_pct'] = pct
        row['stake_dkk_raw'] = round(stake, 2)
        raw.append(row)
    total_raw = sum(p['stake_dkk_raw'] for p in raw)
    scale = min(1.0, total_cap / total_raw) if total_raw > 0 else 1.0
    for p in raw:
        p['stake_dkk'] = round(max(MIN_STAKE_DKK, p['stake_dkk_raw'] * scale), 2)
        p['stake_note'] = f"Konservativ winner-stake ud fra bankroll {bankroll:.2f} kr., pct {p['stake_pct']:.4f}, total cap {MAX_TOTAL_STAKE_PCT:.0%}."
    return raw


def build_final_picks(analysis):
    generated_at = analysis.get('generated_at') or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    reference_utc = parse_iso_utc(generated_at)
    bankroll = analysis.get('detected_bankroll_dkk') or DEFAULT_BANKROLL_DKK

    candidates = enrich_market_probabilities(collect_candidates(analysis))
    enriched = []
    for c in candidates:
        row = dict(c)
        start_iso, hours_until = parse_visible_start(row.get('start_time_visible'), reference_utc)
        row['start_datetime_local'] = start_iso
        row['hours_until_start'] = hours_until
        row['winner_score'] = winner_score(row)
        enriched.append(row)

    picked = []
    rejected = []
    seen = set()

    def sort_key(c):
        hours = c.get('hours_until_start') if c.get('hours_until_start') is not None else 9999
        return (hours, -c.get('winner_score', 0), -(c.get('normalized_probability') or 0), c.get('odds') or 999)

    for c in sorted(enriched, key=sort_key):
        reason = reject_reason(c)
        if c.get('event') in seen and not reason:
            reason = 'event_already_selected'
        if reason:
            rejected.append({**c, 'final_reject_reason': reason})
            continue
        row = dict(c)
        row['final_pick'] = True
        row['pick_type'] = 'winner'
        row['final_reason'] = (
            f"Vinderpick: markedsfavorit blandt holdene, normaliseret sandsynlighed {row.get('normalized_probability')}, "
            f"margin {row.get('team_probability_margin')}, odds {row.get('odds')}, starter om {row.get('hours_until_start')} timer. "
            "Ingen reel multi-bookmaker edge; vurderingen bruger kun de data, OCR/PDF-flowet har adgang til."
        )
        picked.append(row)
        seen.add(row.get('event'))
        if len(picked) >= MAX_PICKS:
            break

    picked = apply_stakes(picked, bankroll)
    return {
        'rules': {
            'mode': 'conservative_winner_selector',
            'max_picks': MAX_PICKS,
            'min_odds': MIN_ODDS,
            'max_odds': MAX_ODDS,
            'confidence': REQUIRED_CONFIDENCE,
            'allow_draws': False,
            'one_pick_per_event': True,
            'soon_hours': SOON_HOURS,
            'min_start_minutes': MIN_START_MINUTES,
            'min_normalized_probability': MIN_NORMALIZED_PROB,
            'min_team_probability_margin': MIN_TEAM_PROB_MARGIN,
            'overround_range': [MIN_OVERROUND, MAX_OVERROUND],
            'max_section_event_count': MAX_SECTION_EVENT_COUNT,
            'bankroll_dkk': bankroll,
            'max_total_stake_pct': MAX_TOTAL_STAKE_PCT,
            'min_stake_dkk': MIN_STAKE_DKK,
            'max_stake_dkk': MAX_STAKE_DKK,
            'note': 'Winner selector. Uses all available OCR/PDF fields: parsed market odds, implied probabilities, parse confidence, section size, start time, and bankroll. No external team-strength or multi-bookmaker edge is available in this flow.',
        },
        'picks': picked,
        'rejected_sample': rejected[:100],
    }


def write_md(final_picks, generated_at):
    lines = [
        '# OCR FINAL PICKS — WINNER SELECTOR', '',
        f'Generated: {generated_at}', '',
        'Vigtigt: Dette er vinderpicks baseret på OCR/PDF og bet365-markedet. Det er ikke en fuld value/edge-model.', '',
        '## Regler',
    ]
    rules = final_picks['rules']
    for key in ['mode', 'min_odds', 'max_odds', 'confidence', 'soon_hours', 'min_start_minutes', 'min_normalized_probability', 'min_team_probability_margin', 'max_section_event_count', 'bankroll_dkk', 'max_total_stake_pct']:
        lines.append(f'- {key}: {rules.get(key)}')
    lines.extend(['', '## Final winner picks'])
    if not final_picks['picks']:
        lines.append('Ingen winner picks efter filteret.')
    else:
        lines.append(f'Samlet stake: {sum(p.get("stake_dkk", 0) for p in final_picks["picks"]):.2f} kr.')
    for i, p in enumerate(final_picks['picks'], 1):
        lines.extend([
            '',
            f'### {i}. {p.get("event")}',
            f'- Liga: {p.get("league")}',
            f'- Tidspunkt: {p.get("start_time_visible")}',
            f'- Starter om: {p.get("hours_until_start")} timer',
            f'- Vinderpick: {p.get("selection")}',
            f'- Odds: {p.get("odds")}',
            f'- Normaliseret sandsynlighed: {p.get("normalized_probability")}',
            f'- Margin til næstbedste hold: {p.get("team_probability_margin")}',
            f'- Overround: {p.get("market_overround")}',
            f'- Winner score: {p.get("winner_score")}',
            f'- Stake: {p.get("stake_dkk")} kr.',
            f'- Confidence: {p.get("confidence")}',
            f'- Begrundelse: {p.get("final_reason")}',
            f'- Stake-note: {p.get("stake_note")}',
        ])
    FINAL_PICKS_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    analysis = load_analysis()
    generated_at = analysis.get('generated_at') or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    final_picks = build_final_picks(analysis)
    analysis['final_picks'] = final_picks
    analysis['winner_selector_applied'] = True
    ANALYSIS_JSON.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding='utf-8')
    FINAL_PICKS_JSON.write_text(json.dumps({'generated_at': generated_at, **final_picks}, ensure_ascii=False, indent=2), encoding='utf-8')
    write_md(final_picks, generated_at)
    print(f'OCR winner selector OK | picks={len(final_picks["picks"])}')


if __name__ == '__main__':
    main()
