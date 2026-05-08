import json
import os
import pathlib
import re
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

ROOT = pathlib.Path('.')
OUT = ROOT / 'output'
FINAL_PICKS_JSON = OUT / 'ocr_final_picks.json'
FINAL_PICKS_MD = OUT / 'ocr_final_picks.md'
RESEARCH_JSON = OUT / 'ocr_gemini_research.json'
RESEARCH_MD = OUT / 'ocr_gemini_research.md'

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
MAX_RESEARCH_PICKS = int(os.getenv('OCR_GEMINI_MAX_RESEARCH_PICKS', '25'))
RESEARCH_TIMEOUT = int(os.getenv('OCR_GEMINI_TIMEOUT_SECONDS', '45'))
REQUIRE_GEMINI_APPROVAL = os.getenv('OCR_REQUIRE_GEMINI_APPROVAL', '1') == '1'
ALLOW_REDUCE = os.getenv('OCR_GEMINI_ALLOW_REDUCE', '1') == '1'
MIN_GEMINI_CONFIDENCE = float(os.getenv('OCR_GEMINI_MIN_CONFIDENCE', '0.55'))


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def load_json(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def extract_json(text):
    if not text:
        return None
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r'\{.*\}', text, flags=re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def gemini_generate_json(prompt):
    if not GEMINI_API_KEY:
        return {'error': 'missing_GEMINI_API_KEY'}
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent'
    payload = {
        'contents': [{'parts': [{'text': prompt}]}],
        'tools': [{'google_search': {}}],
        'generationConfig': {
            'temperature': 0.1,
            'topP': 0.8,
            'responseMimeType': 'application/json'
        }
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'x-goog-api-key': GEMINI_API_KEY,
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=RESEARCH_TIMEOUT) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        return {'error': f'http_{exc.code}', 'body': body[:2000]}
    except Exception as exc:
        return {'error': 'request_failed', 'body': str(exc)[:1000]}

    try:
        obj = json.loads(raw)
    except Exception:
        return {'error': 'bad_api_json', 'body': raw[:2000]}

    text = ''
    candidate = None
    candidates = obj.get('candidates') or []
    if candidates:
        candidate = candidates[0]
        parts = (((candidate.get('content') or {}).get('parts')) or [])
        text = ''.join(p.get('text', '') for p in parts)
    parsed = extract_json(text)
    if parsed is None:
        parsed = {'error': 'bad_model_json', 'raw_text': text[:2000]}

    grounding = (candidate or {}).get('groundingMetadata') or {}
    chunks = grounding.get('groundingChunks') or []
    sources = []
    for ch in chunks:
        web = ch.get('web') or {}
        uri = web.get('uri')
        title = web.get('title')
        if uri or title:
            sources.append({'title': title, 'uri': uri})
    parsed['grounding_sources'] = sources[:12]
    parsed['web_search_queries'] = grounding.get('webSearchQueries') or []
    return parsed


def build_prompt(pick):
    return f"""
You are a cautious sports betting research filter. Use Google Search grounding.

Task: evaluate this candidate winner bet using all public information you can find: recent form, home/away context, injuries/suspensions, lineup/rotation risk, tournament motivation, match importance, recent news, and other bookmaker/market odds if available.

Strict rules:
- Do NOT invent facts.
- Do NOT create new picks.
- If you cannot verify enough current information, return insufficient_data.
- Prefer rejecting uncertain bets.
- Compare the bet365 odds with other available bookmaker/odds-comparison sources when possible.
- For 1X2, evaluate only the listed selection, not draw or handicap.
- Return JSON only.

Candidate:
{json.dumps(pick, ensure_ascii=False, indent=2)}

Return exactly this JSON shape:
{{
  "event": "string",
  "selection": "string",
  "verdict": "approve|reduce|reject|insufficient_data",
  "risk_level": "low|medium|high",
  "gemini_confidence": 0.0,
  "winner_probability_estimate": 0.0,
  "stake_multiplier": 0.0,
  "edge_status": "positive|neutral|negative|unknown",
  "edge_percent_estimate": 0.0,
  "other_bookmaker_odds": [
    {{"bookmaker": "string", "odds": 0.0, "source": "string", "confidence": "low|medium|high"}}
  ],
  "market_summary": "short string",
  "form_summary": "short string",
  "injury_rotation_summary": "short string",
  "motivation_summary": "short string",
  "key_reasons_for": ["string"],
  "key_reasons_against": ["string"],
  "red_flags": ["string"],
  "final_action": "keep|keep_reduced|remove",
  "summary": "short Danish summary"
}}
""".strip()


def decision_from_research(pick, research):
    if research.get('error'):
        return 'remove', 0.0, 'gemini_error'
    verdict = str(research.get('verdict') or '').lower()
    action = str(research.get('final_action') or '').lower()
    confidence = float(research.get('gemini_confidence') or 0)
    red_flags = research.get('red_flags') or []
    stake_multiplier = research.get('stake_multiplier')
    try:
        stake_multiplier = float(stake_multiplier)
    except Exception:
        stake_multiplier = 0.0

    if confidence < MIN_GEMINI_CONFIDENCE:
        return 'remove', 0.0, 'gemini_confidence_too_low'
    if verdict in {'reject', 'insufficient_data'} or action == 'remove':
        return 'remove', 0.0, f'gemini_{verdict or action}'
    if red_flags:
        # Red flags are not automatic hard rejects if Gemini explicitly says reduce, but stake is capped hard.
        if verdict == 'approve' and action == 'keep':
            return 'remove', 0.0, 'gemini_red_flags'
    if verdict == 'approve' and action == 'keep':
        return 'keep', max(0.1, min(1.0, stake_multiplier or 1.0)), 'gemini_approved'
    if ALLOW_REDUCE and verdict in {'approve', 'reduce'} and action in {'keep', 'keep_reduced'}:
        return 'keep_reduced', max(0.1, min(0.75, stake_multiplier or 0.5)), 'gemini_reduced'
    return 'remove', 0.0, 'gemini_not_approved'


def rebuild_final_picks(base_data, research_rows):
    picks = base_data.get('picks') or []
    research_by_key = {}
    for r in research_rows:
        key = (r.get('event'), r.get('selection'), r.get('line'))
        research_by_key[key] = r

    final = []
    removed = []
    for p in picks:
        key = (p.get('event'), p.get('selection'), p.get('line'))
        r = research_by_key.get(key)
        row = dict(p)
        row['gemini_research'] = r
        if REQUIRE_GEMINI_APPROVAL:
            action, mult, reason = decision_from_research(p, r or {'error': 'missing_research'})
            row['gemini_final_decision'] = action
            row['gemini_decision_reason'] = reason
            row['gemini_stake_multiplier'] = mult
            if action.startswith('keep'):
                original_stake = float(row.get('stake_dkk') or 0)
                row['stake_dkk_before_gemini'] = original_stake
                row['stake_dkk'] = round(original_stake * mult, 2)
                row['stake_note'] = (row.get('stake_note') or '') + f' Gemini multiplier {mult:.2f} ({reason}).'
                row['final_reason'] = (row.get('final_reason') or '') + f' Gemini: {reason}.'
                final.append(row)
            else:
                row['final_reject_reason'] = reason
                removed.append(row)
        else:
            final.append(row)

    base_data['rules']['gemini_required'] = REQUIRE_GEMINI_APPROVAL
    base_data['rules']['gemini_min_confidence'] = MIN_GEMINI_CONFIDENCE
    base_data['picks_before_gemini'] = picks
    base_data['picks_removed_by_gemini'] = removed
    base_data['picks'] = final
    return base_data


def write_md(research_data, final_data):
    lines = [
        '# OCR GEMINI RESEARCH', '',
        f'Generated: {research_data["generated_at"]}', '',
        'Gemini-laget bruger Google Search grounding til kampresearch, marked/odds-sammenligning og sanity check. Det erstatter ikke en garanteret edge-model.', '',
        '## Final picks after Gemini',
    ]
    picks = final_data.get('picks') or []
    if not picks:
        lines.append('Ingen picks overlevede Gemini-filteret.')
    for i, p in enumerate(picks, 1):
        r = p.get('gemini_research') or {}
        lines.extend([
            '',
            f'### {i}. {p.get("event")}',
            f'- Pick: {p.get("selection")} ({p.get("line")})',
            f'- Odds: {p.get("odds")}',
            f'- Stake: {p.get("stake_dkk")} kr.',
            f'- Gemini verdict: {r.get("verdict")}',
            f'- Risk: {r.get("risk_level")}',
            f'- Confidence: {r.get("gemini_confidence")}',
            f'- Edge: {r.get("edge_status")} ({r.get("edge_percent_estimate")})',
            f'- Summary: {r.get("summary")}',
        ])
        sources = r.get('grounding_sources') or []
        if sources:
            lines.append('- Sources:')
            for s in sources[:5]:
                lines.append(f'  - {s.get("title")}: {s.get("uri")}')

    removed = final_data.get('picks_removed_by_gemini') or []
    lines.extend(['', '## Removed by Gemini'])
    if not removed:
        lines.append('Ingen picks fjernet.')
    for p in removed:
        r = p.get('gemini_research') or {}
        lines.extend([
            '',
            f'- {p.get("event")} / {p.get("selection")} @ {p.get("odds")} — {p.get("gemini_decision_reason")} — {r.get("summary")}',
        ])
    RESEARCH_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    base = load_json(FINAL_PICKS_JSON)
    if not base:
        data = {'generated_at': now_iso(), 'error': 'missing_ocr_final_picks_json'}
        write_json(RESEARCH_JSON, data)
        print('Gemini research skipped | missing final picks')
        return

    picks = (base.get('picks') or [])[:MAX_RESEARCH_PICKS]
    rows = []
    if not GEMINI_API_KEY:
        data = {'generated_at': now_iso(), 'enabled': False, 'error': 'missing_GEMINI_API_KEY', 'researched': []}
        write_json(RESEARCH_JSON, data)
        if REQUIRE_GEMINI_APPROVAL:
            final = rebuild_final_picks(base, [])
            write_json(FINAL_PICKS_JSON, final)
            write_md(data, final)
        print('Gemini research disabled | missing key')
        return

    for idx, pick in enumerate(picks, 1):
        prompt = build_prompt(pick)
        research = gemini_generate_json(prompt)
        research['event'] = research.get('event') or pick.get('event')
        research['selection'] = research.get('selection') or pick.get('selection')
        research['line'] = pick.get('line')
        research['original_pick'] = pick
        research['researched_at'] = now_iso()
        rows.append(research)
        time.sleep(float(os.getenv('OCR_GEMINI_SLEEP_SECONDS', '0.5')))

    data = {'generated_at': now_iso(), 'enabled': True, 'model': GEMINI_MODEL, 'researched_count': len(rows), 'researched': rows}
    write_json(RESEARCH_JSON, data)
    final = rebuild_final_picks(base, rows)
    write_json(FINAL_PICKS_JSON, final)
    write_md(data, final)
    print(f'Gemini research OK | researched={len(rows)} final_picks={len(final.get("picks") or [])}')


if __name__ == '__main__':
    main()
