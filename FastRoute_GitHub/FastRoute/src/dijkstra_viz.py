"""Interactive Dijkstra visualization using the student implementation."""
import json
import random
import networkx as nx
from .algorithms import dijkstra, reconstruct
from .road_data import to_adjacency


def sample_intersection_choices(graph, count=40, seed=42):
    """Pick labeled intersections from the largest strongly connected component."""
    try:
        component = max(nx.strongly_connected_components(graph), key=len)
        nodes = sorted(component)
    except ValueError:
        nodes = sorted(graph.nodes)
    if len(nodes) <= count:
        chosen = nodes
    else:
        chosen = sorted(random.Random(seed).sample(nodes, count))
    options = []
    for node in chosen:
        data = graph.nodes[node]
        options.append({
            'id': node,
            'label': f"Intersection {node} ({data['y']:.5f}, {data['x']:.5f})",
            'lat': float(data['y']),
            'lon': float(data['x']),
        })
    return options


def sample_reachable_pair(graph, seed=42, attempts=40):
    """Return (source, target) known reachable on the directed graph, or None."""
    choices = sample_intersection_choices(graph, count=min(60, max(10, len(graph.nodes))), seed=seed)
    ids = [item['id'] for item in choices]
    if len(ids) < 2:
        return None
    adjacency = to_adjacency(graph)
    rng = random.Random(seed)
    for _ in range(attempts):
        source, target = rng.sample(ids, 2)
        distances, _, _ = dijkstra(adjacency, source, target)
        if target in distances:
            return source, target
    # Fall back: walk from first node until a reachable other node appears.
    source = ids[0]
    distances, _, _ = dijkstra(adjacency, source)
    for target in ids[1:]:
        if target in distances:
            return source, target
    return None


def is_reachable(graph, source, target):
    if source == target:
        return False
    adjacency = to_adjacency(graph)
    distances, _, _ = dijkstra(adjacency, source, target)
    return target in distances


def build_dijkstra_trace(graph, source, target):
    """Run the real Dijkstra algorithm and package geometry + step history."""
    if source == target:
        raise ValueError('Choose two different intersections.')
    adjacency = to_adjacency(graph)
    distances, previous, explored, steps = dijkstra(adjacency, source, target, record_steps=True)
    if target not in distances:
        raise ValueError(
            'Destination is unreachable from the start on this directed road graph '
            '(one-way streets can block a path). Pick another pair or click '
            '"Generate reachable example".'
        )
    path = reconstruct(previous, source, target)
    if not path:
        raise ValueError('No road path could be reconstructed.')
    path_coords = [[float(graph.nodes[n]['y']), float(graph.nodes[n]['x'])] for n in path]
    node_coords = {
        str(node): [float(graph.nodes[node]['y']), float(graph.nodes[node]['x'])]
        for node in graph.nodes
    }
    mentioned = {source, target, *path}
    for step in steps:
        if 'node' in step:
            mentioned.add(step['node'])
        if 'from' in step:
            mentioned.add(step['from'])
        if 'to' in step:
            mentioned.add(step['to'])
        for item in step.get('next_frontier') or []:
            mentioned.add(item['node'])
    slim_coords = {str(n): node_coords[str(n)] for n in mentioned if str(n) in node_coords}
    total_m = distances[target]
    return {
        'source': source,
        'target': target,
        'explored_count': explored,
        'distance_m': total_m,
        'distance_km': round(total_m / 1000, 4),
        'path': path,
        'path_coords': path_coords,
        'node_coords': slim_coords,
        'steps': [
            {
                **step,
                'node': step.get('node'),
                'from': step.get('from'),
                'to': step.get('to'),
                'next_frontier': step.get('next_frontier') or [],
            }
            for step in steps
        ],
    }


def build_dijkstra_animation_html(trace, height=620):
    """Self-contained Leaflet page that steps through recorded Dijkstra events."""
    payload = json.dumps(trace, default=str)
    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
html,body{{margin:0;height:100%;background:#0B1220;color:#E2E8F0;font-family:Segoe UI,sans-serif}}
#wrap{{display:flex;flex-direction:column;height:{height}px}}
#bar{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;padding:10px;background:#0F172A;border-bottom:1px solid #1E293B}}
button{{background:#1E293B;color:#fff;border:1px solid #334155;border-radius:8px;padding:7px 12px;cursor:pointer;font-weight:600}}
button.primary{{background:#2563EB;border-color:#2563EB}}
#status{{flex:1;min-width:240px;font-size:13px;color:#94A3B8}}
#map{{flex:1}}
#explain{{padding:10px 12px;background:#111827;border-top:1px solid #1E293B;font-size:13px;min-height:52px}}
</style></head><body>
<div id="wrap">
  <div id="bar">
    <button class="primary" id="start">Start</button>
    <button id="pause">Pause</button>
    <button id="resume">Resume</button>
    <button id="step">Step Forward</button>
    <button id="auto">Run Automatically</button>
    <button id="reset">Reset</button>
    <div id="status">Choose Start to watch Dijkstra explore the road graph.</div>
  </div>
  <div id="map"></div>
  <div id="explain">Dijkstra expands the closest unsettled intersection from a priority queue until the destination is settled. Not every examined edge improves a distance.</div>
</div>
<script>
const DATA = {payload};
const map = L.map('map');
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
  attribution: 'Basemap tiles &copy; Esri · Road network geometry &copy; OpenStreetMap contributors (via OSMnx)'
}}).addTo(map);
const pathBounds = (DATA.path_coords && DATA.path_coords.length)
  ? DATA.path_coords
  : [DATA.node_coords[String(DATA.source)], DATA.node_coords[String(DATA.target)]];
map.fitBounds(pathBounds, {{padding:[48,48], maxZoom:16}});
const src = DATA.node_coords[String(DATA.source)];
const dst = DATA.node_coords[String(DATA.target)];
L.circleMarker(src, {{radius:9, color:'#0F172A', fillColor:'#38BDF8', fillOpacity:1, weight:2}}).addTo(map).bindTooltip('Start');
L.circleMarker(dst, {{radius:9, color:'#0F172A', fillColor:'#F43F5E', fillOpacity:1, weight:2}}).addTo(map).bindTooltip('Destination');
const settled = L.layerGroup().addTo(map);
const frontier = L.layerGroup().addTo(map);
const relaxEdges = L.layerGroup().addTo(map);
const currentLayer = L.layerGroup().addTo(map);
const pathLayer = L.polyline([], {{color:'#22C55E', weight:6, opacity:0.95}}).addTo(map);
let index = 0, timer = null;
const statusEl = document.getElementById('status');
const explainEl = document.getElementById('explain');
function clearDynamic() {{
  settled.clearLayers(); frontier.clearLayers(); relaxEdges.clearLayers(); currentLayer.clearLayers(); pathLayer.setLatLngs([]);
}}
function coord(id) {{ return DATA.node_coords[String(id)]; }}
function applyStep(i) {{
  clearDynamic();
  for (let k = 0; k <= i; k++) {{
    const step = DATA.steps[k];
    if (step.event === 'settle') {{
      const c = coord(step.node);
      if (c) {{
        L.circleMarker(c, {{radius:5, color:'#0F172A', fillColor:'#FACC15', fillOpacity:0.95, weight:1}}).addTo(settled);
        if (k === i) L.circleMarker(c, {{radius:8, color:'#F8FAFC', fillColor:'#F97316', fillOpacity:0.35, weight:2}}).addTo(currentLayer);
      }}
      frontier.clearLayers();
      (step.next_frontier || []).forEach(item => {{
        const fc = coord(item.node);
        if (fc) L.circleMarker(fc, {{radius:5, color:'#0F172A', fillColor:'#A78BFA', fillOpacity:0.9, weight:1}}).addTo(frontier);
      }});
      statusEl.textContent = `Settled intersection ${{step.node}} · known distance ${{step.distance.toFixed(1)}} m · explored ${{step.explored}}`;
      const nxt = (step.next_frontier || [])[0];
      explainEl.textContent = nxt
        ? `Settled the closest queued intersection (orange ring). Yellow dots are already settled. Purple dots preview the next frontier. Next candidate: ${{nxt.node}} at ${{nxt.distance.toFixed(1)}} m.`
        : `Settled intersection ${{step.node}}. The previewed priority-queue frontier is empty.`;
    }} else if (step.event === 'relax') {{
      const a = coord(step.from), b = coord(step.to);
      if (a && b) L.polyline([a,b], {{color:'#60A5FA', weight:2, opacity:0.55}}).addTo(relaxEdges);
      explainEl.textContent = `Found an improved tentative distance for ${{step.to}} via ${{step.from}} → ${{step.to}} (${{step.distance.toFixed(1)}} m). Only improving updates are recorded as relax events.`;
      statusEl.textContent = `Relaxing neighbors · explored ${{step.explored}}`;
    }}
  }}
  if (i >= DATA.steps.length - 1) {{
    pathLayer.setLatLngs(DATA.path_coords);
    if (DATA.path_coords.length) map.fitBounds(DATA.path_coords, {{padding:[48,48], maxZoom:16}});
    statusEl.textContent = `Done. Shortest road path = ${{DATA.distance_m.toFixed(1)}} m (${{DATA.distance_km}} km).`;
    explainEl.textContent = 'The destination is settled. The green line is the reconstructed shortest road path along OSM geometry.';
  }}
}}
function stop() {{ if (timer) {{ clearInterval(timer); timer = null; }} }}
function reset() {{ stop(); index = 0; clearDynamic(); statusEl.textContent = 'Reset. Press Start or Step Forward.'; explainEl.textContent = 'Yellow = settled. Orange ring = current settle. Purple = frontier preview. Blue = improving relaxations. Green = final path.'; }}
function stepForward() {{
  if (!DATA.steps.length) return;
  if (index >= DATA.steps.length) index = DATA.steps.length - 1;
  applyStep(index);
  if (index < DATA.steps.length - 1) index += 1;
  else stop();
}}
function startAuto() {{ stop(); timer = setInterval(() => {{
  stepForward();
  if (index >= DATA.steps.length - 1) stop();
}}, 120); }}
document.getElementById('start').onclick = () => {{ reset(); startAuto(); }};
document.getElementById('pause').onclick = () => stop();
document.getElementById('resume').onclick = () => startAuto();
document.getElementById('step').onclick = () => {{ stop(); stepForward(); }};
document.getElementById('auto').onclick = () => startAuto();
document.getElementById('reset').onclick = reset;
reset();
</script></body></html>"""
