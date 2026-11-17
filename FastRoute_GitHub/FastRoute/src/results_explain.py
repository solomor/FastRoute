"""Build human-readable explanations from measured experiment results only."""
from .algorithms import ALGORITHM_SHORT, WORK_COUNTER_UNITS


def route_quality(results):
    """Summarize route quality using only measured fields."""
    if not results:
        return {
            'shortest': None,
            'fastest': None,
            'lowest_memory': None,
            'nn_initial_km': None,
            'nn_two_opt_km': None,
            'two_opt_saved_km': None,
            'two_opt_improvement_pct': None,
            'exact_available': False,
        }
    shortest = min(results, key=lambda row: row['distance_m'])
    fastest = min(results, key=lambda row: row['Runtime (ms)'])
    lowest_memory = min(results, key=lambda row: row['Peak memory (KB)'])
    nn = next((row for row in results if row['Algorithm'].startswith('Nearest Neighbor (greedy)')), None)
    two_opt = next((row for row in results if row['Algorithm'].startswith('Nearest Neighbor + 2-Opt')), None)
    saved = None
    improvement = None
    nn_initial = None
    two_opt_km = None
    if two_opt is not None:
        two_opt_km = two_opt['Distance (km)']
        nn_initial = two_opt.get('Initial distance (km)')
        if nn_initial is not None:
            saved = round(nn_initial - two_opt_km, 3)
            if nn_initial > 0:
                improvement = round(100 * (nn_initial - two_opt_km) / nn_initial, 2)
    elif nn is not None:
        nn_initial = nn['Distance (km)']
    return {
        'shortest': shortest,
        'fastest': fastest,
        'lowest_memory': lowest_memory,
        'nn_initial_km': nn_initial,
        'nn_two_opt_km': two_opt_km,
        'two_opt_saved_km': saved,
        'two_opt_improvement_pct': improvement,
        'exact_available': any(row.get('exact') for row in results),
    }


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
        f"{fast['Runtime (ms)']} ms. Runtime is solver time only; OSM download and Dijkstra "
        f"matrix construction are excluded."
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
        "Algorithm-specific work counters (permutations, DP states, candidate checks) are "
        "not comparable across algorithms, so they are not ranked here. Prefer runtime and "
        "memory for resource comparisons, and distance / optimality gap for solution quality."
    )
    for row in results:
        unit = row.get('Work unit') or WORK_COUNTER_UNITS.get(row['Algorithm'], 'algorithm-specific units')
        value = row.get('Algorithm-Specific Work Counter', row.get('Operations / states'))
        lines.append(
            f"- {ALGORITHM_SHORT[row['Algorithm']]}: {value} {unit}."
        )
    if quality['nn_initial_km'] is not None and quality['nn_two_opt_km'] is not None:
        if quality['two_opt_saved_km'] is not None and quality['two_opt_saved_km'] > 0:
            lines.append(
                f"**2-Opt improvement:** Nearest Neighbor started at {quality['nn_initial_km']} km. "
                f"After 2-Opt the route was {quality['nn_two_opt_km']} km, saving "
                f"{quality['two_opt_saved_km']} km ({quality['two_opt_improvement_pct']}% shorter)."
            )
        elif quality['two_opt_saved_km'] == 0:
            lines.append(
                f"**2-Opt improvement:** 2-Opt did not find an improving swap. "
                f"The route stayed at {quality['nn_two_opt_km']} km."
            )
        else:
            lines.append(
                f"**2-Opt result:** final distance {quality['nn_two_opt_km']} km "
                f"(NN seed {quality['nn_initial_km']} km)."
            )
    if quality['exact_available']:
        lines.append(
            "An exact solver ran on this stop count, so optimality gaps compare each route "
            "against the known optimum for the same distance matrix."
        )
        for row in results:
            gap = row.get('Optimality gap (%)')
            if gap is None:
                lines.append(
                    f"{ALGORITHM_SHORT[row['Algorithm']]}: optimality gap unavailable for this row."
                )
                continue
            if row.get('exact'):
                lines.append(
                    f"{ALGORITHM_SHORT[row['Algorithm']]} is exact, so its gap is {gap}% "
                    "(matching the optimal distance)."
                )
            else:
                matched = abs(gap) < 1e-9
                if matched:
                    lines.append(
                        f"{ALGORITHM_SHORT[row['Algorithm']]} matched the known exact optimum on this instance."
                    )
                else:
                    lines.append(
                        f"{ALGORITHM_SHORT[row['Algorithm']]} is {gap}% longer than the exact optimum."
                    )
    else:
        lines.append(
            "No exact solver ran for this delivery count, so optimality gaps are unavailable. "
            "We cannot claim that a heuristic found a proven optimal route."
        )
    lines.append(
        "Overall, this run shows the usual trade-off: exact methods search more carefully, "
        "while heuristics finish faster and may leave some distance on the table."
    )
    return lines


def optimality_gap_help():
    return (
        "**How to read optimality gap**\n\n"
        "- **0%** means the route distance matches the known optimal distance.\n"
        "- **5%** means the route is 5% longer than the known optimal distance.\n"
        "- **Unavailable / blank** means no exact solver ran, or the optimum was zero and the "
        "comparison is undefined.\n\n"
        "**Exact algorithms:** Brute Force, Held-Karp.\n"
        "**Heuristic algorithms:** Nearest Neighbor, Nearest Neighbor + 2-Opt.\n\n"
        "Formula (only when optimal distance > 0):\n\n"
        "`Optimality Gap = ((Heuristic Distance - Optimal Distance) / Optimal Distance) × 100`\n\n"
        "The optimal distance is the best exact result on the **same** delivery stops and road-distance matrix."
    )
