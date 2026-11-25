"""Load built-in delivery datasets and datasets added from the user's files."""
from pathlib import Path
import hashlib
import json
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
USER_DATA_DIR = ROOT / 'data' / 'user'
CATALOG_NAME = 'catalog.json'
TABLE_SUFFIXES = {'.csv', '.json'}

# Primary stop dataset for NYC/NJ demos first; India food-delivery is secondary only.
SOURCES = {
    'Grubhub restaurant listings': ROOT / 'data' / 'grubhub.csv',
    'Food delivery records': ROOT / 'data' / 'food_delivery_dataset.csv',
}
COORDINATES = {
    'Grubhub restaurant listings': [('latitude', 'longitude'), ('searched_lat', 'searched_lng')],
    'Food delivery records': [
        ('Restaurant_latitude', 'Restaurant_longitude'),
        ('Delivery_location_latitude', 'Delivery_location_longitude'),
    ],
}

# Provenance for the CPS 3440 paper / README. Keep license wording honest.
DATASET_PROVENANCE = {
    'Grubhub restaurant listings': {
        'role': 'Primary stop-location dataset for NYC / NJ OpenStreetMap experiments',
        'what_rows_represent': (
            'Restaurant listing / search-result rows with restaurant coordinates and the '
            'search location used when the listing was collected.'
        ),
        'geographic_coverage': (
            'US metros including NY, NJ, IL, CA, MA '
            '(from searched_state / searched_metro; ~3.5k NY-metro rows in the local file).'
        ),
        'approx_records': 8088,
        'fields_used': [
            'latitude', 'longitude', 'searched_lat', 'searched_lng',
            'searched_city', 'searched_state', 'searched_metro', 'loc_name',
        ],
        'source': 'Kaggle — Grubhub Restaurant Data (BarkingData / polartech)',
        'source_url': 'https://www.kaggle.com/datasets/polartech/grubhub-restaurant-data',
        'license': (
            'Listed as Unknown on Kaggle at documentation time. Redistribute only if your '
            'course/use case permits; otherwise download via the Kaggle URL and do not re-upload.'
        ),
        'accessed': 'Local copy shipped in data/grubhub.csv (RunDate samples around 2022-04)',
        'preprocessing': [
            'Select lat/lon column pair (restaurant or search location).',
            'Drop missing / non-finite / out-of-range / (0,0) coordinates.',
            'Keep points inside the OSM graph bounding box.',
            'Snap each point to the nearest OSM intersection (haversine meters, max-snap limit).',
        ],
        'limitations': [
            'Points are restaurant/search locations, not historical multi-stop driver GPS tours.',
            'Kaggle license is Unknown — cite the URL and follow course redistribution rules.',
            'A duplicate copy under data/user/ may exist; the UI lists unique content only.',
        ],
    },
    'Food delivery records': {
        'role': 'Secondary tabular dataset (India geography — not for NJ/NY road demos)',
        'what_rows_represent': (
            'Tabular delivery-order style records with restaurant and customer coordinates, '
            'traffic/weather attributes, and delivery duration.'
        ),
        'geographic_coverage': 'Coordinates consistent with India (approx. lat 10–31, lon 73–88).',
        'approx_records': 38964,
        'fields_used': [
            'Restaurant_latitude', 'Restaurant_longitude',
            'Delivery_location_latitude', 'Delivery_location_longitude',
            'City', 'Time_taken (min)',
        ],
        'source': (
            'Public Kaggle food-delivery / Zomato-style operations datasets '
            '(column schema matches common India delivery-time releases; local file may be a cleaned derivative).'
        ),
        'source_url': 'https://www.kaggle.com/datasets/saurabhbadole/zomato-delivery-operations-analytics-dataset',
        'license': (
            'Confirm the specific Kaggle listing license before redistribution. '
            'Local file includes derived columns (distance_km, delivery_speed).'
        ),
        'accessed': 'Local copy shipped in data/food_delivery_dataset.csv',
        'preprocessing': [
            'Same clean → bounds → snap pipeline when used as stop source.',
            'Prefer an India OSM area if routing with these coordinates.',
        ],
        'limitations': [
            'Not proven multi-stop driver GPS traces.',
            'City values are categorical labels (Metropolitian/Urban/…), not US city names.',
            'Points generally fall outside Jersey City / NYC OSM downloads — do not use as the primary US demo dataset.',
        ],
    },
}

_LAT = re.compile(r'(?i)(?:^|_)(?:latitude|lat)$')
_LON = re.compile(r'(?i)(?:^|_)(?:longitude|lng|lon|long)$')


def detect_coordinate_pairs(columns):
    """Pair latitude/longitude columns that share a name prefix."""
    grouped = {}
    for column in columns:
        lat_match = _LAT.search(str(column))
        lon_match = _LON.search(str(column))
        if lat_match:
            prefix = str(column)[:lat_match.start()].rstrip('_').lower()
            grouped.setdefault(prefix, {})['lat'] = column
        elif lon_match:
            prefix = str(column)[:lon_match.start()].rstrip('_').lower()
            grouped.setdefault(prefix, {})['lon'] = column
    pairs = []
    for prefix in grouped:
        axes = grouped[prefix]
        if 'lat' in axes and 'lon' in axes:
            pairs.append((axes['lat'], axes['lon']))
    return pairs


def file_digest(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def coordinate_pair_label(lat_col, lon_col):
    """Human label for a lat/lon column pair based on real column names."""
    text = f'{lat_col} / {lon_col}'.lower()
    if 'restaurant' in text:
        return 'Restaurant location'
    if 'delivery' in text or 'customer' in text:
        return 'Customer / delivery location'
    if 'searched' in text or 'search' in text:
        return 'Search location'
    if lat_col.lower() in {'latitude', 'lat'} and lon_col.lower() in {'longitude', 'lng', 'lon', 'long'}:
        return 'Primary latitude / longitude'
    return 'Other coordinates'


def dataset_validation_summary(frame, lat_col, lon_col):
    """Summarize coordinate quality without silently inventing values."""
    total = len(frame)
    lat = pd.to_numeric(frame[lat_col], errors='coerce')
    lon = pd.to_numeric(frame[lon_col], errors='coerce')
    missing = int(lat.isna().sum() | lon.isna().sum())
    # Count rows where either axis failed numeric conversion or is null.
    missing = int((lat.isna() | lon.isna()).sum())
    non_numeric = missing  # coerced failures appear as NA
    invalid_range = int((~(lat.isna() | lon.isna()) & ~((lat.between(-90, 90)) & (lon.between(-180, 180)))).sum())
    zero_zero = int(((lat == 0) & (lon == 0)).sum())
    usable = clean_coordinates(frame, lat_col, lon_col)
    duplicate_coords = int(usable.duplicated(subset=[lat_col, lon_col]).sum()) if len(usable) else 0
    coverage = None
    if len(usable):
        coverage = {
            'min_lat': float(usable[lat_col].min()),
            'max_lat': float(usable[lat_col].max()),
            'min_lon': float(usable[lon_col].min()),
            'max_lon': float(usable[lon_col].max()),
        }
    return {
        'original_rows': total,
        'selected_lat': lat_col,
        'selected_lon': lon_col,
        'selected_pair_label': coordinate_pair_label(lat_col, lon_col),
        'usable_coordinate_rows': len(usable),
        'missing_or_non_numeric': missing,
        'invalid_lat_lon_range': invalid_range,
        'zero_zero_coordinates': zero_zero,
        'duplicate_coordinates_among_usable': duplicate_coords,
        'geographic_coverage': coverage,
    }


def dataset_provenance(name):
    info = DATASET_PROVENANCE.get(name, {
        'what_rows_represent': 'User-supplied table rows.',
        'geographic_coverage': 'Depends on file contents.',
        'source': 'Source not yet verified',
        'source_url': 'Source not yet verified',
        'license': 'License not yet verified',
        'accessed': 'Unknown',
        'limitations': ['Coordinates are experiment inputs after cleaning/snapping, not proven driver tours.'],
    })
    return dict(info)


def list_datasets(user_dir=None):
    """Built-in datasets first, then unique user datasets (skip byte-identical duplicates)."""
    folder = _user_dir(user_dir)
    items = []
    builtin_digests = set()
    for name, path in SOURCES.items():
        item = {
            'name': name,
            'path': path,
            'coordinates': list(COORDINATES[name]),
            'builtin': True,
            'provenance': dataset_provenance(name),
        }
        items.append(item)
        if path.is_file():
            try:
                builtin_digests.add(file_digest(path))
            except OSError:
                pass
    claimed = set()
    known = {item['name'] for item in items}
    for name, meta in _read_catalog(folder).items():
        path = _catalog_file(folder, meta)
        if path is None or name in known:
            continue
        try:
            digest = file_digest(path)
        except OSError:
            continue
        if digest in builtin_digests:
            claimed.add(path.name)
            continue
        claimed.add(path.name)
        known.add(name)
        coordinates = _catalog_coordinates(meta)
        if coordinates is None:
            coordinates = detect_coordinate_pairs(_column_names(path))
        items.append({
            'name': name,
            'path': path,
            'coordinates': coordinates,
            'builtin': False,
            'provenance': dataset_provenance(name),
        })
    if folder.is_dir():
        for path in sorted(folder.iterdir()):
            if not _is_table(path) or path.name in claimed:
                continue
            try:
                digest = file_digest(path)
            except OSError:
                continue
            if digest in builtin_digests:
                continue
            name = _unique_name(path.stem, known)
            known.add(name)
            items.append({
                'name': name,
                'path': path,
                'coordinates': detect_coordinate_pairs(_column_names(path)),
                'builtin': False,
                'provenance': dataset_provenance(name),
            })
    return items


def load_dataset(name, user_dir=None):
    match = _require(name, user_dir)
    return _read_table(match['path'])


def dataset_coordinates(name, user_dir=None):
    return list(_require(name, user_dir)['coordinates'])


def add_dataset(name, filename, content, coordinates=None, user_dir=None):
    """Save a CSV or JSON file and register it so the explorer can open it."""
    folder = _user_dir(user_dir)
    label = _validate_name(name, folder)
    safe_name = _safe_filename(filename)
    folder.mkdir(parents=True, exist_ok=True)
    path = _available_path(folder, safe_name)
    if isinstance(content, str):
        content = content.encode('utf-8')
    path.write_bytes(content)
    try:
        frame = _read_table(path)
        if frame.empty or len(frame.columns) == 0:
            raise ValueError('The file has no rows to add.')
        chosen = _validate_coordinates(frame.columns, coordinates)
        if chosen is None:
            chosen = detect_coordinate_pairs(frame.columns)
    except Exception as exc:
        path.unlink(missing_ok=True)
        if isinstance(exc, ValueError):
            raise
        raise ValueError(f'Could not read {safe_name} as a table: {exc}') from exc
    catalog = _read_catalog(folder)
    catalog[label] = {
        'file': path.name,
        'coordinates': [list(pair) for pair in chosen],
    }
    _write_catalog(folder, catalog)
    return {'name': label, 'path': path, 'coordinates': chosen, 'rows': len(frame), 'columns': list(frame.columns)}


def remove_dataset(name, user_dir=None):
    """Delete a user-added dataset file. Built-in datasets stay in place."""
    folder = _user_dir(user_dir)
    match = _require(name, folder)
    if match['builtin']:
        raise ValueError('Built-in datasets cannot be removed.')
    catalog = _read_catalog(folder)
    catalog.pop(match['name'], None)
    _write_catalog(folder, catalog)
    if match['path'].is_file():
        match['path'].unlink()


def clean_coordinates(df, lat_col, lon_col):
    frame = df.copy()
    frame[lat_col] = pd.to_numeric(frame[lat_col], errors='coerce')
    frame[lon_col] = pd.to_numeric(frame[lon_col], errors='coerce')
    mask = frame[lat_col].between(-90, 90) & frame[lon_col].between(-180, 180)
    mask &= ~((frame[lat_col] == 0) & (frame[lon_col] == 0))
    return frame.loc[mask].copy()


def _require(name, user_dir):
    for item in list_datasets(user_dir):
        if item['name'] == name:
            if not item['path'].is_file():
                raise FileNotFoundError(f'Missing {item["path"].name}. Place the file in data/ or data/user/.')
            return item
    raise ValueError(f'Unknown dataset: {name}')


def _user_dir(user_dir):
    return Path(user_dir) if user_dir is not None else USER_DATA_DIR


def _read_catalog(folder):
    path = folder / CATALOG_NAME
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise ValueError(f'{CATALOG_NAME} is not valid JSON: {exc}') from exc
    if not isinstance(raw, dict):
        raise ValueError(f'{CATALOG_NAME} must be an object keyed by dataset name.')
    cleaned = {}
    for name, meta in raw.items():
        if not isinstance(name, str) or not isinstance(meta, dict) or 'file' not in meta:
            raise ValueError(f'{CATALOG_NAME} entry {name!r} needs a file name.')
        cleaned[name] = meta
    return cleaned


def _write_catalog(folder, catalog):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / CATALOG_NAME
    path.write_text(json.dumps(catalog, indent=2), encoding='utf-8')


def _catalog_file(folder, meta):
    filename = _safe_filename(str(meta['file']))
    path = (folder / filename).resolve()
    if path.parent != folder.resolve() or not path.is_file():
        return None
    return path


def _catalog_coordinates(meta):
    raw = meta.get('coordinates')
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ValueError('coordinates must be a list of [latitude, longitude] pairs.')
    pairs = []
    for pair in raw:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError('Each coordinate entry must be [latitude_column, longitude_column].')
        pairs.append((str(pair[0]), str(pair[1])))
    return pairs


def _column_names(path):
    if path.suffix.lower() == '.csv':
        return list(pd.read_csv(path, nrows=0).columns)
    return list(_read_table(path).columns)


def _read_table(path):
    suffix = path.suffix.lower()
    if suffix == '.csv':
        return pd.read_csv(path, low_memory=False)
    if suffix == '.json':
        return pd.read_json(path)
    raise ValueError('Only CSV and JSON files can be added.')


def _is_table(path):
    return path.is_file() and path.suffix.lower() in TABLE_SUFFIXES and path.name != CATALOG_NAME


def _validate_name(name, folder):
    label = ' '.join(str(name).split())
    if not label:
        raise ValueError('Enter a dataset name.')
    if label in SOURCES or any(item['name'] == label for item in list_datasets(folder)):
        raise ValueError(f'A dataset named {label!r} already exists.')
    return label


def _safe_filename(filename):
    base = Path(str(filename)).name
    if base in {'', '.', '..', CATALOG_NAME}:
        raise ValueError('Choose a CSV or JSON file name.')
    cleaned = re.sub(r'[^A-Za-z0-9._-]+', '_', base).strip('._')
    suffix = Path(cleaned).suffix.lower()
    if suffix not in TABLE_SUFFIXES:
        raise ValueError('Only CSV and JSON files can be added.')
    return cleaned


def _available_path(folder, filename):
    path = folder / filename
    if not path.exists():
        return path
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    number = 2
    while True:
        candidate = folder / f'{stem}_{number}{suffix}'
        if not candidate.exists():
            return candidate
        number += 1


def _unique_name(name, taken):
    label = name
    number = 2
    while label in taken:
        label = f'{name} ({number})'
        number += 1
    return label


def _validate_coordinates(columns, coordinates):
    if not coordinates:
        return None
    available = set(map(str, columns))
    pairs = []
    for pair in coordinates:
        if len(pair) != 2:
            raise ValueError('Each coordinate pair needs a latitude column and a longitude column.')
        lat, lon = str(pair[0]), str(pair[1])
        if lat not in available or lon not in available:
            raise ValueError(f'Columns {lat!r} and {lon!r} were not found in the file.')
        pairs.append((lat, lon))
    return pairs

