"""Run with: streamlit run app.py"""
import streamlit as st
from src.algorithms import ALGORITHM_COLORS, ALGORITHM_SHORT, ALGORITHMS, BRUTE_FORCE_MAX_STOPS, HELD_KARP_MAX_STOPS
from src.dashboard import (
    render_build_and_watch,
    render_compare_results,
    render_dijkstra_lab,
    render_experiments,
    render_guided_demo,
    render_learn,
)
from src.datasets import coordinate_pair_label, dataset_coordinates, dataset_provenance, list_datasets
from src.road_data import (
    DEFAULT_MAX_SNAP_M,
    PLACE,
    download_graph,
    has_cached_graph,
    list_cached_places,
    osm_area_label,
    osm_area_options,
)
from src.route_prep import available_stop_sources, prepare_dataset_experiment, prepare_osm_experiment

st.set_page_config(page_title='FastRoute | CPS 3440', page_icon='🚚', layout='wide', initial_sidebar_state='expanded')

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500&display=swap');
    html, body, [class*="css"]  { font-family: 'IBM Plex Sans', Segoe UI, sans-serif; }
    .stApp { background: radial-gradient(1200px 600px at 10% -10%, #172554 0%, #0B1220 45%, #020617 100%); }
    [data-testid="stSidebar"] { background: #0F172A; border-right: 1px solid #1E293B; }
    .hero-title { font-size: 2.1rem; font-weight: 700; color: #F8FAFC; margin-bottom: .15rem; }
    .hero-sub { color: #94A3B8; margin-bottom: 1rem; }
    .metric-card {
        background: linear-gradient(180deg, #111827 0%, #0F172A 100%);
        border: 1px solid #1E293B; border-radius: 14px; padding: 14px 16px; margin-bottom: 10px;
    }
    .metric-label { color: #94A3B8; font-size: .78rem; letter-spacing: .04em; text-transform: uppercase; }
    .metric-value { color: #F8FAFC; font-size: 1.35rem; font-weight: 600; font-family: 'IBM Plex Mono', monospace; }
    .algo-pill {
        display:inline-flex; align-items:center; gap:8px; padding:6px 10px; border-radius:999px;
        background:#111827; border:1px solid #334155; color:#E2E8F0; font-size:.85rem; margin:0 6px 6px 0;
    }
    .swatch { width:14px; height:14px; border-radius:999px; display:inline-block; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="hero-title">FastRoute</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">Interactive delivery-route algorithm visualization · CPS 3440 · OpenStreetMap roads · student Dijkstra + TSP solvers</div>',
    unsafe_allow_html=True,
)
st.markdown(
    ' · '.join(
        f'<span class="algo-pill"><span class="swatch" style="background:{ALGORITHM_COLORS[name]}"></span>{ALGORITHM_SHORT[name]}</span>'
        for name in ALGORITHMS
    ),
    unsafe_allow_html=True,
)

SECTIONS = [
    'Build Your Delivery Route',
    'Watch the Algorithms',
    'Compare Results',
    'Learn How It Works',
    'Experiments and Reports',
    'Guided Demo',
    'Demo Mode',
]

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
    st.header('Navigate')
    section = st.radio('Section', SECTIONS, index=SECTIONS.index(st.session_state.section) if st.session_state.section in SECTIONS else 0)
    st.session_state.section = section
    st.caption('Dataset Explorer is available as a separate page in the left app menu.')

    st.header('Route controls')
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
    stop_source = st.selectbox('Stop source', sources)
    delivery_count = st.slider('Delivery destinations', 3, 25, 6)
    seed = st.number_input('Random sample seed', 0, 100000, 42)
    warehouse_index = 0
    coordinate_pair = None
    max_snap_m = DEFAULT_MAX_SNAP_M
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
            st.caption('Grubhub points are mostly NYC metros. Prefer Brooklyn or New York OSM areas.')
        elif 'Food delivery' in stop_source:
            st.caption('Food-delivery coordinates are mostly India. Use a matching Indian city area.')

    st.subheader('Algorithms')
    selected = []
    for name in ALGORITHMS:
        default = True
        if name.startswith('Brute Force') and delivery_count > BRUTE_FORCE_MAX_STOPS:
            default = False
        if name.startswith('Held-Karp') and delivery_count > HELD_KARP_MAX_STOPS:
            default = False
        if st.checkbox(ALGORITHM_SHORT[name], value=default, key=f'sel_{name}'):
            selected.append(name)
    st.caption(
        f'Brute Force ≤ {BRUTE_FORCE_MAX_STOPS} deliveries · Held-Karp ≤ {HELD_KARP_MAX_STOPS}. '
        'Exact search grows exponentially — larger inputs skip exact solvers on purpose.'
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
            with st.spinner('Building road-distance matrix with Dijkstra, then running TSP solvers...'):
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
            experiment['delivery_count'] = delivery_count
            experiment['seed'] = int(seed)
            st.session_state.experiment = experiment
            st.session_state.visible_algorithms = [row['Algorithm'] for row in experiment['results']]
            st.session_state.autoplay_map = True
            st.session_state.section = 'Build Your Delivery Route'
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

if section == 'Build Your Delivery Route':
    st.header('Build Your Delivery Route')
    if experiment is None:
        st.markdown(
            """
            1. Choose an OpenStreetMap area and stop source in the sidebar.
            2. Select algorithms and delivery count.
            3. Click **Compare All**.
            4. Watch routes draw live on the map, then open **Compare Results**.
            """
        )
    render_build_and_watch(experiment)
elif section == 'Watch the Algorithms':
    st.header('Watch the Algorithms')
    tab_map, tab_dij = st.tabs(['Live route drawing', 'Dijkstra shortest-path lab'])
    with tab_map:
        render_build_and_watch(experiment)
    with tab_dij:
        render_dijkstra_lab(load_graph_with_status, place)
elif section == 'Compare Results':
    st.header('Compare Results')
    render_compare_results(experiment)
elif section == 'Learn How It Works':
    st.header('Learn How It Works')
    render_learn()
elif section == 'Experiments and Reports':
    st.header('Experiments and Reports')
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
4. Algorithms: all four (exact solvers are within caps)
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
            st.session_state.visible_algorithms = [row['Algorithm'] for row in experiment['results']]
            st.session_state.autoplay_map = True
            st.session_state.section = 'Build Your Delivery Route'
            st.success('Demo experiment loaded. Opening the map view.')
            st.rerun()
        except Exception as exc:
            st.error(f'Demo Mode could not load: {exc}')
            st.info('Ensure Jersey City is cached or online OSM download works, then retry.')
    if experiment is not None:
        st.caption(f"Current experiment ready: {experiment.get('place')} · {experiment.get('delivery_count')} deliveries")
        render_build_and_watch(experiment)
