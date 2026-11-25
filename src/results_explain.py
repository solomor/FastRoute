"""Build human-readable explanations from measured experiment results only."""
from .algorithms import ALGORITHM_SHORT, WORK_COUNTER_UNITS


def route_quality(results):
    """Summarize route quality using only measured fields."""
    if not results:
        return {
            'shortest': None,
            'fastest': None,
            'lowest_memory': None,
            'exact_available': False,
        }
    shortest = min(results, key=lambda row: row['distance_m'])
    fastest = min(results, key=lambda row: row['Runtime (ms)'])
    lowest_memory = min(results, key=lambda row: row['Peak memory (KB)'])
    return {
        'shortest': shortest,
        'fastest': fastest,
        'lowest_memory': lowest_memory,
        'exact_available': any(row.get('exact') for row in results),
    }


def _by_name(results):
    return {row['Algorithm']: row for row in results}


def _pct_delta(new_value, base_value):
    if base_value is None or new_value is None:
        return None
    if abs(base_value) < 1e-12:
        return None
    return round(100.0 * (new_value / base_value - 1.0), 2)


def _abs_delta(new_value, base_value):
    if base_value is None or new_value is None:
        return None
    return round(new_value - base_value, 4)


def pairwise_comparisons(results):
    """Build head-to-head diffs from measured rows only."""
    by_name = _by_name(results)
    pairs = [
        ('A* Search Algorithm', "Dijkstra's Algorithm", 'Same stop order · pathfinding engines'),
        ('A* Search Algorithm', 'Brute-Force Route Search', 'Fixed order vs order search'),
        ("Dijkstra's Algorithm", 'Brute-Force Route Search', 'Fixed order vs order search'),
    ]
    rows = []
    for left, right, note in pairs:
        a = by_name.get(left)
        b = by_name.get(right)
        if a is None or b is None:
            continue
        dist_delta_km = _abs_delta(a.get('Distance (km)'), b.get('Distance (km)'))
        runtime_delta_ms = _abs_delta(a.get('Runtime (ms)'), b.get('Runtime (ms)'))
        work_a = a.get('Algorithm-Specific Work Counter', a.get('Operations / states'))
        work_b = b.get('Algorithm-Specific Work Counter', b.get('Operations / states'))
        rows.append({
            'Comparison': f"{ALGORITHM_SHORT[left]} vs {ALGORITHM_SHORT[right]}",
            'Left': ALGORITHM_SHORT[left],
            'Right': ALGORITHM_SHORT[right],
            'Note': note,
            f'{ALGORITHM_SHORT[left]} distance (km)': a.get('Distance (km)'),
            f'{ALGORITHM_SHORT[right]} distance (km)': b.get('Distance (km)'),
            'Distance delta (km)': dist_delta_km,
            'Distance delta (%)': _pct_delta(a.get('distance_m'), b.get('distance_m')),
            f'{ALGORITHM_SHORT[left]} runtime (ms)': a.get('Runtime (ms)'),
            f'{ALGORITHM_SHORT[right]} runtime (ms)': b.get('Runtime (ms)'),
            'Runtime delta (ms)': runtime_delta_ms,
            'Runtime delta (%)': _pct_delta(a.get('Runtime (ms)'), b.get('Runtime (ms)')),
            f'{ALGORITHM_SHORT[left]} work': work_a,
            f'{ALGORITHM_SHORT[right]} work': work_b,
            f'{ALGORITHM_SHORT[left]} work unit': a.get('Work unit') or WORK_COUNTER_UNITS.get(left),
            f'{ALGORITHM_SHORT[right]} work unit': b.get('Work unit') or WORK_COUNTER_UNITS.get(right),
            'Same route order': list(a.get('Route') or []) == list(b.get('Route') or []),
            'Distance match': abs((a.get('distance_m') or 0) - (b.get('distance_m') or 0)) <= 1e-6,
        })
    return rows


def pairwise_summary_table(results):
    """Compact table for the Compare Results UI."""
    rows = []
    for item in pairwise_comparisons(results):
        rows.append({
            'Comparison': item['Comparison'],
            'What differs': item['Note'],
            'Distance delta (km)': item['Distance delta (km)'],
            'Distance delta (%)': item['Distance delta (%)'],
            'Runtime delta (ms)': item['Runtime delta (ms)'],
            'Runtime delta (%)': item['Runtime delta (%)'],
            'Same delivery order': 'Yes' if item['Same route order'] else 'No',
            'Same distance': 'Yes' if item['Distance match'] else 'No',
        })
    return rows


def pairwise_comparison_bullets(results):
    """Short bullets explaining each available head-to-head pair."""
    bullets = []
    detailed = pairwise_comparisons(results)
    if not detailed:
        return ['Need at least two algorithms in the current experiment for head-to-head comparison.']
    for row in detailed:
        left = row['Left']
        right = row['Right']
        if row['Distance match']:
            dist_line = f'{left} and {right} matched on road distance.'
        else:
            delta = row['Distance delta (km)']
            pct = row['Distance delta (%)']
            if delta is None:
                dist_line = f'{left} vs {right}: distance comparison unavailable.'
            elif delta < 0:
                dist_line = (
                    f'{left} is shorter than {right} by {abs(delta)} km'
                    + (f' ({abs(pct)}% shorter).' if pct is not None else '.')
                )
            else:
                dist_line = (
                    f'{left} is longer than {right} by {delta} km'
                    + (f' ({pct}% longer).' if pct is not None else '.')
                )
        runtime_delta = row['Runtime delta (ms)']
        if runtime_delta is None:
            runtime_line = f'{left} vs {right}: runtime comparison unavailable.'
        elif abs(runtime_delta) < 1e-9:
            runtime_line = f'{left} and {right} had essentially the same runtime.'
        elif runtime_delta < 0:
            runtime_line = f'{left} was faster by {abs(runtime_delta)} ms.'
        else:
            runtime_line = f'{right} was faster by {runtime_delta} ms.'
        order_line = (
            f'{left} and {right} used the same delivery order.'
            if row['Same route order']
            else f'{left} and {right} used different delivery orders.'
        )
        bullets.append(f"**{row['Comparison']}** ({row['Note']}): {dist_line} {runtime_line} {order_line}")
        bullets.append(
            f"- Work counters stay algorithm-specific: {left} = {row[f'{left} work']} "
            f"({row[f'{left} work unit']}); {right} = {row[f'{right} work']} "
            f"({row[f'{right} work unit']}). Do not rank these units against each other."
        )
    return bullets


def algorithm_role_rows():
    """Static role comparison for Learn / Compare panels."""
    return [
        {
            'Algorithm': 'A*',
            'Job': 'Shortest road path with geographic heuristic',
            'Tour order': 'Keeps the sampled stop order',
            'What “best” means': 'Fewest meters on each leg (same as Dijkstra when heuristic is admissible)',
            'Scales to 1000 stops?': 'Yes (path searches per leg)',
            'Exact for multi-stop order?': 'No',
        },
        {
            'Algorithm': 'Dijkstra',
            'Job': 'Shortest road path / distance-matrix builder',
            'Tour order': 'Keeps the sampled stop order',
            'What “best” means': 'Fewest meters on each leg with nonnegative weights',
            'Scales to 1000 stops?': 'Yes (path searches per leg)',
            'Exact for multi-stop order?': 'No',
        },
        {
            'Algorithm': 'Brute Force',
            'Job': 'Search delivery orders on the road-distance matrix',
            'Tour order': 'Reorders deliveries (warehouse fixed at ends)',
            'What “best” means': 'Shortest closed tour among examined orders',
            'Scales to 1000 stops?': 'Yes only as sampled search; exact only for tiny n',
            'Exact for multi-stop order?': 'Yes when enumeration finishes; sampled otherwise',
        },
    ]


def understanding_results_text(experiment):
    """Natural-language summary of the current experiment. No invented numbers."""
    results = experiment.get('results') or []
    if not results:
        return ['No algorithm results are available for this experiment yet.']
    quality = route_quality(results)
    lines = []
    short = quality['shortest']
    fast = quality['fastest']
    mem = quality['lowest_memory']
    lines.append(
        f"**Shortest route among tested solvers:** {ALGORITHM_SHORT[short['Algorithm']]} at "
        f"{short['Distance (km)']} km ({short['distance_m']:.1f} meters of road)."
    )
    same_distance = [row for row in results if abs(row['distance_m'] - short['distance_m']) <= 1e-9]
    if len(same_distance) > 1:
        names = ', '.join(ALGORITHM_SHORT[row['Algorithm']] for row in same_distance)
        lines.append(f"Several solvers tied for shortest distance: {names}.")
    lines.append(
        f"**Lowest measured runtime:** {ALGORITHM_SHORT[fast['Algorithm']]} finished in "
        f"{fast['Runtime (ms)']} ms. Runtime is solver time only; OSM download and matrix "
        f"construction are excluded where applicable."
    )
    if fast['Algorithm'] != short['Algorithm']:
        lines.append(
            "The fastest solver was not the same as the shortest-route solver. "
            "Speed and route quality measure different things."
        )
    lines.append(
        f"**Lowest measured Python-traced memory:** {ALGORITHM_SHORT[mem['Algorithm']]} peaked at "
        f"{mem['Peak memory (KB)']} KB (`tracemalloc`, not full OS memory)."
    )
    lines.append(
        "A* and Dijkstra both search for shortest road paths. On the same stop order they should "
        "agree on distance; A* may explore fewer nodes when the heuristic helps. "
        "Brute-Force Route Search instead searches delivery orders."
    )
    for row in results:
        unit = row.get('Work unit') or WORK_COUNTER_UNITS.get(row['Algorithm'], 'algorithm-specific units')
        value = row.get('Algorithm-Specific Work Counter', row.get('Operations / states'))
        lines.append(f"- {ALGORITHM_SHORT[row['Algorithm']]}: {value} {unit}.")
    lines.append('Algorithm-specific work counters are not comparable across algorithms.')
    sampled_bf = next(
        (
            row for row in results
            if row['Algorithm'] == 'Brute-Force Route Search' and not row.get('exact')
        ),
        None,
    )
    if sampled_bf is not None:
        lines.append(
            f"Brute-Force Route Search ran in **sampled** mode ({sampled_bf.get('Operations / states')} "
            "orders evaluated), so it is not a proof of the global optimum on this matrix."
        )
    if quality['exact_available']:
        lines.append(
            "Brute-Force Route Search finished an exact enumeration, so optimality gaps compare "
            "each route against the best delivery order on this distance matrix."
        )
        for row in results:
            gap = row.get('Optimality gap (%)')
            if gap is None:
                lines.append(f"{ALGORITHM_SHORT[row['Algorithm']]}: optimality gap unavailable for this row.")
                continue
            if row.get('exact'):
                lines.append(
                    f"{ALGORITHM_SHORT[row['Algorithm']]} is the exact order search, so its gap is {gap}%."
                )
            elif abs(gap) < 1e-9:
                lines.append(
                    f"{ALGORITHM_SHORT[row['Algorithm']]} matched the brute-force optimum on this instance."
                )
            else:
                lines.append(
                    f"{ALGORITHM_SHORT[row['Algorithm']]} is {gap}% longer than the brute-force optimum "
                    "(usually because it kept the sampled stop order instead of reordering deliveries)."
                )
    else:
        lines.append(
            "Brute-Force Route Search did not run for this delivery count, so optimality gaps are "
            "unavailable. We cannot claim a pathfinding tour is a proven optimal multi-stop order."
        )
    return lines


def optimality_gap_help():
    return (
        "**How to read optimality gap**\n\n"
        "- **0%** means the route distance matches an **exact** Brute-Force Route Search on this matrix.\n"
        "- **5%** means the route is 5% longer than that exact order-search result.\n"
        "- **Unavailable / blank** means no exact brute-force reference ran (missing BF, or BF was sampled only).\n\n"
        "**Exact order search:** Brute-Force Route Search (when enumeration finishes).\n"
        "**Shortest-path engines:** Dijkstra and A* (same stop order; compare search work/runtime).\n\n"
        "Formula (only when optimal distance > 0):\n\n"
        "`Optimality Gap = ((Distance - Optimal Distance) / Optimal Distance) × 100`"
    )


def comparison_guide_text():
    return (
        "**How to compare the three algorithms**\n\n"
        "1. **A* vs Dijkstra** — same job (shortest road paths), usually the same tour distance on the "
        "same stop order. Prefer the one with lower runtime / fewer settled nodes on this map.\n"
        "2. **Pathfinders vs Brute Force** — different job. A*/Dijkstra keep the sampled order; "
        "Brute Force may reorder deliveries and change total km.\n"
        "3. **Distance** — solution quality (road meters).\n"
        "4. **Runtime / memory** — computational cost of the solve step.\n"
        "5. **Work counters** — algorithm-specific units only; never rank permutations against node settles.\n"
        "6. **Optimality gap** — only trustworthy when exact brute force finished."
    )
