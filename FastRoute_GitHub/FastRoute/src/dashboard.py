"""Streamlit section renderers for the FastRoute dashboard."""
import csv
import io
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from .algorithms import ALGORITHM_COLORS, ALGORITHM_SHORT, ALGORITHMS, BRUTE_FORCE_MAX_STOPS, HELD_KARP_MAX_STOPS
from .dijkstra_viz import (
    build_dijkstra_animation_html,
    build_dijkstra_trace,
    is_reachable,
    sample_intersection_choices,
    sample_reachable_pair,
)
from .guided_demo import DEMO_STEPS, clamp_step
from .learn_content import ALGORITHM_LESSONS, DIJKSTRA_LESSON, limitations_copy, pipeline_steps
from .map_viz import build_live_animation_html
from .report import build_experiment_report, report_to_csv_rows, report_to_html, report_to_json
from .results_explain import optimality_gap_help, route_quality, understanding_results_text
from .road_data import stop_labels
from .scalability import DEFAULT_COUNTS, run_scalability, save_scalability_csv


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
        default_visible = [name for name in st.session_state.visible_algorithms if name in set(options)]
        if not default_visible:
            default_visible = options
        visible = st.multiselect(
            'Show / hide algorithm routes',
            options,
            default=default_visible,
            format_func=lambda name: ALGORITHM_SHORT.get(name, name),
            help='Uncheck all to hide every route. The map will not secretly re-enable them.',
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


def render_compare_results(experiment):
    if experiment is None:
        st.info('Run **Compare All** first to populate this section.')
        return
    results = experiment['results']
    if not results:
        st.warning('No results available.')
        return

    st.subheader('Route quality snapshot')
    quality = route_quality(results)
    q1, q2, q3, q4 = st.columns(4)
    q1.metric('Shortest route', f"{quality['shortest']['Distance (km)']} km", ALGORITHM_SHORT[quality['shortest']['Algorithm']])
    q2.metric('Fastest computation', f"{quality['fastest']['Runtime (ms)']} ms", ALGORITHM_SHORT[quality['fastest']['Algorithm']])
    q3.metric('Lowest memory', f"{quality['lowest_memory']['Peak memory (KB)']} KB", ALGORITHM_SHORT[quality['lowest_memory']['Algorithm']])
    if quality['two_opt_saved_km'] is not None:
        q4.metric('Distance saved by 2-Opt', f"{quality['two_opt_saved_km']} km", f"{quality['two_opt_improvement_pct']}%")
    else:
        q4.metric('2-Opt savings', 'Unavailable', 'Need NN + 2-Opt result')

    if quality['nn_initial_km'] is not None:
        st.caption(
            f"Nearest Neighbor seed: **{quality['nn_initial_km']} km** · "
            f"NN + 2-Opt final: **{quality['nn_two_opt_km'] if quality['nn_two_opt_km'] is not None else 'n/a'} km**. "
            'Runtime and distance are different ideas: a fast solver is not automatically shortest.'
        )

    st.subheader('Algorithm comparison')
    table_rows = []
    for row in results:
        item = {
            'Algorithm': row['Algorithm'],
            'Distance (km)': row.get('Distance (km)'),
            'Runtime (ms)': row.get('Runtime (ms)'),
            'Peak memory (KB)': row.get('Peak memory (KB)'),
            'Algorithm-Specific Work Counter': row.get('Algorithm-Specific Work Counter', row.get('Operations / states')),
            'Work unit': row.get('Work unit'),
            'Optimality gap (%)': row.get('Optimality gap (%)'),
        }
        if row.get('Initial distance (km)') is not None:
            item['Initial NN distance (km)'] = row['Initial distance (km)']
            item['2-Opt swaps'] = row.get('2-Opt swaps')
        table_rows.append(item)
    table = pd.DataFrame(table_rows)
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.caption(
        'Work counters are algorithm-specific (permutations vs DP states vs candidate checks) and '
        'must not be ranked against each other. Compare runtime/memory for resources and distance/gap for quality.'
    )
    st.markdown(optimality_gap_help())

    st.subheader('What Do These Results Mean?')
    for line in understanding_results_text(experiment):
        st.markdown(f'- {line}')

    labels = stop_labels(len(experiment['stops']))
    for row in results:
        pretty = [labels[stop_i] if stop_i < len(labels) else f'#{stop_i}' for stop_i in row['Route']]
        extra = ''
        if row.get('2-Opt swaps') is not None:
            extra = f" · NN {row['Initial distance (km)']} km → {row['Distance (km)']} km after {row['2-Opt swaps']} swaps"
        with st.expander(f"{ALGORITHM_SHORT[row['Algorithm']]} delivery order{extra}"):
            st.write(' → '.join(pretty))

    st.subheader('Performance charts')
    chart_df = pd.DataFrame([
        {
            'Algorithm': ALGORITHM_SHORT[row['Algorithm']],
            'Distance (km)': row['Distance (km)'],
            'Runtime (ms)': row['Runtime (ms)'],
            'Peak memory (KB)': row['Peak memory (KB)'],
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
            chart_df, x='Runtime (ms)', y='Distance (km)', color='Algorithm',
            color_discrete_map=color_map, title='Runtime vs route quality',
            hover_data=['Algorithm'],
        )
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)', font_color='#E2E8F0')
        st.plotly_chart(fig, use_container_width=True)
        st.caption('Exact vs heuristic trade-off: look for short routes that are still affordable to compute.')
    gap_df = chart_df.dropna(subset=['Optimality gap (%)'])
    if not gap_df.empty:
        fig = px.bar(gap_df, x='Algorithm', y='Optimality gap (%)', color='Algorithm', color_discrete_map=color_map, title='Optimality gap (when exact optimum known)')
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,23,42,0.6)', font_color='#E2E8F0', showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption('0% matches the exact optimum on this matrix. Missing bars mean N/A, not zero.')
    else:
        st.info('Optimality gap chart unavailable because no exact algorithm ran.')

    st.download_button('Download comparison (CSV)', table.to_csv(index=False).encode(), 'fastroute_results.csv', 'text/csv')


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
    st.subheader('Dijkstra vs the four delivery algorithms')
    st.markdown(
        f"""
**Dijkstra** answers: *what is the shortest road path between two intersections?*

- Time: `{DIJKSTRA_LESSON['time']}`
- Space: `{DIJKSTRA_LESSON['space']}`
- {DIJKSTRA_LESSON['note']}

**Brute Force / Held-Karp / Nearest Neighbor / 2-Opt** answer: *what order should we visit the deliveries?*

They are different jobs. Dijkstra prepares the pairwise road costs; the TSP solvers choose the tour order.
"""
    )
    st.subheader('End-to-end process')
    for index, step in enumerate(pipeline_steps(), start=1):
        st.markdown(f'{index}. {step}')
    st.code(
        'OSM roads → graph → Dijkstra matrix → TSP solvers → reconstruct streets → map + measurements',
        language='text',
    )
    st.subheader('The four algorithms')
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
    st.subheader('How Do Algorithms Perform as Deliveries Increase?')
    st.markdown(
        'Each delivery count reuses one stop sample and one Dijkstra matrix for every algorithm. '
        'Reported runtimes are **solver-only** (OSM download and matrix construction are excluded).'
    )
    counts = st.multiselect('Delivery counts', DEFAULT_COUNTS, default=[4, 6, 8, 10, 12])
    trials = st.slider('Trials per algorithm / size', 1, 7, 3)
    if st.button('Run scalability experiment', type='primary'):
        if not counts:
            st.error('Select at least one delivery count.')
        else:
            try:
                graph = get_graph_fn(place)
                with st.spinner('Running measured scalability trials...'):
                    rows = run_scalability(graph, counts=sorted(counts), trials=trials, seed=42)
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
                ('avg_peak_memory_kb', 'Delivery count vs peak Python-traced memory', 'Held-Karp memory rises with DP states.'),
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
