import streamlit as st
import pandas as pd
import plotly.express as px
from src.datasets import add_dataset, clean_coordinates, dataset_coordinates, list_datasets, load_dataset, remove_dataset
from src.ui_theme import inject_theme

st.set_page_config(page_title='FastRoute | Dataset Explorer', layout='wide', page_icon='📊')
inject_theme()
st.markdown(
    """
    <div class="fr-hero">
      <div class="fr-hero-top">
        <div class="fr-brand-row">
          <div class="fr-mark">DX</div>
          <div>
            <div class="fr-hero-kicker">FastRoute · Data plane</div>
            <div class="fr-hero-title">Dataset Explorer</div>
          </div>
        </div>
        <div class="fr-status-cluster">
          <span class="fr-chip fr-chip-live"><span class="fr-dot"></span>Catalog live</span>
          <span class="fr-chip">OSM snap</span>
        </div>
      </div>
      <p class="fr-hero-sub">
        Inspect built-in and uploaded stop tables. Coordinates become routing inputs after cleaning and snapping to OpenStreetMap roads.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.warning(
    'These sources describe different regions and observations. They are not matched delivery trips. '
    'After you add a file here, it also appears under Stop source on the main FastRoute page. '
    'CSV points are snapped to nearby OpenStreetMap roads inside the area you download.'
)
notice = st.session_state.pop('dataset_notice', None)
if notice:
    st.success(notice)

with st.expander('Add a dataset from a file'):
    st.caption('Upload a CSV or JSON table, or copy the file into the data/user folder and refresh this page. The two built-in datasets stay available.')
    upload = st.file_uploader('Dataset file', type=['csv', 'json'])
    default_name = upload.name.rsplit('.', 1)[0].replace('_', ' ') if upload else ''
    label = st.text_input('Dataset name', value=default_name, key=f'dataset-name-{upload.name if upload else "none"}')
    chosen_pair = None
    if upload is not None:
        try:
            if upload.name.lower().endswith('.json'):
                preview = pd.read_json(upload)
            else:
                preview = pd.read_csv(upload, low_memory=False)
            upload.seek(0)
        except Exception as exc:
            preview = None
            st.error(f'Could not read that file: {exc}')
        if preview is not None:
            st.caption(f'{len(preview):,} rows · {len(preview.columns)} columns')
            st.dataframe(preview.head(5), use_container_width=True)
            columns = ['(auto-detect)'] + list(map(str, preview.columns))
            lat_col = st.selectbox('Latitude column', columns)
            lon_col = st.selectbox('Longitude column', columns)
            if lat_col != '(auto-detect)' and lon_col != '(auto-detect)':
                chosen_pair = [(lat_col, lon_col)]
    if st.button('Add dataset', type='primary', disabled=upload is None):
        try:
            added = add_dataset(label, upload.name, upload.getvalue(), chosen_pair)
            st.session_state['dataset_notice'] = f'Added {added["name"]} ({added["rows"]:,} rows).'
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

datasets = list_datasets()
if not datasets:
    st.info('No datasets are available yet.')
    st.stop()

names = [item['name'] for item in datasets]
name = st.selectbox('Select dataset', names)
selected = next(item for item in datasets if item['name'] == name)
if selected['builtin']:
    st.caption('Built-in dataset')
else:
    st.caption(f'Added from file: {selected["path"].name}')
    if st.button('Remove this dataset'):
        try:
            remove_dataset(name)
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

try:
    df = load_dataset(name)
except Exception as exc:
    st.error(str(exc))
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric('Rows', f'{len(df):,}')
c2.metric('Columns', len(df.columns))
c3.metric('Missing cells', f'{int(df.isna().sum().sum()):,}')
st.subheader('Preview')
st.dataframe(df.head(300), use_container_width=True)
st.subheader('Columns and missing values')
info = pd.DataFrame({'column': df.columns, 'dtype': df.dtypes.astype(str).values, 'missing': df.isna().sum().values})
st.dataframe(info, use_container_width=True, hide_index=True)

coordinates = dataset_coordinates(name)
if not coordinates:
    st.info('No latitude/longitude columns were found. Map view stays hidden until the file has columns such as latitude and longitude.')
else:
    coord_labels = [f'{lat} / {lon}' for lat, lon in coordinates]
    chosen = st.selectbox('Coordinates to visualize', coord_labels)
    lat, lon = coordinates[coord_labels.index(chosen)]
    valid = clean_coordinates(df, lat, lon)
    st.caption(f'{len(valid):,} rows have valid nonzero coordinates; {len(df) - len(valid):,} excluded from map.')
    if not valid.empty:
        limit = st.slider('Maximum map points', 100, 3000, 500, 100)
        subset = valid.sample(min(limit, len(valid)), random_state=42)
        st.map(subset.rename(columns={lat: 'lat', lon: 'lon'})[['lat', 'lon']])

if 'Time_taken (min)' in df:
    st.subheader('Delivery-time distribution')
    vals = pd.to_numeric(df['Time_taken (min)'], errors='coerce').dropna()
    if not vals.empty:
        st.plotly_chart(px.histogram(x=vals, nbins=35, labels={'x': 'Time taken (minutes)'}, title='Recorded delivery times'), use_container_width=True)
if 'searched_city' in df:
    st.subheader('Restaurant locations by city')
    st.bar_chart(df['searched_city'].fillna('Unknown').value_counts().head(12))
st.download_button('Export preview (CSV)', df.head(300).to_csv(index=False).encode(), 'fastroute_dataset_preview.csv', 'text/csv')
