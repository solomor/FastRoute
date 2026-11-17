"""Generate downloadable experiment reports from measured session data only."""
import html
import json
from datetime import datetime, timezone
from .algorithms import ALGORITHM_SHORT, WORK_COUNTER_UNITS
from .results_explain import understanding_results_text, route_quality, optimality_gap_help


def _esc(value):
    if value is None:
        return ''
    return html.escape(str(value), quote=True)


def build_experiment_report(experiment, scalability_rows=None):
    """Assemble a structured report dict. Missing values stay missing."""
    results = experiment.get('results') or []
    quality = route_quality(results)
    report = {
        'project': 'FastRoute',
        'course': 'CPS 3440 Analysis of Algorithms',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'place': experiment.get('place'),
        'stop_source': experiment.get('source'),
        'deliveries': experiment.get('delivery_count'),
        'seed': experiment.get('seed'),
        'network_nodes': experiment.get('network_nodes'),
        'network_edges': experiment.get('network_edges'),
        'metric': 'road length in meters (not live traffic time)',
        'algorithms_tested': [row['Algorithm'] for row in results],
        'results': [
            {
                'algorithm': row['Algorithm'],
                'short_name': ALGORITHM_SHORT.get(row['Algorithm'], row['Algorithm']),
                'distance_km': row.get('Distance (km)'),
                'distance_m': row.get('distance_m'),
                'runtime_ms': row.get('Runtime (ms)'),
                'peak_memory_kb': row.get('Peak memory (KB)'),
                'algorithm_specific_work_counter': row.get('Algorithm-Specific Work Counter', row.get('Operations / states')),
                'work_unit': row.get('Work unit', WORK_COUNTER_UNITS.get(row['Algorithm'])),
                'operations_or_states': row.get('Operations / states'),
                'optimality_gap_percent': row.get('Optimality gap (%)'),
                'exact': bool(row.get('exact')),
                'initial_nn_distance_km': row.get('Initial distance (km)'),
                'two_opt_swaps': row.get('2-Opt swaps'),
                'route_order': row.get('Route'),
            }
            for row in results
        ],
        'route_quality': {
            'shortest_algorithm': None if quality['shortest'] is None else quality['shortest']['Algorithm'],
            'shortest_distance_km': None if quality['shortest'] is None else quality['shortest']['Distance (km)'],
            'fastest_algorithm': None if quality['fastest'] is None else quality['fastest']['Algorithm'],
            'fastest_runtime_ms': None if quality['fastest'] is None else quality['fastest']['Runtime (ms)'],
            'lowest_memory_algorithm': None if quality['lowest_memory'] is None else quality['lowest_memory']['Algorithm'],
            'lowest_memory_kb': None if quality['lowest_memory'] is None else quality['lowest_memory']['Peak memory (KB)'],
            'nn_initial_km': quality['nn_initial_km'],
            'nn_two_opt_km': quality['nn_two_opt_km'],
            'two_opt_saved_km': quality['two_opt_saved_km'],
            'two_opt_improvement_pct': quality['two_opt_improvement_pct'],
            'exact_available': quality['exact_available'],
        },
        'automatic_explanation': understanding_results_text(experiment),
        'optimality_gap_notes': optimality_gap_help(),
        'benchmark_settings': {
            'note': 'TSP runtime excludes OSM download and Dijkstra distance-matrix construction. Peak memory is Python tracemalloc, not full OS RSS.',
            'scalability_rows': scalability_rows or [],
        },
        'limitations': [
            'One warehouse, one vehicle, closed tour.',
            'Optimizes road distance, not live traffic travel time.',
            'No capacity constraints or time windows.',
            'Dataset coordinates are snapped to OSM intersections and are not claimed as historical multi-stop driver traces.',
            'Exact solvers are capped for UI responsiveness.',
            'Algorithm-specific work counters are not comparable across algorithms.',
        ],
    }
    return report


def report_to_json(report):
    return json.dumps(report, indent=2, default=str)


def report_to_csv_rows(report):
    rows = []
    for item in report.get('results', []):
        rows.append({
            'project': report['project'],
            'generated_at_utc': report['generated_at_utc'],
            'place': report.get('place'),
            'stop_source': report.get('stop_source'),
            'deliveries': report.get('deliveries'),
            'seed': report.get('seed'),
            'algorithm': item['algorithm'],
            'distance_km': item['distance_km'],
            'runtime_ms': item['runtime_ms'],
            'peak_memory_kb': item['peak_memory_kb'],
            'algorithm_specific_work_counter': item.get('algorithm_specific_work_counter'),
            'work_unit': item.get('work_unit'),
            'operations_or_states': item['operations_or_states'],
            'optimality_gap_percent': item['optimality_gap_percent'],
            'initial_nn_distance_km': item['initial_nn_distance_km'],
            'two_opt_swaps': item['two_opt_swaps'],
        })
    return rows


def report_to_html(report):
    explanation = ''.join(
        f'<li>{_esc(line.replace("**", ""))}</li>'
        for line in report.get('automatic_explanation', [])
    )
    result_rows = ''.join(
        '<tr>'
        f"<td>{_esc(item['short_name'])}</td>"
        f"<td>{_esc(item['distance_km'])}</td>"
        f"<td>{_esc(item['runtime_ms'])}</td>"
        f"<td>{_esc(item['peak_memory_kb'])}</td>"
        f"<td>{_esc(item.get('algorithm_specific_work_counter'))} "
        f"({_esc(item.get('work_unit') or 'algorithm-specific units')})</td>"
        f"<td>{_esc(item['optimality_gap_percent'] if item['optimality_gap_percent'] is not None else 'Unavailable')}</td>"
        '</tr>'
        for item in report.get('results', [])
    )
    limitations = ''.join(f'<li>{_esc(item)}</li>' for item in report.get('limitations', []))
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>FastRoute Experiment Report</title>
<style>
body {{ font-family: Segoe UI, sans-serif; margin: 2rem; color: #0f172a; }}
table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
th, td {{ border: 1px solid #cbd5e1; padding: 8px; text-align: left; }}
th {{ background: #e2e8f0; }}
h1,h2 {{ color: #0f172a; }}
</style></head><body>
<h1>FastRoute Experiment Report</h1>
<p><b>Generated (UTC):</b> {_esc(report['generated_at_utc'])}</p>
<p><b>Area:</b> {_esc(report.get('place'))}<br>
<b>Stop source:</b> {_esc(report.get('stop_source'))}<br>
<b>Deliveries:</b> {_esc(report.get('deliveries'))}<br>
<b>Seed:</b> {_esc(report.get('seed'))}<br>
<b>Road graph:</b> {_esc(report.get('network_nodes'))} nodes, {_esc(report.get('network_edges'))} edges<br>
<b>Metric:</b> {_esc(report.get('metric'))}</p>
<h2>Algorithm Results</h2>
<table>
<tr><th>Algorithm</th><th>Distance (km)</th><th>Runtime (ms)</th><th>Peak memory (KB)</th><th>Algorithm-specific work</th><th>Optimality gap (%)</th></tr>
{result_rows}
</table>
<h2>Automatic Explanation</h2>
<ul>{explanation}</ul>
<h2>Limitations</h2>
<ul>{limitations}</ul>
<p>This report contains only measured experiment values. Missing fields were left blank or marked unavailable. Work counters are not comparable across algorithms.</p>
</body></html>"""
