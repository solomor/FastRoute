"""Run with: streamlit run app.py"""
import streamlit as st
from src.algorithms import ALGORITHM_COLORS, ALGORITHM_SHORT, ALGORITHMS
from src.dashboard import (
    render_build_and_watch,
    render_compare_results,
    render_dijkstra_lab,
    render_experiments,
    render_guided_demo,
    render_learn,
)
from src.datasets import coordinate_pair_label, dataset_coordinates, dataset_provenance, list_datasets
from src.constants import (
    BRUTE_FORCE_EXACT_MAX_STOPS,
    BRUTE_FORCE_SAMPLE_BUDGET,
    DEFAULT_MAX_SNAP_M,
    MAX_DELIVERY_DESTINATIONS,
    PLACE,
    default_visible_algorithms,
)
from src.road_data import (
    download_graph,
    has_cached_graph,
    is_merged_place,
    list_cached_places,
    merged_components_ready,
    osm_area_label,
    osm_area_options,
)
from src.route_prep import available_stop_sources, prepare_dataset_experiment, prepare_osm_experiment
from src.ui_theme import inject_theme, render_hero

st.set_page_config(page_title='FastRoute | CPS 3440', page_icon='🚚', layout='wide', initial_sidebar_state='expanded')
inject_theme()
render_hero(ALGORITHM_COLORS, ALGORITHM_SHORT, ALGORITHMS)

# Clear classroom workflow (existing pages preserved under these labels).
SECTIONS = [
    '1 · Configure & Run Route',
    '2 · Visualize Algorithms',
    '3 · Compare Results',
    '4 · Learn Theory',
    '5 · Scalability & Export',
    'Guided Demo',
    'Demo Mode',
]

# Back-compat aliases if an old session still holds a previous label.
_SECTION_ALIASES = {
    'Build Your Delivery Route': '1 · Configure & Run Route',
    'Watch the Algorithms': '2 · Visualize Algorithms',
    'Compare Results': '3 · Compare Results',
    'Learn How It Works': '4 · Learn Theory',
    'Experiments and Reports': '5 · Scalability & Export',
}

@st.cache_resource(show_spinner=False)
def get_graph(place):
    return download_graph(place)


def load_graph_with_status(place):
    if has_cached_graph(place):
        with st.spinner(f'Loading cached road network for {place}...'):
            return get_graph(place)
    with st.spinner(
        f'Downloading OpenStreetMap roads for {place}. '
        'Large cities can take several minutes; prefer Jersey City or Brooklyn.'
    ):
        return get_graph(place)


if 'experiment' not in st.session_state:
    st.session_state.experiment = None
if 'visible_algorithms' not in st.session_state:
    st.session_state.visible_algorithms = list(ALGORITHMS)
if 'show_markers' not in st.session_state:
    st.session_state.show_markers = True
if 'autoplay_map' not in st.session_state:
    st.session_state.autoplay_map = False
if 'section' not in st.session_state:
    st.session_state.section = SECTIONS[0]

with st.sidebar:
    st.markdown('### Workspace')
    if st.session_state.section in _SECTION_ALIASES:
        st.session_state.section = _SECTION_ALIASES[st.session_state.section]
    section = st.radio(
        'Workflow',
        SECTIONS,
        index=SECTIONS.index(st.session_state.section) if st.session_state.section in SECTIONS else 0,
        help='Follow steps 1→5 for a full experiment: configure, visualize, compare, learn, export.',
    )
    st.session_state.section = section
    st.caption('Dataset Explorer is a separate page in the left app menu.')
    st.caption('Dijkstra · A* · Brute Force · Bad→Semi→Best ladder in Compare Results.')

    st.markdown('### Experiment setup')
    area_options = osm_area_options()
    area_labels = [osm_area_label(place) for place in area_options] + ['Custom area...']
    label_to_place = {osm_area_label(place): place for place in area_options}
    default_label = osm_area_label(PLACE) if PLACE in area_options else area_labels[0]
    default_index = area_labels.index(default_label) if default_label in area_labels else 0
    place_choice = st.selectbox(
        'OpenStreetMap area',
        area_labels,
        index=default_index,
        help=(
            'Cached areas are validated so the name matches the road geography. '
            'Items marked "needs download" are not faked from a neighboring city cache.'
        ),
    )
    if place_choice == 'Custom area...':
        place = st.text_input('Custom area name', PLACE)
    else:
        place = label_to_place[place_choice]
    cached = list_cached_places()
    if has_cached_graph(place):
        st.caption(f'Cached locally ({len(cached)} areas ready) — loads without Overpass.')
    else:
        st.caption('Not cached yet. First run downloads live OSM and may take several minutes.')

    sources = available_stop_sources()
    stop_source = st.selectbox(
        'Stop source',
        sources,
        help=(
            'Primary portfolio setup: OpenStreetMap roads + Grubhub restaurant listings '
            '(NYC/NJ overlap). Food delivery records are India-centric — secondary only.'
        ),
    )
    delivery_count = st.slider(
        'Delivery destinations',
        3,
        MAX_DELIVERY_DESTINATIONS,
        6,
        help=(
            f'Up to {MAX_DELIVERY_DESTINATIONS} destinations. '
            'For large counts use New York or NYC / NJ metro (merged caches). '
            'A* and Dijkstra stay available; brute force stays capped.'
        ),
    )
    seed = st.number_input('Random sample seed', 0, 100000, 42)
    warehouse_index = 0
    coordinate_pair = None
    max_snap_m = DEFAULT_MAX_SNAP_M
    if is_merged_place(place):
        ready, missing = merged_components_ready(place)
        st.caption(
            f'Merged road network from {len(ready)} cached area(s)'
            + (f' · still missing: {", ".join(missing)}' if missing else '')
            + '.'
        )
    if delivery_count >= 100:
        st.warning(
            f'{delivery_count} destinations: pathfinding will run about {delivery_count} road searches '
            'per algorithm and can take several minutes. Prefer A*/Dijkstra only (brute force auto-skips). '
            'Use **NYC / NJ metro (merged caches)** or **New York** with Grubhub for large dataset runs.'
        )
    if stop_source != 'OpenStreetMap sampled intersections':
        pairs = dataset_coordinates(stop_source)
        pair_labels = {
            f'{coordinate_pair_label(lat, lon)} — {lat}, {lon}': (lat, lon)
            for lat, lon in pairs
        }
        chosen_pair_label = st.selectbox(
            'Coordinate pair for routing',
            list(pair_labels.keys()),
            help='Restaurant vs delivery/search columns can point to different places. Your choice is used for the experiment.',
        )
        coordinate_pair = pair_labels[chosen_pair_label]
        st.session_state.selected_coordinate_pair = coordinate_pair
        label = coordinate_pair_label(*coordinate_pair)
        if 'Restaurant' in label or 'Search' in label:
            st.warning(
                f'Selected columns look like **{label}**. '
                'They may not represent customer delivery destinations.'
            )
        warehouse_index = st.number_input('Warehouse row in sample (0-based)', 0, max(delivery_count, 0), 0)
        max_snap_m = st.number_input('Max snap distance to road (meters)', 50.0, 5000.0, float(DEFAULT_MAX_SNAP_M), 50.0)
        provenance = dataset_provenance(stop_source)
        with st.expander('Dataset provenance'):
            st.write(provenance)
        if 'Grubhub' in stop_source:
            st.caption(
                'Grubhub has thousands of NY-metro points. '
                'For 100–1000 destinations choose **NYC / NJ metro (merged caches)** or **New York**.'
            )
        elif 'Food delivery' in stop_source:
            st.caption('Food-delivery coordinates are mostly India. Use a matching Indian city area.')

    st.subheader('Algorithms')
    selected = []
    for name in ALGORITHMS:
        if st.checkbox(ALGORITHM_SHORT[name], value=True, key=f'sel_{name}'):
            selected.append(name)
    if delivery_count > BRUTE_FORCE_EXACT_MAX_STOPS and 'Brute-Force Route Search' in selected:
        st.warning(
            f'Brute Force above {BRUTE_FORCE_EXACT_MAX_STOPS} deliveries cannot enumerate every order '
            f'({delivery_count}! is enormous). It will sample up to {BRUTE_FORCE_SAMPLE_BUDGET:,} random '
            'delivery orders and return the best found — not a proven optimum. '
            'Building the distance matrix for large n can also take several minutes.'
        )
    st.caption(
        f'A* · Dijkstra · Brute-Force Route Search. '
        f'Exact brute force ≤ {BRUTE_FORCE_EXACT_MAX_STOPS} deliveries; '
        f'sampled brute force runs up to {MAX_DELIVERY_DESTINATIONS}.'
    )

    compare_all = st.button('Compare All', type='primary', use_container_width=True)
    optimize = st.button('Optimize selected', use_container_width=True)
    if st.button('Reset experiment', use_container_width=True):
        st.session_state.experiment = None
        st.session_state.autoplay_map = False
        st.rerun()

run_requested = compare_all or optimize
if compare_all:
    selected_algorithms = list(ALGORITHMS)
elif optimize:
    selected_algorithms = selected
else:
    selected_algorithms = selected

if run_requested:
    if optimize and not selected:
        st.error('Select at least one algorithm, or click **Compare All**.')
    elif not selected_algorithms:
        st.error('Select at least one algorithm before running.')
    else:
        try:
            graph = load_graph_with_status(place)
            spinner_msg = (
                f'Running selected solvers on {delivery_count} deliveries '
                '(large runs can take several minutes)...'
                if delivery_count >= 50
                else 'Preparing routes and running selected solvers...'
            )
            with st.spinner(spinner_msg):
                if stop_source == 'OpenStreetMap sampled intersections':
                    experiment = prepare_osm_experiment(graph, delivery_count, int(seed), selected_algorithms)
                else:
                    experiment = prepare_dataset_experiment(
                        graph,
                        stop_source,
                        delivery_count,
                        int(seed),
                        selected_algorithms,
                        int(warehouse_index),
                        coordinate_pair=coordinate_pair,
                        max_snap_m=float(max_snap_m),
                    )
            experiment['place'] = place
            experiment['delivery_count'] = experiment.get('actual_stop_count', delivery_count)
            experiment['requested_delivery_count'] = delivery_count
            experiment['seed'] = int(seed)
            st.session_state.experiment = experiment
            st.session_state.visible_algorithms = default_visible_algorithms(
                experiment['results'],
                experiment.get('delivery_count'),
            )
            st.session_state.autoplay_map = True
            st.session_state.section = '1 · Configure & Run Route'
        except Exception as exc:
            message = str(exc)
            st.error(f'Unable to run this experiment: {message}')
            lower = message.lower()
            if 'download' in lower or 'timeout' in lower or 'overpass' in lower:
                st.info('Network/OSM issue. Prefer a cached preset such as **Jersey City, New Jersey, USA**.')
            elif 'coordinate' in lower or 'points' in lower or 'snap' in lower:
                st.info('Check the selected coordinate pair, OSM area overlap, and snap-distance limit.')
            elif 'algorithm' in lower:
                st.info('Select one or more algorithms in the sidebar.')
            else:
                st.info('Verify the area, stop source, and delivery count, then try again.')

experiment = st.session_state.experiment
section = st.session_state.section

if section == '1 · Configure & Run Route':
    st.header('1 · Configure & Run Route')
    st.caption('Project overview live here: pick OSM area + stops, select Dijkstra / A* / Brute Force, then Compare All.')
    if experiment is None:
        st.markdown(
            """
            1. Choose an OpenStreetMap area and stop source in the sidebar (**Grubhub** for NYC/NJ).
            2. Select algorithms and delivery count.
            3. Click **Compare All**.
            4. Continue to **Visualize**, then **Compare Results**, then **Scalability & Export**.
            """
        )
    render_build_and_watch(experiment)
elif section == '2 · Visualize Algorithms':
    st.header('2 · Visualize Algorithms')
    tab_map, tab_dij = st.tabs(['Live route drawing', 'Dijkstra shortest-path lab'])
    with tab_map:
        render_build_and_watch(experiment)
    with tab_dij:
        render_dijkstra_lab(load_graph_with_status, place)
elif section == '3 · Compare Results':
    st.header('3 · Compare Results')
    st.caption('Side-by-side metrics, Bad→Semi→Best ladder, and improvement story.')
    compare_graph = None
    try:
        compare_graph = load_graph_with_status(place)
    except Exception:
        compare_graph = None
    render_compare_results(experiment, compare_graph)
elif section == '4 · Learn Theory':
    st.header('4 · Learn Theory')
    render_learn()
elif section == '5 · Scalability & Export':
    st.header('5 · Scalability & Export')
    st.caption('Delivery-count scalability, paper evidence zip (CSV + screenshots), and experiment reports.')
    render_experiments(experiment, load_graph_with_status, place)
elif section == 'Guided Demo':
    st.header('Guided Demo')
    render_guided_demo()
elif section == 'Demo Mode':
    st.header('Presentation Demo Mode')
    st.markdown(
        """
A reproducible classroom scenario:

1. Area: cached **Jersey City, New Jersey, USA** when available  
2. Stop source: OpenStreetMap sampled intersections  
3. Deliveries: **6** · seed **42**  
4. Algorithms: Dijkstra · A* · Brute-Force Route Search (exact BF within caps)
"""
    )
    if st.button('Load Demo Experiment', type='primary'):
        demo_place = 'Jersey City, New Jersey, USA'
        try:
            graph = load_graph_with_status(demo_place)
            with st.spinner('Building reproducible demo routes...'):
                experiment = prepare_osm_experiment(graph, 6, 42, list(ALGORITHMS))
            experiment['place'] = demo_place
            experiment['delivery_count'] = 6
            experiment['seed'] = 42
            experiment['source'] = experiment.get('source', '') + ' · Demo Mode'
            st.session_state.experiment = experiment
            st.session_state.visible_algorithms = default_visible_algorithms(
                experiment['results'],
                experiment.get('delivery_count'),
            )
            st.session_state.autoplay_map = True
            st.session_state.section = '1 · Configure & Run Route'
            st.success('Demo experiment loaded. Opening the map view.')
            st.rerun()
        except Exception as exc:
            st.error(f'Demo Mode could not load: {exc}')
            st.info('Ensure Jersey City is cached or online OSM download works, then retry.')
    if experiment is not None:
        st.caption(f"Current experiment ready: {experiment.get('place')} · {experiment.get('delivery_count')} deliveries")
        render_build_and_watch(experiment)
