"""Streamlit section renderers for the FastRoute dashboard."""
import csv
import io
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from .algorithms import ALGORITHM_COLORS, ALGORITHM_SHORT, ALGORITHMS, WORK_COUNTER_UNITS
from .constants import BRUTE_FORCE_EXACT_MAX_STOPS, BRUTE_FORCE_SAMPLE_BUDGET
from .dijkstra_viz import (
    build_dijkstra_animation_html,
    build_dijkstra_trace,
    is_reachable,
    sample_intersection_choices,
    sample_reachable_pair,
)
from .guided_demo import DEMO_STEPS, clamp_step
from .learn_content import ALGORITHM_LESSONS, DIJKSTRA_LESSON, limitations_copy, pipeline_steps
from .improvement import build_improvement_story
from .map_viz import build_comparison_map, build_live_animation_html
from .optimization_ladder import (
    LADDER_SPECS,
    TIER_COLORS,
    ladder_summary_table,
    run_optimization_ladder,
)
from .portfolio_export import PAPER_EVIDENCE_ZIP_NAME, build_portfolio_zip
from .report import build_experiment_report, report_to_csv_rows, report_to_html, report_to_json
from .results_explain import (
    algorithm_role_rows,
    comparison_guide_text,
    optimality_gap_help,
    pairwise_comparison_bullets,
    pairwise_summary_table,
    route_quality,
    understanding_results_text,
)
from .road_data import stop_labels
from .scalability import (
    DEFAULT_COUNTS,
    LARGE_PATHFINDER_COUNTS,
    available_scale_counts,
    max_delivery_capacity,
    run_scalability,
    save_scalability_csv,
    unavailable_scale_counts,
)


def render_build_and_watch(experiment):
    """Map + live animation for the current experiment."""
    if experiment is None:
        st.info('Configure the sidebar and click **Compare All** to build a delivery experiment.')
        return
    results = experiment['results']
    if not results:
        st.warning('No algorithm results for this stop count.')
        return
    c1, c2, c3 = st.columns([2.4, 1.2, 1.2])
    with c1:
        options = [row['Algorithm'] for row in results]
        # One-time restore: older sessions hid Dijkstra so only green A* showed.
        if not st.session_state.get('routes_visibility_show_all_v2'):
            st.session_state.visible_algorithms = list(options)
            st.session_state.routes_visibility_show_all_v2 = True
        default_visible = [name for name in st.session_state.visible_algorithms if name in set(options)]
        if not default_visible:
            default_visible = options
        visible = st.multiselect(
            'Show / hide algorithm routes',
            options,
            default=default_visible,
            format_func=lambda name: ALGORITHM_SHORT.get(name, name),
            help='Uncheck a name to hide that route. Click map chips/legend items to toggle without reloading.',
            key='visible_algo_routes_v2',
        )
        st.session_state.visible_algorithms = visible
    with c2:
        st.session_state.show_markers = st.toggle('Show markers', value=st.session_state.show_markers)
    with c3:
        anim_speed = st.select_slider('Live draw speed', options=['Slow', 'Normal', 'Fast'], value='Normal')

    if not visible:
        st.warning('No routes selected. Choose at least one algorithm above to draw routes on the map.')

    quality = route_quality(results)
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f'<div class="metric-card"><div class="metric-label">Stops</div><div class="metric-value">{experiment["delivery_count"]}</div></div>', unsafe_allow_html=True)
    m2.markdown(f'<div class="metric-card"><div class="metric-label">Shortest</div><div class="metric-value">{quality["shortest"]["Distance (km)"]} km</div></div>', unsafe_allow_html=True)
    m3.markdown(f'<div class="metric-card"><div class="metric-label">Fastest</div><div class="metric-value">{quality["fastest"]["Runtime (ms)"]} ms</div></div>', unsafe_allow_html=True)
    m4.markdown(f'<div class="metric-card"><div class="metric-label">Road graph</div><div class="metric-value">{experiment["network_nodes"]:,}</div></div>', unsafe_allow_html=True)

    snap = experiment.get('snap')
    if snap:
        stats = snap['stats']
        st.caption(
            f"Snapping: {stats['accepted']}/{stats['requested']} accepted · "
            f"rejected {stats['rejected']} · shared-node locations {stats['shared_node_locations']} · "
            f"avg snap {stats['avg_snap_distance_m']} m · max snap {stats['max_snap_distance_m']} m"
        )
        with st.expander('Snap details (original vs road node)'):
            st.dataframe(pd.DataFrame(snap['records']), use_container_width=True, hide_index=True)
    if experiment.get('map_simplified'):
        st.info(
            'Large route: the map still follows street centerlines, with fewer vertices kept so the '
            'browser stays responsive. Reported distances still use full road shortest paths.'
        )
    st.caption(
        'A* = solid green (on top). Dijkstra = dashed orange (underneath). '
        'They often share the same stop order. Click a chip/legend item to hide one if the map looks crowded.'
    )
    requested = experiment.get('requested_delivery_count')
    actual = experiment.get('delivery_count')
    if requested is not None and actual is not None and requested != actual:
        st.caption(f'Requested {requested} deliveries · using {actual} mutually reachable snapped stops.')

    validation = experiment.get('dataset_validation')
    if validation:
        with st.expander('Dataset validation summary'):
            st.json(validation)

    autoplay = st.session_state.autoplay_map
    html = build_live_animation_html(
        experiment['stop_coords'],
        results,
        show_algorithms=visible,
        show_markers=st.session_state.show_markers,
        autoplay=autoplay and bool(visible),
        speed=anim_speed,
        height=700,
    )
    components.html(html, height=760, scrolling=False)
    st.session_state.autoplay_map = False
    st.info('Use **Play all / Pause / Resume / Reset** on the map toolbar for live drawing with no page reload.')
    st.caption(f"Stop source: {experiment['source']} · Area: {experiment['place']}")


def _render_optimization_ladder(experiment, graph):
    """Bad → Semi → Best tiers for each algorithm family."""
    st.subheader('Optimization ladder (Bad → Semi → Best)')
    st.caption(
        'Teacher-style optimized versions: each algorithm family runs a weak baseline, '
        'a solid course implementation, and a stronger optimized variant on the **same stops**.'
    )
    if graph is None:
        st.info('Load a road graph so the ladder can re-run pathfinders.')
        return

    families = st.multiselect(
        'Families to ladder',
        list(LADDER_SPECS),
        default=list(LADDER_SPECS),
        format_func=lambda name: ALGORITHM_SHORT.get(name, name),
        key='ladder_families',
    )
    if st.button('Run Bad / Semi / Best ladder', type='primary', key='run_opt_ladder'):
        if not families:
            st.error('Select at least one algorithm family.')
        else:
            with st.spinner('Running optimization ladder (up to 9 variants)...'):
                try:
                    rows = run_optimization_ladder(
                        graph,
                        experiment['stops'],
                        matrix=experiment.get('matrix'),
                        families=families,
                        seed=int(experiment.get('seed') or 42),
                    )
                    experiment['optimization_ladder'] = rows
                    st.session_state.experiment = experiment
                    st.success(f'Measured {len(rows)} tier results.')
                except Exception as exc:
                    st.error(f'Ladder failed: {exc}')
                    return

    rows = experiment.get('optimization_ladder') or []
    if not rows:
        st.info('Click **Run Bad / Semi / Best ladder** after Compare All.')
        return

    summary = ladder_summary_table(rows)
    st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)
    st.download_button(
        'Download ladder CSV',
        pd.DataFrame(summary).to_csv(index=False).encode(),
        'fastroute_optimization_ladder.csv',
        'text/csv',
        key='ladder_csv_dl',
    )

    chart_df = pd.DataFrame(summary)
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(
            chart_df, x='Tier', y='Runtime (ms)', color='Family', barmode='group',
            category_orders={'Tier': ['Bad', 'Semi', 'Best']},
            title='Runtime by optimization tier',
        )
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)', font_color='#E2E8F0')
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.bar(
            chart_df, x='Tier', y='Work counter', color='Family', barmode='group',
            category_orders={'Tier': ['Bad', 'Semi', 'Best']},
            title='Work counter by tier (units differ by family)',
        )
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)', font_color='#E2E8F0')
        st.plotly_chart(fig, use_container_width=True)

    with st.expander('What each tier means'):
        for family, tiers in LADDER_SPECS.items():
            st.markdown(f"**{ALGORITHM_SHORT.get(family, family)}**")
            for tier in ('Bad', 'Semi', 'Best'):
                color = TIER_COLORS[tier]
                st.markdown(
                    f"- <span style='color:{color}'>**{tier}**</span>: {tiers[tier]['label']}",
                    unsafe_allow_html=True,
                )


def _render_improvement_story(experiment, graph):
    """Original sample order (Dijkstra) vs BF-chosen order (same Dijkstra engine)."""
    st.subheader('Improvement story')
    st.caption(
        'Before: original delivery order + Dijkstra. After: Brute-Force Route Search chooses a '
        'delivery order, then the **same Dijkstra** engine rebuilds the tour on the same graph/stops. '
        'Nearest-neighbor order is not used (it would change the problem, not improve pathfinding).'
    )
    if graph is None:
        st.info('Load a road graph (sidebar area) so the tuned re-run can execute.')
        return

    deliveries = max(0, len(experiment.get('stops') or []) - 1)
    auto_ready = deliveries <= 25 and not experiment.get('improvement_story')
    run_clicked = st.button('Run before/after improvement', type='primary', key='run_improvement_story')
    if run_clicked or auto_ready:
        with st.spinner('Running Dijkstra original order vs Brute-Force order + Dijkstra...'):
            try:
                story = build_improvement_story(experiment, graph)
                experiment['improvement_story'] = story
                st.session_state.experiment = experiment
            except Exception as exc:
                st.error(f'Unable to build the improvement story: {exc}')
                return

    story = experiment.get('improvement_story')
    if not story:
        st.info('Click **Run before/after improvement** after Compare All to generate the story.')
        return

    baseline = story['baseline']
    improved = story['improved']
    for line in story['narrative']:
        st.markdown(f'- {line}')

    c1, c2, c3 = st.columns(3)
    c1.metric(
        'Before (Dijkstra order)',
        f"{baseline['Distance (km)']} km",
        f"{baseline['Runtime (ms)']} ms pathfinding",
    )
    delta_label = f"{story['distance_delta_km']} km"
    if story.get('distance_delta_pct') is not None:
        delta_label = f"{story['distance_delta_pct']}%"
    c2.metric(
        'After (BF order + Dijkstra)',
        f"{improved['Distance (km)']} km",
        delta_label,
        delta_color='inverse',
    )
    timings = story.get('timings') or {}
    c3.metric(
        'End-to-end (matrix+search+paths)',
        f"{timings.get('total_end_to_end_ms', '—')} ms",
        f"search {timings.get('route_search_ms', '—')} ms",
    )
    st.caption(story['settings_label'])
    if timings:
        st.caption(
            f"Timing split — matrix {timings.get('distance_matrix_prep_ms')} ms · "
            f"original pathfinding {timings.get('original_pathfinding_ms')} ms · "
            f"BF search {timings.get('route_search_ms')} ms · "
            f"reconstruct {timings.get('improved_reconstruction_ms')} ms."
        )
    search = story.get('search') or {}
    if search:
        st.caption(
            f"BF status: mode={search.get('search_mode')} · exact={search.get('exact')} · "
            f"budget={search.get('budget')} · evaluations={search.get('candidate_evaluations')} · "
            f"seed={search.get('seed')}."
        )

    before_after = pd.DataFrame([
        {
            'Stage': 'Before',
            'Algorithm': baseline.get('Short name', 'Dijkstra original order'),
            'Distance (km)': baseline['Distance (km)'],
            'Runtime (ms)': baseline['Runtime (ms)'],
            'Work counter': baseline.get('Algorithm-Specific Work Counter', baseline.get('Operations / states')),
            'Delivery order': ' → '.join(str(i) for i in baseline['Route']),
        },
        {
            'Stage': 'After',
            'Algorithm': improved.get('Short name', 'Dijkstra BF order'),
            'Distance (km)': improved['Distance (km)'],
            'Runtime (ms)': improved['Runtime (ms)'],
            'Work counter': improved.get('Algorithm-Specific Work Counter', improved.get('Operations / states')),
            'Delivery order': ' → '.join(str(i) for i in improved['Route']),
        },
    ])
    st.dataframe(before_after, use_container_width=True, hide_index=True)

    chart_df = pd.DataFrame([
        {'Stage': 'Before', 'Distance (km)': baseline['Distance (km)'], 'Runtime (ms)': baseline['Runtime (ms)']},
        {'Stage': 'After', 'Distance (km)': improved['Distance (km)'], 'Runtime (ms)': improved['Runtime (ms)']},
    ])
    g1, g2 = st.columns(2)
    with g1:
        fig = px.bar(chart_df, x='Stage', y='Distance (km)', color='Stage', title='Route distance before → after')
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)', font_color='#E2E8F0', showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with g2:
        fig = px.bar(chart_df, x='Stage', y='Runtime (ms)', color='Stage', title='Dijkstra pathfinding runtime before → after')
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)', font_color='#E2E8F0', showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    baseline_map = dict(baseline)
    baseline_map['Algorithm'] = 'Dijkstra original order'
    baseline_map['Short name'] = 'Dijkstra original order'
    improved_map = dict(improved)
    improved_map['Algorithm'] = 'Dijkstra BF order'
    improved_map['Short name'] = 'Dijkstra BF order'
    map_rows = [baseline_map, improved_map]
    try:
        fmap = build_comparison_map(
            experiment['stop_coords'],
            map_rows,
            show_markers=True,
            title='Before/after: sample order vs BF order (Dijkstra)',
        )
        components.html(fmap.get_root().render(), height=480)
        st.caption('Map: original-order Dijkstra tour vs BF-order Dijkstra tour (same pathfinding engine).')
    except Exception as exc:
        st.warning(f'Could not draw the before/after map: {exc}')


def render_compare_results(experiment, graph=None):
    if experiment is None:
        st.info('Run **Compare All** first to populate this section.')
        return
    results = experiment['results']
    if not results:
        st.warning('No results available.')
        return

    _render_improvement_story(experiment, graph)
    _render_optimization_ladder(experiment, graph)

    st.subheader('Route quality snapshot')
    quality = route_quality(results)
    q1, q2, q3, q4 = st.columns(4)
    q1.metric('Shortest route', f"{quality['shortest']['Distance (km)']} km", ALGORITHM_SHORT[quality['shortest']['Algorithm']])
    q2.metric('Fastest computation', f"{quality['fastest']['Runtime (ms)']} ms", ALGORITHM_SHORT[quality['fastest']['Algorithm']])
    q3.metric('Lowest memory', f"{quality['lowest_memory']['Peak memory (KB)']} KB", ALGORITHM_SHORT[quality['lowest_memory']['Algorithm']])
    exact = next((row for row in results if row.get('exact')), None)
    brute = next((row for row in results if row['Algorithm'] == 'Brute-Force Route Search'), None)
    if exact is not None:
        q4.metric('Exact order search', f"{exact['Distance (km)']} km", 'Brute Force')
    elif brute is not None:
        q4.metric('Sampled order search', f"{brute['Distance (km)']} km", f'≤ {BRUTE_FORCE_SAMPLE_BUDGET:,} perms')
    else:
        q4.metric('Order search', 'Unavailable', f'Exact ≤ {BRUTE_FORCE_EXACT_MAX_STOPS}')

    st.caption(
        'A* and Dijkstra follow the sampled stop order using shortest road paths. '
        'Brute-Force Route Search reorders deliveries. Fastest is not always shortest.'
    )

    st.subheader('What each algorithm is doing')
    st.dataframe(pd.DataFrame(algorithm_role_rows()), use_container_width=True, hide_index=True)
    st.markdown(comparison_guide_text())

    st.subheader('Side-by-side results')
    cols = st.columns(len(results))
    for col, row in zip(cols, results):
        short = ALGORITHM_SHORT[row['Algorithm']]
        with col:
            st.markdown(
                f"<div class='metric-card'><div class='metric-label'>{short}</div>"
                f"<div class='metric-value' style='font-size:1.4rem'>{row.get('Distance (km)')} km</div></div>",
                unsafe_allow_html=True,
            )
            st.caption(f"Runtime: {row.get('Runtime (ms)')} ms")
            st.caption(f"Memory: {row.get('Peak memory (KB)')} KB")
            work = row.get('Algorithm-Specific Work Counter', row.get('Operations / states'))
            st.caption(f"Work: {work}")
            st.caption(row.get('Work unit') or WORK_COUNTER_UNITS.get(row['Algorithm'], ''))
            gap = row.get('Optimality gap (%)')
            st.caption('Gap: ' + ('Unavailable' if gap is None else f'{gap}%'))
            if row.get('exact'):
                st.success('Exact order search')
            elif row['Algorithm'] == 'Brute-Force Route Search':
                st.warning('Sampled order search')
            else:
                st.info('Fixed sample order')

    st.subheader('Head-to-head comparison')
    pair_table = pairwise_summary_table(results)
    if pair_table:
        st.dataframe(pd.DataFrame(pair_table), use_container_width=True, hide_index=True)
        st.caption(
            'Distance/runtime deltas are Left − Right from the Comparison label '
            '(for example A* vs Dijkstra means A* minus Dijkstra).'
        )
        for line in pairwise_comparison_bullets(results):
            st.markdown(f'- {line}')
    else:
        st.info('Run at least two algorithms to see head-to-head deltas.')

    st.subheader('Full comparison table')
    table_rows = []
    for row in results:
        table_rows.append({
            'Algorithm': row['Algorithm'],
            'Distance (km)': row.get('Distance (km)'),
            'Runtime (ms)': row.get('Runtime (ms)'),
            'Peak memory (KB)': row.get('Peak memory (KB)'),
            'Algorithm-Specific Work Counter': row.get('Algorithm-Specific Work Counter', row.get('Operations / states')),
            'Work unit': row.get('Work unit'),
            'Optimality gap (%)': row.get('Optimality gap (%)'),
            'Exact order search': bool(row.get('exact')),
        })
    table = pd.DataFrame(table_rows)
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.caption(
        'Work counters are algorithm-specific (A*/Dijkstra node settles vs brute-force permutations) and '
        'must not be ranked against each other. Compare runtime/memory for resources and distance/gap for quality.'
    )
    st.markdown(optimality_gap_help())

    st.subheader('What Do These Results Mean?')
    for line in understanding_results_text(experiment):
        st.markdown(f'- {line}')

    labels = stop_labels(len(experiment['stops']))
    for row in results:
        pretty = [labels[stop_i] if stop_i < len(labels) else f'#{stop_i}' for stop_i in row['Route']]
        with st.expander(f"{ALGORITHM_SHORT[row['Algorithm']]} delivery order"):
            st.write(' → '.join(pretty))

    st.subheader('Performance charts')
    chart_df = pd.DataFrame([
        {
            'Algorithm': ALGORITHM_SHORT[row['Algorithm']],
            'Distance (km)': row['Distance (km)'],
            'Runtime (ms)': row['Runtime (ms)'],
            'Peak memory (KB)': row['Peak memory (KB)'],
            'Work counter': row.get('Algorithm-Specific Work Counter', row.get('Operations / states')),
            'Optimality gap (%)': row['Optimality gap (%)'],
            'exact': row.get('exact'),
        }
        for row in results
    ])
    color_map = {ALGORITHM_SHORT[k]: v for k, v in ALGORITHM_COLORS.items()}
    g1, g2 = st.columns(2)
    with g1:
        fig = px.bar(chart_df, x='Algorithm', y='Distance (km)', color='Algorithm', color_discrete_map=color_map, title='Route distance (solution quality)')
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)', font_color='#E2E8F0', showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption('Lower road distance is better. This is not travel time.')
    with g2:
        fig = px.bar(chart_df, x='Algorithm', y='Runtime (ms)', color='Algorithm', color_discrete_map=color_map, title='Solver runtime (ms)')
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)', font_color='#E2E8F0', showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption('Lower runtime is faster computation. Fastest ≠ shortest route.')
    g3, g4 = st.columns(2)
    with g3:
        fig = px.bar(chart_df, x='Algorithm', y='Peak memory (KB)', color='Algorithm', color_discrete_map=color_map, title='Peak Python-traced memory')
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)', font_color='#E2E8F0', showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption('`tracemalloc` peak during the solve — not full operating-system RAM.')
    with g4:
        fig = px.scatter(
            chart_df, x='Runtime (ms)', y='Distance (km)', color='Algorithm', size='Work counter',
            color_discrete_map=color_map, title='Runtime vs distance (marker size = work counter)',
            hover_data=['Algorithm', 'Work counter'],
        )
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)', font_color='#E2E8F0')
        st.plotly_chart(fig, use_container_width=True)
        st.caption('Marker size uses each algorithm’s own work counter — sizes are not cross-comparable units.')
    gap_df = chart_df.dropna(subset=['Optimality gap (%)'])
    if not gap_df.empty:
        fig = px.bar(gap_df, x='Algorithm', y='Optimality gap (%)', color='Algorithm', color_discrete_map=color_map, title='Optimality gap (when exact optimum known)')
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)', font_color='#E2E8F0', showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption('0% matches the exact optimum on this matrix. Missing bars mean N/A, not zero.')
    else:
        st.info('Optimality gap chart unavailable because no exact brute-force enumeration ran.')

    pair_csv = pd.DataFrame(pair_table) if pair_table else pd.DataFrame()
    export = table.copy()
    st.download_button('Download comparison (CSV)', export.to_csv(index=False).encode(), 'fastroute_results.csv', 'text/csv')
    if not pair_csv.empty:
        st.download_button(
            'Download head-to-head deltas (CSV)',
            pair_csv.to_csv(index=False).encode(),
            'fastroute_pairwise.csv',
            'text/csv',
        )


def render_learn():
    st.subheader('Understanding the problem')
    st.markdown(
        """
Delivery route optimization asks: *in what order should a vehicle visit several stops so the total driving distance stays small?*

That matters because every extra kilometer costs time, fuel, and money. In FastRoute:

- The **warehouse** is the depot where the tour starts and ends.
- **Delivery stops** are places that must be visited once.
- The vehicle **returns to the warehouse** so the plan is a complete round trip.
- We use **actual road distances** from OpenStreetMap instead of straight-line ("as the crow flies") distances, because trucks must follow streets and one-way rules.

**Tiny example:** warehouse W and stops A, B, C, D. One possible tour is W→A→B→C→D→W. Another is W→B→D→A→C→W. The algorithms search among such orders using a road-distance matrix.
"""
    )
    st.subheader('How the three algorithms compare')
    st.markdown(
        f"""
**Dijkstra** answers: *what is the shortest road path between two intersections?*

- Time: `{DIJKSTRA_LESSON['time']}`
- Space: `{DIJKSTRA_LESSON['space']}`
- {DIJKSTRA_LESSON['note']}

**A* and Dijkstra** answer: *what is the shortest road path between intersections?*  
In Compare All they also draw a full tour by chaining those paths in the sampled stop order.

**Brute-Force Route Search** answers: *what delivery order is shortest?*

They are related but different jobs. Pathfinding builds road distances; order search rearranges the stops.
"""
    )
    st.dataframe(pd.DataFrame(algorithm_role_rows()), use_container_width=True, hide_index=True)
    st.markdown(comparison_guide_text())
    st.subheader('End-to-end process')
    for index, step in enumerate(pipeline_steps(), start=1):
        st.markdown(f'{index}. {step}')
    st.code(
        'OSM roads → graph → Dijkstra matrix → TSP solvers → reconstruct streets → map + measurements',
        language='text',
    )
    st.subheader('The three algorithms')
    for lesson in ALGORITHM_LESSONS:
        with st.expander(f"{lesson['name']}  ·  {'Exact' if lesson['exact'] else 'Heuristic'}", expanded=False):
            st.markdown(
                f'<span class="swatch" style="background:{lesson["color"]}"></span> '
                f'<b>Map color</b> shown above',
                unsafe_allow_html=True,
            )
            st.write(lesson['simple'])
            st.markdown('**Step by step**')
            for step in lesson['steps']:
                st.markdown(f'- {step}')
            st.markdown(f"**Time complexity:** `{lesson['time']}`")
            st.markdown(f"**Space complexity:** `{lesson['space']}`")
            st.markdown(f"**Optimal?** {lesson['optimal']}")
            st.markdown('**Advantages**')
            for item in lesson['pros']:
                st.markdown(f'- {item}')
            st.markdown('**Disadvantages**')
            for item in lesson['cons']:
                st.markdown(f'- {item}')
            st.markdown(f"**When useful:** {lesson['when']}")
    st.subheader('Project limitations')
    limits = limitations_copy()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('**Current model supports**')
        for item in limits['supports']:
            st.markdown(f'- {item}')
    with c2:
        st.markdown('**Not supported**')
        for item in limits['does_not']:
            st.markdown(f'- {item}')
    st.info('FastRoute is a simplified mathematical model of a delivery problem: shortest road distance is not the same as fastest travel time under live traffic.')


def render_dijkstra_lab(get_graph_fn, place):
    st.subheader('Watch Dijkstra Find the Shortest Road Path')
    st.caption('This uses the same student Dijkstra implementation that builds the delivery distance matrix.')
    try:
        graph = get_graph_fn(place)
    except Exception as exc:
        st.error(f'Unable to load road graph: {exc}')
        st.info('Try a cached preset such as Jersey City, or check your internet connection for a first download.')
        return
    choices = sample_intersection_choices(graph, count=40, seed=7)
    if len(choices) < 2:
        st.error('Not enough intersections available for a Dijkstra demo.')
        return
    def ensure_choice(node_id):
        existing = next((item for item in choices if item['id'] == node_id), None)
        if existing is not None:
            return existing
        data = graph.nodes[node_id]
        item = {
            'id': node_id,
            'label': f"Intersection {node_id} ({data['y']:.5f}, {data['x']:.5f})",
            'lat': float(data['y']),
            'lon': float(data['x']),
        }
        choices.append(item)
        return item

    if st.button('Generate reachable example'):
        pair = sample_reachable_pair(graph, seed=st.session_state.get('dij_pair_seed', 11))
        st.session_state.dij_pair_seed = int(st.session_state.get('dij_pair_seed', 11)) + 1
        if pair is None:
            st.error('Could not find a reachable pair in the sampled intersections.')
        else:
            source_id, target_id = pair
            source_choice = ensure_choice(source_id)
            target_choice = ensure_choice(target_id)
            st.session_state.dij_start = source_choice['label']
            st.session_state.dij_end = target_choice['label']
            try:
                st.session_state.dijkstra_trace = build_dijkstra_trace(graph, source_id, target_id)
                st.success('Loaded a reachable start/destination pair.')
            except Exception as exc:
                st.error(str(exc))

    labels = [item['label'] for item in choices]
    # Keep selectbox keys in sync if a generated pair added new labels.
    if st.session_state.get('dij_start') not in labels:
        st.session_state.dij_start = labels[0]
    if st.session_state.get('dij_end') not in labels:
        st.session_state.dij_end = labels[min(1, len(labels) - 1)]

    c1, c2 = st.columns(2)
    with c1:
        start_label = st.selectbox('Starting intersection', labels, key='dij_start')
    with c2:
        end_label = st.selectbox('Destination intersection', labels, key='dij_end')
    start = next(item for item in choices if item['label'] == start_label)
    end = next(item for item in choices if item['label'] == end_label)
    if start['id'] != end['id'] and not is_reachable(graph, start['id'], end['id']):
        st.warning(
            'This destination is currently unreachable from the start on the directed road graph '
            '(common with one-way streets). Choose another pair or click **Generate reachable example**.'
        )
    if st.button('Build Dijkstra visualization', type='primary'):
        try:
            trace = build_dijkstra_trace(graph, start['id'], end['id'])
            st.session_state.dijkstra_trace = trace
        except Exception as exc:
            st.error(str(exc))
            return
    trace = st.session_state.get('dijkstra_trace')
    if not trace:
        st.info('Pick two intersections and click **Build Dijkstra visualization**, or generate a reachable example.')
        return
    st.success(
        f"Shortest road distance: **{trace['distance_m']:.1f} m** ({trace['distance_km']} km) · "
        f"explored {trace['explored_count']} settles"
    )
    components.html(build_dijkstra_animation_html(trace), height=680, scrolling=False)
    st.caption(
        'Yellow = settled · Orange ring = current settle · Purple = frontier preview · '
        'Blue = improving relaxations · Green = final shortest path. Map fits the full path geometry.'
    )


def render_experiments(experiment, get_graph_fn, place):
    st.subheader('Export paper evidence')
    st.markdown(
        'Builds **`paper_evidence.zip`**: CSVs (compare + **improvement story** + **optimization ladder**), '
        'PNG screenshots, chart/map HTML, docs, and CLO prompts. '
        'If improvement / ladder were not run yet, export runs them first when a road graph is loaded.'
    )
    if experiment is None:
        st.info('Run **Compare All** first, then return here to export.')
    else:
        has_imp = bool(experiment.get('improvement_story'))
        has_ladder = bool(experiment.get('optimization_ladder'))
        st.caption(
            f"Pack checklist — improvement story: {'yes' if has_imp else 'will auto-run on export'} · "
            f"optimization ladder: {'yes' if has_ladder else 'will auto-run on export'}"
        )
        if st.button('Download all paper evidence', type='primary', key='portfolio_export_btn'):
            try:
                graph = None
                try:
                    graph = get_graph_fn(place)
                except Exception:
                    graph = None
                with st.spinner('Running any missing improvement/ladder, then building paper_evidence.zip...'):
                    zip_bytes, pack_dir, notes = build_portfolio_zip(
                        experiment,
                        st.session_state.get('scalability_rows'),
                        graph=graph,
                        auto_run_extras=True,
                    )
                st.session_state.experiment = experiment
                st.session_state.portfolio_zip = zip_bytes
                st.session_state.portfolio_pack_dir = str(pack_dir)
                st.session_state.portfolio_notes = notes
                st.success(f'Pack ready as **{PAPER_EVIDENCE_ZIP_NAME}** · folder `{pack_dir}`')
                for note in notes:
                    st.caption(f'• {note}')
            except Exception as exc:
                st.error(f'Export failed: {exc}')
        if st.session_state.get('portfolio_zip'):
            st.download_button(
                'Save paper_evidence_FINAL.zip',
                data=st.session_state.portfolio_zip,
                file_name='paper_evidence_FINAL.zip',
                mime='application/zip',
                key='portfolio_zip_dl',
            )
            if st.session_state.get('portfolio_pack_dir'):
                st.caption(
                    f'Folder copy: `{st.session_state.portfolio_pack_dir}` '
                    '(also `portfolio_evidence_pack/paper_evidence` and `.../latest`)'
                )

    st.subheader('How Do Algorithms Perform as Deliveries Increase?')
    st.markdown(
        'Each delivery count reuses one stop sample. Runtimes are **solver-only** '
        '(OSM download and matrix construction are excluded). '
        'Stress sizes **1000 / 10 000 / 100 000** run A*/Dijkstra only when the loaded road graph is large enough.'
    )
    try:
        scale_graph = get_graph_fn(place)
        capacity = max_delivery_capacity(scale_graph)
        count_options = available_scale_counts(scale_graph, DEFAULT_COUNTS + LARGE_PATHFINDER_COUNTS)
        blocked = unavailable_scale_counts(scale_graph, LARGE_PATHFINDER_COUNTS)
    except Exception:
        scale_graph = None
        capacity = None
        count_options = list(DEFAULT_COUNTS)
        blocked = []
    default_counts = [n for n in [4, 6, 8, 9, 12, 25, 50, 100, 1000] if n in count_options]
    if not default_counts:
        default_counts = count_options[:6]
    counts = st.multiselect('Delivery counts', count_options, default=default_counts)
    if capacity is not None:
        st.caption(f'Loaded graph supports up to **{capacity}** deliveries (largest SCC − 1).')
    if blocked:
        st.info(
            'Not available on this graph:\n'
            + '\n'.join(f"- **{row['deliveries']}** deliveries — {row['reason']}" for row in blocked)
        )
    trials = st.slider('Trials per algorithm / size', 1, 7, 3)
    if st.button('Run scalability experiment', type='primary'):
        if not counts:
            st.error('Select at least one delivery count.')
        else:
            try:
                graph = scale_graph if scale_graph is not None else get_graph_fn(place)
                with st.spinner('Running measured scalability trials...'):
                    # Prefer fewer trials on huge stress sizes so the UI stays usable.
                    big = [n for n in counts if n >= 10_000]
                    small = [n for n in counts if n < 10_000]
                    rows = []
                    if small:
                        rows.extend(run_scalability(graph, counts=sorted(small), trials=trials, seed=42))
                    if big:
                        rows.extend(
                            run_scalability(
                                graph,
                                counts=sorted(big),
                                trials=1,
                                seed=42,
                                selected=['A* Search Algorithm', "Dijkstra's Algorithm"],
                            )
                        )
                path = save_scalability_csv(rows)
                st.session_state.scalability_rows = rows
                st.session_state.scalability_path = str(path)
                st.success(f'Saved measured results to {path}')
            except Exception as exc:
                st.error(str(exc))
    rows = st.session_state.get('scalability_rows') or []
    if rows:
        frame = pd.DataFrame(rows)
        st.dataframe(frame, use_container_width=True, hide_index=True)
        ok = frame[frame['status'] == 'ok']
        if not ok.empty:
            color_map = {ALGORITHM_SHORT[k]: v for k, v in ALGORITHM_COLORS.items()}
            for ycol, title, note in [
                ('avg_runtime_ms', 'Delivery count vs average runtime', 'Exact methods grow quickly; heuristics stay flatter.'),
                ('avg_distance_km', 'Delivery count vs route distance', 'Distance is road meters converted to km.'),
                ('avg_peak_memory_kb', 'Delivery count vs peak Python-traced memory', 'Memory is Python tracemalloc during the solve.'),
                ('avg_operations', 'Delivery count vs algorithm-specific work counter', 'Units differ by algorithm — do not cross-rank these curves.'),
            ]:
                fig = px.line(ok, x='deliveries', y=ycol, color='short_name', markers=True, title=title,
                              color_discrete_map=color_map)
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)', font_color='#E2E8F0')
                st.plotly_chart(fig, use_container_width=True)
                st.caption(note)
            if 'optimality_gap_percent' in ok.columns:
                gap_ok = ok.dropna(subset=['optimality_gap_percent'])
                if not gap_ok.empty:
                    fig = px.line(
                        gap_ok, x='deliveries', y='optimality_gap_percent', color='short_name',
                        markers=True, title='Optimality gap vs deliveries (exact reference required)',
                        color_discrete_map=color_map,
                    )
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)', font_color='#E2E8F0')
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption('Gaps only appear when an exact solver finished on that same matrix.')
        skipped = frame[frame['status'] == 'skipped']
        if not skipped.empty:
            st.info(
                'Not run — exceeds supported limit:\n'
                + '\n'.join(
                    f"- {row.short_name} at {row.deliveries} deliveries: {row.skip_reason}"
                    for row in skipped.itertuples()
                )
            )

    st.subheader('Generate Experiment Report')
    if experiment is None:
        st.info('Run Compare All before generating a full experiment report.')
        return
    if st.button('Generate Experiment Report', type='primary'):
        report = build_experiment_report(experiment, st.session_state.get('scalability_rows'))
        st.session_state.experiment_report = report
    report = st.session_state.get('experiment_report')
    if report:
        st.json({k: report[k] for k in ('project', 'generated_at_utc', 'place', 'stop_source', 'deliveries')})
        st.download_button('Download report JSON', report_to_json(report).encode(), 'fastroute_experiment_report.json', 'application/json')
        csv_buffer = io.StringIO()
        rows = report_to_csv_rows(report)
        if rows:
            writer = csv.DictWriter(csv_buffer, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
            st.download_button('Download report CSV', csv_buffer.getvalue().encode(), 'fastroute_experiment_report.csv', 'text/csv')
        st.download_button('Download printable HTML report', report_to_html(report).encode(), 'fastroute_experiment_report.html', 'text/html')


def render_guided_demo():
    if 'demo_step' not in st.session_state:
        st.session_state.demo_step = 0
    step = clamp_step(st.session_state.demo_step)
    item = DEMO_STEPS[step]
    st.subheader(f"Guided Demo ({step + 1}/{len(DEMO_STEPS)}): {item['title']}")
    st.write(item['body'])
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button('Back', disabled=step == 0):
            st.session_state.demo_step = clamp_step(step - 1)
            st.rerun()
    with b2:
        if st.button('Next', type='primary', disabled=step >= len(DEMO_STEPS) - 1):
            st.session_state.demo_step = clamp_step(step + 1)
            st.rerun()
    with b3:
        if st.button('Exit demo'):
            st.session_state.demo_step = 0
            st.session_state.section = 'Build Your Delivery Route'
            st.rerun()
