"""One-click portfolio evidence pack: CSVs, visuals, docs, and AI/paper prompts."""
from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
from PIL import Image, ImageDraw, ImageFont

from .algorithms import ALGORITHM_COLORS, ALGORITHM_SHORT, WORK_COUNTER_UNITS
from .datasets import DATASET_PROVENANCE
from .map_viz import build_comparison_map
from .report import build_experiment_report, report_to_csv_rows, report_to_html, report_to_json
from .results_explain import pairwise_summary_table, understanding_results_text

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'results'
FIGURES = ROOT / 'figures'
DOCS = ROOT / 'docs'
PACK_DIR = ROOT / 'portfolio_evidence_pack'
# Download basename prefix; full name is paper_evidence_FINAL_<utc>.zip
PAPER_EVIDENCE_ZIP_NAME = 'paper_evidence_FINAL.zip'


def _utc_stamp():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _write_text(zf, arcname, text):
    zf.writestr(arcname, text if text.endswith('\n') else text + '\n')


def _write_bytes(zf, arcname, data: bytes):
    zf.writestr(arcname, data)


def _copy_file_if_exists(zf, path: Path, arcname: str):
    if path.is_file():
        zf.write(path, arcname)
        return True
    return False


def _font(size=18):
    for name in ('arial.ttf', 'segoeui.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _results_table_png(experiment) -> bytes:
    """Synthetic screenshot of the comparison table (no browser required)."""
    rows = experiment.get('results') or []
    headers = ['Algorithm', 'Distance (km)', 'Runtime (ms)', 'Work', 'Gap %']
    lines = [headers]
    for row in rows:
        short = ALGORITHM_SHORT.get(row['Algorithm'], row['Algorithm'])
        gap = row.get('Optimality gap (%)')
        lines.append([
            short,
            str(row.get('Distance (km)', '')),
            str(row.get('Runtime (ms)', '')),
            str(row.get('Algorithm-Specific Work Counter', row.get('Operations / states', ''))),
            'n/a' if gap is None else str(gap),
        ])

    col_w = [160, 130, 130, 120, 90]
    pad, row_h = 16, 36
    width = sum(col_w) + pad * 2
    height = pad * 2 + row_h * (len(lines) + 2)
    img = Image.new('RGB', (width, height), '#0B1220')
    draw = ImageDraw.Draw(img)
    title_font = _font(22)
    cell_font = _font(16)
    draw.text((pad, pad), 'FastRoute — Compare Results', fill='#F8FAFC', font=title_font)
    meta = (
        f"{experiment.get('place') or ''} · "
        f"{experiment.get('delivery_count')} deliveries · seed {experiment.get('seed')}"
    )
    draw.text((pad, pad + 28), meta[:110], fill='#94A3B8', font=cell_font)

    y0 = pad + 60
    for r, line in enumerate(lines):
        x = pad
        bg = '#1E293B' if r == 0 else ('#111827' if r % 2 else '#0F172A')
        draw.rectangle([pad - 4, y0, width - pad + 4, y0 + row_h - 4], fill=bg)
        for c, text in enumerate(line):
            color = '#E2E8F0' if r == 0 else '#F8FAFC'
            if r > 0 and c == 0:
                algo = rows[r - 1]['Algorithm']
                color = ALGORITHM_COLORS.get(algo, color)
            draw.text((x + 6, y0 + 8), text, fill=color, font=cell_font)
            x += col_w[c]
        y0 += row_h

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def _metrics_cards_png(experiment) -> bytes:
    rows = experiment.get('results') or []
    cards = []
    for row in rows:
        short = ALGORITHM_SHORT.get(row['Algorithm'], row['Algorithm'])
        cards.append((
            short,
            f"{row.get('Distance (km)')} km",
            f"{row.get('Runtime (ms)')} ms",
            ALGORITHM_COLORS.get(row['Algorithm'], '#94A3B8'),
        ))
    if experiment.get('improvement_story'):
        story = experiment['improvement_story']
        cards.append((
            'Improved settings',
            f"{story['improved'].get('Distance (km)')} km",
            f"{story['improved'].get('Runtime (ms)')} ms",
            '#A78BFA',
        ))

    card_w, card_h, gap = 220, 140, 16
    pad = 20
    width = pad * 2 + max(1, len(cards)) * card_w + max(0, len(cards) - 1) * gap
    height = pad * 2 + card_h + 50
    img = Image.new('RGB', (width, max(height, 120)), '#0B1220')
    draw = ImageDraw.Draw(img)
    draw.text((pad, pad), 'FastRoute — Result cards', fill='#F8FAFC', font=_font(22))
    x = pad
    y = pad + 44
    for title, dist, runtime, color in cards:
        draw.rounded_rectangle([x, y, x + card_w - 8, y + card_h - 8], radius=12, fill='#111827', outline=color, width=3)
        draw.text((x + 14, y + 16), title, fill=color, font=_font(18))
        draw.text((x + 14, y + 56), dist, fill='#F8FAFC', font=_font(28))
        draw.text((x + 14, y + 96), runtime, fill='#94A3B8', font=_font(16))
        x += card_w + gap
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def _comparison_csv(experiment) -> str:
    buf = io.StringIO()
    fieldnames = [
        'Algorithm', 'Distance (km)', 'Runtime (ms)', 'Peak memory (KB)',
        'Algorithm-Specific Work Counter', 'Work unit', 'Optimality gap (%)', 'Exact order search',
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in experiment.get('results') or []:
        writer.writerow({
            'Algorithm': row['Algorithm'],
            'Distance (km)': row.get('Distance (km)'),
            'Runtime (ms)': row.get('Runtime (ms)'),
            'Peak memory (KB)': row.get('Peak memory (KB)'),
            'Algorithm-Specific Work Counter': row.get(
                'Algorithm-Specific Work Counter', row.get('Operations / states')
            ),
            'Work unit': row.get('Work unit') or WORK_COUNTER_UNITS.get(row['Algorithm']),
            'Optimality gap (%)': row.get('Optimality gap (%)'),
            'Exact order search': bool(row.get('exact')),
        })
    return buf.getvalue()


def _improvement_csv(experiment) -> str | None:
    story = experiment.get('improvement_story')
    if not story:
        return None
    buf = io.StringIO()
    timings = story.get('timings') or {}
    search = story.get('search') or {}
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            'stage', 'algorithm', 'distance_km', 'runtime_ms', 'work_counter',
            'distance_delta_km', 'distance_delta_pct', 'settings_label',
            'experiment_type', 'search_mode', 'exact', 'sampling_budget',
            'matrix_prep_ms', 'route_search_ms', 'end_to_end_ms',
        ],
    )
    writer.writeheader()
    base = story['baseline']
    improved = story['improved']
    writer.writerow({
        'stage': 'before_original_order_dijkstra',
        'algorithm': base.get('Short name', base['Algorithm']),
        'distance_km': base.get('Distance (km)'),
        'runtime_ms': base.get('Runtime (ms)'),
        'work_counter': base.get('Algorithm-Specific Work Counter', base.get('Operations / states')),
        'distance_delta_km': 0,
        'distance_delta_pct': 0,
        'settings_label': base.get('settings_label'),
        'experiment_type': story.get('experiment_type'),
        'search_mode': '',
        'exact': '',
        'sampling_budget': '',
        'matrix_prep_ms': timings.get('distance_matrix_prep_ms'),
        'route_search_ms': '',
        'end_to_end_ms': timings.get('total_end_to_end_ms'),
    })
    writer.writerow({
        'stage': 'after_bf_order_dijkstra',
        'algorithm': improved.get('Short name', improved['Algorithm']),
        'distance_km': improved.get('Distance (km)'),
        'runtime_ms': improved.get('Runtime (ms)'),
        'work_counter': improved.get('Algorithm-Specific Work Counter', improved.get('Operations / states')),
        'distance_delta_km': story.get('distance_delta_km'),
        'distance_delta_pct': story.get('distance_delta_pct'),
        'settings_label': story.get('settings_label'),
        'experiment_type': story.get('experiment_type'),
        'search_mode': search.get('search_mode'),
        'exact': search.get('exact'),
        'sampling_budget': search.get('budget'),
        'matrix_prep_ms': timings.get('distance_matrix_prep_ms'),
        'route_search_ms': timings.get('route_search_ms'),
        'end_to_end_ms': timings.get('total_end_to_end_ms'),
    })
    return buf.getvalue()


def _chart_bundle(scalability_rows):
    """Return dict with html_files, csv_files, png_files lists of (name, bytes_or_text)."""
    html_files, csv_files, png_files = [], [], []
    if not scalability_rows:
        return {'html': html_files, 'csv': csv_files, 'png': png_files}
    frame = pd.DataFrame(scalability_rows)
    ok = frame[frame['status'] == 'ok'] if 'status' in frame.columns else frame
    if ok.empty:
        return {'html': html_files, 'csv': csv_files, 'png': png_files}
    color_map = {ALGORITHM_SHORT[k]: v for k, v in ALGORITHM_COLORS.items()}
    specs = [
        ('avg_runtime_ms', 'runtime_vs_deliveries', 'Runtime vs deliveries'),
        ('avg_distance_km', 'distance_vs_deliveries', 'Distance vs deliveries'),
        ('avg_operations', 'operations_vs_deliveries', 'Work counter vs deliveries'),
    ]
    for ycol, stem, title in specs:
        if ycol not in ok.columns:
            continue
        fig = px.line(
            ok, x='deliveries', y=ycol, color='short_name', markers=True, title=title,
            color_discrete_map=color_map,
        )
        fig.update_layout(template='plotly_white')
        html_files.append((f'{stem}.html', fig.to_html(include_plotlyjs='cdn', full_html=True).encode('utf-8')))
        csv_files.append((f'{stem}.csv', ok[['deliveries', 'short_name', ycol]].to_csv(index=False)))
        try:
            png_files.append((f'{stem}.png', fig.to_image(format='png', width=1000, height=560, scale=2)))
        except Exception:
            pass
    return {'html': html_files, 'csv': csv_files, 'png': png_files}


def _ai_prompt_markdown(experiment, scalability_rows) -> str:
    place = experiment.get('place')
    deliveries = experiment.get('delivery_count')
    nodes = experiment.get('network_nodes')
    edges = experiment.get('network_edges')
    return f"""# FastRoute — feed this folder to ChatGPT / Claude for the CPS 3440 paper

## How to use
1. Upload this whole zip (or paste key CSVs + `00_READ_ME_FIRST.md` + `prompts/CLO_AND_PAPER_QUESTIONS.md`).
2. Ask: "Using ONLY the measured files in this pack, draft the CPS 3440 technical paper sections and presentation answers. Do not invent numbers."
3. You must still read and defend every answer — AI drafts are not a substitute for understanding.

## This experiment snapshot
- Area: {place}
- Deliveries: {deliveries}
- Seed: {experiment.get('seed')}
- Stop source: {experiment.get('source')}
- Road graph: {nodes} nodes, {edges} edges
- Scalability rows attached: {len(scalability_rows or [])}

## Files
- `csv/compare_results.csv` — main algorithm table
- `csv/improvement_story.csv` — middle-algorithm baseline → improved settings
- `csv/optimization_ladder.csv` — Bad → Semi → Best tiers
- `csv/` — other measured tables (scalability, provenance, report)
- `screenshots/` — auto-generated PNG result visuals (not live Streamlit chrome)
- `visuals/` — interactive Plotly HTML charts + Folium map HTML (open in browser, screenshot/print for paper)
- `docs/` — methodology / hardness / dataset text already written for the course
- `prompts/` — exact questions to answer for full marks

## Hard rules for the AI
- Use only numbers from the CSVs / report JSON.
- Label skipped / unavailable gaps honestly.
- Grubhub + OSM are the primary dataset story; India food-delivery CSV is secondary.
- A* and Dijkstra often match distance (same stop order); compare nodes settled / runtime.
- Brute Force is the order-search baseline (exact ≤9; sampled above).
"""


def ensure_improvement_and_ladder(experiment, graph) -> list[str]:
    """Run middle-algorithm improvement + Bad/Semi/Best ladder if missing, then pack them."""
    notes = []
    if experiment is None:
        return ['No experiment — run Compare All first']
    if graph is None:
        notes.append('No road graph — could not auto-run improvement/ladder')
        return notes

    if not experiment.get('improvement_story'):
        try:
            from .improvement import build_improvement_story
            experiment['improvement_story'] = build_improvement_story(experiment, graph)
            notes.append('Auto-ran middle-algorithm improvement for paper pack')
        except Exception as exc:
            notes.append(f'Improvement story not added: {exc}')
    else:
        notes.append('Improvement story already present')

    if not experiment.get('optimization_ladder'):
        try:
            from .optimization_ladder import run_optimization_ladder
            experiment['optimization_ladder'] = run_optimization_ladder(
                graph,
                experiment['stops'],
                matrix=experiment.get('matrix'),
                seed=int(experiment.get('seed') or 42),
            )
            notes.append('Auto-ran Bad→Semi→Best optimization ladder for paper pack')
        except Exception as exc:
            notes.append(f'Optimization ladder not added: {exc}')
    else:
        notes.append('Optimization ladder already present')
    return notes


def _question_bank() -> str:
    return """# CLO + paper + presentation questions (answer using the pack)

## CLO A — Efficiency
Give one concrete result from this project demonstrating why algorithmic efficiency matters.
Evidence: `csv/scalability_results.csv`, `visuals/runtime_vs_deliveries.html`, brute-force runtime at n=8–9 vs A*/Dijkstra.

## CLO B — Complexity
Pick one major algorithm. Explain time/space complexity and whether measurements matched theory.
Evidence: `docs/ALGORITHMIC_EFFICIENCY_ANALYSIS.md`, `csv/compare_results.csv` work counters.

## CLO C — Hardness
Explain inefficient algorithm vs computationally hard problem using this project (TSP-order search vs shortest paths).
Evidence: `docs/ALGORITHMIC_EFFICIENCY_ANALYSIS.md`, BF factorial growth in scalability CSV.

## CLO D — Selection
Which algorithms did you investigate? Which would you recommend for a real courier app, and why?
Evidence: compare_results + improvement story CSV if present.

## Paper sections to draft
Abstract, Introduction, Dataset, Problem Formulation, Algorithms, Correctness & Complexity,
Implementation, Experimental Methodology, Results, Theory vs Observed Performance,
Algorithmic Efficiency vs Computational Hardness, Limitations, CLO Reflection, Conclusion, References.

## Presentation / defense prompts
1. What real-world problem?
2. What dataset?
3. What algorithms?
4. Theoretical complexities?
5. What experiments?
6. What did results show?
7. Did theory and experiments agree?
8. Which approach performed best and why?
9. What would you improve next?
"""


def build_portfolio_zip(
    experiment,
    scalability_rows=None,
    graph=None,
    *,
    auto_run_extras=True,
) -> tuple[bytes, Path, list[str]]:
    """Build zip bytes, also mirror files under portfolio_evidence_pack/.

    Returns (zip_bytes, pack_dir, notes). Zip download name: paper_evidence.zip.
    When auto_run_extras is True and a graph is provided, middle-algorithm improvement
    and the optimization ladder are generated if missing so they land in the pack.
    """
    if experiment is None:
        raise ValueError('Run Compare All before exporting the portfolio pack.')

    scalability_rows = scalability_rows or []
    stamp = _utc_stamp()
    zip_name = f'paper_evidence_FINAL_{stamp}.zip'
    pack = PACK_DIR / f'paper_evidence_FINAL_{stamp}'
    pack.mkdir(parents=True, exist_ok=True)
    notes = []
    if auto_run_extras:
        notes.extend(ensure_improvement_and_ladder(experiment, graph))

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        readme = _ai_prompt_markdown(experiment, scalability_rows)
        _write_text(zf, '00_READ_ME_FIRST.md', readme)
        (pack / '00_READ_ME_FIRST.md').write_text(readme, encoding='utf-8')

        # --- CSVs ---
        compare_csv = _comparison_csv(experiment)
        _write_text(zf, 'csv/compare_results.csv', compare_csv)
        (pack / 'csv').mkdir(exist_ok=True)
        (pack / 'csv' / 'compare_results.csv').write_text(compare_csv, encoding='utf-8')

        pair = pairwise_summary_table(experiment.get('results') or [])
        if pair:
            pair_csv = pd.DataFrame(pair).to_csv(index=False)
            _write_text(zf, 'csv/pairwise_deltas.csv', pair_csv)
            (pack / 'csv' / 'pairwise_deltas.csv').write_text(pair_csv, encoding='utf-8')

        imp_csv = _improvement_csv(experiment)
        if imp_csv:
            _write_text(zf, 'csv/improvement_story.csv', imp_csv)
            (pack / 'csv' / 'improvement_story.csv').write_text(imp_csv, encoding='utf-8')
            notes.append('Packed csv/improvement_story.csv')
        else:
            notes.append('Missing improvement story CSV')

        ladder_rows = experiment.get('optimization_ladder') or []
        if ladder_rows:
            from .optimization_ladder import ladder_summary_table
            ladder_csv = pd.DataFrame(ladder_summary_table(ladder_rows)).to_csv(index=False)
            _write_text(zf, 'csv/optimization_ladder.csv', ladder_csv)
            (pack / 'csv' / 'optimization_ladder.csv').write_text(ladder_csv, encoding='utf-8')
            notes.append('Packed csv/optimization_ladder.csv')
            # Also keep a full-row dump for paper tables.
            full_ladder = pd.DataFrame(ladder_rows)
            keep = [c for c in full_ladder.columns if c not in {'node_paths', 'legs', 'coordinates'}]
            if keep:
                full_csv = full_ladder[keep].to_csv(index=False)
                _write_text(zf, 'csv/optimization_ladder_full.csv', full_csv)
                (pack / 'csv' / 'optimization_ladder_full.csv').write_text(full_csv, encoding='utf-8')
        else:
            notes.append('Missing optimization ladder CSV')

        report = build_experiment_report(experiment, scalability_rows)
        _write_text(zf, 'csv/experiment_report.json', report_to_json(report))
        report_rows = report_to_csv_rows(report)
        if report_rows:
            rbuf = io.StringIO()
            writer = csv.DictWriter(rbuf, fieldnames=list(report_rows[0].keys()))
            writer.writeheader()
            writer.writerows(report_rows)
            _write_text(zf, 'csv/experiment_report.csv', rbuf.getvalue())
        _write_text(zf, 'visuals/experiment_report.html', report_to_html(report))

        for name in (
            'scalability_results.csv',
            'benchmark_results.csv',
            'scalability_large_pathfinders.csv',
            'pathfinder_graph_scale.csv',
            'pathfinder_graph_scale_manifest.json',
            'brute_force_delivery_scale.csv',
            'brute_force_delivery_scale_manifest.json',
        ):
            if _copy_file_if_exists(zf, RESULTS / name, f'csv/{name}'):
                dest = pack / 'csv' / name
                dest.write_bytes((RESULTS / name).read_bytes())
                notes.append(f'Packed results/{name}')

        if scalability_rows and not (RESULTS / 'scalability_results.csv').is_file():
            scale_csv = pd.DataFrame(scalability_rows).to_csv(index=False)
            _write_text(zf, 'csv/scalability_session.csv', scale_csv)

        # Provenance
        prov = {
            'generated_at_utc': report['generated_at_utc'],
            'experiment': {
                'place': experiment.get('place'),
                'source': experiment.get('source'),
                'deliveries': experiment.get('delivery_count'),
                'seed': experiment.get('seed'),
                'network_nodes': experiment.get('network_nodes'),
                'network_edges': experiment.get('network_edges'),
            },
            'datasets': DATASET_PROVENANCE,
            'auto_explanation': understanding_results_text(experiment),
        }
        prov_text = json.dumps(prov, indent=2)
        _write_text(zf, 'csv/dataset_and_run_provenance.json', prov_text)
        (pack / 'csv' / 'dataset_and_run_provenance.json').write_text(prov_text, encoding='utf-8')

        # --- Screenshots (generated PNGs) ---
        (pack / 'screenshots').mkdir(exist_ok=True)
        table_png = _results_table_png(experiment)
        cards_png = _metrics_cards_png(experiment)
        _write_bytes(zf, 'screenshots/compare_results_table.png', table_png)
        _write_bytes(zf, 'screenshots/result_metric_cards.png', cards_png)
        (pack / 'screenshots' / 'compare_results_table.png').write_bytes(table_png)
        (pack / 'screenshots' / 'result_metric_cards.png').write_bytes(cards_png)
        notes.append('Generated PNG result screenshots')

        # --- Charts ---
        (pack / 'visuals').mkdir(exist_ok=True)
        rows_for_charts = scalability_rows
        if not rows_for_charts and (RESULTS / 'scalability_results.csv').is_file():
            rows_for_charts = pd.read_csv(RESULTS / 'scalability_results.csv').to_dict(orient='records')
        charts = _chart_bundle(rows_for_charts)
        for name, data in charts['html']:
            _write_bytes(zf, f'visuals/{name}', data)
            (pack / 'visuals' / name).write_bytes(data)
        for name, text in charts['csv']:
            _write_text(zf, f'visuals/{name}', text)
            (pack / 'visuals' / name).write_text(text, encoding='utf-8')
        for name, data in charts['png']:
            _write_bytes(zf, f'screenshots/{name}', data)
            (pack / 'screenshots' / name).write_bytes(data)
            notes.append(f'Chart PNG {name}')

        # Copy pre-exported figures if present
        if FIGURES.is_dir():
            for path in FIGURES.glob('*'):
                if path.is_file():
                    zf.write(path, f'visuals/figures/{path.name}')

        # Map HTML
        try:
            stops = experiment.get('stop_coords') or []
            map_rows = list(experiment.get('results') or [])
            story = experiment.get('improvement_story')
            if story:
                base = dict(story['baseline'])
                base['Algorithm'] = f"{ALGORITHM_SHORT.get(base['Algorithm'], 'Baseline')} baseline"
                base['Short name'] = base['Algorithm']
                improved = dict(story['improved'])
                improved['Algorithm'] = f"{ALGORITHM_SHORT.get(story['baseline']['Algorithm'], 'Algo')} improved"
                improved['Short name'] = improved['Algorithm']
                map_rows = map_rows + [base, improved]
            fmap = build_comparison_map(stops, map_rows, show_markers=True, title='FastRoute portfolio map')
            map_html = fmap.get_root().render()
            _write_text(zf, 'visuals/route_map.html', map_html)
            (pack / 'visuals' / 'route_map.html').write_text(map_html, encoding='utf-8')
            notes.append('Included interactive route map HTML')
        except Exception as exc:
            notes.append(f'Map export skipped: {exc}')

        # Docs
        (pack / 'docs').mkdir(exist_ok=True)
        for name in (
            'DATASET_METHODOLOGY.md',
            'BENCHMARK_METHODOLOGY.md',
            'ALGORITHMIC_EFFICIENCY_ANALYSIS.md',
            'ALGORITHM_THEORY.md',
            'OPTIMIZATION_TIER_COMPARABILITY.md',
            'ALGORITHM_CORRECTNESS_AUDIT.md',
            'FINAL_RUBRIC_AUDIT.md',
            'RESEARCH_PAPER_CHECKLIST.md',
            'FINAL_PROJECT_EVIDENCE_CHECKLIST.md',
        ):
            src = DOCS / name
            if src.is_file():
                zf.write(src, f'docs/{name}')
                (pack / 'docs' / name).write_bytes(src.read_bytes())

        data_readme = ROOT / 'data' / 'README.md'
        if data_readme.is_file():
            zf.write(data_readme, 'docs/DATA_README.md')

        # Prompts
        questions = _question_bank()
        _write_text(zf, 'prompts/CLO_AND_PAPER_QUESTIONS.md', questions)
        (pack / 'prompts').mkdir(exist_ok=True)
        (pack / 'prompts' / 'CLO_AND_PAPER_QUESTIONS.md').write_text(questions, encoding='utf-8')

        manifest = {
            'created_utc': stamp,
            'download_name': zip_name,
            'includes_improvement_story': bool(experiment.get('improvement_story')),
            'includes_optimization_ladder': bool(experiment.get('optimization_ladder')),
            'scientific_repair': {
                'astar_best_uses_cached_haversine_same_order': True,
                'nearest_neighbor_removed_from_active_ladder': True,
                'bf_sampled_mode': 'streaming_with_replacement',
                'bf_nested_budgets_same_seed': True,
                'improvement_story': 'dijkstra_original_order_vs_bf_order_plus_dijkstra',
            },
            'notes': notes,
            'paper_tip': (
                'Open visuals/*.html and screenshots/*.png for figures. '
                'Paste csv/* numbers into tables. Use prompts/* with ChatGPT carefully. '
                'improvement_story.csv and optimization_ladder.csv are the before/after + Bad→Best tables. '
                'Do not reuse historical NN-based ~92% improvement claims.'
            ),
        }
        _write_text(zf, 'MANIFEST.json', json.dumps(manifest, indent=2))
        (pack / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')

    # Also write the zip to disk under the FINAL name.
    zip_path = PACK_DIR / zip_name
    zip_path.write_bytes(buf.getvalue())
    notes.append(f'Wrote {zip_path}')

    # Stable pointers: latest/ and paper_evidence_FINAL/
    import shutil
    for alias in ('latest', 'paper_evidence_FINAL', 'paper_evidence'):
        target = PACK_DIR / alias
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(pack, target)

    return buf.getvalue(), pack, notes
