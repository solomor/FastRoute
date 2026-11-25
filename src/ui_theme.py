"""Enterprise / futuristic dark theme for FastRoute."""

THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');

:root {
  --fr-void: #030712;
  --fr-panel: rgba(10, 16, 32, 0.78);
  --fr-panel-solid: #0A1020;
  --fr-elev: #101A2E;
  --fr-line: rgba(94, 234, 212, 0.18);
  --fr-line-strong: rgba(45, 212, 191, 0.35);
  --fr-text: #D7E3F4;
  --fr-muted: #8BA0B8;
  --fr-title: #F4F8FF;
  --fr-accent: #2DD4BF;
  --fr-accent-2: #22D3EE;
  --fr-accent-hot: #67E8F9;
  --fr-warn: #FBBF24;
  --fr-ok: #34D399;
  --fr-danger: #F87171;
  --fr-glow: 0 0 24px rgba(45, 212, 191, 0.18);
}

html, body, [class*="css"], .stApp, .stMarkdown, button, input {
  font-family: 'Outfit', 'Segoe UI', sans-serif !important;
  color: var(--fr-text);
}

.stApp {
  background-color: var(--fr-void);
  background-image:
    radial-gradient(ellipse 80% 50% at 15% -10%, rgba(34, 211, 238, 0.14), transparent 55%),
    radial-gradient(ellipse 60% 40% at 90% 0%, rgba(45, 212, 191, 0.10), transparent 50%),
    radial-gradient(ellipse 50% 30% at 50% 110%, rgba(14, 165, 233, 0.08), transparent 55%),
    linear-gradient(rgba(45, 212, 191, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(45, 212, 191, 0.035) 1px, transparent 1px),
    linear-gradient(180deg, #050B16 0%, #030712 45%, #02060F 100%);
  background-size: auto, auto, auto, 48px 48px, 48px 48px, auto;
  background-attachment: fixed;
}

/* Do NOT use a fixed full-screen overlay here — it can cover Streamlit map iframes. */

[data-testid="stHeader"] {
  background: rgba(3, 7, 18, 0.82) !important;
  backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--fr-line);
}

[data-testid="stToolbar"] { right: 1rem; }

[data-testid="stSidebar"] {
  background:
    linear-gradient(180deg, rgba(8, 14, 28, 0.98) 0%, rgba(5, 10, 22, 0.98) 100%) !important;
  border-right: 1px solid var(--fr-line) !important;
  box-shadow: 8px 0 40px rgba(0, 0, 0, 0.35);
}
[data-testid="stSidebar"] > div:first-child {
  background: transparent !important;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] label {
  color: var(--fr-muted) !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] .stMarkdown h3 {
  color: var(--fr-title) !important;
  font-weight: 700 !important;
  letter-spacing: 0.04em !important;
  text-transform: uppercase !important;
  font-size: 0.78rem !important;
}

.block-container {
  padding-top: 1.15rem !important;
  padding-bottom: 3.5rem !important;
  max-width: 1320px !important;
  position: relative;
  z-index: 1;
}

h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
  color: var(--fr-title) !important;
  letter-spacing: -0.02em !important;
  font-weight: 700 !important;
}
.stCaption, [data-testid="stCaption"] { color: var(--fr-muted) !important; }

/* ——— Enterprise command hero ——— */
.fr-hero {
  position: relative;
  overflow: hidden;
  display: grid;
  gap: 0.85rem;
  margin: 0 0 1.35rem 0;
  padding: 1.35rem 1.45rem 1.4rem;
  border-radius: 20px;
  border: 1px solid var(--fr-line-strong);
  background:
    linear-gradient(135deg, rgba(12, 20, 38, 0.92) 0%, rgba(8, 16, 32, 0.88) 48%, rgba(6, 28, 36, 0.82) 100%);
  box-shadow: var(--fr-glow), 0 24px 60px rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(18px);
}
.fr-hero::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, transparent, rgba(103, 232, 249, 0.08), transparent);
  transform: translateX(-100%);
  animation: fr-scan 7s ease-in-out infinite;
  pointer-events: none;
}
@keyframes fr-scan {
  0%, 100% { transform: translateX(-100%); }
  45%, 55% { transform: translateX(100%); }
}
.fr-hero::after {
  content: "";
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--fr-accent-hot), var(--fr-accent), transparent);
  opacity: 0.9;
}
.fr-hero-top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  position: relative;
  z-index: 1;
}
.fr-brand-row {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}
.fr-mark {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  font-size: 0.85rem;
  color: #042F2E;
  background: linear-gradient(145deg, #67E8F9 0%, #2DD4BF 55%, #14B8A6 100%);
  box-shadow: 0 0 20px rgba(45, 212, 191, 0.45);
}
.fr-hero-kicker {
  color: var(--fr-accent-hot);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  margin: 0 0 0.15rem 0;
}
.fr-hero-title {
  font-size: clamp(2rem, 3vw, 2.65rem);
  font-weight: 800;
  color: var(--fr-title);
  line-height: 1.05;
  margin: 0;
  letter-spacing: -0.03em;
  text-shadow: 0 0 40px rgba(103, 232, 249, 0.15);
}
.fr-status-cluster {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}
.fr-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  border: 1px solid var(--fr-line);
  background: rgba(6, 12, 24, 0.75);
  color: var(--fr-muted);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-family: 'JetBrains Mono', monospace;
}
.fr-chip-live {
  border-color: rgba(52, 211, 153, 0.45);
  color: #A7F3D0;
}
.fr-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--fr-ok);
  box-shadow: 0 0 10px rgba(52, 211, 153, 0.85);
  animation: fr-pulse 1.8s ease-in-out infinite;
}
@keyframes fr-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.55; transform: scale(0.85); }
}
.fr-hero-sub {
  position: relative;
  z-index: 1;
  color: var(--fr-muted);
  font-size: 1.02rem;
  line-height: 1.5;
  max-width: 52rem;
  margin: 0;
}
.fr-pill-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  position: relative;
  z-index: 1;
}
.fr-algo-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0.45rem 0.85rem;
  border-radius: 999px;
  background: rgba(8, 14, 28, 0.88);
  border: 1px solid rgba(148, 163, 184, 0.22);
  color: #E2E8F0;
  font-size: 0.84rem;
  font-weight: 600;
  backdrop-filter: blur(8px);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.fr-algo-pill:hover {
  border-color: var(--fr-accent);
  box-shadow: 0 0 16px rgba(45, 212, 191, 0.2);
}
.fr-swatch {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  display: inline-block;
  box-shadow: 0 0 8px currentColor;
}

.metric-card {
  background: linear-gradient(165deg, rgba(16, 26, 46, 0.95) 0%, rgba(10, 16, 32, 0.95) 100%);
  border: 1px solid var(--fr-line);
  border-radius: 16px;
  padding: 15px 16px;
  margin-bottom: 10px;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.28);
  position: relative;
  overflow: hidden;
}
.metric-card::before {
  content: "";
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(103, 232, 249, 0.55), transparent);
}
.metric-label {
  color: var(--fr-muted);
  font-size: 0.7rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-weight: 700;
}
.metric-value {
  color: var(--fr-title);
  font-size: 1.4rem;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  margin-top: 0.25rem;
}

/* Controls */
div[data-testid="stRadio"] label { color: var(--fr-text) !important; }
.stTextInput input, .stNumberInput input,
.stSelectbox div[data-baseweb="select"] > div,
.stMultiSelect div[data-baseweb="select"] > div,
textarea {
  background-color: #070E1C !important;
  color: var(--fr-title) !important;
  border: 1px solid rgba(45, 212, 191, 0.22) !important;
  border-radius: 10px !important;
  box-shadow: inset 0 0 0 1px rgba(45, 212, 191, 0.04);
}
.stSlider [data-baseweb="slider"] div[role="slider"] {
  background-color: var(--fr-accent) !important;
  box-shadow: 0 0 12px rgba(45, 212, 191, 0.55);
}

.stButton > button {
  border-radius: 11px !important;
  border: 1px solid rgba(45, 212, 191, 0.28) !important;
  background: linear-gradient(180deg, #152038 0%, #0C1426 100%) !important;
  color: var(--fr-title) !important;
  font-weight: 700 !important;
  letter-spacing: 0.02em !important;
  transition: all 0.18s ease !important;
}
.stButton > button:hover {
  border-color: var(--fr-accent-hot) !important;
  box-shadow: 0 0 0 1px rgba(45, 212, 191, 0.35), 0 8px 24px rgba(34, 211, 238, 0.15) !important;
  transform: translateY(-1px);
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
  background: linear-gradient(135deg, #22D3EE 0%, #2DD4BF 48%, #14B8A6 100%) !important;
  border-color: #67E8F9 !important;
  color: #042F2E !important;
  box-shadow: 0 0 22px rgba(45, 212, 191, 0.35) !important;
}
.stDownloadButton > button {
  border-radius: 11px !important;
  border: 1px solid rgba(34, 211, 238, 0.4) !important;
  background: linear-gradient(180deg, #0E3A46 0%, #082430 100%) !important;
  color: #CFFAFE !important;
  font-weight: 700 !important;
}

.stTabs [data-baseweb="tab-list"] {
  gap: 0.4rem;
  border-bottom: 1px solid var(--fr-line);
}
.stTabs [data-baseweb="tab"] {
  background: transparent;
  color: var(--fr-muted);
  border-radius: 10px 10px 0 0;
  font-weight: 600;
}
.stTabs [aria-selected="true"] {
  background: rgba(45, 212, 191, 0.1) !important;
  color: var(--fr-accent-hot) !important;
  box-shadow: inset 0 -2px 0 var(--fr-accent);
}
[data-testid="stExpander"] {
  background: var(--fr-panel);
  border: 1px solid var(--fr-line);
  border-radius: 14px;
  backdrop-filter: blur(10px);
}
div[data-testid="stAlert"] {
  border-radius: 14px;
  border: 1px solid var(--fr-line);
  background: rgba(10, 16, 32, 0.85) !important;
  backdrop-filter: blur(8px);
}

[data-testid="stDataFrame"], [data-testid="stTable"] {
  border: 1px solid var(--fr-line);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
}
[data-testid="stMetric"] {
  background: linear-gradient(165deg, rgba(16, 26, 46, 0.95) 0%, rgba(10, 16, 32, 0.95) 100%);
  border: 1px solid var(--fr-line);
  border-radius: 16px;
  padding: 0.9rem 1rem;
  box-shadow: var(--fr-glow);
}
[data-testid="stMetricLabel"] {
  color: var(--fr-muted) !important;
  text-transform: uppercase;
  letter-spacing: 0.08em !important;
  font-size: 0.72rem !important;
}
[data-testid="stMetricValue"] {
  color: var(--fr-title) !important;
  font-family: 'JetBrains Mono', monospace !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
  border: 1px solid var(--fr-line) !important;
  border-radius: 16px !important;
  background: rgba(10, 16, 32, 0.55) !important;
}

/* Keep Leaflet / Folium embeds visible above themed backgrounds */
iframe {
  position: relative !important;
  z-index: 3 !important;
  background: #030712 !important;
  border: 1px solid rgba(45, 212, 191, 0.22) !important;
  border-radius: 14px !important;
}
div[data-testid="stElementToolbar"],
div[data-testid="stCustomComponentV1"] {
  position: relative !important;
  z-index: 3 !important;
}

hr { border-color: var(--fr-line) !important; }
footer { visibility: hidden; }

@media (max-width: 768px) {
  .fr-hero { padding: 1.1rem; }
  .fr-hero-title { font-size: 1.75rem; }
}
</style>
"""


def inject_theme():
    import streamlit as st
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def render_hero(algorithm_colors, algorithm_short, algorithms):
    import streamlit as st
    pills = ''.join(
        f'<span class="fr-algo-pill"><span class="fr-swatch" style="background:{algorithm_colors[name]};color:{algorithm_colors[name]}"></span>'
        f'{algorithm_short[name]}</span>'
        for name in algorithms
    )
    st.markdown(
        f"""
        <div class="fr-hero">
          <div class="fr-hero-top">
            <div class="fr-brand-row">
              <div class="fr-mark">FR</div>
              <div>
                <div class="fr-hero-kicker">Enterprise routing lab · CPS 3440</div>
                <div class="fr-hero-title">FastRoute</div>
              </div>
            </div>
            <div class="fr-status-cluster">
              <span class="fr-chip fr-chip-live"><span class="fr-dot"></span>System online</span>
              <span class="fr-chip">OSM graph</span>
              <span class="fr-chip">3 solvers</span>
              <span class="fr-chip">Bad→Best tiers</span>
            </div>
          </div>
          <p class="fr-hero-sub">
            Command-console for delivery-route algorithm engineering on live OpenStreetMap networks —
            Dijkstra, A*, and Brute-Force order search with measured benchmarks and optimization ladders.
          </p>
          <div class="fr-pill-row">{pills}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
