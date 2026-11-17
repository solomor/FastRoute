"""Folium/Leaflet map builders for FastRoute algorithm comparison."""
import json
import folium
from folium import FeatureGroup, LayerControl, Map, Marker, PolyLine, CircleMarker
from folium.plugins import BeautifyIcon
from branca.element import Element, MacroElement, Template
from .algorithms import ALGORITHM_COLORS, ALGORITHM_SHORT
from .road_data import stop_labels


def build_comparison_map(
    stop_coords,
    algorithm_routes,
    *,
    show_algorithms=None,
    show_markers=True,
    highlight_stop=None,
    highlight_stops=None,
    partial_route=None,
    partial_color='#F8FAFC',
    partial_routes=None,
    draw_full_routes=True,
    title='FastRoute comparison',
):
    """Build an interactive OSM map with street-level algorithm routes."""
    if not stop_coords:
        raise ValueError('No stop coordinates to display')
    visible = algorithm_routes
    if show_algorithms is not None:
        visible = [row for row in algorithm_routes if row['Algorithm'] in show_algorithms]

    center_lat = sum(lat for lat, _ in stop_coords) / len(stop_coords)
    center_lon = sum(lon for _, lon in stop_coords) / len(stop_coords)
    fmap = Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
    )
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
        attr='Basemap tiles &copy; Esri · Route geometry &copy; OpenStreetMap contributors (via OSMnx)',
        name='Dark streets (Esri basemap)',
        control=True,
    ).add_to(fmap)
    folium.TileLayer(
        'OpenStreetMap',
        name='OpenStreetMap basemap',
        control=True,
        attr='Basemap &copy; OpenStreetMap contributors · Route geometry from OSM via OSMnx',
    ).add_to(fmap)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
        attr='Basemap tiles &copy; Esri · Route geometry &copy; OpenStreetMap contributors (via OSMnx)',
        name='Light streets',
        control=True,
    ).add_to(fmap)

    active_highlights = set()
    if highlight_stops:
        active_highlights.update(index for index in highlight_stops if index is not None)
    if highlight_stop is not None:
        active_highlights.add(highlight_stop)

    labels = stop_labels(len(stop_coords))
    if show_markers:
        marker_group = FeatureGroup(name='Delivery markers', show=True)
        for index, (lat, lon) in enumerate(stop_coords):
            color = '#38BDF8' if index == 0 else '#F8FAFC'
            if index in active_highlights:
                color = '#FACC15'
            popup = (
                f'<div style="font-family:IBM Plex Sans,Segoe UI,sans-serif;min-width:150px">'
                f'<b>{labels[index]}</b><br>Latitude {lat:.5f}<br>Longitude {lon:.5f}</div>'
            )
            if index == 0:
                Marker(
                    location=[lat, lon],
                    popup=popup,
                    tooltip=labels[index],
                    icon=BeautifyIcon(
                        icon='home',
                        icon_shape='marker',
                        border_color='#38BDF8',
                        background_color='#0F172A',
                        text_color='#38BDF8',
                    ),
                ).add_to(marker_group)
            else:
                CircleMarker(
                    location=[lat, lon],
                    radius=9 if index in active_highlights else 7,
                    color='#0F172A',
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.95,
                    weight=2,
                    popup=popup,
                    tooltip=labels[index],
                ).add_to(marker_group)
                folium.map.Marker(
                    [lat, lon],
                    icon=folium.DivIcon(
                        html=(
                            f'<div style="font:600 11px IBM Plex Sans,Segoe UI,sans-serif;'
                            f'color:#E2E8F0;text-shadow:0 1px 3px #020617;transform:translate(10px,-8px)">'
                            f'{labels[index]}</div>'
                        )
                    ),
                ).add_to(marker_group)
        marker_group.add_to(fmap)

    if draw_full_routes:
        for row in visible:
            coords = row.get('coordinates') or []
            if len(coords) < 2:
                continue
            short = ALGORITHM_SHORT.get(row['Algorithm'], row['Algorithm'])
            group = FeatureGroup(name=f'{short} route', show=True)
            PolyLine(
                locations=coords,
                color=row.get('Color', ALGORITHM_COLORS.get(row['Algorithm'], '#94A3B8')),
                weight=5,
                opacity=0.9,
                tooltip=f"{short}: {row.get('Distance (km)', '?')} km",
            ).add_to(group)
            group.add_to(fmap)

    overlays = list(partial_routes or [])
    if partial_route and len(partial_route) >= 2:
        overlays.append({
            'name': 'Animation progress',
            'color': partial_color,
            'coordinates': partial_route,
        })
    for overlay in overlays:
        coords = overlay.get('coordinates') or []
        if len(coords) < 2:
            continue
        short = overlay.get('name', 'Progress')
        color = overlay.get('color', '#F8FAFC')
        group = FeatureGroup(name=f'{short} progress', show=True)
        PolyLine(
            locations=coords,
            color=color,
            weight=7,
            opacity=0.95,
            tooltip=short,
        ).add_to(group)
        group.add_to(fmap)

    legend_rows = visible if (draw_full_routes and visible) else algorithm_routes
    if overlays and not draw_full_routes:
        legend_rows = [
            {
                'Algorithm': item.get('algorithm', item.get('name', 'Progress')),
                'Color': item.get('color', '#F8FAFC'),
            }
            for item in overlays
        ]
    fmap.fit_bounds([[lat, lon] for lat, lon in stop_coords], padding=(28, 28))
    _add_legend(fmap, legend_rows if legend_rows else algorithm_routes)
    LayerControl(collapsed=False).add_to(fmap)
    fmap.get_root().html.add_child(Element(f'<div style="display:none">{title}</div>'))
    return fmap


def animation_frame_coords(legs, stop_index):
    """Build the progressive polyline after completing stop_index legs from the warehouse."""
    if stop_index <= 0 or not legs:
        return []
    coords = []
    for index, leg in enumerate(legs[:stop_index]):
        if index and leg:
            coords.extend(leg[1:])
        else:
            coords.extend(leg)
    return coords


def progressive_algorithm_overlays(results, step, matrix=None):
    """Build simultaneous progress polylines and status lines for every algorithm."""
    overlays = []
    statuses = []
    highlights = []
    for row in results:
        route = row['Route']
        max_leg = len(route) - 1
        current = min(step, max_leg)
        coords = animation_frame_coords(row.get('legs') or [], current)
        short = ALGORITHM_SHORT.get(row['Algorithm'], row['Algorithm'])
        color = row.get('Color', ALGORITHM_COLORS.get(row['Algorithm'], '#94A3B8'))
        if len(coords) >= 2:
            overlays.append({
                'name': short,
                'algorithm': row['Algorithm'],
                'color': color,
                'coordinates': coords,
            })
        if current < len(route):
            highlights.append(route[current])
        remaining = max(0, max_leg - current)
        if matrix is not None and current > 0:
            distance_m = sum(matrix[route[i]][route[i + 1]] for i in range(current))
            distance_txt = f'{distance_m / 1000:.3f} km'
        elif current >= max_leg:
            distance_txt = f"{row.get('Distance (km)', '?')} km"
        else:
            distance_txt = '0.000 km'
        statuses.append(f'{short}: stop {current}/{max_leg} · {distance_txt} · {remaining} left')
    return overlays, statuses, highlights


def downsample_coords(coords, max_points=1200):
    """Keep animation smooth for long street geometries."""
    if len(coords) <= max_points:
        return [[float(lat), float(lon)] for lat, lon in coords]
    step = max(1, len(coords) // max_points)
    sampled = [coords[i] for i in range(0, len(coords), step)]
    if sampled[-1] != coords[-1]:
        sampled.append(coords[-1])
    return [[float(lat), float(lon)] for lat, lon in sampled]


def build_live_animation_html(
    stop_coords,
    algorithm_routes,
    *,
    show_algorithms=None,
    show_markers=True,
    autoplay=False,
    speed='Normal',
    height=680,
):
    """Return a self-contained Leaflet page that draws routes live in the browser.

    No Streamlit reruns: Play/Pause/Reset run entirely in JavaScript.
    """
    if not stop_coords:
        raise ValueError('No stop coordinates to display')
    # Respect an explicit empty selection: do not fall back to "show all".
    if show_algorithms is None:
        visible = algorithm_routes
    else:
        selected = set(show_algorithms)
        visible = [row for row in algorithm_routes if row['Algorithm'] in selected]

    labels = stop_labels(len(stop_coords))
    stops_payload = [
        {'lat': float(lat), 'lon': float(lon), 'label': labels[i], 'warehouse': i == 0, 'order': i}
        for i, (lat, lon) in enumerate(stop_coords)
    ]
    routes_payload = []
    for row in visible:
        coords = downsample_coords(row.get('coordinates') or [])
        if len(coords) < 2:
            continue
        routes_payload.append({
            'name': ALGORITHM_SHORT.get(row['Algorithm'], row['Algorithm']),
            'algorithm': row['Algorithm'],
            'color': row.get('Color', ALGORITHM_COLORS.get(row['Algorithm'], '#94A3B8')),
            'distance_km': row.get('Distance (km)'),
            'coords': coords,
        })

    bound_points = [[float(lat), float(lon)] for lat, lon in stop_coords]
    for row in routes_payload:
        bound_points.extend(row['coords'])
    if not bound_points:
        raise ValueError('No coordinates available to bound the map')
    lats = [p[0] for p in bound_points]
    lons = [p[1] for p in bound_points]
    pad_lat = max(0.0008, (max(lats) - min(lats)) * 0.08) if max(lats) != min(lats) else 0.002
    pad_lon = max(0.0008, (max(lons) - min(lons)) * 0.08) if max(lons) != min(lons) else 0.002
    bounds = [[min(lats) - pad_lat, min(lons) - pad_lon], [max(lats) + pad_lat, max(lons) + pad_lon]]
    speed_ms = {'Slow': 55, 'Normal': 28, 'Fast': 12}.get(speed, 28)
    points_per_tick = {'Slow': 4, 'Normal': 10, 'Fast': 22}.get(speed, 10)

    payload = {
        'stops': stops_payload,
        'routes': routes_payload,
        'bounds': bounds,
        'showMarkers': bool(show_markers),
        'autoplay': bool(autoplay),
        'intervalMs': speed_ms,
        'pointsPerTick': points_per_tick,
    }
    data_json = json.dumps(payload)
    legend_items = ''.join(
        f'<div class="leg"><span style="background:{r["color"]}"></span>{r["name"]}</div>'
        for r in routes_payload
    )

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    html, body {{ margin:0; padding:0; height:100%; background:#0B1220; color:#E2E8F0;
      font-family:IBM Plex Sans,Segoe UI,sans-serif; }}
    #wrap {{ display:flex; flex-direction:column; height:{height}px; }}
    #toolbar {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; padding:10px 12px;
      background:#0F172A; border-bottom:1px solid #1E293B; }}
    #toolbar button {{ background:#1E293B; color:#F8FAFC; border:1px solid #334155; border-radius:8px;
      padding:7px 12px; cursor:pointer; font-weight:600; }}
    #toolbar button.primary {{ background:#2563EB; border-color:#2563EB; }}
    #toolbar button:hover {{ filter:brightness(1.08); }}
    #status {{ flex:1; min-width:220px; color:#94A3B8; font-size:13px; }}
    #map {{ flex:1; min-height:420px; }}
    #legend {{ position:absolute; bottom:18px; left:18px; z-index:1000; background:rgba(15,23,42,.92);
      border:1px solid #334155; border-radius:10px; padding:10px 12px; font-size:12px;
      box-shadow:0 8px 24px rgba(0,0,0,.35); }}
    #legend .title {{ font-weight:600; margin-bottom:6px; }}
    #legend .leg {{ display:flex; align-items:center; gap:8px; margin:4px 0; }}
    #legend .leg span {{ width:18px; height:4px; border-radius:2px; display:inline-block; }}
    #live {{ display:flex; gap:8px; flex-wrap:wrap; padding:8px 12px; background:#111827;
      border-top:1px solid #1E293B; font-size:12px; }}
    .chip {{ background:#0F172A; border:1px solid #334155; border-radius:999px; padding:4px 10px; }}
  </style>
</head>
<body>
  <div id="wrap">
    <div id="toolbar">
      <button class="primary" id="btnPlayAll" type="button">Play all</button>
      <button id="btnPause" type="button">Pause</button>
      <button id="btnResume" type="button">Resume</button>
      <button id="btnReset" type="button">Reset</button>
      <button id="btnShowAll" type="button">Show finished routes</button>
      <div id="status">Press Play all to draw every algorithm live on the map.</div>
    </div>
    <div id="map"></div>
    <div id="live"></div>
  </div>
  <div id="legend"><div class="title">Route legend</div>{legend_items}</div>
  <script>
    const DATA = {data_json};
    const map = L.map('map', {{ zoomControl: true }});
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      attribution: 'Basemap tiles &copy; Esri · Road route geometry &copy; OpenStreetMap contributors (via OSMnx)'
    }}).addTo(map);
    map.fitBounds(DATA.bounds, {{ padding: [28, 28], maxZoom: 16 }});
    if (!DATA.routes.length) {{
      document.getElementById('status').textContent = 'No algorithm routes are visible. Select at least one route above the map.';
    }}

    if (DATA.showMarkers) {{
      DATA.stops.forEach((stop) => {{
        if (stop.warehouse) {{
          L.circleMarker([stop.lat, stop.lon], {{
            radius: 9, color: '#0F172A', fillColor: '#38BDF8', fillOpacity: 1, weight: 2
          }}).addTo(map).bindTooltip(stop.label);
        }} else {{
          L.circleMarker([stop.lat, stop.lon], {{
            radius: 7, color: '#0F172A', fillColor: '#F8FAFC', fillOpacity: 1, weight: 2
          }}).addTo(map).bindTooltip(stop.label);
        }}
      }});
    }}

    const layers = DATA.routes.map((route) => {{
      const line = L.polyline([], {{ color: route.color, weight: 5, opacity: 0.95 }}).addTo(map);
      const tip = L.circleMarker([route.coords[0][0], route.coords[0][1]], {{
        radius: 5, color: '#0F172A', fillColor: route.color, fillOpacity: 1, weight: 2
      }}).addTo(map);
      tip.setStyle({{ opacity: 0, fillOpacity: 0 }});
      return {{ ...route, line, tip, index: 0 }};
    }});

    let timer = null;
    let playing = false;
    const statusEl = document.getElementById('status');
    const liveEl = document.getElementById('live');

    function setStatus(text) {{ statusEl.textContent = text; }}

    function updateLive() {{
      liveEl.innerHTML = layers.map((layer) => {{
        const pct = Math.min(100, Math.round(100 * layer.index / Math.max(1, layer.coords.length - 1)));
        return `<span class="chip"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${{layer.color}};margin-right:6px"></span>${{layer.name}}: ${{pct}}% · ${{layer.distance_km}} km</span>`;
      }}).join('');
    }}

    function clearRoutes() {{
      layers.forEach((layer) => {{
        layer.index = 0;
        layer.line.setLatLngs([]);
        layer.tip.setStyle({{ opacity: 0, fillOpacity: 0 }});
      }});
      updateLive();
    }}

    function showFinished() {{
      stopTimer();
      layers.forEach((layer) => {{
        layer.index = layer.coords.length;
        layer.line.setLatLngs(layer.coords);
        const last = layer.coords[layer.coords.length - 1];
        layer.tip.setLatLng(last);
        layer.tip.setStyle({{ opacity: 1, fillOpacity: 1 }});
      }});
      updateLive();
      setStatus('Finished routes shown for comparison.');
    }}

    function tick() {{
      let done = true;
      layers.forEach((layer) => {{
        if (layer.index >= layer.coords.length) return;
        done = false;
        const next = Math.min(layer.coords.length, layer.index + DATA.pointsPerTick);
        layer.index = next;
        layer.line.setLatLngs(layer.coords.slice(0, next));
        const tip = layer.coords[next - 1];
        layer.tip.setLatLng(tip);
        layer.tip.setStyle({{ opacity: 1, fillOpacity: 1 }});
      }});
      updateLive();
      if (done) {{
        stopTimer();
        setStatus('All algorithms finished drawing.');
      }} else {{
        const progress = layers.map((l) => Math.round(100 * l.index / Math.max(1, l.coords.length - 1)));
        setStatus('Drawing live · ' + progress.map((p, i) => layers[i].name + ' ' + p + '%').join(' · '));
      }}
    }}

    function stopTimer() {{
      playing = false;
      if (timer) {{ clearInterval(timer); timer = null; }}
    }}

    function playAll() {{
      stopTimer();
      clearRoutes();
      playing = true;
      setStatus('Drawing all algorithms in real time...');
      timer = setInterval(tick, DATA.intervalMs);
    }}

    function pause() {{
      stopTimer();
      setStatus('Paused.');
    }}

    function resume() {{
      if (playing) return;
      const unfinished = layers.some((l) => l.index < l.coords.length);
      if (!unfinished) {{
        playAll();
        return;
      }}
      playing = true;
      setStatus('Resumed live drawing...');
      timer = setInterval(tick, DATA.intervalMs);
    }}

    document.getElementById('btnPlayAll').onclick = playAll;
    document.getElementById('btnPause').onclick = pause;
    document.getElementById('btnResume').onclick = resume;
    document.getElementById('btnReset').onclick = () => {{ stopTimer(); clearRoutes(); setStatus('Reset. Press Play all to draw again.'); }};
    document.getElementById('btnShowAll').onclick = showFinished;

    updateLive();
    if (DATA.autoplay) {{
      playAll();
    }} else {{
      showFinished();
      setStatus('Routes ready. Press Play all to redraw them live without reloading the page.');
    }}
  </script>
</body>
</html>"""


def _add_legend(fmap, routes):
    items = []
    seen = set()
    for row in routes:
        name = row.get('Algorithm', row.get('name', 'Route'))
        if name in seen:
            continue
        seen.add(name)
        color = row.get('Color', ALGORITHM_COLORS.get(name, '#94A3B8'))
        label = ALGORITHM_SHORT.get(name, name)
        items.append(
            f'<div style="margin:4px 0;display:flex;align-items:center;gap:8px">'
            f'<span style="width:18px;height:4px;background:{color};display:inline-block;'
            f'border-radius:2px"></span>{label}</div>'
        )
    if not items:
        return
    html = f"""
    {{% macro html(this, kwargs) %}}
    <div style="position:fixed;bottom:28px;left:28px;z-index:9999;background:rgba(15,23,42,0.92);
                color:#E2E8F0;padding:12px 14px;border:1px solid #334155;border-radius:10px;
                font-family:IBM Plex Sans,Segoe UI,sans-serif;font-size:12px;
                box-shadow:0 8px 24px rgba(0,0,0,.35)">
      <div style="font-weight:600;margin-bottom:6px;letter-spacing:.02em">Route legend</div>
      {''.join(items)}
      <div style="margin-top:8px;opacity:.75">Blue house marker = warehouse</div>
    </div>
    {{% endmacro %}}
    """
    legend = MacroElement()
    legend._template = Template(html)
    fmap.get_root().add_child(legend)
