"""Validate a FastRoute paper evidence pack for scientific consistency.

Usage:
  .\\.venv\\Scripts\\python.exe scripts\\validate_paper_evidence.py
  .\\.venv\\Scripts\\python.exe scripts\\validate_paper_evidence.py --pack portfolio_evidence_pack\\paper_evidence_FINAL
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK = ROOT / 'portfolio_evidence_pack' / 'paper_evidence_FINAL'

REQUIRED = [
    '00_READ_ME_FIRST.md',
    'MANIFEST.json',
    'csv/compare_results.csv',
    'prompts/CLO_AND_PAPER_QUESTIONS.md',
]

BANNED_PHRASES = [
    r'nearest-neighbor stop order',
    r'A\* Best — haversine heuristic \+ nearest-neighbor',
    r'92\.33%',
]


def validate(pack: Path) -> dict:
    errors, warnings, manual = [], [], []
    if not pack.is_dir():
        return {
            'pack': str(pack),
            'errors': [f'Pack directory missing: {pack}'],
            'warnings': [],
            'manual_verification': [],
            'ok': False,
        }

    for rel in REQUIRED:
        if not (pack / rel).is_file():
            errors.append(f'Missing required file: {rel}')

    manifest_path = pack / 'MANIFEST.json'
    manifest = {}
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if not manifest.get('includes_improvement_story'):
            warnings.append('Manifest reports improvement story missing')
        if not manifest.get('includes_optimization_ladder'):
            warnings.append('Manifest reports optimization ladder missing')
        repair = manifest.get('scientific_repair') or {}
        if not repair.get('nearest_neighbor_removed_from_active_ladder'):
            warnings.append('Manifest missing NN-removal scientific_repair flag')

    # Scan text for outdated NN ladder claims
    for path in pack.rglob('*'):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {'.md', '.csv', '.json', '.txt'}:
            continue
        try:
            text = path.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            continue
        for pat in BANNED_PHRASES:
            if re.search(pat, text, flags=re.I):
                # Historical archives under docs copies may still mention policy; flag as warning.
                warnings.append(f'Possible outdated claim matching /{pat}/ in {path.relative_to(pack)}')

    scale_csv = pack / 'csv' / 'pathfinder_graph_scale.csv'
    if scale_csv.is_file():
        text = scale_csv.read_text(encoding='utf-8', errors='ignore')
        if 'target_status' in text and 'completed' in text:
            # Ensure 100k completed rows actually have enough nodes if present
            for line in text.splitlines()[1:]:
                parts = line.split(',')
                if len(parts) < 8:
                    continue
                # Soft check: if label mentions 100k and status completed, actual nodes should be >= 100000
                if '100k' in line.lower() and 'completed' in line:
                    nums = re.findall(r'\d+', line)
                    if nums and max(int(n) for n in nums if len(n) >= 4) < 100_000:
                        errors.append('100k target marked completed with actual_nodes < 100000')
    else:
        warnings.append('pathfinder_graph_scale.csv not in pack')

    ladder = pack / 'csv' / 'optimization_ladder.csv'
    if ladder.is_file():
        text = ladder.read_text(encoding='utf-8', errors='ignore').lower()
        if 'nearest' in text and 'neighbor' in text:
            errors.append('optimization_ladder.csv still references nearest neighbor')
    else:
        warnings.append('optimization_ladder.csv missing')

    if not (pack / 'tests' / 'test_results.txt').is_file():
        manual.append('Add tests/test_results.txt from the latest unittest run')
    if not (ROOT / '.git').exists():
        manual.append('GitHub repository / commit history not verified in this environment')
    manual.append('Verify GitHub Pages URL publicly before claiming category G')
    manual.append('Fill CONTRIBUTIONS.md with real team roles before submission')

    return {
        'pack': str(pack),
        'errors': errors,
        'warnings': warnings,
        'manual_verification': manual,
        'ok': not errors,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pack', type=Path, default=DEFAULT_PACK)
    args = parser.parse_args()
    report = validate(args.pack)
    out_dir = args.pack if args.pack.is_dir() else ROOT / 'portfolio_evidence_pack'
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / 'validation_report.json'
    txt_path = out_dir / 'validation_report.txt'
    json_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    lines = [
        f"Pack: {report['pack']}",
        f"OK: {report['ok']}",
        '',
        'ERRORS:',
        *(f'- {e}' for e in report['errors'] or ['(none)']),
        '',
        'WARNINGS:',
        *(f'- {w}' for w in report['warnings'] or ['(none)']),
        '',
        'MANUAL VERIFICATION:',
        *(f'- {m}' for m in report['manual_verification'] or ['(none)']),
    ]
    txt_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(txt_path.read_text(encoding='utf-8'))
    raise SystemExit(0 if report['ok'] else 1)


if __name__ == '__main__':
    main()
