import json
import os
import pathlib
from datetime import datetime, timezone, timedelta

ROOT = pathlib.Path('.')
INBOX = ROOT / 'inbox' / 'possible_bets'
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)
REPORT_JSON = OUT / 'ocr_cleanup_report.json'
REPORT_MD = OUT / 'ocr_cleanup_report.md'

RETENTION_HOURS = int(os.getenv('OCR_RETENTION_HOURS', '48'))
DRY_RUN = os.getenv('OCR_CLEANUP_DRY_RUN', '0') == '1'


def now():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def main():
    cutoff = now() - timedelta(hours=RETENTION_HOURS)
    deleted = []
    kept = []

    if INBOX.exists():
        for p in INBOX.rglob('*'):
            if not p.is_file():
                continue
            mtime = datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
            row = {
                'file': str(p),
                'mtime': iso(mtime),
                'age_hours': round((now() - mtime).total_seconds() / 3600, 2),
            }
            if mtime < cutoff:
                row['action'] = 'would_delete' if DRY_RUN else 'deleted'
                deleted.append(row)
                if not DRY_RUN:
                    p.unlink(missing_ok=True)
            else:
                row['action'] = 'kept'
                kept.append(row)

    report = {
        'generated_at': iso(now()),
        'retention_hours': RETENTION_HOURS,
        'dry_run': DRY_RUN,
        'deleted_count': len(deleted),
        'kept_count': len(kept),
        'deleted': deleted,
        'kept': kept,
    }
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = [
        '# OCR CLEANUP REPORT',
        '',
        f'Generated: {report["generated_at"]}',
        f'Retention hours: {RETENTION_HOURS}',
        f'Dry run: {DRY_RUN}',
        f'Deleted: {len(deleted)}',
        f'Kept: {len(kept)}',
        '',
        '## Deleted',
    ]
    if not deleted:
        lines.append('None')
    for row in deleted:
        lines.append(f'- {row["file"]} | age {row["age_hours"]}h | {row["action"]}')
    lines.append('\n## Kept')
    if not kept:
        lines.append('None')
    for row in kept[:100]:
        lines.append(f'- {row["file"]} | age {row["age_hours"]}h')
    REPORT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'OCR cleanup OK | deleted={len(deleted)} kept={len(kept)} dry_run={DRY_RUN}')


if __name__ == '__main__':
    main()
