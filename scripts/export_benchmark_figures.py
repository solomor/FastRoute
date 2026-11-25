"""Export paper/site charts from measured scalability CSVs.

Run:
  .venv\\Scripts\\python.exe -m scripts.export_benchmark_figures
"""
from pathlib import Path
import pandas as pd
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'results'
FIGURES = ROOT / 'figures'


def _load(path):
    if not path.is_file():
        return None
    frame = pd.read_csv(path)
    return frame[frame['status'] == 'ok'].copy() if 'status' in frame.columns else frame


def _save_bar(frame, x, y, color, title, outfile):
    fig = px.line(frame, x=x, y=y, color=color, markers=True, title=title)
    fig.update_layout(template='plotly_white', legend_title_text='')
    outfile.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(outfile.with_suffix('.html')))
    frame[[x, color, y]].to_csv(outfile.with_suffix('.csv'), index=False)
    print(f'Wrote {outfile.with_suffix(".html")} and {outfile.with_suffix(".csv")}')


def main():
    FIGURES.mkdir(exist_ok=True)
    scale = _load(RESULTS / 'scalability_results.csv')
    large = _load(RESULTS / 'scalability_large_pathfinders.csv')
    offline = _load(RESULTS / 'benchmark_results.csv')

    frames = []
    for frame in (scale, offline):
        if frame is not None and not frame.empty:
            frames.append(frame)
    if not frames:
        raise SystemExit(
            'No measured results found. Run: python -m benchmarks.run_benchmarks'
        )

    primary = frames[0]
    name_col = 'short_name' if 'short_name' in primary.columns else 'algorithm'
    runtime_col = 'avg_runtime_ms' if 'avg_runtime_ms' in primary.columns else None
    if runtime_col is None:
        raise SystemExit('CSV missing avg_runtime_ms')

    _save_bar(
        primary,
        'deliveries',
        runtime_col,
        name_col,
        'Runtime vs deliveries (measured)',
        FIGURES / 'runtime_vs_deliveries',
    )
    if 'avg_distance_km' in primary.columns:
        _save_bar(
            primary,
            'deliveries',
            'avg_distance_km',
            name_col,
            'Tour distance vs deliveries (measured)',
            FIGURES / 'distance_vs_deliveries',
        )
    ops_col = 'avg_operations' if 'avg_operations' in primary.columns else 'operations_or_states'
    if ops_col in primary.columns:
        _save_bar(
            primary,
            'deliveries',
            ops_col,
            name_col,
            'Work counter vs deliveries (algorithm-specific units)',
            FIGURES / 'operations_vs_deliveries',
        )

    if large is not None and not large.empty:
        _save_bar(
            large,
            'deliveries',
            'avg_runtime_ms',
            'short_name' if 'short_name' in large.columns else 'algorithm',
            'Large-n pathfinder runtime (A* vs Dijkstra)',
            FIGURES / 'large_pathfinder_runtime',
        )

    print(f'Figures directory: {FIGURES}')


if __name__ == '__main__':
    main()
