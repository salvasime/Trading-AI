import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import requests
from datetime import datetime, timedelta
import anthropic
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Investment Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── STYLES ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

:root {
    --bg: #0A0E1A;
    --surface: #111827;
    --surface2: #1C2333;
    --border: #2A3347;
    --accent: #3B82F6;
    --accent2: #10B981;
    --warn: #F59E0B;
    --danger: #EF4444;
    --text: #E2E8F0;
    --muted: #64748B;
    --buy: #10B981;
    --watch: #F59E0B;
    --sell: #EF4444;
}

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
    color: var(--text);
}

.stApp { background: var(--bg); }
.main .block-container { padding: 1.5rem 2rem; max-width: 1600px; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

/* Cards */
.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}
.card-header {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.5rem;
}
.card-value {
    font-size: 1.8rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    color: var(--text);
}
.card-delta {
    font-size: 0.85rem;
    font-family: 'JetBrains Mono', monospace;
    margin-top: 0.25rem;
}
.delta-up { color: var(--buy); }
.delta-down { color: var(--danger); }

/* Section titles */
.section-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.02em;
    margin: 1.5rem 0 1rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
}

/* Watchlist badges */
.badge-buy { background: rgba(16,185,129,0.15); color: #10B981; border: 1px solid rgba(16,185,129,0.3); padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
.badge-watch { background: rgba(245,158,11,0.15); color: #F59E0B; border: 1px solid rgba(245,158,11,0.3); padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
.badge-sell { background: rgba(239,68,68,0.15); color: #EF4444; border: 1px solid rgba(239,68,68,0.3); padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }

/* AI analysis box */
.ai-box {
    background: linear-gradient(135deg, #0F172A 0%, #1E1B4B 100%);
    border: 1px solid #3730A3;
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1rem 0;
    line-height: 1.7;
}

/* Tables */
.stDataFrame { background: var(--surface) !important; }
[data-testid="stTable"] { background: var(--surface); }

/* Buttons */
.stButton > button {
    background: var(--accent);
    color: white;
    border: none;
    border-radius: 8px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    font-size: 0.85rem;
    padding: 0.5rem 1.2rem;
    transition: all 0.2s;
}
.stButton > button:hover { background: #2563EB; transform: translateY(-1px); }

/* Inputs */
.stTextInput input, .stNumberInput input, .stSelectbox select {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 8px !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: var(--surface);
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
    border: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: var(--muted);
    border-radius: 8px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: var(--accent) !important;
    color: white !important;
}

/* Metric delta override */
[data-testid="metric-container"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem;
}

/* Hide streamlit branding */
#MainMenu, footer, header { visibility: hidden; }
.viewerBadge_container__1QSob { display: none; }
</style>
""", unsafe_allow_html=True)

# ── DATA PERSISTENCE ──────────────────────────────────────────────────────────
DATA_FILE = Path("data/portfolio.json")
DATA_FILE.parent.mkdir(exist_ok=True)

DEFAULT_DATA = {
    "portfolio": [
        {"nome": "Leonardo", "ticker": "LDO.MI", "valuta": "EUR", "prezzo_carico": 20.640, "quantita": 33, "categoria": "Azioni"},
        {"nome": "Ipsos", "ticker": "IPS.PA", "valuta": "EUR", "prezzo_carico": 46.053, "quantita": 30, "categoria": "Azioni"},
        {"nome": "Trigano", "ticker": "TRI.PA", "valuta": "EUR", "prezzo_carico": 106.19, "quantita": 5, "categoria": "Azioni"},
        {"nome": "Pinduoduo (PDD)", "ticker": "PDD", "valuta": "USD", "prezzo_carico": 100.377, "quantita": 7, "categoria": "Azioni"},
        {"nome": "Global Ship Lease", "ticker": "GSL", "valuta": "USD", "prezzo_carico": 19.140, "quantita": 36, "categoria": "Azioni"},
        {"nome": "Cal-Maine Foods", "ticker": "CALM", "valuta": "USD", "prezzo_carico": 93.73, "quantita": 16, "categoria": "Azioni"},
        {"nome": "Zealand Pharma", "ticker": "ZEAL.CO", "valuta": "DKK", "prezzo_carico": 421.95, "quantita": 22, "categoria": "Azioni"},
        {"nome": "Adobe", "ticker": "ADBE", "valuta": "USD", "prezzo_carico": 272.47, "quantita": 4, "categoria": "Azioni"},
        {"nome": "BSKT/BARC 2028", "ticker": "N/A", "valuta": "EUR", "prezzo_carico": 97.09, "quantita": 14, "categoria": "Certificati"},
        {"nome": "Von Expe 2027", "ticker": "N/A", "valuta": "EUR", "prezzo_carico": 980.84, "quantita": 2, "categoria": "Certificati"},
        {"nome": "Von Expe 2029", "ticker": "N/A", "valuta": "EUR", "prezzo_carico": 99.10, "quantita": 14, "categoria": "Certificati"},
        {"nome": "BTP 4.00% 2037", "ticker": "N/A", "valuta": "EUR", "prezzo_carico": 98.097, "quantita": 7000, "categoria": "Obbligazioni"},
        {"nome": "BTP 4.45% 2043", "ticker": "N/A", "valuta": "EUR", "prezzo_carico": 100.140, "quantita": 6000, "categoria": "Obbligazioni"},
        {"nome": "BTP 4.50% 2053", "ticker": "N/A", "valuta": "EUR", "prezzo_carico": 100.020, "quantita": 6000, "categoria": "Obbligazioni"},
        {"nome": "BTP 4.15% 2039", "ticker": "N/A", "valuta": "EUR", "prezzo_carico": 98.409, "quantita": 6000, "categoria": "Obbligazioni"},
        {"nome": "Romania 5.25% 2032", "ticker": "N/A", "valuta": "EUR", "prezzo_carico": 99.94, "quantita": 1000, "categoria": "Obbligazioni"},
        {"nome": "USA T-Bond 4.00% 2030", "ticker": "N/A", "valuta": "USD", "prezzo_carico": 98.71, "quantita": 6000, "categoria": "Obbligazioni"},
        {"nome": "Barclays 30GE45 100C", "ticker": "N/A", "valuta": "GBP", "prezzo_carico": 97.30, "quantita": 1000, "categoria": "Obbligazioni"},
        {"nome": "CSIF MSCI USA Small Cap ESG", "ticker": "CUSS.SW", "valuta": "EUR", "prezzo_carico": 156.660, "quantita": 14, "categoria": "ETF"},
        {"nome": "Lyxor MSCI Emerging Markets", "ticker": "LEM.PA", "valuta": "EUR", "prezzo_carico": 13.183, "quantita": 115, "categoria": "ETF"},
        {"nome": "iShares MSCI World Value Factor", "ticker": "IWVL.AS", "valuta": "EUR", "prezzo_carico": 42.429, "quantita": 36, "categoria": "ETF"},
        {"nome": "iShares MSCI India", "ticker": "NDIA.L", "valuta": "EUR", "prezzo_carico": 8.594, "quantita": 176, "categoria": "ETF"},
        {"nome": "Xtrackers World Consumer Staples", "ticker": "XCS6.DE", "valuta": "EUR", "prezzo_carico": 43.306, "quantita": 45, "categoria": "ETF"},
        {"nome": "Xtrackers Healthcare", "ticker": "XDWH.DE", "valuta": "EUR", "prezzo_carico": 47.717, "quantita": 38, "categoria": "ETF"},
        {"nome": "Xtrackers II Global Gov. Bond", "ticker": "XGSG.DE", "valuta": "EUR", "prezzo_carico": 221.001, "quantita": 18, "categoria": "ETF"},
        {"nome": "iShares Core MSCI World", "ticker": "SWDA.MI", "valuta": "EUR", "prezzo_carico": 82.363, "quantita": 53, "categoria": "ETF"},
        {"nome": "Ethereum (ETH)", "ticker": "ETH-EUR", "valuta": "USD", "prezzo_carico": 3099.44, "quantita": 0.48, "categoria": "Crypto"},
        {"nome": "Bitcoin (BTC)", "ticker": "BTC-EUR", "valuta": "USD", "prezzo_carico": 56403.66, "quantita": 0.26, "categoria": "Crypto"},
        {"nome": "Ripple (XRP)", "ticker": "XRP-EUR", "valuta": "USD", "prezzo_carico": 2.35, "quantita": 638.87, "categoria": "Crypto"},
        {"nome": "Oro (Gold ETC)", "ticker": "PHAU.MI", "valuta": "EUR", "prezzo_carico": 1580.000, "quantita": 0.47, "categoria": "Materie Prime"},
        {"nome": "WisdomTree Copper", "ticker": "COPA.MI", "valuta": "EUR", "prezzo_carico": 38.070, "quantita": 27, "categoria": "Materie Prime"},
        {"nome": "WisdomTree Physical Gold", "ticker": "PHGP.MI", "valuta": "EUR", "prezzo_carico": 173.300, "quantita": 21, "categoria": "Materie Prime"},
    ],
    "watchlist": [
        {"ticker": "NVDA", "nome": "NVIDIA", "categoria": "Azioni", "segnale": "COMPRA", "prezzo_target": 850.0, "stop_loss": 750.0, "orizzonte": "Lungo", "note": "Leader AI, correzione attesa come opportunità di ingresso"},
        {"ticker": "GLD", "nome": "SPDR Gold Shares ETF", "categoria": "ETF", "segnale": "MONITORA", "prezzo_target": 220.0, "stop_loss": 190.0, "orizzonte": "Medio", "note": "Copertura inflazione, aspetto conferma breakout"},
        {"ticker": "TSLA", "nome": "Tesla", "categoria": "Azioni", "segnale": "VENDI", "prezzo_target": 180.0, "stop_loss": 220.0, "orizzonte": "Breve", "note": "Fondamentali deteriorati, ridurre esposizione EV"},
    ]
}

def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return DEFAULT_DATA.copy()

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if "data" not in st.session_state:
    st.session_state.data = load_data()

# ── HELPERS ───────────────────────────────────────────────────────────────────
CATEGORY_COLORS = {
    "Azioni": "#3B82F6",
    "ETF": "#10B981",
    "Obbligazioni": "#F59E0B",
    "Crypto": "#8B5CF6",
    "Certificati": "#06B6D4",
    "Materie Prime": "#F97316",
}

@st.cache_data(ttl=300)
def get_fx_rates():
    """Scarica tassi di cambio verso EUR in tempo reale"""
    pairs = {
        "USD": "EURUSD=X",   # quanti USD per 1 EUR
        "GBP": "EURGBP=X",   # quanti GBP per 1 EUR
        "DKK": "EURDKK=X",   # quanti DKK per 1 EUR
        "CHF": "EURCHF=X",
    }
    rates = {"EUR": 1.0}
    for currency, ticker in pairs.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            if not hist.empty:
                rates[currency] = float(hist["Close"].iloc[-1])
        except:
            # fallback approssimato se Yahoo non risponde
            fallback = {"USD": 1.08, "GBP": 0.85, "DKK": 7.46, "CHF": 0.95}
            rates[currency] = fallback.get(currency, 1.0)
    return rates

def convert_to_eur(amount, currency, fx_rates):
    """Converte un importo in valuta locale verso EUR"""
    if currency == "EUR":
        return amount
    rate = fx_rates.get(currency, 1.0)
    # rate = unità di valuta per 1 EUR (es. DKK: 7.46 DKK = 1 EUR)
    return amount / rate

@st.cache_data(ttl=300)
def get_price(ticker):
    if ticker == "N/A":
        return None
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="2d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except:
        pass
    return None

@st.cache_data(ttl=300)
def get_market_data():
    tickers = {"VIX": "^VIX", "S&P 500": "^GSPC", "FTSE MIB": "FTSEMIB.MI",
               "Nasdaq": "^IXIC", "EUR/USD": "EURUSD=X", "Oro": "GC=F"}
    result = {}
    for name, ticker in tickers.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if len(hist) >= 2:
                curr = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                result[name] = {"value": curr, "delta": (curr - prev) / prev * 100}
            elif len(hist) == 1:
                result[name] = {"value": float(hist["Close"].iloc[-1]), "delta": 0}
        except:
            result[name] = {"value": 0, "delta": 0}
    return result

@st.cache_data(ttl=3600)
def get_news(api_key, query="economy inflation market stocks", days=2):
    if not api_key:
        return []
    try:
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        url = f"https://newsapi.org/v2/everything?q={query}&from={from_date}&sortBy=relevancy&language=en&pageSize=20&apiKey={api_key}"
        r = requests.get(url, timeout=10)
        articles = r.json().get("articles", [])
        return [{"title": a["title"], "description": a.get("description",""), "source": a["source"]["name"], "url": a["url"]} for a in articles[:15]]
    except:
        return []

def build_portfolio_df():
    fx = get_fx_rates()
    rows = []
    for item in st.session_state.data["portfolio"]:
        categoria = item["categoria"]
        valuta = item["valuta"]
        prezzo_carico = item["prezzo_carico"]
        quantita = item["quantita"]

        # ── Prezzo attuale ──────────────────────────────────────────────────
        # Usa prezzo manuale se presente, altrimenti scarica da Yahoo
        prezzo_manuale = item.get("prezzo_manuale")
        if prezzo_manuale and prezzo_manuale > 0:
            price_locale = prezzo_manuale
            price_source = "manuale"
        elif item["ticker"] != "N/A":
            price_locale = get_price(item["ticker"])
            price_source = "live"
            if price_locale is None:
                price_locale = prezzo_carico
                price_source = "carico"
        else:
            price_locale = prezzo_carico
            price_source = "carico"

        # ── Controvalore in EUR ─────────────────────────────────────────────
        # Obbligazioni: prezzo in % del nominale (es. 98.5 = 98.5% di quantita nominale)
        if categoria == "Obbligazioni":
            controvalore_locale = (price_locale / 100) * quantita
            carico_locale = (prezzo_carico / 100) * quantita
        else:
            controvalore_locale = price_locale * quantita
            carico_locale = prezzo_carico * quantita

        # Converti tutto in EUR
        controvalore_eur = convert_to_eur(controvalore_locale, valuta, fx)
        carico_eur = convert_to_eur(carico_locale, valuta, fx)

        pnl_eur = controvalore_eur - carico_eur
        pnl_pct = (pnl_eur / carico_eur * 100) if carico_eur > 0 else 0

        rows.append({
            "Nome": item["nome"],
            "Ticker": item["ticker"],
            "Categoria": categoria,
            "Valuta": valuta,
            "P.Carico": prezzo_carico,
            "P.Attuale": price_locale,
            "Fonte": price_source,
            "Quantità": quantita,
            "Controvalore €": controvalore_eur,
            "P&L €": pnl_eur,
            "P&L %": pnl_pct,
        })
    return pd.DataFrame(rows)

def call_claude(prompt, api_key):
    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text
    except Exception as e:
        return f"Errore API: {str(e)}"

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configurazione")
    anthropic_key = st.text_input("🔑 Chiave Anthropic API", type="password", placeholder="sk-ant-...")
    news_api_key = st.text_input("📰 Chiave NewsAPI", type="password", placeholder="newsapi key...")
    st.markdown("---")
    st.markdown("### 📅 Info")
    st.markdown(f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    assets_count = len(st.session_state.data["portfolio"])
    watch_count = len(st.session_state.data["watchlist"])
    st.markdown(f"**Asset in portafoglio:** {assets_count}")
    st.markdown(f"**Titoli in watchlist:** {watch_count}")
    st.markdown("---")
    st.markdown("### 🔄 Aggiornamento")
    if st.button("🔄 Aggiorna prezzi", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex; align-items:center; gap:12px; margin-bottom:1.5rem;">
    <div style="font-size:2rem;">📈</div>
    <div>
        <div style="font-size:1.6rem; font-weight:700; letter-spacing:-0.03em; color:#E2E8F0;">Investment Intelligence</div>
        <div style="font-size:0.8rem; color:#64748B; font-family:'JetBrains Mono',monospace;">Dashboard AI — Portafoglio Personale</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── TECHNICAL ANALYSIS ───────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_technical_data(ticker):
    """Scarica 200 giorni di storia e calcola indicatori tecnici"""
    if ticker == "N/A":
        return None
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1y")
        if len(hist) < 30:
            return None
        close = hist["Close"]
        # Moving averages
        ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else None
        ma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None
        price = float(close.iloc[-1])
        # RSI
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss
        rsi = float((100 - 100 / (1 + rs)).iloc[-1])
        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9).mean()
        macd_val = float(macd_line.iloc[-1])
        macd_sig = float(signal_line.iloc[-1])
        macd_hist = macd_val - macd_sig
        # Support / Resistance (20-day high/low)
        support = float(close.rolling(20).min().iloc[-1])
        resistance = float(close.rolling(20).max().iloc[-1])
        # Golden/Death cross
        cross = None
        if ma50 and ma200:
            prev_ma50 = close.rolling(50).mean().iloc[-2]
            prev_ma200 = close.rolling(200).mean().iloc[-2]
            if prev_ma50 < prev_ma200 and ma50 >= ma200:
                cross = "golden"
            elif prev_ma50 > prev_ma200 and ma50 <= ma200:
                cross = "death"
        return {
            "price": price,
            "ma50": float(ma50) if ma50 else None,
            "ma200": float(ma200) if ma200 else None,
            "rsi": rsi,
            "macd": macd_val,
            "macd_signal": macd_sig,
            "macd_hist": macd_hist,
            "support": support,
            "resistance": resistance,
            "cross": cross,
            "history": hist,
        }
    except:
        return None

def get_technical_signal(td):
    """Genera semaforo basato su indicatori tecnici"""
    if not td:
        return "⚪", "N/D", "Dati tecnici non disponibili (inserisci prezzo manuale)"
    score = 0
    reasons = []
    # MA signals
    if td["ma50"] and td["price"] > td["ma50"]:
        score += 1
        reasons.append("sopra MA50 ✓")
    elif td["ma50"]:
        score -= 1
        reasons.append("sotto MA50 ✗")
    if td["ma200"] and td["price"] > td["ma200"]:
        score += 2
        reasons.append("sopra MA200 ✓")
    elif td["ma200"]:
        score -= 2
        reasons.append("sotto MA200 ✗")
    # Cross
    if td["cross"] == "golden":
        score += 2
        reasons.append("GOLDEN CROSS 🌟")
    elif td["cross"] == "death":
        score -= 2
        reasons.append("DEATH CROSS ⚠️")
    # RSI
    rsi = td["rsi"]
    if rsi > 70:
        score -= 1
        reasons.append(f"RSI {rsi:.0f} ipercomprato")
    elif rsi < 30:
        score += 1
        reasons.append(f"RSI {rsi:.0f} ipervenduto (opportunità)")
    else:
        reasons.append(f"RSI {rsi:.0f} neutro")
    # MACD
    if td["macd_hist"] > 0:
        score += 1
        reasons.append("MACD positivo ↑")
    else:
        score -= 1
        reasons.append("MACD negativo ↓")
    # Semaforo
    if score >= 2:
        return "🟢", "TIENI / INCREMENTA", " | ".join(reasons[:3])
    elif score >= 0:
        return "🟡", "ATTENZIONE", " | ".join(reasons[:3])
    else:
        return "🔴", "ALLEGGERISCI / ESCI", " | ".join(reasons[:3])

@st.cache_data(ttl=3600)
def get_correlation_matrix(tickers_valid):
    """Calcola matrice di correlazione tra asset con ticker validi"""
    try:
        data = {}
        for name, ticker in tickers_valid:
            t = yf.Ticker(ticker)
            hist = t.history(period="6mo")
            if not hist.empty:
                data[name[:15]] = hist["Close"].pct_change()
        if len(data) < 2:
            return None
        df_corr = pd.DataFrame(data).dropna()
        return df_corr.corr()
    except:
        return None

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🌍 Mercati",
    "💼 Portafoglio",
    "📡 Tecnica & Rischio",
    "👁️ Watchlist",
    "🤖 Analisi AI",
    "✏️ Gestione"
])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — MERCATI
# ════════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-title">📊 Panoramica Mercati</div>', unsafe_allow_html=True)
    market = get_market_data()

    cols = st.columns(6)
    for i, (name, d) in enumerate(market.items()):
        with cols[i]:
            delta_color = "delta-up" if d["delta"] >= 0 else "delta-down"
            delta_sign = "▲" if d["delta"] >= 0 else "▼"
            vix_alert = " ⚠️" if name == "VIX" and d["value"] > 25 else ""
            st.markdown(f"""
            <div class="card" style="text-align:center;">
                <div class="card-header">{name}{vix_alert}</div>
                <div class="card-value" style="font-size:1.4rem;">{d['value']:,.2f}</div>
                <div class="card-delta {delta_color}">{delta_sign} {abs(d['delta']):.2f}%</div>
            </div>
            """, unsafe_allow_html=True)

    # VIX gauge
    st.markdown('<div class="section-title">🌡️ Indice di Paura (VIX)</div>', unsafe_allow_html=True)
    vix_val = market.get("VIX", {}).get("value", 20)
    col_vix, col_desc = st.columns([1, 2])
    with col_vix:
        fig_vix = go.Figure(go.Indicator(
            mode="gauge+number",
            value=vix_val,
            title={"text": "VIX", "font": {"color": "#E2E8F0", "family": "Space Grotesk"}},
            gauge={
                "axis": {"range": [0, 80], "tickcolor": "#64748B"},
                "bar": {"color": "#3B82F6"},
                "steps": [
                    {"range": [0, 15], "color": "rgba(16,185,129,0.3)"},
                    {"range": [15, 25], "color": "rgba(245,158,11,0.3)"},
                    {"range": [25, 80], "color": "rgba(239,68,68,0.3)"},
                ],
                "threshold": {"line": {"color": "white", "width": 2}, "value": vix_val}
            },
            number={"font": {"color": "#E2E8F0", "family": "JetBrains Mono"}}
        ))
        fig_vix.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E2E8F0",
            height=220, margin=dict(t=30, b=10, l=20, r=20)
        )
        st.plotly_chart(fig_vix, use_container_width=True)

    with col_desc:
        if vix_val < 15:
            vix_status = ("🟢 Mercato Calmo", "Bassa volatilità. Buone condizioni per investire. Attenzione alla complacency.", "#10B981")
        elif vix_val < 25:
            vix_status = ("🟡 Volatilità Moderata", "Condizioni normali. Monitorare le posizioni a rischio.", "#F59E0B")
        elif vix_val < 35:
            vix_status = ("🟠 Alta Volatilità", "Mercato nervoso. Ridurre esposizione, rafforzare hedging.", "#F97316")
        else:
            vix_status = ("🔴 Fear & Panic", "Massima paura. Potenziale opportunità contrarian per i coraggiosi.", "#EF4444")
        
        title, desc, color = vix_status
        st.markdown(f"""
        <div style="background:{color}22; border:1px solid {color}44; border-radius:12px; padding:1.5rem; margin-top:1rem;">
            <div style="font-size:1.1rem; font-weight:700; color:{color}; margin-bottom:0.5rem;">{title}</div>
            <div style="color:#CBD5E1; line-height:1.6;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

    # Indice charts
    st.markdown('<div class="section-title">📈 Andamento Indici (1 Mese)</div>', unsafe_allow_html=True)
    indices = {"S&P 500": "^GSPC", "Nasdaq": "^IXIC", "FTSE MIB": "FTSEMIB.MI"}
    
    @st.cache_data(ttl=300)
    def get_index_history():
        dfs = {}
        for name, ticker in indices.items():
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="1mo")
                if not hist.empty:
                    dfs[name] = hist["Close"]
            except:
                pass
        return dfs

    idx_data = get_index_history()
    if idx_data:
        fig_idx = go.Figure()
        colors_idx = ["#3B82F6", "#10B981", "#F59E0B"]
        for i, (name, series) in enumerate(idx_data.items()):
            norm = (series / series.iloc[0] - 1) * 100
            fig_idx.add_trace(go.Scatter(
                x=series.index, y=norm, name=name,
                line=dict(color=colors_idx[i], width=2),
                hovertemplate=f"{name}: %{{y:.2f}}%<extra></extra>"
            ))
        fig_idx.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(17,24,39,0.5)",
            font_color="#E2E8F0",
            xaxis=dict(gridcolor="#1C2333", color="#64748B"),
            yaxis=dict(gridcolor="#1C2333", color="#64748B", ticksuffix="%"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            height=300, margin=dict(t=10, b=10)
        )
        st.plotly_chart(fig_idx, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — PORTAFOGLIO
# ════════════════════════════════════════════════════════════════════════════════
with tab2:
    df = build_portfolio_df()
    fx_rates = get_fx_rates()
    total = df["Controvalore €"].sum()
    total_pnl = df["P&L €"].sum()
    total_pnl_pct = (total_pnl / (total - total_pnl) * 100) if (total - total_pnl) > 0 else 0

    # FX rates info bar
    st.markdown(f"""
    <div style="background:#1C2333;border:1px solid #2A3347;border-radius:8px;padding:0.6rem 1rem;margin-bottom:1rem;font-size:0.8rem;color:#64748B;display:flex;gap:2rem;">
        <span>💱 Cambi live:</span>
        <span>USD/EUR: <b style="color:#E2E8F0;">{fx_rates.get('USD',1.08):.4f}</b></span>
        <span>GBP/EUR: <b style="color:#E2E8F0;">{fx_rates.get('GBP',0.85):.4f}</b></span>
        <span>DKK/EUR: <b style="color:#E2E8F0;">{fx_rates.get('DKK',7.46):.4f}</b></span>
        <span style="color:#F59E0B;">Tutti i valori convertiti in EUR</span>
    </div>
    """, unsafe_allow_html=True)

    # KPI row
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("💼 Totale Portafoglio (EUR)", f"€ {total:,.0f}")
    with k2:
        st.metric("📈 P&L Totale", f"€ {total_pnl:,.0f}", f"{total_pnl_pct:+.2f}%")
    with k3:
        best = df.nlargest(1, "P&L %").iloc[0]
        st.metric("🏆 Best Performer", best["Nome"][:20], f"{best['P&L %']:+.1f}%")
    with k4:
        worst = df.nsmallest(1, "P&L %").iloc[0]
        st.metric("⚠️ Worst Performer", worst["Nome"][:20], f"{worst['P&L %']:+.1f}%")

    # Charts row
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-title">🥧 Allocazione per Categoria</div>', unsafe_allow_html=True)
        alloc = df.groupby("Categoria")["Controvalore €"].sum().reset_index()
        alloc.columns = ["Categoria", "Valore"]
        fig_pie = go.Figure(go.Pie(
            labels=alloc["Categoria"],
            values=alloc["Valore"],
            hole=0.55,
            marker_colors=[CATEGORY_COLORS.get(c, "#64748B") for c in alloc["Categoria"]],
            textfont_color="white",
            hovertemplate="%{label}<br>€ %{value:,.0f}<br>%{percent}<extra></extra>"
        ))
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#E2E8F0",
            showlegend=True,
            legend=dict(bgcolor="rgba(0,0,0,0)", font_size=11),
            height=320, margin=dict(t=10, b=10)
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        st.markdown('<div class="section-title">📊 P&L per Asset</div>', unsafe_allow_html=True)
        df_sorted = df.sort_values("P&L €")
        colors_bar = ["#EF4444" if x < 0 else "#10B981" for x in df_sorted["P&L €"]]
        fig_bar = go.Figure(go.Bar(
            x=df_sorted["P&L €"],
            y=df_sorted["Nome"].str[:20],
            orientation="h",
            marker_color=colors_bar,
            hovertemplate="%{y}<br>P&L: € %{x:,.0f}<extra></extra>"
        ))
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(17,24,39,0.5)",
            font_color="#E2E8F0",
            xaxis=dict(gridcolor="#1C2333", tickprefix="€"),
            yaxis=dict(gridcolor="#1C2333", tickfont_size=10),
            height=320, margin=dict(t=10, b=10, l=10)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # Valuta exposure
    st.markdown('<div class="section-title">💱 Esposizione Valutaria (convertita in EUR)</div>', unsafe_allow_html=True)
    val_exp = df.groupby("Valuta")["Controvalore €"].sum()
    val_cols = st.columns(len(val_exp))
    val_colors = {"EUR": "#10B981", "USD": "#3B82F6", "GBP": "#F59E0B", "DKK": "#8B5CF6"}
    for i, (val, amt) in enumerate(val_exp.items()):
        pct = amt / total * 100
        with val_cols[i]:
            c = val_colors.get(val, "#64748B")
            st.markdown(f"""
            <div style="background:{c}18; border:1px solid {c}44; border-radius:10px; padding:1rem; text-align:center;">
                <div style="font-size:1.5rem; font-weight:700; color:{c}; font-family:'JetBrains Mono',monospace;">{val}</div>
                <div style="font-size:1.1rem; font-weight:600; color:#E2E8F0;">€ {amt:,.0f}</div>
                <div style="font-size:0.85rem; color:#64748B;">{pct:.1f}% del portafoglio</div>
            </div>
            """, unsafe_allow_html=True)

    # Portfolio table
    st.markdown('<div class="section-title">📋 Dettaglio Posizioni</div>', unsafe_allow_html=True)
    st.caption("🔵 Fonte = live (Yahoo Finance) | 🟡 Fonte = carico (prezzo live non disponibile) | ✏️ Fonte = manuale")

    display_df = df.copy()
    display_df["Controvalore €"] = display_df["Controvalore €"].apply(lambda x: f"€ {x:,.0f}")
    display_df["P&L €"] = display_df["P&L €"].apply(lambda x: f"€ {x:+,.0f}")
    display_df["P&L %"] = display_df["P&L %"].apply(lambda x: f"{x:+.2f}%")
    display_df["P.Carico"] = display_df["P.Carico"].apply(lambda x: f"{x:,.3f}")
    display_df["P.Attuale"] = display_df["P.Attuale"].apply(lambda x: f"{x:,.3f}")
    display_df["Fonte"] = display_df["Fonte"].map({"live": "🔵 live", "carico": "🟡 carico", "manuale": "✏️ manuale"})

    st.dataframe(
        display_df[["Nome", "Categoria", "Valuta", "P.Carico", "P.Attuale", "Fonte", "Quantità", "Controvalore €", "P&L €", "P&L %"]],
        use_container_width=True,
        hide_index=True,
        height=400
    )

# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — TECNICA & RISCHIO
# ════════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-title">📡 Analisi Tecnica per Posizione</div>', unsafe_allow_html=True)
    st.caption("🟢 Tieni/Incrementa  |  🟡 Attenzione  |  🔴 Alleggerisci/Esci  |  ⚪ Dati non disponibili (inserisci prezzo manuale)")

    df_tech = build_portfolio_df()
    # Only assets with live ticker
    tradeable = [p for p in st.session_state.data["portfolio"] if p["ticker"] != "N/A"]
    non_tradeable = [p for p in st.session_state.data["portfolio"] if p["ticker"] == "N/A"]

    # ── Semaforo table ────────────────────────────────────────────────────────
    rows_tech = []
    with st.spinner("Calcolo indicatori tecnici in corso..."):
        for item in tradeable:
            td = get_technical_data(item["ticker"])
            emoji, label, reason = get_technical_signal(td)
            rsi_str = f"{td['rsi']:.0f}" if td else "—"
            macd_str = f"{td['macd_hist']:+.3f}" if td else "—"
            ma50_str = f"{td['ma50']:,.2f}" if td and td['ma50'] else "—"
            ma200_str = f"{td['ma200']:,.2f}" if td and td['ma200'] else "—"
            cross_str = "🌟 Golden" if td and td['cross']=="golden" else ("💀 Death" if td and td['cross']=="death" else "—")
            rows_tech.append({
                "Segnale": emoji,
                "Nome": item["nome"][:25],
                "Ticker": item["ticker"],
                "Raccomandazione": label,
                "RSI": rsi_str,
                "MACD Hist": macd_str,
                "MA50": ma50_str,
                "MA200": ma200_str,
                "Cross": cross_str,
                "Motivazione": reason,
            })

    df_signals = pd.DataFrame(rows_tech)
    if not df_signals.empty:
        st.dataframe(df_signals, use_container_width=True, hide_index=True, height=420)

    # Non-tradeable notice
    if non_tradeable:
        st.markdown('<div class="section-title">✏️ Asset senza prezzi automatici — Aggiorna manualmente</div>', unsafe_allow_html=True)
        nt_cols = st.columns(3)
        for i, item in enumerate(non_tradeable):
            with nt_cols[i % 3]:
                prezzo_man = item.get("prezzo_manuale", 0) or 0
                st.markdown(f"""
                <div style="background:#1C2333;border:1px solid #2A3347;border-radius:10px;padding:1rem;margin-bottom:0.5rem;">
                    <div style="font-weight:700;color:#E2E8F0;">{item['nome']}</div>
                    <div style="font-size:0.8rem;color:#64748B;margin:0.3rem 0;">{item['categoria']} | {item['valuta']}</div>
                    <div style="font-size:0.85rem;color:#F59E0B;">Prezzo carico: {item['prezzo_carico']:,.3f}</div>
                    <div style="font-size:0.85rem;color:{'#10B981' if prezzo_man > 0 else '#EF4444'};">
                        Prezzo attuale: {'%,.3f' % prezzo_man if prezzo_man > 0 else '⚠️ NON INSERITO'}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        st.info("👆 Aggiorna i prezzi manuali nella tab **✏️ Gestione** → Modifica Esistenti → campo 'Prezzo Attuale Manuale'")

    # ── Dettaglio tecnico singolo titolo ─────────────────────────────────────
    st.markdown('<div class="section-title">🔍 Grafico Tecnico Dettagliato</div>', unsafe_allow_html=True)
    ticker_list = [p["ticker"] for p in tradeable]
    nome_list = [p["nome"] for p in tradeable]
    sel_idx = st.selectbox("Seleziona titolo", range(len(ticker_list)),
                           format_func=lambda i: f"{nome_list[i]} ({ticker_list[i]})", key="sel_tech")
    if sel_idx is not None:
        sel_ticker = ticker_list[sel_idx]
        td = get_technical_data(sel_ticker)
        if td and "history" in td:
            hist = td["history"]
            close = hist["Close"]
            fig_det = go.Figure()
            # Candlestick
            fig_det.add_trace(go.Candlestick(
                x=hist.index, open=hist["Open"], high=hist["High"],
                low=hist["Low"], close=hist["Close"],
                name="Prezzo", increasing_line_color="#10B981", decreasing_line_color="#EF4444"
            ))
            # MA50
            ma50_series = close.rolling(50).mean()
            fig_det.add_trace(go.Scatter(x=hist.index, y=ma50_series, name="MA50",
                line=dict(color="#F59E0B", width=1.5, dash="dot")))
            # MA200
            if len(close) >= 200:
                ma200_series = close.rolling(200).mean()
                fig_det.add_trace(go.Scatter(x=hist.index, y=ma200_series, name="MA200",
                    line=dict(color="#8B5CF6", width=1.5, dash="dash")))
            # Support/Resistance
            fig_det.add_hline(y=td["support"], line_color="#10B981", line_dash="dot",
                annotation_text=f"Support {td['support']:.2f}", annotation_font_color="#10B981")
            fig_det.add_hline(y=td["resistance"], line_color="#EF4444", line_dash="dot",
                annotation_text=f"Resist. {td['resistance']:.2f}", annotation_font_color="#EF4444")
            fig_det.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,24,39,0.8)",
                font_color="#E2E8F0", xaxis_rangeslider_visible=False,
                xaxis=dict(gridcolor="#1C2333"), yaxis=dict(gridcolor="#1C2333"),
                legend=dict(bgcolor="rgba(0,0,0,0)"), height=380, margin=dict(t=10,b=10)
            )
            st.plotly_chart(fig_det, use_container_width=True)

            # RSI subplot
            delta = close.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rsi_series = 100 - 100 / (1 + gain/loss)
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(x=hist.index, y=rsi_series, name="RSI",
                line=dict(color="#3B82F6", width=2), fill="tonexty"))
            fig_rsi.add_hline(y=70, line_color="#EF4444", line_dash="dot", annotation_text="Ipercomprato 70")
            fig_rsi.add_hline(y=30, line_color="#10B981", line_dash="dot", annotation_text="Ipervenduto 30")
            fig_rsi.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,24,39,0.8)",
                font_color="#E2E8F0", xaxis=dict(gridcolor="#1C2333"),
                yaxis=dict(gridcolor="#1C2333", range=[0,100]),
                height=160, margin=dict(t=5,b=10), showlegend=False
            )
            st.plotly_chart(fig_rsi, use_container_width=True)

    # ── Risk Management ───────────────────────────────────────────────────────
    st.markdown('<div class="section-title">⚖️ Risk Management</div>', unsafe_allow_html=True)
    r1, r2 = st.columns(2)

    with r1:
        st.markdown("**Peso % per posizione**")
        df_weight = df_tech[["Nome","Categoria","Controvalore €"]].copy()
        df_weight["Peso %"] = (df_weight["Controvalore €"] / df_weight["Controvalore €"].sum() * 100).round(2)
        df_weight = df_weight.sort_values("Peso %", ascending=False)
        # Bar chart
        fig_w = go.Figure(go.Bar(
            x=df_weight["Nome"].str[:18], y=df_weight["Peso %"],
            marker_color=[CATEGORY_COLORS.get(c,"#64748B") for c in df_weight["Categoria"]],
            hovertemplate="%{x}<br>%{y:.1f}%<extra></extra>"
        ))
        fig_w.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,24,39,0.5)",
            font_color="#E2E8F0", xaxis=dict(tickangle=-45, gridcolor="#1C2333"),
            yaxis=dict(gridcolor="#1C2333", ticksuffix="%"),
            height=300, margin=dict(t=10,b=80)
        )
        st.plotly_chart(fig_w, use_container_width=True)
        # Concentration warning
        top3_pct = df_weight.head(3)["Peso %"].sum()
        if top3_pct > 40:
            st.warning(f"⚠️ Le top 3 posizioni pesano il {top3_pct:.1f}% del portafoglio — concentrazione elevata")

    with r2:
        st.markdown("**Correlazione tra asset (6 mesi)**")
        tickers_valid = [(p["nome"][:12], p["ticker"]) for p in tradeable[:12]]
        corr_matrix = get_correlation_matrix(tuple(tickers_valid))
        if corr_matrix is not None:
            fig_corr = go.Figure(go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.index,
                colorscale=[[0,"#EF4444"],[0.5,"#1C2333"],[1,"#10B981"]],
                zmid=0, zmin=-1, zmax=1,
                text=corr_matrix.round(2).values,
                texttemplate="%{text}",
                hovertemplate="%{x} / %{y}<br>Corr: %{z:.2f}<extra></extra>"
            ))
            fig_corr.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#E2E8F0", font_size=9,
                height=300, margin=dict(t=10,b=10)
            )
            st.plotly_chart(fig_corr, use_container_width=True)
            st.caption("Verde = correlazione positiva (si muovono insieme) | Rosso = negativa (hedging naturale)")
        else:
            st.info("Dati insufficienti per la matrice di correlazione")

    # ── Stagionalità ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">📅 Stagionalità — Pattern Storici</div>', unsafe_allow_html=True)
    month = datetime.now().month
    stagionalita = {
        1: [("Small Cap", "Gennaio Effect: storicamente outperformance delle small cap", "#10B981"),
            ("Azionario USA", "Mercati tendono a salire dopo il rally di Natale", "#10B981")],
        2: [("Oro", "Febbraio storicamente forte per l'oro", "#10B981"),
            ("Crypto", "Spesso volatile dopo i rally di gennaio", "#F59E0B")],
        3: [("Azionario", "Correzioni tipiche a marzo, attenzione ai rimbalzi", "#F59E0B")],
        4: [("Azionario", "'Sell in May' si avvicina, ridurre esposizione growth", "#F59E0B"),
            ("Energia", "Primavera favorevole per materie prime energetiche", "#10B981")],
        5: [("Azionario Growth", "Sell in May — storicamente mese debole", "#EF4444"),
            ("Oro/Obbligazioni", "Fase difensiva, rotazione verso asset sicuri", "#10B981")],
        6: [("Energia", "Estate: domanda petrolio alta (driving season USA)", "#10B981")],
        7: [("Azionario", "Luglio storicamente buono, earnings season Q2", "#10B981")],
        8: [("Volatilità", "Agosto spesso volatile, volumi bassi = movimenti amplificati", "#EF4444"),
            ("Oro", "Agosto/Settembre storicamente forti per l'oro", "#10B981")],
        9: [("Azionario", "Settembre il mese peggiore storicamente per S&P500", "#EF4444"),
            ("Oro", "Stagione forte per metalli preziosi", "#10B981")],
        10: [("Azionario", "Ottobre spesso volatile ma poi rimbalzo (Halloween Effect)", "#F59E0B"),
             ("Crypto", "Q4 storicamente bullish per Bitcoin", "#10B981")],
        11: [("Azionario USA", "Rally di fine anno inizia, Black Friday effect", "#10B981"),
             ("Crypto", "Novembre/Dicembre storicamente forti", "#10B981")],
        12: [("Azionario", "Santa Claus Rally — ultimi giorni dell'anno bullish", "#10B981"),
             ("Small Cap", "Tax-loss harvesting crea opportunità", "#F59E0B")],
    }
    hints = stagionalita.get(month, [])
    if hints:
        h_cols = st.columns(len(hints))
        for i, (asset, desc, color) in enumerate(hints):
            with h_cols[i]:
                st.markdown(f"""
                <div style="background:{color}18;border:1px solid {color}44;border-radius:10px;padding:1rem;">
                    <div style="font-weight:700;color:{color};margin-bottom:0.4rem;">{asset}</div>
                    <div style="font-size:0.82rem;color:#CBD5E1;line-height:1.5;">{desc}</div>
                </div>
                """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — WATCHLIST
# ════════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-title">👁️ La Mia Watchlist</div>', unsafe_allow_html=True)

    # Summary badges
    watchlist = st.session_state.data["watchlist"]
    buy_count = sum(1 for w in watchlist if w["segnale"] == "COMPRA")
    watch_count = sum(1 for w in watchlist if w["segnale"] == "MONITORA")
    sell_count = sum(1 for w in watchlist if w["segnale"] == "VENDI")

    sb1, sb2, sb3 = st.columns(3)
    with sb1:
        st.markdown(f'<div style="background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);border-radius:10px;padding:1rem;text-align:center;"><span style="font-size:1.8rem;font-weight:700;color:#10B981;">{buy_count}</span><div style="color:#64748B;font-size:0.8rem;margin-top:2px;">🟢 DA COMPRARE</div></div>', unsafe_allow_html=True)
    with sb2:
        st.markdown(f'<div style="background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);border-radius:10px;padding:1rem;text-align:center;"><span style="font-size:1.8rem;font-weight:700;color:#F59E0B;">{watch_count}</span><div style="color:#64748B;font-size:0.8rem;margin-top:2px;">🟡 MONITORARE</div></div>', unsafe_allow_html=True)
    with sb3:
        st.markdown(f'<div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:10px;padding:1rem;text-align:center;"><span style="font-size:1.8rem;font-weight:700;color:#EF4444;">{sell_count}</span><div style="color:#64748B;font-size:0.8rem;margin-top:2px;">🔴 DA VENDERE</div></div>', unsafe_allow_html=True)

    st.markdown("")

    # Filter
    filtro = st.radio("Filtra per:", ["Tutti", "🟢 COMPRA", "🟡 MONITORA", "🔴 VENDI"], horizontal=True)
    filtro_map = {"Tutti": None, "🟢 COMPRA": "COMPRA", "🟡 MONITORA": "MONITORA", "🔴 VENDI": "VENDI"}
    filtered = [w for w in watchlist if filtro_map[filtro] is None or w["segnale"] == filtro_map[filtro]]

    # Cards grid
    cols_per_row = 3
    for i in range(0, len(filtered), cols_per_row):
        row_items = filtered[i:i+cols_per_row]
        cols = st.columns(cols_per_row)
        for j, item in enumerate(row_items):
            with cols[j]:
                sig = item["segnale"]
                sig_color = {"COMPRA": "#10B981", "MONITORA": "#F59E0B", "VENDI": "#EF4444"}[sig]
                sig_emoji = {"COMPRA": "🟢", "MONITORA": "🟡", "VENDI": "🔴"}[sig]
                price = get_price(item["ticker"])
                price_str = f"{price:,.2f}" if price else "N/A"

                # Technical signal for watchlist item
                td_w = get_technical_data(item["ticker"]) if item["ticker"] != "N/A" else None
                tech_emoji, tech_label, _ = get_technical_signal(td_w)
                rsi_w = f"RSI {td_w['rsi']:.0f}" if td_w else "—"

                # Distance from target
                if price and item.get("prezzo_target"):
                    dist = (item["prezzo_target"] - price) / price * 100
                    dist_str = f"{dist:+.1f}% al target"
                else:
                    dist_str = ""

                # Opportunity score 1-10
                score_num = 5
                if td_w:
                    if td_w["price"] > (td_w["ma50"] or 0): score_num += 1
                    if td_w["price"] > (td_w["ma200"] or 0): score_num += 1
                    if td_w["rsi"] < 40: score_num += 1
                    if td_w["macd_hist"] > 0: score_num += 1
                    if td_w["rsi"] > 70: score_num -= 2
                    score_num = max(1, min(10, score_num))
                score_color = "#10B981" if score_num >= 7 else ("#F59E0B" if score_num >= 4 else "#EF4444")

                st.markdown(f"""
                <div style="background:#111827;border:1px solid {sig_color}44;border-radius:12px;padding:1.2rem;margin-bottom:0.5rem;border-left:3px solid {sig_color};">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
                        <span style="font-family:'JetBrains Mono',monospace;font-weight:700;color:{sig_color};font-size:1rem;">{item['ticker']}</span>
                        <div style="display:flex;gap:6px;align-items:center;">
                            <span style="background:{score_color}22;color:{score_color};border:1px solid {score_color}44;padding:1px 7px;border-radius:20px;font-size:0.7rem;font-weight:700;">Score {score_num}/10</span>
                            <span style="background:{sig_color}22;color:{sig_color};border:1px solid {sig_color}44;padding:2px 8px;border-radius:20px;font-size:0.7rem;font-weight:700;">{sig_emoji} {sig}</span>
                        </div>
                    </div>
                    <div style="font-size:0.9rem;font-weight:600;color:#E2E8F0;margin-bottom:0.75rem;">{item['nome']}</div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;font-size:0.8rem;">
                        <div><span style="color:#64748B;">Prezzo:</span> <span style="font-family:'JetBrains Mono',monospace;color:#E2E8F0;">{price_str}</span></div>
                        <div><span style="color:#64748B;">Target:</span> <span style="font-family:'JetBrains Mono',monospace;color:{sig_color};">{item.get('prezzo_target','—')}</span></div>
                        <div><span style="color:#64748B;">Stop:</span> <span style="font-family:'JetBrains Mono',monospace;color:#EF4444;">{item.get('stop_loss','—')}</span></div>
                        <div><span style="color:#64748B;">Tecnica:</span> <span>{tech_emoji} {rsi_w}</span></div>
                    </div>
                    {f'<div style="margin-top:0.6rem;font-size:0.75rem;color:#64748B;font-style:italic;">{dist_str}</div>' if dist_str else ''}
                    {f'<div style="margin-top:0.6rem;font-size:0.8rem;color:#94A3B8;border-top:1px solid #1C2333;padding-top:0.5rem;">{item["note"]}</div>' if item.get("note") else ''}
                </div>
                """, unsafe_allow_html=True)

                # Quick delete
                if st.button(f"🗑️ Rimuovi", key=f"del_watch_{i+j}"):
                    idx = st.session_state.data["watchlist"].index(item)
                    st.session_state.data["watchlist"].pop(idx)
                    save_data(st.session_state.data)
                    st.rerun()

    # Add to watchlist
    st.markdown('<div class="section-title">➕ Aggiungi alla Watchlist</div>', unsafe_allow_html=True)
    with st.expander("Aggiungi nuovo titolo alla watchlist", expanded=False):
        wc1, wc2, wc3 = st.columns(3)
        with wc1:
            w_ticker = st.text_input("Ticker (es. AAPL)", key="w_ticker")
            w_nome = st.text_input("Nome asset", key="w_nome")
            w_cat = st.selectbox("Categoria", ["Azioni", "ETF", "Crypto", "Obbligazioni", "Materie Prime"], key="w_cat")
        with wc2:
            w_segnale = st.selectbox("Segnale", ["COMPRA", "MONITORA", "VENDI"], key="w_segnale")
            w_target = st.number_input("Prezzo Target", min_value=0.0, value=0.0, step=0.01, key="w_target")
            w_stop = st.number_input("Stop Loss", min_value=0.0, value=0.0, step=0.01, key="w_stop")
        with wc3:
            w_orizzonte = st.selectbox("Orizzonte", ["Breve (< 3 mesi)", "Medio (3-12 mesi)", "Lungo (> 1 anno)"], key="w_orizzonte")
            w_note = st.text_area("Note / Motivazione", key="w_note", height=100)

        if st.button("➕ Aggiungi alla Watchlist", key="btn_add_watch"):
            if w_ticker and w_nome:
                st.session_state.data["watchlist"].append({
                    "ticker": w_ticker.upper(),
                    "nome": w_nome,
                    "categoria": w_cat,
                    "segnale": w_segnale,
                    "prezzo_target": w_target,
                    "stop_loss": w_stop,
                    "orizzonte": w_orizzonte,
                    "note": w_note
                })
                save_data(st.session_state.data)
                st.success(f"✅ {w_nome} aggiunto alla watchlist!")
                st.rerun()
            else:
                st.error("Inserisci almeno Ticker e Nome")

# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — ANALISI AI
# ════════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown('<div class="section-title">🤖 Analisi AI del Portafoglio</div>', unsafe_allow_html=True)

    if not anthropic_key:
        st.warning("⚠️ Inserisci la tua chiave Anthropic nella sidebar per attivare le analisi AI.")
    else:
        df_ai = build_portfolio_df()
        market_ai = get_market_data()
        watchlist_ai = st.session_state.data["watchlist"]

        portfolio_summary = df_ai.groupby("Categoria").agg(
            Valore=("Controvalore €", "sum"),
            PnL=("P&L €", "sum")
        ).reset_index().to_string()

        watchlist_summary = "\n".join([
            f"- {w['ticker']} ({w['nome']}): {w['segnale']} | Target: {w.get('prezzo_target')} | Stop: {w.get('stop_loss')} | {w.get('note','')}"
            for w in watchlist_ai
        ])

        vix = market_ai.get("VIX", {}).get("value", 20)
        sp500_delta = market_ai.get("S&P 500", {}).get("delta", 0)

        ai_col1, ai_col2 = st.columns(2)

        with ai_col1:
            if st.button("🔍 Analisi Portafoglio + Raccomandazioni", use_container_width=True):
                with st.spinner("Claude sta analizzando il tuo portafoglio..."):
                    prompt = f"""Sei un esperto analista finanziario. Analizza questo portafoglio e fornisci raccomandazioni pratiche.

SITUAZIONE MERCATO:
- VIX: {vix:.1f} ({'alta volatilità' if vix > 25 else 'normale'})
- S&P 500: {sp500_delta:+.2f}% oggi
- EUR/USD: {market_ai.get('EUR/USD',{}).get('value',1.1):.4f}

PORTAFOGLIO PER CATEGORIA (in EUR):
{portfolio_summary}

WATCHLIST PERSONALE:
{watchlist_summary}

Fornisci:
1. **Valutazione generale** del portafoglio (diversificazione, rischio, esposizione valutaria)
2. **3 posizioni da incrementare** con motivazione
3. **3 posizioni da ridurre/uscire** con motivazione  
4. **Asset allocation ottimale** suggerita per il periodo attuale
5. **Integrazione watchlist**: quali titoli della watchlist hanno più senso da eseguire ora e perché

Rispondi in italiano, sii specifico e diretto. Massimo 600 parole."""

                    result = call_claude(prompt, anthropic_key)
                    st.markdown(f'<div class="ai-box">{result}</div>', unsafe_allow_html=True)

        with ai_col2:
            if st.button("💡 Nuove Opportunità di Mercato", use_container_width=True):
                with st.spinner("Claude sta cercando opportunità..."):
                    news_titles = ""
                    if news_api_key:
                        news = get_news(news_api_key)
                        news_titles = "\n".join([f"- {n['title']}" for n in news[:10]])

                    prompt = f"""Sei un analista finanziario esperto. Suggerisci nuove opportunità di investimento concrete.

SITUAZIONE MERCATO:
- VIX: {vix:.1f}
- S&P500: {sp500_delta:+.2f}%

PORTAFOGLIO ATTUALE (categorie):
{portfolio_summary}

NOTIZIE RECENTI:
{news_titles if news_titles else "Notizie non disponibili"}

Suggerisci 5 nuove opportunità di investimento (titoli, ETF, obbligazioni, crypto o materie prime) che si integrano bene con il portafoglio esistente.

Per ognuna fornisci:
- **Ticker** e nome
- **Strategia**: breve o lungo termine
- **Prezzo di ingresso** consigliato
- **Target price** (12 mesi)
- **Stop loss**
- **Motivazione** (2-3 righe)
- **Rischio**: Basso / Medio / Alto

Rispondi in italiano. Sii specifico con i prezzi."""

                    result = call_claude(prompt, anthropic_key)
                    st.markdown(f'<div class="ai-box">{result}</div>', unsafe_allow_html=True)

        st.markdown("---")

        # News section
        st.markdown('<div class="section-title">📰 Radar Notizie Economiche</div>', unsafe_allow_html=True)
        if news_api_key:
            news_items = get_news(news_api_key)
            if news_items:
                if st.button("🌍 Analizza Impatto Notizie sul Portafoglio", use_container_width=False):
                    with st.spinner("Analizzando l'impatto delle notizie..."):
                        news_text = "\n".join([f"- {n['title']}: {n.get('description','')}" for n in news_items[:10]])
                        prompt = f"""Analizza queste notizie recenti e il loro impatto sul portafoglio.

NOTIZIE:
{news_text}

PORTAFOGLIO:
{portfolio_summary}

Per ogni notizia rilevante:
1. Qual è l'impatto sul portafoglio? (positivo/negativo/neutro)
2. Quali posizioni sono più esposte?
3. Azione raccomandata (se necessaria)

Poi dai un sentiment generale: RISK-ON o RISK-OFF per i prossimi 30 giorni con motivazione.
Rispondi in italiano, massimo 400 parole."""
                        result = call_claude(prompt, anthropic_key)
                        st.markdown(f'<div class="ai-box">{result}</div>', unsafe_allow_html=True)

                n_cols = st.columns(3)
                for i, news in enumerate(news_items[:9]):
                    with n_cols[i % 3]:
                        st.markdown(f"""
                        <div style="background:#111827;border:1px solid #1C2333;border-radius:10px;padding:1rem;margin-bottom:0.5rem;height:140px;overflow:hidden;">
                            <div style="font-size:0.75rem;color:#3B82F6;margin-bottom:0.4rem;font-weight:600;">{news['source']}</div>
                            <div style="font-size:0.82rem;color:#E2E8F0;line-height:1.4;font-weight:500;">{news['title'][:100]}{'...' if len(news['title'])>100 else ''}</div>
                            <div style="font-size:0.75rem;color:#64748B;margin-top:0.4rem;">{news.get('description','')[:80]}...</div>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.info("Inserisci la chiave NewsAPI nella sidebar per vedere le notizie.")

# ════════════════════════════════════════════════════════════════════════════════
# TAB 5 — GESTIONE PORTAFOGLIO
# ════════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown('<div class="section-title">✏️ Gestione Portafoglio</div>', unsafe_allow_html=True)

    g_tab1, g_tab2 = st.tabs(["➕ Aggiungi / Modifica Posizione", "📋 Modifica Esistenti"])

    with g_tab1:
        st.markdown("#### Nuova Operazione")
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            g_nome = st.text_input("Nome asset *", placeholder="es. Apple Inc.", key="g_nome")
            g_ticker = st.text_input("Ticker Yahoo Finance *", placeholder="es. AAPL", key="g_ticker")
            g_categoria = st.selectbox("Categoria *", ["Azioni", "ETF", "Obbligazioni", "Crypto", "Certificati", "Materie Prime"], key="g_cat")
        with fc2:
            g_valuta = st.selectbox("Valuta *", ["EUR", "USD", "GBP", "DKK", "CHF"], key="g_valuta")
            g_prezzo = st.number_input("Prezzo medio di carico *", min_value=0.0, value=0.0, step=0.001, format="%.3f", key="g_prezzo")
            g_qty = st.number_input("Quantità *", min_value=0.0, value=0.0, step=0.001, format="%.4f", key="g_qty")
        with fc3:
            g_op = st.radio("Operazione", ["Nuovo acquisto", "Incremento posizione esistente"], key="g_op")
            st.markdown("")
            st.markdown("""
            <div style="background:#1C2333;border-radius:8px;padding:0.75rem;font-size:0.8rem;color:#64748B;">
            <strong style="color:#E2E8F0;">💡 Suggerimento ticker:</strong><br>
            • Azioni IT: LDO.MI, ENI.MI<br>
            • Azioni USA: AAPL, MSFT<br>
            • Crypto: BTC-EUR, ETH-EUR<br>
            • ETF: SWDA.MI, VWCE.DE<br>
            • <a href="https://finance.yahoo.com" target="_blank" style="color:#3B82F6;">Cerca su Yahoo Finance →</a>
            </div>
            """, unsafe_allow_html=True)

        btn_add, btn_clear = st.columns([1, 4])
        with btn_add:
            if st.button("✅ Aggiungi Posizione", key="btn_add_pos"):
                if g_nome and g_ticker and g_prezzo > 0 and g_qty > 0:
                    # Check if incrementing existing
                    existing = next((i for i, p in enumerate(st.session_state.data["portfolio"]) 
                                   if p["ticker"].upper() == g_ticker.upper()), None)
                    if existing is not None and g_op == "Incremento posizione esistente":
                        old = st.session_state.data["portfolio"][existing]
                        old_val = old["prezzo_carico"] * old["quantita"]
                        new_val = g_prezzo * g_qty
                        new_qty = old["quantita"] + g_qty
                        new_prezzo = (old_val + new_val) / new_qty
                        st.session_state.data["portfolio"][existing]["quantita"] = new_qty
                        st.session_state.data["portfolio"][existing]["prezzo_carico"] = new_prezzo
                        save_data(st.session_state.data)
                        st.success(f"✅ Posizione {g_ticker} incrementata! Nuovo prezzo medio: {new_prezzo:.3f}")
                    else:
                        st.session_state.data["portfolio"].append({
                            "nome": g_nome,
                            "ticker": g_ticker.upper(),
                            "valuta": g_valuta,
                            "prezzo_carico": g_prezzo,
                            "quantita": g_qty,
                            "categoria": g_categoria
                        })
                        save_data(st.session_state.data)
                        st.success(f"✅ {g_nome} aggiunto al portafoglio!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Compila tutti i campi obbligatori (*)")

    with g_tab2:
        st.markdown("#### Posizioni Attuali — Clicca per modificare o eliminare")
        st.caption("💡 Per Obbligazioni e Certificati senza ticker, usa il campo **Prezzo Attuale Manuale** per aggiornare il valore corrente.")
        portfolio = st.session_state.data["portfolio"]
        
        # Group by category
        cats = sorted(set(p["categoria"] for p in portfolio))
        for cat in cats:
            cat_items = [p for p in portfolio if p["categoria"] == cat]
            cat_color = CATEGORY_COLORS.get(cat, "#64748B")
            st.markdown(f'<div style="color:{cat_color};font-weight:700;font-size:0.85rem;letter-spacing:0.1em;text-transform:uppercase;margin:1rem 0 0.5rem 0;">{cat} ({len(cat_items)} posizioni)</div>', unsafe_allow_html=True)
            
            for item in cat_items:
                idx = portfolio.index(item)
                prezzo_manuale = item.get("prezzo_manuale", 0.0) or 0.0
                label_manual = " ✏️" if prezzo_manuale > 0 else ""
                with st.expander(f"  {item['nome']} — {item['ticker']} | {item['quantita']} @ {item['prezzo_carico']:.3f} {item['valuta']}{label_manual}"):
                    ec1, ec2, ec3 = st.columns(3)
                    with ec1:
                        new_nome = st.text_input("Nome", value=item["nome"], key=f"en_{idx}")
                        new_ticker = st.text_input("Ticker Yahoo Finance", value=item["ticker"], key=f"et_{idx}")
                    with ec2:
                        new_prezzo = st.number_input("Prezzo carico", value=float(item["prezzo_carico"]), step=0.001, format="%.3f", key=f"ep_{idx}")
                        new_qty = st.number_input("Quantità / Nominale", value=float(item["quantita"]), step=0.001, format="%.4f", key=f"eq_{idx}")
                    with ec3:
                        new_valuta = st.selectbox("Valuta", ["EUR", "USD", "GBP", "DKK", "CHF"],
                                                 index=["EUR", "USD", "GBP", "DKK", "CHF"].index(item["valuta"]) if item["valuta"] in ["EUR", "USD", "GBP", "DKK", "CHF"] else 0,
                                                 key=f"ev_{idx}")
                        new_manuale = st.number_input(
                            "Prezzo Attuale Manuale (0 = usa Yahoo)",
                            value=float(prezzo_manuale),
                            step=0.001, format="%.3f",
                            key=f"em_{idx}",
                            help="Usa questo campo per Obbligazioni, Certificati o ETF con ticker non disponibile su Yahoo Finance"
                        )

                    btn_s, btn_d = st.columns([1, 1])
                    with btn_s:
                        if st.button("💾 Salva modifiche", key=f"save_{idx}"):
                            st.session_state.data["portfolio"][idx].update({
                                "nome": new_nome, "ticker": new_ticker,
                                "prezzo_carico": new_prezzo, "quantita": new_qty,
                                "valuta": new_valuta,
                                "prezzo_manuale": new_manuale if new_manuale > 0 else None
                            })
                            save_data(st.session_state.data)
                            st.cache_data.clear()
                            st.success("✅ Salvato!")
                            st.rerun()
                    with btn_d:
                        if st.button("🗑️ Elimina posizione", key=f"del_{idx}"):
                            st.session_state.data["portfolio"].pop(idx)
                            save_data(st.session_state.data)
                            st.cache_data.clear()
                            st.rerun()
