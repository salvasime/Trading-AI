import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import json, requests, time, smtplib, ssl
try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path
import anthropic

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Investment Intelligence", page_icon="📈",
                   layout="wide", initial_sidebar_state="collapsed")

# ── GLOBAL STYLES ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
:root {
    --bg:#070D1A; --s1:#0F1829; --s2:#162035; --s3:#1E2D47;
    --border:#243352; --border2:#2E4070;
    --accent:#3B82F6; --accent2:#60A5FA;
    --green:#10B981; --yellow:#F59E0B; --red:#EF4444; --purple:#8B5CF6;
    --text:#E8EDF5; --text2:#94A3B8; --text3:#64748B;
    --mono:'JetBrains Mono',monospace;
}
*, *::before, *::after { box-sizing:border-box; margin:0; padding:0; }
html, body, [class*="css"] { font-family:'Inter',sans-serif; background:var(--bg); color:var(--text); }
.stApp { background:var(--bg); }
.main .block-container { padding:1rem 1.5rem 2rem; max-width:1800px; }
section[data-testid="stSidebar"] { background:var(--s1) !important; border-right:1px solid var(--border); }
section[data-testid="stSidebar"] * { color:var(--text) !important; }
.stTabs [data-baseweb="tab-list"] { background:var(--s1); border:1px solid var(--border); border-radius:10px; padding:3px; gap:2px; }
.stTabs [data-baseweb="tab"] { background:transparent; color:var(--text3); border-radius:8px; font-size:.82rem; font-weight:500; padding:.4rem .9rem; }
.stTabs [aria-selected="true"] { background:var(--accent) !important; color:#fff !important; }
[data-testid="metric-container"] { background:var(--s1); border:1px solid var(--border); border-radius:10px; padding:.9rem 1rem; }
[data-testid="stMetricValue"] { font-family:var(--mono); font-size:1.3rem !important; }
.stTextInput input, .stNumberInput input, .stSelectbox > div > div { background:var(--s2) !important; border:1px solid var(--border) !important; color:var(--text) !important; border-radius:8px !important; }
.stButton > button { background:var(--accent); color:#fff; border:none; border-radius:8px; font-weight:600; font-size:.82rem; padding:.45rem 1rem; transition:all .15s; }
.stButton > button:hover { background:var(--accent2); transform:translateY(-1px); }
.streamlit-expanderHeader { background:var(--s2) !important; border:1px solid var(--border) !important; border-radius:8px !important; color:var(--text) !important; }
.streamlit-expanderContent { background:var(--s2) !important; border:1px solid var(--border) !important; border-top:none !important; border-radius:0 0 8px 8px !important; }
.stDataFrame { border-radius:10px; overflow:hidden; }
.stRadio > div { gap:.5rem; }
.stRadio label { color:var(--text2) !important; font-size:.85rem; }
#MainMenu, footer, header { visibility:hidden; }
.kpi-card { background:var(--s1); border:1px solid var(--border); border-radius:12px; padding:1rem 1.2rem; }
.kpi-label { font-size:.68rem; font-weight:600; letter-spacing:.1em; text-transform:uppercase; color:var(--text3); margin-bottom:.35rem; }
.kpi-value { font-family:var(--mono); font-size:1.5rem; font-weight:600; color:var(--text); }
.kpi-delta { font-family:var(--mono); font-size:.78rem; margin-top:.2rem; }
.up { color:var(--green); } .dn { color:var(--red); }
.section-hd { font-size:.7rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; color:var(--text3); padding:.5rem 0 .4rem; border-bottom:1px solid var(--border); margin-bottom:.8rem; margin-top:1.2rem; }
.ai-block { background:linear-gradient(135deg,#0D1526 0%,#16213E 100%); border:1px solid #2E4480; border-radius:12px; padding:1.2rem 1.4rem; line-height:1.75; font-size:.9rem; }
.tooltip-box { background:var(--s3); border:1px solid var(--border2); border-radius:8px; padding:.6rem .8rem; font-size:.78rem; color:var(--text2); line-height:1.5; margin-top:.3rem; }
.agent-card { background:var(--s2); border:1px solid var(--border); border-radius:10px; padding:1rem; margin-bottom:.5rem; }
.health-ring { display:flex; align-items:center; justify-content:center; flex-direction:column; }
.score-big { font-family:var(--mono); font-size:3.5rem; font-weight:700; line-height:1; }
.trade-row { background:var(--s1); border:1px solid var(--border); border-radius:8px; padding:.6rem 1rem; margin-bottom:.4rem; display:flex; align-items:center; gap:1rem; font-size:.82rem; }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ──────────────────────────────────────────────────────────────────
DATA_FILE = Path("data/portfolio.json")
DATA_FILE.parent.mkdir(exist_ok=True)
CATEGORY_COLORS = {"Azioni":"#3B82F6","ETF":"#10B981","Obbligazioni":"#F59E0B",
                   "Crypto":"#8B5CF6","Certificati":"#06B6D4","Materie Prime":"#F97316",
                   "Liquidità":"#94A3B8"}

DEFAULT_DATA = {
    "portfolio": [
        # AZIONI
        {"nome":"Leonardo","ticker":"LDO.MI","valuta":"EUR","prezzo_carico":20.640,"quantita":33,"categoria":"Azioni","prezzo_manuale":None},
        {"nome":"Ipsos","ticker":"IPS.PA","valuta":"EUR","prezzo_carico":46.053,"quantita":30,"categoria":"Azioni","prezzo_manuale":None},
        {"nome":"Trigano","ticker":"TRI.PA","valuta":"EUR","prezzo_carico":106.19,"quantita":5,"categoria":"Azioni","prezzo_manuale":None},
        {"nome":"Pinduoduo (PDD)","ticker":"PDD","valuta":"USD","prezzo_carico":100.377,"quantita":7,"categoria":"Azioni","prezzo_manuale":None},
        {"nome":"Global Ship Lease","ticker":"GSL","valuta":"USD","prezzo_carico":19.140,"quantita":36,"categoria":"Azioni","prezzo_manuale":None},
        {"nome":"Cal-Maine Foods","ticker":"CALM","valuta":"USD","prezzo_carico":93.73,"quantita":16,"categoria":"Azioni","prezzo_manuale":None},
        {"nome":"Zealand Pharma","ticker":"ZEAL.CO","valuta":"DKK","prezzo_carico":421.95,"quantita":22,"categoria":"Azioni","prezzo_manuale":None},
        {"nome":"Adobe","ticker":"ADBE","valuta":"USD","prezzo_carico":272.47,"quantita":4,"categoria":"Azioni","prezzo_manuale":None},
        # CERTIFICATI
        {"nome":"BSKT/BARC 2028","ticker":"N/A","valuta":"EUR","prezzo_carico":97.09,"quantita":14,"categoria":"Certificati","prezzo_manuale":None},
        {"nome":"Von Expe 2027","ticker":"N/A","valuta":"EUR","prezzo_carico":980.84,"quantita":2,"categoria":"Certificati","prezzo_manuale":None},
        {"nome":"Von Expe 2029","ticker":"N/A","valuta":"EUR","prezzo_carico":99.10,"quantita":14,"categoria":"Certificati","prezzo_manuale":None},
        # OBBLIGAZIONI
        {"nome":"BTP 4.00% 2037","ticker":"N/A","valuta":"EUR","prezzo_carico":98.097,"quantita":7000,"categoria":"Obbligazioni","prezzo_manuale":None},
        {"nome":"BTP 4.45% 2043","ticker":"N/A","valuta":"EUR","prezzo_carico":100.140,"quantita":6000,"categoria":"Obbligazioni","prezzo_manuale":None},
        {"nome":"BTP 4.50% 2053","ticker":"N/A","valuta":"EUR","prezzo_carico":100.020,"quantita":6000,"categoria":"Obbligazioni","prezzo_manuale":None},
        {"nome":"BTP 4.15% 2039","ticker":"N/A","valuta":"EUR","prezzo_carico":98.409,"quantita":6000,"categoria":"Obbligazioni","prezzo_manuale":None},
        {"nome":"Romania 5.25% 2032","ticker":"N/A","valuta":"EUR","prezzo_carico":99.94,"quantita":1000,"categoria":"Obbligazioni","prezzo_manuale":None},
        {"nome":"USA T-Bond 4.00% 2030","ticker":"N/A","valuta":"USD","prezzo_carico":98.71,"quantita":6000,"categoria":"Obbligazioni","prezzo_manuale":None},
        {"nome":"Barclays 30GE45 100C","ticker":"N/A","valuta":"GBP","prezzo_carico":97.30,"quantita":1000,"categoria":"Obbligazioni","prezzo_manuale":None},
        # ETF
        {"nome":"CSIF MSCI USA Small Cap ESG","ticker":"IE00BJBYDP94.SG","valuta":"EUR","prezzo_carico":156.660,"quantita":14,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"Lyxor ETF MSCI Emerging Markets","ticker":"LEM.PA","valuta":"EUR","prezzo_carico":13.183,"quantita":115,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"iShares Edge MSCI World Value Factor","ticker":"IWWL.L","valuta":"EUR","prezzo_carico":42.429,"quantita":36,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"iShares MSCI India","ticker":"ISHARESMSCII.SI","valuta":"EUR","prezzo_carico":8.594,"quantita":176,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"Xtrackers World Consumer Staples","ticker":"XDWS.L","valuta":"EUR","prezzo_carico":43.306,"quantita":45,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"Xtrackers Healthcare","ticker":"XDWH.L","valuta":"EUR","prezzo_carico":47.717,"quantita":38,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"Xtrackers II Global Gov. Bond","ticker":"XGSH.MI","valuta":"EUR","prezzo_carico":221.001,"quantita":18,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"iShares Core MSCI World","ticker":"SWDA.MI","valuta":"EUR","prezzo_carico":82.363,"quantita":53,"categoria":"ETF","prezzo_manuale":None},
        # CRYPTO
        {"nome":"Ethereum (ETH)","ticker":"ETH-USD","valuta":"USD","prezzo_carico":3099.44,"quantita":0.48,"categoria":"Crypto","prezzo_manuale":None},
        {"nome":"Bitcoin (BTC)","ticker":"BTC-USD","valuta":"USD","prezzo_carico":56403.66,"quantita":0.03,"categoria":"Crypto","prezzo_manuale":None},
        {"nome":"Ripple (XRP)","ticker":"XRP-USD","valuta":"USD","prezzo_carico":2.35,"quantita":668.09,"categoria":"Crypto","prezzo_manuale":None},
        # MATERIE PRIME
        {"nome":"Oro (Futures)","ticker":"GC=F","valuta":"USD","prezzo_carico":1580.000,"quantita":0.47,"categoria":"Materie Prime","prezzo_manuale":None},
        {"nome":"WisdomTree Copper","ticker":"COPA.L","valuta":"EUR","prezzo_carico":38.070,"quantita":27,"categoria":"Materie Prime","prezzo_manuale":None},
        {"nome":"WisdomTree Physical Gold","ticker":"PHAU.L","valuta":"EUR","prezzo_carico":173.300,"quantita":21,"categoria":"Materie Prime","prezzo_manuale":None},
        {"nome":"Liquidità","ticker":"N/A","valuta":"EUR","prezzo_carico":1.0,"quantita":16000,"categoria":"Liquidità","prezzo_manuale":1.0},
    ],
    "watchlist": [
        {"ticker":"MSFT",    "nome":"Microsoft",              "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"DAL",     "nome":"Delta Airlines",         "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"RDDT",    "nome":"Reddit",                 "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"DIS",     "nome":"Walt Disney",            "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"KOID",    "nome":"KraneShares Humanoid",   "categoria":"ETF",          "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"NLR",     "nome":"VanEck Uranium Nuclear", "categoria":"ETF",          "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"MELI",    "nome":"MercadoLibre",           "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"AMP.MI",  "nome":"Amplifon",               "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"ENEL.MI", "nome":"Enel",                   "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"SES.MI",  "nome":"Sesa",                   "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"NVDA",    "nome":"NVIDIA",                 "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"XPEL",    "nome":"XPEL Inc.",              "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"ICLR",    "nome":"Icon PLC",               "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"IP.MI",   "nome":"Interpump Group",        "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"AMZN",    "nome":"Amazon",                 "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"PYPL",    "nome":"PayPal",                 "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"IONQ",    "nome":"IonQ",                   "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"SLV",     "nome":"iShares Silver Trust",   "categoria":"Materie Prime","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"Proxy argento (XAG/USD non supportato da Yahoo Finance)","ai_pending":False},
        {"ticker":"NVO",     "nome":"Novo Nordisk",           "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"LLY",     "nome":"Eli Lilly",              "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"REGN",    "nome":"Regeneron Pharma",       "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"XX25.MI", "nome":"Xtrackers MSCI China",   "categoria":"ETF",          "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"GOOG",    "nome":"Alphabet (Google)",      "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"XMJP.MI", "nome":"iShares MSCI Japan",     "categoria":"ETF",          "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"NKE",     "nome":"Nike",                   "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"HLNE",    "nome":"Hamilton Lane",          "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"ARIS.MI", "nome":"Ariston Holding",        "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"MAIRE.MI","nome":"Maire",                  "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"N/A",     "nome":"Klarna (IPO attesa)",    "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"Non quotata. Segui IPO NYSE 2025.","ai_pending":False},
        {"ticker":"PRT.MI",  "nome":"Esprinet",               "categoria":"Azioni",       "sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False}
    ],
    "agent_cache": {},
    "trade_history": [],
    "email_settings": {}
}

# ── SUPABASE PERSISTENCE ──────────────────────────────────────────────────────
def _get_supabase_url():
    """Legge la stringa di connessione Supabase dai Secrets di Streamlit."""
    try:
        return st.secrets.get("SUPABASE_URL", "") if hasattr(st, "secrets") else ""
    except: return ""

def _db_connect():
    """Apre connessione a Supabase. Restituisce conn o None."""
    if not HAS_PSYCOPG2: return None
    url = _get_supabase_url()
    if not url: return None
    try:
        conn = psycopg2.connect(url, connect_timeout=5)
        return conn
    except: return None

def _db_ensure_table(conn):
    """Crea la tabella se non esiste."""
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_data (
                id   TEXT PRIMARY KEY DEFAULT 'main',
                data JSONB NOT NULL,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        conn.commit()
        cur.close()
        return True
    except: return False

def load_data():
    """
    Carica dati da Supabase (persistente) se disponibile,
    altrimenti da file locale, altrimenti da DEFAULT_DATA.
    """
    # ── Prova Supabase ────────────────────────────────────────────────────────
    conn = _db_connect()
    if conn:
        try:
            _db_ensure_table(conn)
            cur = conn.cursor()
            cur.execute("SELECT data FROM portfolio_data WHERE id = 'main'")
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                d = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                # Integra chiavi mancanti
                for k in ["agent_cache","trade_history","email_settings","watchlist"]:
                    if k not in d:
                        d[k] = {} if k in ["agent_cache","email_settings"] else []
                # Aggiungi nuovi asset di DEFAULT_DATA senza toccare esistenti
                existing_t = {p.get("ticker","") for p in d.get("portfolio",[])}
                for item in DEFAULT_DATA["portfolio"]:
                    if item.get("ticker","N/A") not in existing_t:
                        d["portfolio"].append(item)
                existing_wl = {w.get("ticker","") for w in d.get("watchlist",[])}
                for wl in DEFAULT_DATA["watchlist"]:
                    if wl.get("ticker","") not in existing_wl:
                        d["watchlist"].append(wl)
                return d
        except Exception as e:
            try: conn.close()
            except: pass

    # ── Fallback: file locale ─────────────────────────────────────────────────
    if DATA_FILE.exists():
        try:
            d = json.loads(DATA_FILE.read_text())
            for k in ["agent_cache","trade_history","email_settings","watchlist"]:
                if k not in d:
                    d[k] = {} if k in ["agent_cache","email_settings"] else []
            existing_t = {p.get("ticker","") for p in d.get("portfolio",[])}
            for item in DEFAULT_DATA["portfolio"]:
                if item.get("ticker","N/A") not in existing_t:
                    d["portfolio"].append(item)
            existing_wl = {w.get("ticker","") for w in d.get("watchlist",[])}
            for wl in DEFAULT_DATA["watchlist"]:
                if wl.get("ticker","") not in existing_wl:
                    d["watchlist"].append(wl)
            return d
        except: pass

    # ── Primo avvio: DEFAULT_DATA ─────────────────────────────────────────────
    return DEFAULT_DATA.copy()

def save_data(d):
    """
    Salva su Supabase (persistente) E su file locale (fallback).
    """
    saved_to_supabase = False

    # ── Salva su Supabase ─────────────────────────────────────────────────────
    conn = _db_connect()
    if conn:
        try:
            _db_ensure_table(conn)
            cur = conn.cursor()
            # Rimuovi agent_cache (troppo grande, non serve persistere)
            d_save = {k:v for k,v in d.items() if k != "agent_cache"}
            cur.execute("""
                INSERT INTO portfolio_data (id, data, updated_at)
                VALUES ('main', %s, NOW())
                ON CONFLICT (id) DO UPDATE
                SET data = EXCLUDED.data, updated_at = NOW()
            """, (json.dumps(d_save, ensure_ascii=False),))
            conn.commit()
            cur.close()
            conn.close()
            saved_to_supabase = True
        except Exception as e:
            try: conn.close()
            except: pass
            # Mostra errore visibile per debug
            if hasattr(st, "session_state"):
                st.session_state["_last_save_error"] = str(e)
    elif _get_supabase_url():
        # URL configurato ma connessione fallita
        if hasattr(st, "session_state"):
            st.session_state["_last_save_error"] = "Connessione Supabase fallita — controlla URL e password nei Secrets"

    # ── Salva anche in locale (fallback offline) ──────────────────────────────
    try:
        DATA_FILE.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    except: pass

    return saved_to_supabase

if "data" not in st.session_state:
    st.session_state.data = load_data()

# ── MARKET DATA ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_market_data():
    tickers = {"VIX":"^VIX","S&P 500":"^GSPC","FTSE MIB":"FTSEMIB.MI","Nasdaq":"^IXIC","EUR/USD":"EURUSD=X","Oro":"GC=F"}
    out = {}
    for name, t in tickers.items():
        try:
            h = yf.Ticker(t).history(period="5d")
            if len(h) >= 2:
                c, p = float(h["Close"].iloc[-1]), float(h["Close"].iloc[-2])
                out[name] = {"value":c, "delta":(c-p)/p*100}
            elif len(h) == 1:
                out[name] = {"value":float(h["Close"].iloc[-1]), "delta":0}
            else:
                out[name] = {"value":0, "delta":0}
        except:
            out[name] = {"value":0, "delta":0}
    return out

@st.cache_data(ttl=300)
def get_fx_rates():
    pairs = {"USD":"EURUSD=X","GBP":"EURGBP=X","DKK":"EURDKK=X","CHF":"EURCHF=X"}
    fb    = {"USD":1.08,"GBP":0.85,"DKK":7.46,"CHF":0.95}
    rates = {"EUR":1.0}
    for cur, t in pairs.items():
        try:
            h = yf.Ticker(t).history(period="2d")
            rates[cur] = float(h["Close"].iloc[-1]) if not h.empty else fb[cur]
        except:
            rates[cur] = fb[cur]
    return rates

@st.cache_data(ttl=300)
def get_price(ticker):
    if ticker == "N/A": return None
    try:
        h = yf.Ticker(ticker).history(period="2d")
        return float(h["Close"].iloc[-1]) if not h.empty else None
    except: return None

def to_eur(amount, currency, fx):
    return amount if currency == "EUR" else amount / fx.get(currency, 1.0)

@st.cache_data(ttl=3600)
def get_technical(ticker):
    if ticker == "N/A": return None
    try:
        h = yf.Ticker(ticker).history(period="1y")
        if len(h) < 30: return None
        c = h["Close"]
        ma50  = c.rolling(50).mean().iloc[-1]  if len(c)>=50  else None
        ma200 = c.rolling(200).mean().iloc[-1] if len(c)>=200 else None
        price = float(c.iloc[-1])
        d = c.diff()
        gain = d.clip(lower=0).rolling(14).mean()
        loss = (-d.clip(upper=0)).rolling(14).mean()
        rsi = float((100 - 100/(1 + gain/loss.replace(0,1e-9))).iloc[-1])
        ema12 = c.ewm(span=12).mean(); ema26 = c.ewm(span=26).mean()
        macd = ema12 - ema26; sig = macd.ewm(span=9).mean()
        macd_h = float((macd - sig).iloc[-1])
        bm = c.rolling(20).mean(); bs = c.rolling(20).std()
        boll_up = float((bm + 2*bs).iloc[-1]); boll_dn = float((bm - 2*bs).iloc[-1])
        support = float(c.rolling(20).min().iloc[-1])
        resistance = float(c.rolling(20).max().iloc[-1])
        cross = None
        if ma50 and ma200:
            p50 = c.rolling(50).mean().iloc[-2]; p200 = c.rolling(200).mean().iloc[-2]
            if p50 < p200 and ma50 >= ma200: cross = "golden"
            elif p50 > p200 and ma50 <= ma200: cross = "death"
        vol_avg = float(h["Volume"].rolling(20).mean().iloc[-1]) if "Volume" in h else 0
        vol_cur = float(h["Volume"].iloc[-1]) if "Volume" in h else 0
        return {"price":price,"ma50":float(ma50) if ma50 else None,
                "ma200":float(ma200) if ma200 else None,
                "rsi":rsi,"macd_h":macd_h,"boll_up":boll_up,"boll_dn":boll_dn,
                "support":support,"resistance":resistance,"cross":cross,
                "vol_ratio":vol_cur/vol_avg if vol_avg>0 else 1.0,"history":h}
    except: return None

def tech_signal(td):
    if not td: return "⚪","N/D","Dati non disponibili"
    score = 0; reasons = []
    if td["ma50"]:
        if td["price"] > td["ma50"]: score+=1; reasons.append("▲ MA50")
        else: score-=1; reasons.append("▼ MA50")
    if td["ma200"]:
        if td["price"] > td["ma200"]: score+=2; reasons.append("▲ MA200")
        else: score-=2; reasons.append("▼ MA200")
    if td["cross"] == "golden": score+=2; reasons.append("Golden Cross 🌟")
    elif td["cross"] == "death": score-=2; reasons.append("Death Cross ⚠️")
    r = td["rsi"]
    if r > 70:   score-=1; reasons.append(f"RSI {r:.0f} ipercomprato")
    elif r < 30: score+=1; reasons.append(f"RSI {r:.0f} ipervenduto")
    else: reasons.append(f"RSI {r:.0f}")
    if td["macd_h"] > 0: score+=1; reasons.append("MACD ↑")
    else: score-=1; reasons.append("MACD ↓")
    if td["price"] > td["boll_up"]: score-=1; reasons.append("Sopra Boll.sup")
    elif td["price"] < td["boll_dn"]: score+=1; reasons.append("Sotto Boll.inf")
    if td["vol_ratio"] > 1.5: reasons.append(f"Vol ×{td['vol_ratio']:.1f}")
    if score >= 3:   return "🟢","INCREMENTA",", ".join(reasons[:4])
    elif score >= 1: return "🟡","TIENI",", ".join(reasons[:4])
    elif score >= -1:return "🟡","ATTENZIONE",", ".join(reasons[:4])
    else:            return "🔴","ALLEGGERISCI",", ".join(reasons[:4])

def build_portfolio_df():
    fx = get_fx_rates()
    rows = []
    for item in st.session_state.data["portfolio"]:
        cat, val, pc, qty = item["categoria"], item["valuta"], item["prezzo_carico"], item["quantita"]
        pm = item.get("prezzo_manuale") or 0
        if pm > 0:
            price_loc, src = pm, "manuale"
        elif item["ticker"] != "N/A":
            price_loc = get_price(item["ticker"])
            src = "live" if price_loc else "carico"
            if not price_loc: price_loc = pc
        else:
            price_loc, src = pc, "carico"
        if cat == "Obbligazioni":
            cv_eur = to_eur((price_loc/100)*qty, val, fx)
            ca_eur = to_eur((pc/100)*qty, val, fx)
        else:
            cv_eur = to_eur(price_loc*qty, val, fx)
            ca_eur = to_eur(pc*qty, val, fx)
        pnl = cv_eur - ca_eur
        rows.append({"Nome":item["nome"],"Ticker":item["ticker"],"Categoria":cat,
                     "Valuta":val,"P.Carico":pc,"P.Attuale":price_loc,"Fonte":src,
                     "Quantità":qty,"CV €":cv_eur,"P&L €":pnl,
                     "P&L %":(pnl/ca_eur*100) if ca_eur>0 else 0})
    return pd.DataFrame(rows)

@st.cache_data(ttl=3600)
def get_index_history():
    out = {}
    for name, t in {"S&P 500":"^GSPC","Nasdaq":"^IXIC","FTSE MIB":"FTSEMIB.MI"}.items():
        try:
            h = yf.Ticker(t).history(period="1mo")
            if not h.empty: out[name] = h["Close"]
        except: pass
    return out

@st.cache_data(ttl=3600)
def get_benchmark_history(period="6mo"):
    """MSCI World (SWDA) and 60/40 proxy"""
    out = {}
    for name, t in {"MSCI World":"SWDA.MI","S&P 500":"^GSPC","Obblig. Globali":"XGSG.DE"}.items():
        try:
            h = yf.Ticker(t).history(period=period)
            if not h.empty: out[name] = h["Close"]
        except: pass
    return out

@st.cache_data(ttl=300)
def get_news(api_key, query="economy inflation market", days=2):
    if not api_key: return []
    try:
        from_dt = (datetime.now()-timedelta(days=days)).strftime("%Y-%m-%d")
        r = requests.get(
            f"https://newsapi.org/v2/everything?q={query}&from={from_dt}"
            f"&sortBy=relevancy&language=en&pageSize=20&apiKey={api_key}", timeout=10)
        return [{"title":a["title"],"source":a["source"]["name"],"url":a["url"]}
                for a in r.json().get("articles",[])[:15]]
    except: return []

# ── PORTFOLIO HEALTH SCORE ─────────────────────────────────────────────────────
def compute_health_score(df, mkt):
    """Returns 0-100 score with component breakdown"""
    score = 50; components = {}

    # 1. P&L component (max ±20)
    pnl_pct = df["P&L %"].mean() if not df.empty else 0
    pnl_score = max(-20, min(20, pnl_pct * 2))
    score += pnl_score
    components["P&L medio"] = {"val": f"{pnl_pct:+.1f}%", "pts": pnl_score}

    # 2. Technical signals (max ±20)
    tradeable = [p for p in st.session_state.data["portfolio"] if p["ticker"] != "N/A"]
    green = yellow = red = 0
    for item in tradeable[:10]:
        td = get_technical(item["ticker"])
        em, _, _ = tech_signal(td)
        if em == "🟢": green += 1
        elif em == "🔴": red += 1
        else: yellow += 1
    total_t = green + yellow + red
    if total_t > 0:
        tech_pts = ((green - red) / total_t) * 20
    else:
        tech_pts = 0
    score += tech_pts
    components["Segnali tecnici"] = {"val": f"{green}🟢 {yellow}🟡 {red}🔴", "pts": tech_pts}

    # 3. VIX / market risk (max ±10)
    vix = mkt.get("VIX",{}).get("value",20)
    if vix < 15:   vix_pts = 10
    elif vix < 25: vix_pts = 0
    else:          vix_pts = -10
    score += vix_pts
    components["VIX risk"] = {"val": f"{vix:.1f}", "pts": vix_pts}

    # 4. Concentration risk (max -10)
    if not df.empty:
        top_weight = df["CV €"].max() / df["CV €"].sum() * 100 if df["CV €"].sum() > 0 else 0
        conc_pts = 0 if top_weight < 15 else (-5 if top_weight < 25 else -10)
        score += conc_pts
        components["Concentrazione"] = {"val": f"Top pos. {top_weight:.1f}%", "pts": conc_pts}

    # 5. Missing prices penalty
    missing = sum(1 for p in st.session_state.data["portfolio"]
                  if p["ticker"]=="N/A" and not (p.get("prezzo_manuale") or 0)>0)
    miss_pts = min(0, -missing * 2)
    score += miss_pts
    if missing > 0:
        components["Prezzi mancanti"] = {"val": f"{missing} asset", "pts": miss_pts}

    return max(0, min(100, round(score))), components

# ── MULTI-AGENT AI ─────────────────────────────────────────────────────────────
def call_agent(client, system_prompt, user_prompt, max_tokens=1200):
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role":"user","content":user_prompt}])
        return msg.content[0].text
    except Exception as e:
        return f"Errore agente: {e}"

def run_multi_agent_analysis(api_key, portfolio_df, market_data, watchlist, news_items):
    """
    5 agenti specializzati. Ogni agente riceve il contesto REALE del portafoglio
    con nomi, ticker, P&L, allocazione. L'agente optimizer lavora SOLO sui titoli
    effettivamente in portafoglio, non inventati.
    """
    client = anthropic.Anthropic(api_key=api_key)
    results = {}
    progress = st.progress(0)
    status_box = st.empty()
    vix  = market_data.get("VIX",{}).get("value",20)
    sp500 = market_data.get("S&P 500",{}).get("delta",0)
    eurusd = market_data.get("EUR/USD",{}).get("value",1.08)
    ftse = market_data.get("FTSE MIB",{}).get("delta",0)
    news_text = "\n".join([f"- {n['title']}" for n in news_items[:12]]) if news_items else "Nessuna notizia disponibile"

    # Prepara contesto portafoglio reale completo
    pf_rows = []
    for _, row in portfolio_df.iterrows():
        pnl_str = f"{row['P&L %']:+.1f}%"
        pf_rows.append(f"  {row['Nome']} ({row['Ticker']}): {row['Categoria']} | CV €{row['CV €']:,.0f} | P&L {pnl_str}")
    pf_detail = "\n".join(pf_rows) if pf_rows else "Portafoglio vuoto"

    alloc = portfolio_df.groupby("Categoria")["CV €"].sum()
    total_v = alloc.sum()
    alloc_str = "\n".join([f"  {c}: €{v:,.0f} ({v/total_v*100:.1f}%)" for c,v in alloc.items()]) if total_v > 0 else "N/D"

    # Dati tecnici per ogni titolo tradeable
    tradeable = [(r["Nome"],r["Ticker"],r["P&L %"],r["CV €"]) for _,r in portfolio_df.iterrows()
                 if r["Ticker"] not in ("N/A","",None)]
    tech_per_titolo = []
    for nome, ticker, pnl_pct, cv in tradeable[:14]:
        td = get_technical(ticker)
        if td:
            em, lbl, reason = tech_signal(td)
            tech_per_titolo.append(
                f"  {nome} ({ticker}): {lbl} | RSI={td['rsi']:.0f} | MACD={td['macd_h']:+.3f} | "
                f"P.att={td['price']:.2f} | Supp={td['support']:.2f} | Res={td['resistance']:.2f} | "
                f"P&L={pnl_pct:+.1f}% | CV=€{cv:,.0f} | {reason}")
        else:
            tech_per_titolo.append(f"  {nome} ({ticker}): dati tecnici non disponibili | P&L={pnl_pct:+.1f}%")

    tech_detail = "\n".join(tech_per_titolo) if tech_per_titolo else "Nessun dato tecnico"

    def agent_step(n, total, color, label, system, user, max_t=1200):
        status_box.markdown(
            f'''<div style="background:#0F1829;border:1px solid #243352;border-radius:8px;padding:.7rem 1rem;margin:.3rem 0;">
<span style="color:{color};font-size:.65rem;font-weight:700;letter-spacing:.08em;">▶ AGENTE {n}/{total}</span>
<b style="font-size:.85rem;margin-left:.5rem;">{label}</b>
<span style="font-size:.72rem;color:#64748B;margin-left:.5rem;">in elaborazione...</span></div>''',
            unsafe_allow_html=True)
        result = call_agent(client, system, user, max_t)
        progress.progress(int(n/total*100))
        return result

    # ── AGENTE 1: MACRO ───────────────────────────────────────────────────────
    results["macro"] = agent_step(1, 5, "#10B981", "Analista Macro",
        """Sei un economista macro di livello istituzionale che spiega i mercati in modo chiaro,
anche a investitori non esperti. Usa sempre esempi concreti e spiega l'impatto pratico sul portafoglio.""",
        f"""DATI DI MERCATO OGGI:
VIX={vix:.1f} (paura mercati), S&P500={sp500:+.2f}%, FTSE MIB={ftse:+.2f}%, EUR/USD={eurusd:.4f}

NOTIZIE RILEVANTI:
{news_text}

PORTAFOGLIO DA ANALIZZARE (questi sono i titoli REALI dell'investitore):
{pf_detail}

Analizza in italiano, tono chiaro e comprensibile anche a chi non è esperto di finanza.
Struttura la risposta così:
1) SITUAZIONE MERCATI OGGI — spiega in parole semplici se i mercati sono nervosi o tranquilli e perché
2) 3 RISCHI DA MONITORARE — cosa potrebbe andare male e come impatta su questo portafoglio specifico
3) 3 OPPORTUNITÀ CONCRETE — cosa potrebbe andare bene nei prossimi mesi
4) IMPATTO SULLE TUE POSIZIONI — per ogni categoria del portafoglio (Azioni, ETF, Obbligazioni, Crypto, ecc.) spiega cosa potrebbe succedere
Massimo 400 parole. Sii specifico sui titoli in portafoglio.""")

    # ── AGENTE 2: TECNICO ─────────────────────────────────────────────────────
    results["tecnica"] = agent_step(2, 5, "#3B82F6", "Analista Tecnico",
        """Sei un analista tecnico senior che spiega i grafici in modo comprensibile anche a chi non conosce
il trading. Per ogni titolo dai una spiegazione in linguaggio semplice del perché il segnale è quello che è.""",
        f"""ANALISI TECNICA DETTAGLIATA DEI TITOLI IN PORTAFOGLIO:
{tech_detail}

VIX={vix:.1f}, S&P500={sp500:+.2f}%

Spiega in italiano per OGNI titolo con dati disponibili:
- Cosa sta facendo il titolo (sta salendo, scendendo, lateralizzando?)
- Perché il segnale è INCREMENTA / TIENI / ATTENZIONE / ALLEGGERISCI
- Un livello di prezzo chiave da tenere d'occhio (supporto o resistenza)
- Una frase semplice che spieghi il ragionamento anche a chi non sa cos'è un RSI

Poi un RIEPILOGO con:
- Top 3 titoli con il setup migliore e perché
- Top 3 titoli più a rischio e perché
Massimo 500 parole.""",
        max_t=1400)

    # ── AGENTE 3: RISCHIO ────────────────────────────────────────────────────
    top5 = portfolio_df.nlargest(5,"CV €")[["Nome","Ticker","CV €","P&L %"]].to_string(index=False)
    results["rischio"] = agent_step(3, 5, "#F59E0B", "Risk Manager",
        """Sei un risk manager di un family office. Sai spiegare i rischi in modo concreto,
con esempi pratici che capisce anche chi non ha mai sentito parlare di finanza.""",
        f"""PORTAFOGLIO REALE DA ANALIZZARE:
Totale: €{total_v:,.0f}
Allocazione:
{alloc_str}

Top 5 posizioni per valore:
{top5}

VIX: {vix:.1f}
Notizie rilevanti: {news_text[:500]}

Analizza in italiano:
1) SCORE RISCHIO COMPLESSIVO (1-10) — spiega con parole semplici quanto è rischioso questo portafoglio
2) CONCENTRAZIONE — ci sono posizioni troppo grandi? Cosa succede se quel titolo crolla?
3) RISCHIO VALUTARIO — hai USD, GBP, DKK: cosa succede se l'euro si rafforza?
4) COSA TENERE D'OCCHIO — 3 rischi specifici per questo portafoglio nei prossimi 30-90 giorni
5) SUGGERIMENTO DI RIBILANCIAMENTO — in termini pratici, cosa cambieresti e perché
Massimo 350 parole. Parla dei titoli reali.""")

    # ── AGENTE 4: SENTIMENT ───────────────────────────────────────────────────
    results["sentiment"] = agent_step(4, 5, "#8B5CF6", "Sentiment Analyst",
        """Sei un esperto di sentiment di mercato e psicologia degli investitori.
Spieghi in modo semplice cosa "sentono" i mercati e come questo impatta sulle scelte di investimento.""",
        f"""DATI DI SENTIMENT:
VIX={vix:.1f} (>25=paura, 15-25=neutro, <15=euforia)
S&P500 oggi: {sp500:+.2f}%
EUR/USD: {eurusd:.4f}

NOTIZIE DI OGGI:
{news_text}

Portafoglio dell'investitore:
{alloc_str}

Analizza in italiano:
1) FEAR & GREED OGGI — numero 0-100 e spiegazione in parole semplici (0=panico totale, 100=euforia)
2) COSA PENSANO I GRANDI INVESTITORI — fondi, banche, hedge fund: stanno comprando o vendendo?
3) TRAPPOLE PSICOLOGICHE DA EVITARE — quali errori tipici potrebbe fare chi ha questo portafoglio oggi?
4) OPPORTUNITÀ CONTRARIAN — c'è qualcosa che tutti stanno ignorando o odiando che potrebbe essere un'opportunità?
Massimo 300 parole.""")

    # ── AGENTE 5: OPTIMIZER ───────────────────────────────────────────────────
    wl_str = "\n".join([f"- {w['ticker']}: {w['nome']} ({w.get('categoria','')})" for w in watchlist[:15]]) or "Nessun titolo in watchlist"
    # Agente 5: Optimizer — produce piano testo + JSON separato per watchlist AI
    results["ottimizzazione"] = agent_step(5, 5, "#F97316", "Portfolio Optimizer",
        """Sei il gestore principale di un family office che gestisce questo portafoglio.
Dai indicazioni chiare, pratiche, con motivazioni comprensibili anche a chi non è esperto.
NON inventare titoli che non sono in portafoglio nella PARTE 1. Lavora SOLO sui titoli elencati.""",
        f"""HAI A DISPOSIZIONE QUESTE ANALISI:
MACRO: {results['macro'][:500]}
TECNICA: {results['tecnica'][:500]}
RISCHIO: {results['rischio'][:400]}
SENTIMENT: {results['sentiment'][:300]}

PORTAFOGLIO REALE (lavora SOLO su questi titoli nella PARTE 1):
{pf_detail}

WATCHLIST PERSONALE (titoli già seguiti dall'investitore, considera per nuovi acquisti):
{wl_str}

Produci un PIANO OPERATIVO COMPLETO in italiano:

PARTE 1 — AZIONI SUI TITOLI IN PORTAFOGLIO
Per OGNI titolo in portafoglio scrivi:
[NOME TITOLO] → AZIONE: TIENI / INCREMENTA / RIDUCI / VENDI
Perché (2-3 frasi semplici): spiega la motivazione in modo che la capisca anche chi non conosce la finanza.
Includi almeno una notizia recente o evento specifico sul titolo se rilevante.
Livello chiave: [prezzo supporto o resistenza da monitorare]

PARTE 2 — NUOVI ACQUISTI SUGGERITI (4-6 titoli con ticker Yahoo Finance reale e valido)
Per ciascuno scegli titoli che COMPLETANO questo portafoglio (non duplicarli):
[TICKER] [NOME] → COMPRA o MONITORA
Perché si adatta: [2 frasi su come completa il portafoglio]
Ingresso ideale: [prezzo] | Target 12 mesi: [prezzo] | Stop loss: [prezzo] | Strategia: [Breve/Medio/Lungo termine]

PARTE 3 — ALLOCAZIONE TARGET
Distribuzione % ideale del portafoglio e perché.

Massimo 700 parole. Linguaggio semplice e pratico.""",
        max_t=1800)

    # Agente 5b: estrai i suggerimenti AI in JSON strutturato per la watchlist
    try:
        pf_tickers_set = {p.get("ticker","").upper() for p in st.session_state.data["portfolio"]}
        wl_tickers_set = {w.get("ticker","").upper() for w in watchlist}
        cl_json = anthropic.Anthropic(api_key=api_key)
        json_raw = cl_json.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=800,
            system="Estrai dati strutturati. Rispondi SOLO con JSON array valido, niente altro.",
            messages=[{"role":"user","content":
                f'Dal seguente piano operativo, estrai SOLO i titoli dalla PARTE 2 (Nuovi acquisti suggeriti). '
                f'ESCLUDI questi ticker già in portafoglio: {list(pf_tickers_set)}. '
                f'ESCLUDI questi ticker già in watchlist: {list(wl_tickers_set)}. '
                f'Per ogni titolo trovato crea un oggetto JSON. '
                f'Rispondi con SOLO questo array JSON (nessun testo prima o dopo): '
                f'[{{"ticker":"AAPL","nome":"Apple","categoria":"Azioni","segnale":"COMPRA",'
                f'"ingresso":150.0,"prezzo_target":180.0,"stop_loss":135.0,'
                f'"strategia":"Lungo termine","orizzonte":"Medio (6-12 mesi)",'
                f'"note":"Motivazione perche si adatta al portafoglio, max 120 caratteri"}}] '
                f'Se non trovi titoli chiari con ticker valido Yahoo Finance, rispondi []. '
                f'TESTO DA ANALIZZARE: {results["ottimizzazione"][:2000]}'}]
        ).content[0].text.strip()
        # Pulisci eventuali backtick markdown
        json_raw = json_raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        ai_suggestions = json.loads(json_raw)
        results["ai_watchlist_suggestions"] = ai_suggestions
    except Exception as e:
        results["ai_watchlist_suggestions"] = []

    progress.progress(100)
    status_box.empty()
    progress.empty()
    return results

# ── FUNDAMENTALS ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400)
def get_fundamentals(ticker):
    """Fetch key fundamental ratios from Yahoo Finance. Cached 24h."""
    if ticker in ("N/A","",None): return None
    try:
        t = yf.Ticker(ticker)
        i = t.info
        if not i: return None
        def _f(k): return i.get(k)
        price      = _f("currentPrice") or _f("regularMarketPrice")
        pe         = _f("trailingPE") or _f("forwardPE")
        peg        = _f("pegRatio")
        pb         = _f("priceToBook")
        de         = _f("debtToEquity")
        roe        = _f("returnOnEquity")
        rev_growth = _f("revenueGrowth")
        eps_growth = _f("earningsGrowth")
        div_yield  = _f("dividendYield")
        mktcap     = _f("marketCap")
        sector     = _f("sector")
        industry   = _f("industry")
        earnings_d = _f("earningsTimestamp") or _f("nextEarningsDate")
        return {
            "price": price, "pe": pe, "peg": peg, "pb": pb,
            "de": de, "roe": roe, "rev_growth": rev_growth,
            "eps_growth": eps_growth, "div_yield": div_yield,
            "mktcap": mktcap, "sector": sector, "industry": industry,
            "earnings_date": earnings_d,
        }
    except: return None

@st.cache_data(ttl=86400)
def get_earnings_calendar(tickers_tuple):
    """Get next earnings dates for a list of tickers."""
    results = {}
    for ticker in tickers_tuple:
        if ticker in ("N/A","",None): continue
        try:
            info = yf.Ticker(ticker).info
            ed = info.get("earningsTimestamp") or info.get("nextEarningsDate")
            if ed:
                if isinstance(ed, (int, float)):
                    from datetime import timezone
                    dt = datetime.fromtimestamp(ed, tz=timezone.utc).strftime("%d/%m/%Y")
                else:
                    dt = str(ed)[:10]
                results[ticker] = dt
        except: pass
    return results

@st.cache_data(ttl=3600)
def get_volatility(ticker):
    """Calculate annualised volatility and max drawdown from 1y history."""
    if ticker in ("N/A","",None): return None
    try:
        h = yf.Ticker(ticker).history(period="1y")
        if len(h) < 20: return None
        ret  = h["Close"].pct_change().dropna()
        vol  = float(ret.std() * (252**0.5) * 100)   # annualised %
        roll_max = h["Close"].cummax()
        dd   = (h["Close"] - roll_max) / roll_max * 100
        max_dd = float(dd.min())
        return {"vol_ann": vol, "max_drawdown": max_dd}
    except: return None

# ── POSITION SIZING ───────────────────────────────────────────────────────────
def calc_position_size(portfolio_total_eur, current_price, stop_loss_price,
                       risk_pct_per_trade=1.0, fx_rate=1.0):
    """
    Kelly-inspired position sizing.
    risk_pct_per_trade: % del portafoglio che sei disposto a rischiare (default 1%)
    fx_rate: tasso EUR/valuta (es. 1.08 se il titolo è in USD)
    Returns: n_shares, risk_eur, position_eur, position_pct
    """
    if not stop_loss_price or not current_price or current_price <= stop_loss_price:
        return None
    risk_eur        = portfolio_total_eur * (risk_pct_per_trade / 100)
    risk_per_share  = (current_price - stop_loss_price) / fx_rate  # in EUR
    if risk_per_share <= 0: return None
    n_shares        = int(risk_eur / risk_per_share)
    if n_shares < 1: n_shares = 1
    position_eur    = n_shares * current_price / fx_rate
    position_pct    = position_eur / portfolio_total_eur * 100
    return {
        "n_shares":     n_shares,
        "risk_eur":     risk_eur,
        "position_eur": position_eur,
        "position_pct": position_pct,
        "risk_per_share_eur": risk_per_share,
    }

# ── BLENDED BENCHMARK ─────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_blended_benchmark(alloc_dict, period="6mo"):
    """
    Build a custom blended benchmark matching the user's allocation.
    alloc_dict: {"Azioni": 25.3, "ETF": 18.0, ...}
    """
    proxy = {
        "Azioni":        ("^GSPC",   "S&P 500"),
        "ETF":           ("SWDA.MI", "MSCI World"),
        "Obbligazioni":  ("XGSH.MI", "Global Bond"),
        "Crypto":        ("BTC-USD",  "Bitcoin"),
        "Materie Prime": ("GC=F",     "Oro"),
        "Certificati":   ("XGSH.MI", "Bond proxy"),
        "Liquidità":     (None,       "Cash 0%"),
    }
    total_w = sum(v for k,v in alloc_dict.items() if k != "Liquidità")
    if total_w == 0: return None, None
    weighted = []
    label_parts = []
    for cat, pct in alloc_dict.items():
        if cat == "Liquidità" or pct < 0.5: continue
        ticker_b, name_b = proxy.get(cat, (None,""))
        if not ticker_b: continue
        w = pct / total_w
        try:
            h = yf.Ticker(ticker_b).history(period=period)["Close"]
            if not h.empty:
                ret = (h / h.iloc[0] - 1) * w
                weighted.append(ret)
                label_parts.append(f"{name_b} {pct:.0f}%")
        except: pass
    if not weighted: return None, None
    blended = sum(weighted) * 100
    label = " + ".join(label_parts[:4])
    return blended, label


# ── EMAIL ALERT ────────────────────────────────────────────────────────────────
def send_email_alert(settings, subject, html_body):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = settings["from_email"]
        msg["To"]      = settings["to_email"]
        msg.attach(MIMEText(html_body, "html"))
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as s:
            s.login(settings["from_email"], settings["app_password"])
            s.sendmail(settings["from_email"], settings["to_email"], msg.as_string())
        return True, "Email inviata"
    except Exception as e:
        return False, str(e)

def build_daily_email(df, mkt, health_score, agent_results):
    pnl_tot = df["P&L €"].sum()
    total_v = df["CV €"].sum()
    best = df.nlargest(1,"P&L %").iloc[0]
    worst = df.nsmallest(1,"P&L %").iloc[0]
    sc = "#10B981" if health_score >= 70 else ("#F59E0B" if health_score >= 40 else "#EF4444")
    opt = agent_results.get("ottimizzazione","") if agent_results else ""
    opt_html = opt.replace("\n","<br>")[:800] if opt else "Avvia l'analisi multi-agente per il piano operativo."
    return f"""
<div style="font-family:Inter,sans-serif;background:#070D1A;color:#E8EDF5;padding:2rem;border-radius:12px;max-width:640px;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:1.5rem;border-bottom:1px solid #243352;padding-bottom:1rem;">
    <span style="font-size:1.5rem;">📈</span>
    <div>
      <div style="font-size:1rem;font-weight:700;">Investment Intelligence</div>
      <div style="font-size:.75rem;color:#64748B;">Report giornaliero · {datetime.now().strftime('%A %d %B %Y')}</div>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:.8rem;margin-bottom:1.5rem;">
    <div style="background:#0F1829;border:1px solid #243352;border-radius:8px;padding:.8rem;text-align:center;">
      <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;letter-spacing:.08em;">Totale</div>
      <div style="font-family:'Courier New',monospace;font-weight:700;font-size:1rem;">€{total_v:,.0f}</div>
    </div>
    <div style="background:#0F1829;border:1px solid #243352;border-radius:8px;padding:.8rem;text-align:center;">
      <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;letter-spacing:.08em;">P&L</div>
      <div style="font-family:'Courier New',monospace;font-weight:700;font-size:1rem;color:{'#10B981' if pnl_tot>=0 else '#EF4444'};">€{pnl_tot:+,.0f}</div>
    </div>
    <div style="background:#0F1829;border:1px solid #243352;border-radius:8px;padding:.8rem;text-align:center;">
      <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;letter-spacing:.08em;">VIX</div>
      <div style="font-family:'Courier New',monospace;font-weight:700;font-size:1rem;">{mkt.get('VIX',{}).get('value',0):.1f}</div>
    </div>
    <div style="background:#0F1829;border:1px solid #243352;border-radius:8px;padding:.8rem;text-align:center;">
      <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;letter-spacing:.08em;">Score</div>
      <div style="font-family:'Courier New',monospace;font-weight:700;font-size:1rem;color:{sc};">{health_score}/100</div>
    </div>
  </div>
  <div style="background:#0F1829;border:1px solid #2E4480;border-radius:8px;padding:1rem;margin-bottom:1rem;">
    <div style="font-size:.65rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#64748B;margin-bottom:.5rem;">Best / Worst</div>
    <div style="font-size:.85rem;">🏆 <b>{best['Nome']}</b> <span style="color:#10B981;">{best['P&L %']:+.1f}%</span> &nbsp;&nbsp; ⚠️ <b>{worst['Nome']}</b> <span style="color:#EF4444;">{worst['P&L %']:+.1f}%</span></div>
  </div>
  <div style="background:#0D1526;border:1px solid #2E4480;border-radius:8px;padding:1rem;">
    <div style="font-size:.65rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#64748B;margin-bottom:.5rem;">Piano operativo AI</div>
    <div style="font-size:.82rem;line-height:1.7;color:#94A3B8;">{opt_html}</div>
  </div>
</div>"""

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configurazione")

    # ── Stato connessione Supabase ─────────────────────────────────────────
    _supa_url = _get_supabase_url()
    if not _supa_url:
        st.markdown('<div style="background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.3);border-radius:8px;padding:.5rem .8rem;font-size:.72rem;color:#EF4444;margin-bottom:.4rem;">⚠️ <b>Supabase non configurato</b> — i dati non vengono salvati in modo permanente.<br>Aggiungi SUPABASE_URL nei Secrets di Streamlit.</div>', unsafe_allow_html=True)
    elif not HAS_PSYCOPG2:
        st.markdown('<div style="background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.3);border-radius:8px;padding:.5rem .8rem;font-size:.72rem;color:#EF4444;margin-bottom:.4rem;">⚠️ <b>psycopg2 non installato</b> — aggiungi psycopg2-binary al requirements.txt.</div>', unsafe_allow_html=True)
    else:
        # Test connessione reale
        _test_conn = _db_connect()
        if _test_conn:
            try: _test_conn.close()
            except: pass
            st.markdown('<div style="background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.3);border-radius:8px;padding:.5rem .8rem;font-size:.72rem;color:#10B981;margin-bottom:.4rem;">🗄️ <b>Supabase connesso</b> — dati salvati in modo permanente.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.3);border-radius:8px;padding:.5rem .8rem;font-size:.72rem;color:#EF4444;margin-bottom:.4rem;">❌ <b>Supabase: connessione fallita</b> — controlla la stringa SUPABASE_URL nei Secrets. La password nella stringa è corretta?</div>', unsafe_allow_html=True)

    # Mostra ultimo errore di salvataggio se presente
    if st.session_state.get("_last_save_error"):
        st.markdown(f'<div style="background:rgba(239,68,68,.1);border:1px solid #EF444444;border-radius:8px;padding:.5rem .8rem;font-size:.7rem;color:#EF4444;margin-bottom:.4rem;">❌ Errore salvataggio: {st.session_state["_last_save_error"]}</div>', unsafe_allow_html=True)
        if st.button("✕ Chiudi errore", key="btn_clear_err"):
            del st.session_state["_last_save_error"]
            st.rerun()

    # Leggi dai Secrets di Streamlit Cloud (se configurati)
    _sec_ant  = st.secrets.get("ANTHROPIC_API_KEY", "") if hasattr(st, "secrets") else ""
    _sec_news = st.secrets.get("NEWS_API_KEY", "")      if hasattr(st, "secrets") else ""

    if _sec_ant:
        # Chiavi nei Secrets: caricale automaticamente
        st.session_state["_ant_key"]  = _sec_ant
        st.session_state["_news_key"] = _sec_news
        st.markdown('<div style="background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.3);border-radius:8px;padding:.5rem .8rem;font-size:.75rem;color:#10B981;margin-bottom:.5rem;">✅ Chiavi caricate dai Secrets</div>', unsafe_allow_html=True)
        st.text_input("Chiave Anthropic API", value="sk-ant-••••••••", disabled=True, key="ant_key")
        st.text_input("Chiave NewsAPI", value="••••" if _sec_news else "(non impostata)", disabled=True, key="news_key")
    else:
        # Chiavi inserite manualmente: salvale nel session_state appena digitate
        _inp_ant  = st.text_input("Chiave Anthropic API", type="password", placeholder="sk-ant-...", key="ant_key")
        _inp_news = st.text_input("Chiave NewsAPI",       type="password", placeholder="newsapi key...", key="news_key")
        if _inp_ant:  st.session_state["_ant_key"]  = _inp_ant
        if _inp_news: st.session_state["_news_key"] = _inp_news
        if not st.session_state.get("_ant_key"):
            st.markdown('<div style="background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);border-radius:8px;padding:.5rem .8rem;font-size:.72rem;color:#F59E0B;">⚠️ Inserisci la chiave Anthropic per usare il Multi-Agente AI</div>', unsafe_allow_html=True)

    # Variabili globali usate nel resto dell'app
    anthropic_key = st.session_state.get("_ant_key", "")
    news_api_key  = st.session_state.get("_news_key", "")
    st.markdown("---")
    st.markdown("### 📧 Alert Email")
    with st.expander("Configura email"):
        em_from = st.text_input("Gmail mittente", key="em_from", placeholder="tua@gmail.com")
        em_pass = st.text_input("App Password Gmail", type="password", key="em_pass",
                                help="Vai su myaccount.google.com → Sicurezza → Password app")
        em_to   = st.text_input("Email destinatario", key="em_to", placeholder="tua@email.com")
        if st.button("💾 Salva impostazioni email"):
            st.session_state.data["email_settings"] = {"from_email":em_from,"app_password":em_pass,"to_email":em_to}
            save_data(st.session_state.data)
            st.success("✅ Salvato")
    em_sett = st.session_state.data.get("email_settings",{})
    if em_sett.get("from_email"):
        if st.button("📧 Invia report ora", use_container_width=True):
            df_em = build_portfolio_df()
            mkt_em = get_market_data()
            hs_em, _ = compute_health_score(df_em, mkt_em)
            cache_em = st.session_state.data.get("agent_cache",{}).get("results")
            html = build_daily_email(df_em, mkt_em, hs_em, cache_em)
            ok, msg = send_email_alert(em_sett, f"📈 Report Portafoglio {datetime.now().strftime('%d/%m/%Y')}", html)
            st.success(msg) if ok else st.error(msg)
    st.markdown("---")
    now = datetime.now()
    st.markdown(f"**{now.strftime('%d %B %Y')}** — {now.strftime('%H:%M')}")
    st.markdown(f"**Asset:** {len(st.session_state.data['portfolio'])} &nbsp; **Watchlist:** {len(st.session_state.data['watchlist'])}")
    if st.button("🔄 Aggiorna dati", use_container_width=True):
        st.cache_data.clear(); st.rerun()

# ── MARKET DATA & HEALTH SCORE ─────────────────────────────────────────────────
mkt = get_market_data()
vix_now = mkt.get("VIX",{}).get("value",20)
vix_color = "#EF4444" if vix_now>25 else ("#F59E0B" if vix_now>15 else "#10B981")
df_main = build_portfolio_df()
health_score, health_components = compute_health_score(df_main, mkt)
hs_color = "#10B981" if health_score>=70 else ("#F59E0B" if health_score>=40 else "#EF4444")

# ── HEADER ─────────────────────────────────────────────────────────────────────
pnl_total = df_main["P&L €"].sum()
total_val  = df_main["CV €"].sum()
sp500_d = mkt.get("S&P 500",{}).get("delta",0)
ftse_d  = mkt.get("FTSE MIB",{}).get("delta",0)
eurusd  = mkt.get("EUR/USD",{}).get("value",1.08)

st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            margin-bottom:1rem;padding-bottom:.8rem;border-bottom:1px solid #1E2D47;">
  <div style="display:flex;align-items:center;gap:12px;">
    <span style="font-size:1.5rem;">📈</span>
    <div>
      <div style="font-size:1.1rem;font-weight:700;letter-spacing:-.02em;">Investment Intelligence</div>
      <div style="font-size:.7rem;color:#64748B;font-family:'JetBrains Mono',monospace;">Sistema Multi-Agente AI</div>
    </div>
  </div>
  <div style="display:flex;gap:2rem;align-items:center;">
    <div style="text-align:center;">
      <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;letter-spacing:.08em;">Portafoglio</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;font-size:1rem;">€{total_val:,.0f}</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:.75rem;color:{'#10B981' if pnl_total>=0 else '#EF4444'};">{'+' if pnl_total>=0 else ''}€{pnl_total:,.0f}</div>
    </div>
    <div style="width:1px;height:40px;background:#1E2D47;"></div>
    <div style="text-align:center;">
      <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;letter-spacing:.08em;">Score salute</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;font-size:1.4rem;color:{hs_color};">{health_score}</div>
      <div style="font-size:.65rem;color:#64748B;">/100</div>
    </div>
    <div style="width:1px;height:40px;background:#1E2D47;"></div>
    <div style="text-align:center;">
      <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;letter-spacing:.08em;">VIX</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;color:{vix_color};font-size:1rem;">{vix_now:.1f}</div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;letter-spacing:.08em;">S&P 500</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;color:{'#10B981' if sp500_d>=0 else '#EF4444'};font-size:1rem;">{sp500_d:+.2f}%</div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;letter-spacing:.08em;">FTSE MIB</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;color:{'#10B981' if ftse_d>=0 else '#EF4444'};font-size:1rem;">{ftse_d:+.2f}%</div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;letter-spacing:.08em;">EUR/USD</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;font-size:1rem;">{eurusd:.4f}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── TABS ───────────────────────────────────────────────────────────────────────
tab1,tab2,tab3,tab4,tab5,tab6,tab7,tab8,tab9 = st.tabs([
    "🌍 Mercati","💼 Portafoglio","📡 Tecnica","🤖 Multi-Agente AI",
    "👁️ Watchlist","📊 Benchmark & Scenari","✏️ Gestione","💡 Opportunità","🎯 Reversal Radar"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — MERCATI
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-hd">Score salute portafoglio</div>', unsafe_allow_html=True)
    h1, h2 = st.columns([1,3])
    with h1:
        ring_color = hs_color
        st.markdown(f"""<div style="background:#0F1829;border:1px solid #243352;border-radius:14px;
padding:1.5rem;text-align:center;">
<div style="font-size:.65rem;color:#64748B;text-transform:uppercase;letter-spacing:.1em;margin-bottom:.5rem;">Score di salute</div>
<div style="font-family:'JetBrains Mono',monospace;font-size:3.5rem;font-weight:700;color:{ring_color};line-height:1;">{health_score}</div>
<div style="font-size:.75rem;color:#64748B;margin-top:.3rem;">/100</div>
<div style="margin-top:.8rem;font-size:.82rem;color:{ring_color};font-weight:600;">
{"🟢 Ottimo" if health_score>=70 else ("🟡 Discreto" if health_score>=40 else "🔴 Attenzione")}
</div></div>""", unsafe_allow_html=True)
    with h2:
        st.markdown('<div style="font-size:.7rem;color:#64748B;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin-bottom:.6rem;">Componenti del punteggio</div>', unsafe_allow_html=True)
        for comp, data in health_components.items():
            pts = data["pts"]; val = data["val"]
            bar_color = "#10B981" if pts >= 0 else "#EF4444"
            bar_w = min(100, abs(pts) * 6)
            st.markdown(f"""<div style="display:flex;align-items:center;gap:.8rem;margin-bottom:.5rem;
background:#0F1829;border:1px solid #243352;border-radius:8px;padding:.5rem .8rem;">
<div style="width:110px;font-size:.78rem;color:#94A3B8;flex-shrink:0;">{comp}</div>
<div style="flex:1;height:6px;background:#1E2D47;border-radius:3px;overflow:hidden;">
  <div style="width:{bar_w}%;height:100%;background:{bar_color};border-radius:3px;"></div>
</div>
<div style="font-family:'JetBrains Mono',monospace;font-size:.75rem;color:{bar_color};width:40px;text-align:right;">{'+' if pts>=0 else ''}{pts:.0f}</div>
<div style="font-size:.75rem;color:#64748B;min-width:80px;text-align:right;">{val}</div>
</div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-hd">Panoramica mercati</div>', unsafe_allow_html=True)
    cols_mkt = st.columns(6)
    for i,(name,d) in enumerate(mkt.items()):
        with cols_mkt[i]:
            sign = "▲" if d["delta"]>=0 else "▼"
            dc = "up" if d["delta"]>=0 else "dn"
            st.markdown(f"""<div class="kpi-card"><div class="kpi-label">{name}</div>
<div class="kpi-value">{d['value']:,.2f}</div>
<div class="kpi-delta {dc}">{sign} {abs(d['delta']):.2f}%</div></div>""", unsafe_allow_html=True)

    c1, c2 = st.columns([1,2])
    with c1:
        st.markdown('<div class="section-hd">VIX Gauge</div>', unsafe_allow_html=True)
        fig_vix = go.Figure(go.Indicator(mode="gauge+number", value=vix_now,
            gauge={"axis":{"range":[0,80],"tickcolor":"#64748B"},"bar":{"color":"#3B82F6"},
                   "steps":[{"range":[0,15],"color":"rgba(16,185,129,.2)"},
                             {"range":[15,25],"color":"rgba(245,158,11,.2)"},
                             {"range":[25,80],"color":"rgba(239,68,68,.2)"}]},
            number={"font":{"color":"#E8EDF5","family":"JetBrains Mono"}}))
        fig_vix.update_layout(paper_bgcolor="rgba(0,0,0,0)",font_color="#E8EDF5",
                               height=200,margin=dict(t=20,b=0,l=20,r=20))
        st.plotly_chart(fig_vix, use_container_width=True)
        vix_label,vix_lc = (("🟢 Calmo — risk on","#10B981") if vix_now<15 else
                            (("🟡 Moderato — attenzione","#F59E0B") if vix_now<25 else
                             ("🔴 Paura elevata — contrarian","#EF4444")))
        st.markdown(f'<div style="text-align:center;font-size:.82rem;color:{vix_lc};font-weight:600;">{vix_label}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="section-hd">Indici — 1 mese normalizzato</div>', unsafe_allow_html=True)
        idx_data = get_index_history()
        if idx_data:
            fig_idx = go.Figure()
            for i,(name,s) in enumerate(idx_data.items()):
                norm = (s/s.iloc[0]-1)*100
                fig_idx.add_trace(go.Scatter(x=s.index,y=norm,name=name,
                    line=dict(color=["#3B82F6","#10B981","#F59E0B"][i],width=2)))
            fig_idx.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(22,32,53,.6)",
                font_color="#E8EDF5",xaxis=dict(gridcolor="#1E2D47",color="#64748B"),
                yaxis=dict(gridcolor="#1E2D47",ticksuffix="%"),
                legend=dict(bgcolor="rgba(0,0,0,0)",orientation="h",yanchor="bottom",y=1.02),
                height=230,margin=dict(t=10,b=10))
            st.plotly_chart(fig_idx, use_container_width=True)

    st.markdown('<div class="section-hd">Stagionalità — pattern storici di marzo</div>', unsafe_allow_html=True)
    hints = [("Azionario","Correzioni tipiche a marzo. Rimbalzi tecnici dopo sell-off.","#F59E0B"),
             ("Obbligazioni","Riunione Fed in avvicinamento — volatilità sui tassi.","#F59E0B"),
             ("Oro","Storicamente forte in Q1. Hedging attivo in periodi di incertezza.","#10B981"),
             ("Crypto","Alta volatilità stagionale. Q2 storicamente più debole.","#EF4444")]
    hc = st.columns(4)
    for i,(asset,desc,color) in enumerate(hints):
        with hc[i]:
            st.markdown(f"""<div style="background:{color}12;border:1px solid {color}33;border-radius:10px;padding:.9rem;">
<div style="font-weight:700;color:{color};font-size:.85rem;margin-bottom:.3rem;">{asset}</div>
<div style="font-size:.78rem;color:#94A3B8;line-height:1.5;">{desc}</div></div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PORTAFOGLIO
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    df = build_portfolio_df()
    fx = get_fx_rates()
    total = df["CV €"].sum()
    pnl_tot = df["P&L €"].sum()
    pnl_pct = pnl_tot/(total-pnl_tot)*100 if (total-pnl_tot)>0 else 0
    best  = df.nlargest(1,"P&L %").iloc[0]
    worst = df.nsmallest(1,"P&L %").iloc[0]

    fx_parts = " · ".join([f"{k}/EUR: <b style='color:#E8EDF5'>{v:.4f}</b>" for k,v in fx.items() if k!="EUR"])
    st.markdown(f'<div style="background:#0F1829;border:1px solid #243352;border-radius:8px;padding:.5rem 1rem;font-size:.75rem;color:#64748B;margin-bottom:.8rem;">💱 Cambi live — {fx_parts}</div>', unsafe_allow_html=True)

    k1,k2,k3,k4 = st.columns(4)
    with k1: st.metric("💼 Totale",f"€ {total:,.0f}")
    with k2: st.metric("📈 P&L",f"€ {pnl_tot:,.0f}",f"{pnl_pct:+.2f}%")
    with k3: st.metric("🏆 Best",best["Nome"][:18],f"{best['P&L %']:+.1f}%")
    with k4: st.metric("⚠️ Worst",worst["Nome"][:18],f"{worst['P&L %']:+.1f}%")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-hd">Allocazione per categoria</div>', unsafe_allow_html=True)
        alloc = df.groupby("Categoria")["CV €"].sum().reset_index()
        fig_pie = go.Figure(go.Pie(labels=alloc["Categoria"],values=alloc["CV €"],hole=.55,
            marker_colors=[CATEGORY_COLORS.get(c,"#64748B") for c in alloc["Categoria"]],
            hovertemplate="%{label}<br>€ %{value:,.0f}<br>%{percent}<extra></extra>"))
        fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)",font_color="#E8EDF5",
            showlegend=True,legend=dict(bgcolor="rgba(0,0,0,0)",font_size=10),
            height=280,margin=dict(t=0,b=0))
        st.plotly_chart(fig_pie, use_container_width=True)
    with c2:
        st.markdown('<div class="section-hd">P&L per posizione</div>', unsafe_allow_html=True)
        ds = df.sort_values("P&L €")
        fig_bar = go.Figure(go.Bar(x=ds["P&L €"],y=ds["Nome"].str[:18],orientation="h",
            marker_color=["#EF4444" if x<0 else "#10B981" for x in ds["P&L €"]],
            hovertemplate="%{y}<br>€ %{x:,.0f}<extra></extra>"))
        fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(22,32,53,.6)",
            font_color="#E8EDF5",xaxis=dict(gridcolor="#1E2D47",tickprefix="€"),
            yaxis=dict(tickfont_size=9),height=280,margin=dict(t=0,b=0,l=5))
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown('<div class="section-hd">Esposizione valutaria</div>', unsafe_allow_html=True)
    val_exp = df.groupby("Valuta")["CV €"].sum()
    vcols = {"EUR":"#10B981","USD":"#3B82F6","GBP":"#F59E0B","DKK":"#8B5CF6"}
    vc = st.columns(len(val_exp))
    for i,(v,amt) in enumerate(val_exp.items()):
        with vc[i]:
            c = vcols.get(v,"#64748B")
            st.markdown(f"""<div style="background:{c}12;border:1px solid {c}33;border-radius:10px;padding:.8rem;text-align:center;">
<div style="font-family:'JetBrains Mono',monospace;font-weight:700;color:{c};font-size:1.1rem;">{v}</div>
<div style="font-weight:600;color:#E8EDF5;">€ {amt:,.0f}</div>
<div style="font-size:.75rem;color:#64748B;">{amt/total*100:.1f}%</div></div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-hd">Dettaglio posizioni</div>', unsafe_allow_html=True)
    src_map = {"live":"🔵 live","carico":"🟡 carico","manuale":"✏️ manuale"}
    disp = df.copy()
    disp["CV €"]     = disp["CV €"].apply(lambda x: f"€ {x:,.0f}")
    disp["P&L €"]    = disp["P&L €"].apply(lambda x: f"€ {x:+,.0f}")
    disp["P&L %"]    = disp["P&L %"].apply(lambda x: f"{x:+.2f}%")
    disp["P.Carico"] = disp["P.Carico"].apply(lambda x: f"{x:,.3f}")
    disp["P.Attuale"]= disp["P.Attuale"].apply(lambda x: f"{x:,.3f}")
    disp["Fonte"]    = disp["Fonte"].map(src_map)
    st.dataframe(disp[["Nome","Categoria","Valuta","P.Carico","P.Attuale","Fonte","Quantità","CV €","P&L €","P&L %"]],
        use_container_width=True, hide_index=True, height=380)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — TECNICA & RISCHIO
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-hd">Semaforo tecnico</div>', unsafe_allow_html=True)
    with st.expander("📖 Legenda indicatori"):
        l1,l2,l3 = st.columns(3)
        legends = [
            ("RSI (Relative Strength Index)", "Va da 0 a 100. Sopra 70 = ipercomprato (rischio correzione). Sotto 30 = ipervenduto (possibile rimbalzo). Zona 40-60 = neutrale."),
            ("MA50 / MA200 (Medie Mobili)", "Media degli ultimi 50 o 200 giorni. Prezzo sopra MA50/MA200 = trend positivo. MA50 > MA200 = trend solido su tutti gli orizzonti."),
            ("MACD Histogram", "Differenza tra medie esponenziali 12 e 26 giorni. Valore positivo = momentum rialzista. Negativo = momentum ribassista. Più è grande, più è forte."),
            ("Golden Cross / Death Cross", "Segnali rari e molto significativi. Golden Cross 🌟 = MA50 supera MA200 (forte rialzo). Death Cross ⚠️ = MA50 scende sotto MA200 (forte ribasso)."),
            ("Bande di Bollinger", "Canale statistico (media ± 2 deviazioni standard). Sopra la banda superiore = possibile ipercomprato. Sotto la banda inferiore = possibile ipervenduto."),
            ("Supporto / Resistenza", "Livelli storici dove il titolo ha rimbalzato (supporto) o si è bloccato (resistenza). Una resistenza rotta diventa supporto."),
        ]
        for i, (title, desc) in enumerate(legends):
            with [l1,l2,l3][i%3]:
                st.markdown(f'<div class="tooltip-box" style="margin-bottom:.5rem;"><b>{title}</b><br>{desc}</div>', unsafe_allow_html=True)
        st.markdown("""<div class="tooltip-box"><b>Come leggere il semaforo:</b>
🟢 INCREMENTA = score ≥ 3 (multipli indicatori allineati al rialzo) &nbsp;|&nbsp;
🟡 TIENI/ATTENZIONE = score -1/+2 (segnali misti) &nbsp;|&nbsp;
🔴 ALLEGGERISCI = score ≤ -2 (multipli indicatori deteriorati) &nbsp;|&nbsp;
⚪ N/D = asset senza ticker Yahoo</div>""", unsafe_allow_html=True)

    tradeable_items = [p for p in st.session_state.data["portfolio"] if p["ticker"] != "N/A"]
    non_tradeable   = [p for p in st.session_state.data["portfolio"] if p["ticker"] == "N/A"]

    tech_rows = []
    with st.spinner("Calcolo indicatori..."):
        for item in tradeable_items:
            td = get_technical(item["ticker"])
            em, label, reason = tech_signal(td)
            tech_rows.append({"Segnale":em,"Nome":item["nome"][:22],"Ticker":item["ticker"],
                "Raccomandazione":label,
                "RSI":f"{td['rsi']:.0f}" if td else "—",
                "MACD H":f"{td['macd_h']:+.3f}" if td else "—",
                "MA50":f"{td['ma50']:,.2f}" if td and td["ma50"] else "—",
                "MA200":f"{td['ma200']:,.2f}" if td and td["ma200"] else "—",
                "Cross":("🌟 Golden" if td["cross"]=="golden" else "💀 Death") if td and td["cross"] else "—",
                "Motivazione":reason})
    if tech_rows:
        st.dataframe(pd.DataFrame(tech_rows), use_container_width=True, hide_index=True, height=380)

    # ── RIEPILOGO PORTAFOGLIO ────────────────────────────────────────────────────
    st.markdown('<div class="section-hd">📋 Riepilogo del tuo portafoglio — cosa fare ora</div>', unsafe_allow_html=True)

    if tech_rows:
        df_tech = pd.DataFrame(tech_rows)
        n_incr  = (df_tech["Raccomandazione"] == "INCREMENTA").sum()
        n_tieni = df_tech["Raccomandazione"].isin(["TIENI","ATTENZIONE"]).sum()
        n_alle  = (df_tech["Raccomandazione"] == "ALLEGGERISCI").sum()
        total_tech = len(df_tech)

        # Calcola RSI medio, titoli overbought/oversold
        rsi_vals = [float(r) for r in df_tech["RSI"] if r != "—"]
        rsi_medio = sum(rsi_vals)/len(rsi_vals) if rsi_vals else 50
        overbought = sum(1 for r in rsi_vals if r > 70)
        oversold   = sum(1 for r in rsi_vals if r < 30)

        # Calcola P&L e allocazione dal df_main
        pnl_tot_euro = df_main["P&L €"].sum() if not df_main.empty else 0
        pnl_tot_pct  = (df_main["P&L %"].mean()) if not df_main.empty else 0
        total_val_pf = df_main["CV €"].sum() if not df_main.empty else 0

        # Colore dello stato generale
        if n_incr > n_alle and rsi_medio < 65:
            stato_color = "#10B981"; stato_label = "🟢 Portafoglio in buona salute tecnica"
        elif n_alle > n_incr or rsi_medio > 70:
            stato_color = "#EF4444"; stato_label = "🔴 Segnali di debolezza da non ignorare"
        else:
            stato_color = "#F59E0B"; stato_label = "🟡 Situazione mista — selettività necessaria"

        # Box riepilogo compatto
        vix_val     = mkt.get("VIX",{}).get("value",20)
        sp500_delta = mkt.get("S&P 500",{}).get("delta",0)
        eurusd_val  = mkt.get("EUR/USD",{}).get("value",1.08)
        total_val_pf= df_main["CV €"].sum() if not df_main.empty else 0
        pnl_tot_euro= df_main["P&L €"].sum() if not df_main.empty else 0
        alloc_cat   = {}
        if not df_main.empty and total_val_pf > 0:
            alloc_cat = (df_main.groupby("Categoria")["CV €"].sum() / total_val_pf * 100).to_dict()
        best_items  = df_main.nlargest(3,"P&L %")[["Nome","P&L %"]].values.tolist() if not df_main.empty else []
        worst_items = df_main.nsmallest(3,"P&L %")[["Nome","P&L %"]].values.tolist() if not df_main.empty else []

        # ── 4 KPI box ────────────────────────────────────────────────────────
        kpi_html = f"""<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:.7rem;margin-bottom:1rem;">
  <div style="background:#162035;border-radius:8px;padding:.7rem;text-align:center;">
    <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;margin-bottom:.3rem;">Da incrementare</div>
    <div style="font-size:1.6rem;font-weight:700;color:#10B981;">{n_incr}</div>
    <div style="font-size:.65rem;color:#64748B;">su {total_tech} analizzati</div>
  </div>
  <div style="background:#162035;border-radius:8px;padding:.7rem;text-align:center;">
    <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;margin-bottom:.3rem;">Da tenere</div>
    <div style="font-size:1.6rem;font-weight:700;color:#F59E0B;">{n_tieni}</div>
    <div style="font-size:.65rem;color:#64748B;">su {total_tech} analizzati</div>
  </div>
  <div style="background:#162035;border-radius:8px;padding:.7rem;text-align:center;">
    <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;margin-bottom:.3rem;">Da alleggerire</div>
    <div style="font-size:1.6rem;font-weight:700;color:#EF4444;">{n_alle}</div>
    <div style="font-size:.65rem;color:#64748B;">su {total_tech} analizzati</div>
  </div>
  <div style="background:#162035;border-radius:8px;padding:.7rem;text-align:center;">
    <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;margin-bottom:.3rem;">RSI medio portafoglio</div>
    <div style="font-size:1.6rem;font-weight:700;color:{'#EF4444' if rsi_medio>65 else ('#10B981' if rsi_medio<40 else '#E8EDF5')}">{rsi_medio:.0f}</div>
    <div style="font-size:.65rem;color:#64748B;">{'caldo — attenzione' if rsi_medio>65 else ('freddo — opportunità' if rsi_medio<40 else 'neutro')}</div>
  </div>
</div>"""
        if n_incr > n_alle and rsi_medio < 65:
            stato_color = "#10B981"; stato_label = "🟢 Portafoglio in buona salute — mercati favorevoli"
        elif n_alle > n_incr or vix_val > 30:
            stato_color = "#EF4444"; stato_label = "🔴 Segnali di attenzione — prudenza consigliata"
        else:
            stato_color = "#F59E0B"; stato_label = "🟡 Situazione mista — selettività necessaria"
        st.markdown(
            f'<div style="background:#0F1829;border:1px solid #2E4070;border-radius:12px;padding:1.2rem 1.4rem;margin-bottom:.8rem;">'
            f'<div style="font-size:.72rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:{stato_color};margin-bottom:.8rem;">{stato_label}</div>'
            + kpi_html + '</div>', unsafe_allow_html=True)

        # ── Colonne: analisi narrativa + esposizioni ──────────────────────────
        col_narr, col_exp = st.columns([3, 2])
        with col_narr:
            lines = []
            # 1. Stato tecnico
            if n_incr > n_alle:
                lines.append(f"I tuoi titoli mostrano <b>prevalenza di segnali positivi</b> ({n_incr} da incrementare vs {n_alle} da alleggerire). Momentum complessivo {'forte' if rsi_medio>60 else 'moderato'} con RSI medio {rsi_medio:.0f}.")
            elif n_alle > n_incr:
                lines.append(f"Il portafoglio mostra <b>prevalenza di segnali negativi</b> ({n_alle} da alleggerire vs {n_incr} da incrementare). Momento di rivedere le posizioni deboli prima di aggiungere nuovi titoli.")
            else:
                lines.append(f"Il portafoglio è in <b>fase di transizione</b> con segnali misti: {n_incr} titoli positivi e {n_alle} negativi. Sii selettivo — non tutti i titoli meritano lo stesso trattamento.")
            # 2. Ipercomprato/ipervenduto
            if overbought > 0:
                ovb_names = [str(r["Nome"]) for _, r in df_tech.iterrows() if r["RSI"] != "—" and float(r["RSI"]) > 70][:3]
                lines.append(f"<b style='color:#EF4444'>Surriscaldamento:</b> {overbought} titoli con RSI sopra 70 ({', '.join(ovb_names)}). Hanno corso troppo velocemente — evita di aggiungere ora, aspetta un respiro del prezzo.")
            if oversold > 0:
                ovs_names = [str(r["Nome"]) for _, r in df_tech.iterrows() if r["RSI"] != "—" and float(r["RSI"]) < 30][:3]
                lines.append(f"<b style='color:#10B981'>Possibili opportunità:</b> {oversold} titoli con RSI sotto 30 ({', '.join(ovs_names)}). Eccessivamente venduti — se i fondamentali reggono, questi livelli possono essere interessanti.")
            # 3. Contesto macro + notizie
            vix_desc = "basso — mercati calmi, propendono per il rischio" if vix_val < 15 else ("elevato — mercati nervosi, meglio difendersi" if vix_val > 25 else "moderato — nessun segnale di panico né euforia")
            sp_desc = "in rialzo" if sp500_delta > 0 else "in calo"
            eur_desc = "l'euro forte penalizza le posizioni in USD" if eurusd_val > 1.10 else ("cambio neutro per USD" if eurusd_val > 1.05 else "euro debole amplifica i movimenti sui titoli USA")
            lines.append(f"<b>Contesto macro:</b> VIX a {vix_val:.1f} ({vix_desc}). S&P500 {sp_desc} oggi ({sp500_delta:+.2f}%). EUR/USD {eurusd_val:.4f} — {eur_desc}.")
            # 4. Best/worst
            if best_items:
                best_str  = " · ".join([f"<b>{str(n)[:16]}</b> <span style='color:#10B981'>{float(p):+.1f}%</span>" for n,p in best_items])
                worst_str = " · ".join([f"<b>{str(n)[:16]}</b> <span style='color:#EF4444'>{float(p):+.1f}%</span>" for n,p in worst_items])
                lines.append(f"<b>Top performer:</b> {best_str}<br><b>Peggiori:</b> {worst_str}")
            # 5. Notizie
            cached_news_s = st.session_state.get("last_news_list", [])
            if cached_news_s:
                nt = [n["title"] for n in cached_news_s[:4]]
                lines.append("<b>News di mercato oggi:</b><br>" + "<br>".join([f"• {t[:85]}{'…' if len(t)>85 else ''}" for t in nt]))
            # 6. Suggerimento pratico
            if n_alle > 0 and pnl_tot_euro > 0:
                lines.append(f"<b style='color:#F59E0B'>Suggerimento:</b> Sei in guadagno complessivo di €{pnl_tot_euro:,.0f}. Valuta di alleggerire i {n_alle} titoli con segnali negativi per cristallizzare i profitti e ridurre il rischio.")
            elif n_incr >= 2:
                lines.append(f"<b style='color:#10B981'>Suggerimento:</b> Ci sono {n_incr} titoli con segnali favorevoli. Prima di incrementare, verifica che nessun titolo superi il 15% del portafoglio totale.")
            st.markdown('<div style="background:#0F1829;border:1px solid #2E4070;border-radius:10px;padding:1.1rem 1.3rem;font-size:.83rem;line-height:1.85;color:#94A3B8;">' + "<br><br>".join(lines) + '</div>', unsafe_allow_html=True)

        with col_exp:
            st.markdown('<div style="font-size:.68rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#64748B;margin-bottom:.5rem;">Esposizione per categoria</div>', unsafe_allow_html=True)
            cat_info = {
                "Azioni":        ("#3B82F6","Alta volatilità. Sensibili a utili, macro, sentiment."),
                "ETF":           ("#10B981","Diversificazione. Rischio sistematico sull'indice."),
                "Obbligazioni":  ("#F59E0B","Salgono quando i tassi scendono. Rischio duration."),
                "Crypto":        ("#8B5CF6","Altissima volatilità. Correlata al risk appetite."),
                "Materie Prime": ("#F97316","Hedge inflazione. Correlata al dollaro e ciclo."),
                "Certificati":   ("#06B6D4","Rischio emittente. Valuta la solidità della banca."),
            }
            for cat in ["Azioni","ETF","Obbligazioni","Crypto","Materie Prime","Certificati"]:
                pct = alloc_cat.get(cat, 0)
                if pct < 0.3: continue
                cc, cr = cat_info.get(cat, ("#64748B",""))
                bar_w = min(100, int(pct))
                alert = " ⚠️" if pct > 40 else (" ✅" if pct < 20 else "")
                st.markdown(
                    f'<div style="background:#162035;border-radius:8px;padding:.55rem .8rem;margin-bottom:.4rem;">'
                    f'<div style="display:flex;justify-content:space-between;margin-bottom:.25rem;">'
                    f'<span style="font-size:.78rem;font-weight:600;color:#E8EDF5;">{cat}{alert}</span>'
                    f'<span style="font-size:.82rem;color:{cc};font-weight:700;">{pct:.1f}%</span></div>'
                    f'<div style="background:#0F1829;border-radius:3px;height:5px;margin-bottom:.3rem;">'
                    f'<div style="width:{bar_w}%;height:5px;background:{cc};border-radius:3px;"></div></div>'
                    f'<div style="font-size:.67rem;color:#64748B;line-height:1.35;">{cr}</div></div>',
                    unsafe_allow_html=True)
            st.markdown('<div style="font-size:.68rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#64748B;margin:.7rem 0 .4rem;">Valute</div>', unsafe_allow_html=True)
            if not df_main.empty and total_val_pf > 0:
                val_exp_d = (df_main.groupby("Valuta")["CV €"].sum() / total_val_pf * 100).to_dict()
                val_colors = {"EUR":"#10B981","USD":"#3B82F6","GBP":"#F59E0B","DKK":"#8B5CF6"}
                for val_k, pct_v in sorted(val_exp_d.items(), key=lambda x: -x[1]):
                    if pct_v < 0.5: continue
                    vc = val_colors.get(val_k, "#64748B")
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;padding:.28rem 0;border-bottom:1px solid #1E2D47;font-size:.8rem;">'
                        f'<span style="color:#94A3B8;">{val_k}</span>'
                        f'<span style="color:{vc};font-weight:700;">{pct_v:.1f}%</span></div>',
                        unsafe_allow_html=True)

    st.markdown('<div class="section-hd">Analisi dettagliata — perché fare questa scelta su ogni titolo</div>', unsafe_allow_html=True)
    st.caption("Espandi ogni titolo per i dati tecnici e la spiegazione in linguaggio semplice.")

    for idx_t, item_t in enumerate(tradeable_items):
        td_t   = get_technical(item_t["ticker"])
        em_t, lbl_t, reason_t = tech_signal(td_t)
        sc_map = {"INCREMENTA":"#10B981","TIENI":"#F59E0B","ATTENZIONE":"#F59E0B","ALLEGGERISCI":"#EF4444","N/D":"#64748B"}
        sc_t   = sc_map.get(lbl_t, "#64748B")
        with st.expander(em_t + "  " + item_t["nome"] + " (" + item_t["ticker"] + ")  —  " + lbl_t):
            col_ind, col_ai = st.columns([1, 2])
            with col_ind:
                if td_t:
                    rsi_v  = td_t["rsi"]; macd_v = td_t["macd_h"]
                    rsi_lb = "ipercomprato 🔥" if rsi_v>70 else ("ipervenduto 💎" if rsi_v<30 else "neutro ✓")
                    rsi_c  = "#EF4444" if rsi_v>70 else ("#10B981" if rsi_v<30 else "#94A3B8")
                    mac_c  = "#10B981" if macd_v>0 else "#EF4444"
                    mac_lb = "↑ rialzista" if macd_v>0 else "↓ ribassista"
                    ma50s  = str(round(td_t["ma50"],2)) if td_t["ma50"] else "—"
                    ma200s = str(round(td_t["ma200"],2)) if td_t["ma200"] else "—"
                    cross_s= "🌟 Golden Cross" if td_t["cross"]=="golden" else ("💀 Death Cross" if td_t["cross"]=="death" else "—")
                    rows_html = (
                        "<div style='color:#64748B;'>Prezzo</div><div style='font-family:monospace;'>" + str(round(td_t["price"],2)) + "</div>"
                        "<div style='color:#64748B;'>RSI</div><div style='color:" + rsi_c + ";font-family:monospace;'>" + str(round(rsi_v)) + " — " + rsi_lb + "</div>"
                        "<div style='color:#64748B;'>MACD</div><div style='color:" + mac_c + ";font-family:monospace;'>" + ("+"+str(round(macd_v,3)) if macd_v>0 else str(round(macd_v,3))) + " " + mac_lb + "</div>"
                        "<div style='color:#64748B;'>MA50</div><div style='font-family:monospace;'>" + ma50s + "</div>"
                        "<div style='color:#64748B;'>MA200</div><div style='font-family:monospace;'>" + ma200s + "</div>"
                        "<div style='color:#64748B;'>Supporto</div><div style='color:#10B981;font-family:monospace;'>" + str(round(td_t["support"],2)) + "</div>"
                        "<div style='color:#64748B;'>Resistenza</div><div style='color:#EF4444;font-family:monospace;'>" + str(round(td_t["resistance"],2)) + "</div>"
                        "<div style='color:#64748B;'>Cross</div><div>" + cross_s + "</div>"
                    )
                    st.markdown(
                        "<div style='background:#0F1829;border:1px solid #243352;border-radius:10px;padding:1rem;'>"
                        "<div style='font-size:.65rem;color:#64748B;text-transform:uppercase;margin-bottom:.8rem;'>Indicatori tecnici</div>"
                        "<div style='display:grid;grid-template-columns:1fr 1fr;gap:.45rem;font-size:.8rem;'>" + rows_html + "</div>"
                        "<div style='margin-top:.8rem;background:" + sc_t + "20;border:1px solid " + sc_t + "40;border-radius:6px;padding:.5rem .7rem;font-size:.78rem;color:" + sc_t + ";font-weight:600;'>"
                        + em_t + " " + lbl_t + " — " + reason_t + "</div></div>",
                        unsafe_allow_html=True)
                else:
                    st.info("Dati tecnici non disponibili per questo ticker")

            with col_ai:
                # ── Spiegazione automatica GRATUITA (solo dati tecnici Yahoo Finance) ──
                def explain_free(td, lbl, nome, ticker, pnl_pct=None, cv_eur=None, peso_pct=None):
                    """Genera spiegazione in linguaggio semplice dai dati tecnici. Zero costi API."""
                    if not td:
                        return "<i style='color:#64748B'>Dati tecnici non disponibili per questo ticker.</i>"

                    parts = []
                    p = td["price"]; rsi = td["rsi"]; macd = td["macd_h"]
                    ma50 = td["ma50"]; ma200 = td["ma200"]
                    sup = td["support"]; res = td["resistance"]
                    cross = td["cross"]

                    # 1. TREND GENERALE
                    if ma50 and ma200:
                        if p > ma50 and p > ma200:
                            trend = "Il titolo è <b>in trend positivo</b>: il prezzo è sopra le sue medie storiche sia di breve che di lungo periodo. Questo è un segnale incoraggiante."
                        elif p > ma50 and p < ma200:
                            trend = "Il titolo mostra un <b>recupero di breve periodo</b> ma è ancora sotto la media di lungo termine. Il rimbalzo è in corso, ma non è ancora confermato su scala ampia."
                        elif p < ma50 and p > ma200:
                            trend = "Il titolo è <b>in una fase di debolezza temporanea</b>: ha incrociato al ribasso la media di breve (50 giorni) ma regge ancora quella di lungo (200 giorni). Situazione da monitorare."
                        else:
                            trend = "Il titolo è <b>sotto entrambe le medie storiche</b> (breve e lungo periodo). Il trend è negativo e richiede cautela."
                    elif ma50:
                        trend = "Il titolo è " + ("sopra" if p > ma50 else "sotto") + " la sua media mobile a 50 giorni — segnale di trend " + ("positivo" if p > ma50 else "negativo") + " di breve periodo."
                    else:
                        trend = "Dati storici limitati per calcolare il trend completo."
                    parts.append("<b>📈 SITUAZIONE ATTUALE</b><br>" + trend)

                    # 2. MOMENTUM (RSI + MACD)
                    if rsi > 75:
                        rsi_txt = f"Il <b>momentum è molto alto</b> (RSI {rsi:.0f}): il titolo ha corso tanto e in breve tempo. Significa che molti stanno comprando e il prezzo potrebbe essere 'caldo'. Non è il momento migliore per entrare — meglio aspettare un respiro."
                    elif rsi > 60:
                        rsi_txt = f"Il <b>momentum è positivo</b> (RSI {rsi:.0f}): il titolo sale con forza ma senza esagerare. Chi compra ora è in una posizione ragionevole, ma occorre tenere d'occhio un'eventuale correzione."
                    elif rsi < 25:
                        rsi_txt = f"Il titolo è <b>molto venduto</b> (RSI {rsi:.0f}): molti stanno uscendo e il prezzo potrebbe sembrare conveniente. Attenzione però: a volte i titoli 'economici' continuano a scendere se il problema è strutturale."
                    elif rsi < 40:
                        rsi_txt = f"Il titolo è <b>in fase di debolezza</b> (RSI {rsi:.0f}): c'è pressione di vendita. Chi è già dentro potrebbe considerare di ridurre; chi vuole entrare conviene aspettare segnali di stabilizzazione."
                    else:
                        rsi_txt = f"Il <b>momentum è neutro</b> (RSI {rsi:.0f}): il titolo non è né ipercomprato né ipervenduto. Situazione bilanciata, adatta per valutare una posizione con calma."

                    macd_txt = "Il <b>MACD</b> (indicatore di forza del movimento) è " + ("<b style='color:#10B981'>positivo</b>: la spinta al rialzo è attiva" if macd > 0 else "<b style='color:#EF4444'>negativo</b>: la spinta al ribasso è prevalente") + "."
                    parts.append("<b>⚡ FORZA DEL MOVIMENTO</b><br>" + rsi_txt + "<br><br>" + macd_txt)

                    # 3. LIVELLI CHIAVE
                    dist_sup = (p - sup) / p * 100
                    dist_res = (res - p) / p * 100
                    key_txt = (
                        f"<b>Supporto a {sup:.2f}</b> ({dist_sup:.1f}% sotto il prezzo attuale): "
                        "è il livello dove il titolo ha storicamente trovato acquirenti. "
                        "Se scende fino a lì potrebbe rimbalzare — ma se lo rompe al ribasso è un segnale negativo.<br>"
                        f"<b>Resistenza a {res:.2f}</b> ({dist_res:.1f}% sopra il prezzo attuale): "
                        "è il livello dove il titolo ha storicamente incontrato venditori. "
                        "Se lo supera con forza, potrebbe andare molto più su."
                    )
                    if cross == "golden":
                        key_txt += "<br>🌟 <b>Golden Cross attivo</b>: la media di 50 giorni ha superato quella di 200 giorni. Storicamente è uno dei segnali più positivi che esistano nel trading tecnico."
                    elif cross == "death":
                        key_txt += "<br>💀 <b>Death Cross attivo</b>: la media di 50 giorni è scesa sotto quella di 200 giorni. È uno dei segnali più negativi del trading tecnico — molti istituzionali escono in questi casi."
                    parts.append("<b>🎯 LIVELLI DA TENERE D'OCCHIO</b><br>" + key_txt)

                    # ── Posizione reale ──────────────────────────────────
                    pos_html = ""
                    if cv_eur is not None or pnl_pct is not None:
                        pos_lines = []
                        if cv_eur is not None and peso_pct is not None:
                            pos_lines.append(f"Hai investito <b>€{cv_eur:,.0f}</b> ({peso_pct:.1f}% del portafoglio totale)")
                        if pnl_pct is not None:
                            c = "#10B981" if pnl_pct >= 0 else "#EF4444"
                            s = "+" if pnl_pct >= 0 else ""
                            pos_lines.append(f"Performance attuale: <b style='color:{c}'>{s}{pnl_pct:.1f}%</b> rispetto al prezzo di acquisto")
                        pos_html = " — ".join(pos_lines) + "."
                    if pos_html:
                        parts.insert(0, "<b>💼 LA TUA POSIZIONE</b><br>" + pos_html)

                    # ── Cosa fare — contestualizzato ──────────────────────────
                    if lbl == "INCREMENTA":
                        if peso_pct and peso_pct > 15:
                            azione_txt = (f"Segnali favorevoli, ma <b>sei già esposto per il {peso_pct:.1f}% del portafoglio</b> su questo titolo. "
                                         f"Aggiungere ancora aumenterebbe la concentrazione oltre i livelli consigliati (max 15%). "
                                         f"Se vuoi incrementare, fallo in piccole dosi. Target: {res:.2f}. Stop: {sup*0.97:.2f}.")
                        else:
                            azione_txt = (f"Segnali favorevoli e la tua esposizione attuale è ragionevole. "
                                         f"Puoi valutare di <b>aumentare gradualmente</b>, idealmente vicino al supporto ({sup:.2f}). "
                                         f"Target tecnico: {res:.2f}. Stop loss: {sup*0.97:.2f}.")
                    elif lbl == "TIENI":
                        azione_txt = (f"Situazione stabile. <b>Mantieni la posizione</b> senza modifiche urgenti. "
                                     f"Tieni d'occhio il supporto a {sup:.2f}: se lo rompe, rivaluta. "
                                     f"Se supera {res:.2f}, potresti considerare un piccolo incremento.")
                    elif lbl == "ATTENZIONE":
                        azione_txt = (f"Segnali contrastanti. <b>Non aggiungere posizione ora.</b> "
                                     f"Osserva le prossime settimane. Livello critico: {sup:.2f}.")
                    else:  # ALLEGGERISCI
                        if pnl_pct is not None and pnl_pct > 15:
                            azione_txt = (f"Segnali negativi e sei <b>in guadagno del {pnl_pct:.1f}%</b>: "
                                         f"ha senso prendere una parte dei profitti ora. "
                                         f"Se scende sotto {sup:.2f}, valuta di uscire completamente.")
                        elif pnl_pct is not None and pnl_pct < -15:
                            azione_txt = (f"Segnali negativi con una <b>perdita del {abs(pnl_pct):.1f}%</b>. "
                                         f"Valuta se le ragioni dell'acquisto sono ancora valide. "
                                         f"Se rompe {sup:.2f} al ribasso, considera di limitare le perdite.")
                        else:
                            azione_txt = (f"Segnali tecnici negativi. <b>Considera di ridurre la posizione.</b> "
                                         f"Non aggiungere. Se rompe {sup:.2f}, valuta di uscire.")
                    parts.append("<b>✅ COSA FARE — LA TUA SITUAZIONE</b><br>" + azione_txt)

                    return "<br><br>".join(parts)

                # Recupera dati posizione reale
                pnl_this = None; cv_this = None; peso_this = None
                if not df_main.empty:
                    match = df_main[df_main["Ticker"] == item_t["ticker"]]
                    if not match.empty:
                        pnl_this  = float(match.iloc[0]["P&L %"])
                        cv_this   = float(match.iloc[0]["CV €"])
                        total_pf  = df_main["CV €"].sum()
                        peso_this = (cv_this / total_pf * 100) if total_pf > 0 else None

                # Spiegazione gratuita contestualizzata alla tua posizione reale
                free_html = explain_free(td_t, lbl_t, item_t["nome"], item_t["ticker"],
                                         pnl_pct=pnl_this, cv_eur=cv_this, peso_pct=peso_this)
                ai_cache_key = "techexp_" + item_t["ticker"].replace("=","X").replace("-","_").replace(".","_")
                ai_cached = st.session_state.get(ai_cache_key)

                st.markdown(
                    '<div style="background:#0F1829;border:1px solid #2E4070;border-radius:10px;padding:1rem 1.2rem;font-size:.82rem;line-height:1.75;">'
                    + free_html + '</div>', unsafe_allow_html=True)

                # Sezione AI opzionale solo per notizie recenti
                if ai_cached:
                    st.markdown('<div style="margin-top:.5rem;background:linear-gradient(135deg,#0D1526,#16213E);border:1px solid #2E4480;border-radius:8px;padding:.8rem 1rem;font-size:.8rem;line-height:1.7;">'
                        '<span style="font-size:.62rem;font-weight:700;color:#8B5CF6;text-transform:uppercase;letter-spacing:.06em;">🤖 Notizie & contesto AI</span><br><br>'
                        + ai_cached + '</div>', unsafe_allow_html=True)
                elif anthropic_key:
                    st.markdown('<div style="font-size:.72rem;color:#64748B;margin-top:.4rem;">💡 Vuoi aggiungere notizie recenti e contesto sull&#39;azienda? Clicca il bottone (usa circa 0.01 EUR di API).</div>', unsafe_allow_html=True)
                    if st.button("🗞️ Aggiungi notizie & contesto AI", key="texp_" + str(idx_t), use_container_width=True):
                        with st.spinner("Analisi AI in corso..."):
                            tech_ctx_s = ""
                            if td_t:
                                tech_ctx_s = (
                                    "RSI=" + str(round(td_t["rsi"],1)) +
                                    ", MACD=" + str(round(td_t["macd_h"],3)) +
                                    ", Prezzo=" + str(round(td_t["price"],2)) +
                                    ", MA50=" + (str(round(td_t["ma50"],2)) if td_t["ma50"] else "N/A") +
                                    ", MA200=" + (str(round(td_t["ma200"],2)) if td_t["ma200"] else "N/A") +
                                    ", Supporto=" + str(round(td_t["support"],2)) +
                                    ", Resistenza=" + str(round(td_t["resistance"],2)) +
                                    ", Cross=" + (td_t["cross"] or "nessuno")
                                )
                            pf_ctx_s = ""
                            if not df_main.empty:
                                pf_ctx_s = "Il portafoglio vale EUR " + str(round(df_main["CV €"].sum()))
                            try:
                                import re as _re
                                cl_t = anthropic.Anthropic(api_key=anthropic_key)
                                # Raccoglie contesto notizie se disponibile
                                news_ctx_s = ""
                                cached_news = st.session_state.get("last_news_list", [])
                                if cached_news:
                                    nome_short = item_t["nome"].split()[0].lower()
                                    relevant = [n["title"] for n in cached_news if nome_short in n["title"].lower()][:3]
                                    if relevant:
                                        news_ctx_s = "Notizie recenti su questo titolo: " + " | ".join(relevant) + ". "
                                vix_ctx = market_data.get("VIX",{}).get("value",20) if "market_data" in dir() else mkt.get("VIX",{}).get("value",20)

                                prompt_s = (
                                    "Analizza " + item_t["nome"] + " (" + item_t["ticker"] + ") in modo completo. "
                                    "Dati tecnici: " + (tech_ctx_s if tech_ctx_s else "non disponibili") + ". "
                                    + pf_ctx_s + ". VIX mercati=" + str(round(vix_ctx,1)) + ". "
                                    + news_ctx_s +
                                    "Scrivi in italiano SEMPLICE (come se spiegassi a un amico che non investe), "
                                    "usando questi 5 paragrafi con titolo in grassetto: "
                                    "**COSA STA FACENDO ORA** Spiega il movimento del titolo in parole comuni. "
                                    "E' in crescita, in calo, fermo? Da quanto tempo? "
                                    "**PERCHE' IL SEGNALE E' " + lbl_t.upper() + "** "
                                    "Spiega ogni indicatore tecnico come se non sapessi cos'e' un RSI: "
                                    "cosa significa praticamente per chi possiede il titolo. "
                                    "**NOTIZIE E AZIENDA** "
                                    "Cosa sta succedendo nell'azienda e nel suo settore? "
                                    "Ci sono eventi recenti (cambi CEO, acquisizioni, utili, cause legali, regolamentazione)? "
                                    "Come il contesto macro (tassi, inflazione, geopolitica) impatta questo titolo specifico? "
                                    "**RISCHIO PRINCIPALE** "
                                    "Qual e' la cosa piu' pericolosa che potrebbe fare scendere questo titolo? "
                                    "Spiegala in modo concreto. "
                                    "**COSA FARE ORA** "
                                    "Azione pratica e chiara: comprare piu' / tenere / ridurre / vendere. "
                                    "A quale prezzo ha senso agire. Quanto tempo aspettare. "
                                    "Una frase finale di riepilogo che anche un bambino capirebbe. "
                                    "Max 280 parole totali. Sii diretto e pratico."
                                )
                                explain = cl_t.messages.create(
                                    model="claude-sonnet-4-20250514", max_tokens=700,
                                    system="Sei un analista finanziario esperto che sa spiegare concetti complessi in modo semplice e comprensibile anche a chi non conosce il trading.",
                                    messages=[{"role": "user", "content": prompt_s}]
                                ).content[0].text
                                expl_html = _re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', explain)
                                expl_html  = expl_html.replace("\n\n", "<br><br>").replace("\n", "<br>")
                                st.session_state[ai_cache_key] = expl_html
                                st.rerun()
                            except Exception as e_t:
                                st.error("Errore: " + str(e_t))
                else:
                    st.caption("Aggiungi chiave Anthropic nella sidebar per notizie e contesto aggiornato")

    if non_tradeable:

        st.markdown('<div class="section-hd">Asset senza prezzo automatico</div>', unsafe_allow_html=True)
        nc = st.columns(3)
        for i, item in enumerate(non_tradeable):
            pm = item.get("prezzo_manuale") or 0
            with nc[i%3]:
                ok = pm > 0
                c = "#10B981" if ok else "#EF4444"
                st.markdown(f"""<div style="background:#0F1829;border:1px solid {c}44;border-left:3px solid {c};border-radius:8px;padding:.8rem;margin-bottom:.5rem;">
<div style="font-weight:600;font-size:.85rem;">{item['nome']}</div>
<div style="font-size:.75rem;color:#64748B;">{item['categoria']} · {item['valuta']}</div>
<div style="font-size:.8rem;margin-top:.4rem;color:{'#10B981' if ok else '#EF4444'};">
{'✏️ Manuale: ' + f"{pm:,.3f}" if ok else '🔴 Vai in Gestione → Aggiornamento rapido'}</div></div>""", unsafe_allow_html=True)

    # Chart tecnico singolo
    st.markdown('<div class="section-hd">Grafico tecnico dettagliato</div>', unsafe_allow_html=True)
    t_names = [p["nome"] for p in tradeable_items]
    t_tickers = [p["ticker"] for p in tradeable_items]
    sel = st.selectbox("Seleziona titolo", range(len(t_names)), format_func=lambda i: f"{t_names[i]} ({t_tickers[i]})", key="sel_chart")
    if sel is not None:
        td = get_technical(t_tickers[sel])
        if td and "history" in td:
            h = td["history"]; c = h["Close"]
            fig_c = go.Figure()
            fig_c.add_trace(go.Candlestick(x=h.index,open=h["Open"],high=h["High"],low=h["Low"],close=c,
                name="Prezzo",increasing_line_color="#10B981",decreasing_line_color="#EF4444"))
            if td["ma50"]:  fig_c.add_trace(go.Scatter(x=h.index,y=c.rolling(50).mean(),name="MA50",line=dict(color="#F59E0B",width=1.5,dash="dot")))
            if td["ma200"]: fig_c.add_trace(go.Scatter(x=h.index,y=c.rolling(200).mean(),name="MA200",line=dict(color="#8B5CF6",width=1.5,dash="dash")))
            bm = c.rolling(20).mean(); bs = c.rolling(20).std()
            fig_c.add_trace(go.Scatter(x=h.index,y=bm+2*bs,name="Boll.Sup",line=dict(color="#3B82F6",width=1,dash="dot"),opacity=.6))
            fig_c.add_trace(go.Scatter(x=h.index,y=bm-2*bs,name="Boll.Inf",line=dict(color="#3B82F6",width=1,dash="dot"),fill="tonexty",fillcolor="rgba(59,130,246,.05)",opacity=.6))
            fig_c.add_hline(y=td["support"],line_color="#10B981",line_dash="dot",annotation_text=f"Supp. {td['support']:.2f}",annotation_font_color="#10B981")
            fig_c.add_hline(y=td["resistance"],line_color="#EF4444",line_dash="dot",annotation_text=f"Res. {td['resistance']:.2f}",annotation_font_color="#EF4444")
            fig_c.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(22,32,53,.8)",
                font_color="#E8EDF5",xaxis_rangeslider_visible=False,
                xaxis=dict(gridcolor="#1E2D47"),yaxis=dict(gridcolor="#1E2D47"),
                legend=dict(bgcolor="rgba(0,0,0,0)",orientation="h"),height=360,margin=dict(t=5,b=5))
            st.plotly_chart(fig_c, use_container_width=True)
            d_ = c.diff(); rsi_s = 100-100/(1+d_.clip(lower=0).rolling(14).mean()/(-d_.clip(upper=0)).rolling(14).mean().replace(0,1e-9))
            fig_rsi = go.Figure(go.Scatter(x=h.index,y=rsi_s,line=dict(color="#3B82F6",width=2),fill="tonexty",fillcolor="rgba(59,130,246,.08)"))
            fig_rsi.add_hline(y=70,line_color="#EF4444",line_dash="dot",annotation_text="Ipercomprato 70")
            fig_rsi.add_hline(y=30,line_color="#10B981",line_dash="dot",annotation_text="Ipervenduto 30")
            fig_rsi.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(22,32,53,.8)",
                font_color="#E8EDF5",xaxis=dict(gridcolor="#1E2D47"),yaxis=dict(gridcolor="#1E2D47",range=[0,100]),
                height=150,margin=dict(t=0,b=5),showlegend=False)
            st.plotly_chart(fig_rsi, use_container_width=True)

    # Risk
    st.markdown('<div class="section-hd">Risk management</div>', unsafe_allow_html=True)
    r1,r2 = st.columns(2)
    with r1:
        dw = df[["Nome","Categoria","CV €"]].copy()
        dw["Peso %"] = dw["CV €"]/dw["CV €"].sum()*100
        dw = dw.sort_values("Peso %",ascending=False)
        fig_w = go.Figure(go.Bar(x=dw["Nome"].str[:16],y=dw["Peso %"],
            marker_color=[CATEGORY_COLORS.get(c,"#64748B") for c in dw["Categoria"]],
            hovertemplate="%{x}<br>%{y:.1f}%<extra></extra>"))
        fig_w.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(22,32,53,.6)",
            font_color="#E8EDF5",xaxis=dict(tickangle=-40,gridcolor="#1E2D47",tickfont_size=9),
            yaxis=dict(gridcolor="#1E2D47",ticksuffix="%"),height=260,margin=dict(t=5,b=70))
        st.plotly_chart(fig_w, use_container_width=True)
        top3 = dw.head(3)["Peso %"].sum()
        if top3 > 40: st.warning(f"⚠️ Top 3 posizioni = {top3:.1f}% — concentrazione elevata")
    with r2:
        valid_t = tuple((p["nome"][:12],p["ticker"]) for p in tradeable_items[:14])
        @st.cache_data(ttl=3600)
        def get_corr(t_tuple):
            try:
                data = {}
                for name, ticker in t_tuple:
                    h = yf.Ticker(ticker).history(period="6mo")
                    if not h.empty: data[name] = h["Close"].pct_change()
                return pd.DataFrame(data).dropna().corr() if len(data)>=2 else None
            except: return None
        corr = get_corr(valid_t)
        if corr is not None:
            fig_h = go.Figure(go.Heatmap(z=corr.values,x=corr.columns,y=corr.index,
                colorscale=[[0,"#EF4444"],[.5,"#162035"],[1,"#10B981"]],zmid=0,zmin=-1,zmax=1,
                text=corr.round(2).values,texttemplate="%{text}",
                hovertemplate="%{x}/%{y}<br>Corr:%{z:.2f}<extra></extra>"))
            fig_h.update_layout(paper_bgcolor="rgba(0,0,0,0)",font_color="#E8EDF5",
                font_size=8,height=260,margin=dict(t=5,b=5))
            st.plotly_chart(fig_h, use_container_width=True)
            st.caption("🟢 Alta correlazione = si muovono insieme | 🔴 Negativa = hedging naturale")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — MULTI-AGENT AI
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    if not anthropic_key:
        st.warning("⚠️ Inserisci la chiave Anthropic API nella sidebar per attivare il sistema multi-agente.")
        st.markdown("""<div class="ai-block">
<b>Il sistema multi-agente:</b><br><br>
🟢 <b>Agente Macro</b> — Contesto economico globale, regime di mercato, rischi e opportunità<br>
🔵 <b>Agente Tecnico</b> — Scansiona tutti i titoli, identifica i migliori e peggiori setup<br>
🟡 <b>Agente Rischio</b> — Concentrazione, valuta, drawdown, ribilanciamento<br>
🟣 <b>Agente Sentiment</b> — Fear & Greed, posizionamento istituzionale, contrarian<br>
🟠 <b>Agente Optimizer</b> — Piano operativo finale: acquisti, vendite, nuove opportunità</div>""", unsafe_allow_html=True)
    else:
        cache = st.session_state.data.get("agent_cache",{})
        today = datetime.now().strftime("%Y-%m-%d")
        cache_valid = cache.get("date")==today and "results" in cache

        cb1, cb2 = st.columns([2,3])
        with cb1:
            run_btn = st.button("🚀 Avvia analisi multi-agente", use_container_width=True)
        with cb2:
            if cache_valid:
                st.markdown(f'<div style="padding:.45rem;font-size:.8rem;color:#10B981;">✅ Analisi di oggi aggiornata alle {cache.get("time","—")}</div>', unsafe_allow_html=True)

        if run_btn:
            news = get_news(news_api_key) if news_api_key else []
            with st.spinner(""):
                results = run_multi_agent_analysis(anthropic_key, df_main, mkt, st.session_state.data["watchlist"], news)
                st.session_state.data["agent_cache"] = {"date":today,"time":datetime.now().strftime("%H:%M"),"results":results}
                # Usa i suggerimenti AI già estratti dentro run_multi_agent_analysis
                try:
                    ai_suggestions = results.get("ai_watchlist_suggestions", [])
                    existing_tickers_wl = {w.get("ticker","").upper() for w in st.session_state.data["watchlist"]}
                    pf_tickers_set2 = {p.get("ticker","").upper() for p in st.session_state.data["portfolio"]}
                    new_ai_count = 0
                    for sugg in ai_suggestions:
                        ticker_up = sugg.get("ticker","").upper()
                        if ticker_up and ticker_up not in existing_tickers_wl and ticker_up not in pf_tickers_set2:
                            sugg["sorgente"] = "ai"
                            sugg["ai_pending"] = False
                            st.session_state.data["watchlist"].append(sugg)
                            existing_tickers_wl.add(ticker_up)
                            new_ai_count += 1
                    if new_ai_count > 0:
                        st.info(f"🤖 {new_ai_count} nuovi titoli AI aggiunti alla Watchlist → vai nel tab 👁️")
                except Exception as e:
                    pass
                save_data(st.session_state.data)
                cache_valid = True
                cache = st.session_state.data["agent_cache"]

        if cache_valid:
            results = cache["results"]
            at1,at2,at3,at4,at5 = st.tabs(["🌍 Macro","📡 Tecnica","⚖️ Rischio","🧠 Sentiment","🎯 Piano Operativo"])
            for at, lbl in zip([at1,at2,at3,at4,at5],["macro","tecnica","rischio","sentiment","ottimizzazione"]):
                with at:
                    st.markdown(f'<div class="ai-block">{results.get(lbl,"—")}</div>', unsafe_allow_html=True)

        news = get_news(news_api_key) if news_api_key else []
        if news:
            st.session_state["last_news_list"] = news  # Cache per analisi per-titolo in tab3
            st.markdown('<div class="section-hd">Radar notizie</div>', unsafe_allow_html=True)
            nc = st.columns(3)
            for i, n in enumerate(news[:9]):
                with nc[i%3]:
                    st.markdown(f"""<div style="background:#0F1829;border:1px solid #1E2D47;border-radius:8px;padding:.8rem;margin-bottom:.5rem;min-height:90px;">
<div style="font-size:.65rem;color:#3B82F6;font-weight:600;margin-bottom:.3rem;">{n['source']}</div>
<div style="font-size:.78rem;color:#E8EDF5;line-height:1.4;font-weight:500;">{n['title'][:100]}{'...' if len(n['title'])>100 else ''}</div></div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — WATCHLIST
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    watchlist = st.session_state.data["watchlist"]

    # ── KPI HEADER ────────────────────────────────────────────────────────────
    wl_utente = [w for w in watchlist if w.get("sorgente","utente") == "utente"]
    wl_ai     = [w for w in watchlist if w.get("sorgente") == "ai"]
    buy_c  = sum(1 for w in watchlist if w.get("segnale")=="COMPRA")
    mon_c  = sum(1 for w in watchlist if w.get("segnale")=="MONITORA")
    sell_c = sum(1 for w in watchlist if w.get("segnale")=="VENDI")

    k1,k2,k3,k4,k5 = st.columns(5)
    for col,(cnt,label,color) in zip([k1,k2,k3,k4,k5],[
        (len(wl_utente),"👤 Miei titoli","#3B82F6"),
        (len(wl_ai),"🤖 Idee AI","#8B5CF6"),
        (buy_c,"🟢 COMPRA","#10B981"),
        (mon_c,"🟡 MONITORA","#F59E0B"),
        (sell_c,"🔴 NON CONSIDERARE","#EF4444"),
    ]):
        with col:
            st.markdown(f'''<div style="background:{color}12;border:1px solid {color}33;border-radius:10px;
padding:.7rem;text-align:center;">
<div style="font-size:1.3rem;font-weight:700;color:{color};font-family:'JetBrains Mono',monospace;">{cnt}</div>
<div style="font-size:.68rem;color:#64748B;">{label}</div></div>''', unsafe_allow_html=True)

    # ── AGGIUNGI TITOLO ───────────────────────────────────────────────────────
    st.markdown('<div class="section-hd">Aggiungi titolo alla tua watchlist</div>', unsafe_allow_html=True)
    wa,wb,wc_col,wd_col = st.columns([2,2,2,1])
    with wa: wt = st.text_input("Ticker Yahoo *", placeholder="es. NVDA · AAPL · BTC-EUR", key="wt")
    with wb: wn = st.text_input("Nome *", placeholder="es. NVIDIA Corporation", key="wn")
    with wc_col: wcat = st.selectbox("Categoria", ["Azioni","ETF","Crypto","Obbligazioni","Materie Prime"], key="wcat")
    with wd_col:
        st.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
        add_btn = st.button("➕ Aggiungi", key="btn_wl", use_container_width=True)

    if add_btn:
        if wt and wn:
            new_item = {
                "ticker":wt.upper(),"nome":wn,"categoria":wcat,
                "sorgente":"utente",
                "segnale":"MONITORA","prezzo_target":None,"stop_loss":None,
                "ingresso":None,"strategia":None,"orizzonte":None,
                "note":"⏳ In attesa analisi AI...","ai_pending":True
            }
            st.session_state.data["watchlist"].append(new_item)
            save_data(st.session_state.data)
            if anthropic_key:
                with st.spinner(f"Analisi AI per {wn}..."):
                    td_add = get_technical(wt.upper())
                    tech_ctx = ""
                    if td_add:
                        tech_ctx = (f"Prezzo:{td_add['price']:.2f}, RSI:{td_add['rsi']:.0f}, "
                                    f"MA50:{td_add['ma50'] or 'N/A'}, MA200:{td_add['ma200'] or 'N/A'}, "
                                    f"MACD_H:{td_add['macd_h']:+.3f}, Supp:{td_add['support']:.2f}, Res:{td_add['resistance']:.2f}")
                    try:
                        cl_add = anthropic.Anthropic(api_key=anthropic_key)
                        ai_text = cl_add.messages.create(
                            model="claude-sonnet-4-20250514", max_tokens=500,
                            system="Sei un analista finanziario. Rispondi SOLO in JSON valido senza markdown.",
                            messages=[{"role":"user","content":
                                f'Analizza {wn} ({wt.upper()}). Dati tecnici: {tech_ctx if tech_ctx else "N/A"}. '
                                f'Rispondi con SOLO questo JSON: {{"segnale":"COMPRA","ingresso":0.0,"prezzo_target":0.0,"stop_loss":0.0,"strategia":"Lungo termine","orizzonte":"Medio (3-12 mesi)","note":"motivazione max 150 caratteri italiano"}}. '
                                f'segnale deve essere COMPRA, MONITORA o NON_CONSIDERARE. strategia: Breve termine (< 3 mesi) o Lungo termine (> 1 anno) o Medio termine (3-12 mesi).'}]
                        ).content[0].text.strip()
                        ai_data = json.loads(ai_text)
                        wl_idx = len(st.session_state.data["watchlist"]) - 1
                        st.session_state.data["watchlist"][wl_idx].update({**ai_data,"ai_pending":False})
                        save_data(st.session_state.data)
                        st.success(f"✅ {wn} aggiunto — Segnale: {ai_data.get('segnale','MONITORA')}")
                    except Exception as e:
                        wl_idx = len(st.session_state.data["watchlist"]) - 1
                        st.session_state.data["watchlist"][wl_idx].update({"note":"Analisi AI non disponibile","ai_pending":False})
                        save_data(st.session_state.data)
                        st.warning(f"Aggiunto senza analisi AI: {e}")
            else:
                st.success(f"✅ {wn} aggiunto")
            st.rerun()
        else:
            st.error("Inserisci Ticker e Nome")

    # ── ANALISI GRATUITA BATCH ───────────────────────────────────────────────
    st.markdown('<div class="section-hd">Analisi automatica — segnale e livelli di prezzo</div>', unsafe_allow_html=True)
    col_auto1, col_auto2 = st.columns([2,3])
    with col_auto1:
        missing_count = sum(1 for w in watchlist
                           if w.get("sorgente","utente")=="utente"
                           and not (w.get("prezzo_target") or w.get("ingresso")))
        if missing_count > 0:
            st.markdown(f'<div style="background:rgba(59,130,246,.1);border:1px solid rgba(59,130,246,.3);border-radius:8px;padding:.7rem 1rem;font-size:.82rem;margin-bottom:.5rem;"><b>{missing_count} titoli</b> senza segnale e livelli di prezzo.<br><span style="font-size:.75rem;color:#94A3B8;">Clicca per calcolarli automaticamente dai dati di mercato — <b>gratuito, zero API</b>.</span></div>', unsafe_allow_html=True)
            if st.button("⚡ Calcola segnali e livelli per tutti (gratis)", key="btn_auto_all", use_container_width=True):
                updated = 0
                progress_auto = st.progress(0)
                utente_items_auto = [w for w in st.session_state.data["watchlist"] if w.get("sorgente","utente")=="utente"]
                for qi, item_a in enumerate(utente_items_auto):
                    # Ricalcola sempre (non saltare — l'utente vuole dati freschi)
                    # if item_a.get("prezzo_target") or item_a.get("ingresso"):
                    #     continue
                    ticker_a = item_a.get("ticker","")
                    if not ticker_a or ticker_a == "N/A":
                        continue
                    td_a = get_technical(ticker_a)
                    if not td_a:
                        continue
                    p_a = td_a["price"]; rsi_a = td_a["rsi"]; macd_a = td_a["macd_h"]
                    sup_a = td_a["support"]; res_a = td_a["resistance"]
                    ma50_a = td_a["ma50"]; ma200_a = td_a["ma200"]
                    _, sig_lbl_a, _ = tech_signal(td_a)
                    if sig_lbl_a == "INCREMENTA":    seg_a = "COMPRA"
                    elif sig_lbl_a == "ALLEGGERISCI": seg_a = "NON_CONSIDERARE"
                    else:                             seg_a = "MONITORA"
                    # Sempre un ingresso concreto, anche per NON_CONSIDERARE
                    ideal_entry = sup_a * 1.01
                    ingresso_a  = round(min(ideal_entry, p_a * 0.99), 2)
                    target_a    = round(res_a * 0.99, 2)
                    # Per NON_CONSIDERARE, l'ingresso è il livello "se mai dovesse migliorare"
                    stop_a = round(sup_a * 0.96, 2)
                    if ma200_a and p_a > ma200_a * 1.05:
                        strat_a = "Lungo termine"; orizz_a = "Lungo (> 1 anno)"
                    elif ma50_a and p_a > ma50_a:
                        strat_a = "Medio termine"; orizz_a = "Medio (3-12 mesi)"
                    else:
                        strat_a = "Breve termine"; orizz_a = "Breve (< 3 mesi)"
                    rsi_note_a = "ipercomprato" if rsi_a > 70 else ("ipervenduto" if rsi_a < 30 else "neutro")
                    if seg_a == "NON_CONSIDERARE":
                        ma_note = f"Prezzo {'sotto' if ma50_a and p_a < ma50_a else 'sopra'} MA50" + (f" e {'sotto' if ma200_a and p_a < ma200_a else 'sopra'} MA200" if ma200_a else "")
                        note_a = (f"Momento sfavorevole: RSI {rsi_a:.0f} ({rsi_note_a}), MACD {'positivo' if macd_a>0 else 'negativo'}, {ma_note}. "
                                  f"Aspetta che RSI scenda sotto 60 e il MACD torni positivo prima di valutare l'ingresso a {ingresso_a}.")
                    elif seg_a == "COMPRA":
                        ma_note = "Sopra MA50 e MA200" if (ma50_a and p_a > ma50_a and ma200_a and p_a > ma200_a) else "Trend di breve positivo"
                        note_a = (f"Setup favorevole: RSI {rsi_a:.0f} ({rsi_note_a}), MACD {'positivo' if macd_a>0 else 'negativo'}, {ma_note}. "
                                  f"Ingresso ideale vicino al supporto ({sup_a:.2f}), target {target_a}.")
                    else:
                        trend_dir = "in ripresa" if (ma50_a and p_a > ma50_a) else "in debolezza"
                        note_a = (f"Segnali misti: RSI {rsi_a:.0f} ({rsi_note_a}), trend {trend_dir}. "
                                  f"Supporto chiave a {sup_a:.2f}: se regge è un buon punto di ingresso, se rompe aspetta.")
                    idx_wa = next((k for k,x in enumerate(st.session_state.data["watchlist"]) if x.get("ticker")==ticker_a), None)
                    if idx_wa is not None:
                        st.session_state.data["watchlist"][idx_wa].update({
                            "segnale":seg_a,"ingresso":ingresso_a,"prezzo_target":target_a,
                            "stop_loss":stop_a,"strategia":strat_a,"orizzonte":orizz_a,
                            "note":note_a,"ai_pending":False
                        })
                        updated += 1
                    progress_auto.progress(int((qi+1)/max(len(utente_items_auto),1)*100))
                save_data(st.session_state.data)
                progress_auto.empty()
                st.success(f"Aggiornati {updated} titoli con segnale e livelli di prezzo!")
                st.rerun()
        else:
            st.markdown('<div style="background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.3);border-radius:8px;padding:.7rem 1rem;font-size:.82rem;">Tutti i titoli hanno segnale e livelli calcolati.</div>', unsafe_allow_html=True)
    with col_auto2:
        st.markdown('<div class="tooltip-box"><b>Come funziona:</b> scarica i prezzi storici da Yahoo Finance (gratis) e calcola segnale, ingresso, target, stop loss e strategia per ogni titolo. Per notizie recenti e analisi fondamentale usa "Rianalizza" (AI, circa 0.01 EUR per titolo).</div>', unsafe_allow_html=True)

    # ── FILTRI ────────────────────────────────────────────────────────────────
    st.markdown("")
    fc1, fc2 = st.columns([1,2])
    with fc1:
        filtro_sorg = st.radio("Sorgente:", ["Tutti","👤 Miei","🤖 AI"], horizontal=True, key="filt_sorg")
    with fc2:
        filtro_seg = st.radio("Segnale:", ["Tutti","🟢 COMPRA","🟡 MONITORA","🔴 NON CONSIDERARE"], horizontal=True, key="filt_seg")

    sorg_map = {"Tutti":None,"👤 Miei":"utente","🤖 AI":"ai"}
    seg_map  = {"Tutti":None,"🟢 COMPRA":"COMPRA","🟡 MONITORA":"MONITORA","🔴 NON CONSIDERARE":"NON_CONSIDERARE"}
    filtered = [w for w in watchlist
                if (sorg_map[filtro_sorg] is None or w.get("sorgente","utente")==sorg_map[filtro_sorg])
                and (seg_map[filtro_seg] is None or w.get("segnale")==seg_map[filtro_seg])]

    # ── SEZIONE TITOLI UTENTE ─────────────────────────────────────────────────
    utente_filtered = [w for w in filtered if w.get("sorgente","utente") == "utente"]
    ai_filtered     = [w for w in filtered if w.get("sorgente") == "ai"]

    def render_wl_card(item, card_idx, is_ai=False):
        sig = item.get("segnale","MONITORA")
        # Mappa NON_CONSIDERARE a rosso
        sig_display = "NON CONSIDERARE" if sig == "NON_CONSIDERARE" else sig
        sc = {"COMPRA":"#10B981","MONITORA":"#F59E0B","NON_CONSIDERARE":"#EF4444","VENDI":"#EF4444"}.get(sig,"#F59E0B")

        price = get_price(item["ticker"]) if item.get("ticker","N/A") not in ("N/A","",None) else None
        td_w  = get_technical(item["ticker"]) if item.get("ticker","N/A") not in ("N/A","",None) else None
        rsi_str = f"{td_w['rsi']:.0f}" if td_w else "—"
        tech_em, _, _ = tech_signal(td_w)

        tgt = item.get("prezzo_target")
        sl  = item.get("stop_loss")
        ing = item.get("ingresso")
        tgt_d   = f"{tgt:.2f}" if tgt and tgt > 0 else "—"
        sl_d    = f"{sl:.2f}"  if sl  and sl > 0  else "—"
        # Ingresso: sempre un prezzo concreto. Per NON_CONSIDERARE = livello da aspettare
        if ing and ing > 0:
            ing_d = f"{ing:.2f}" + (" (attendi)" if sig == "NON_CONSIDERARE" else "")
        else:
            ing_d = "—"
        price_d = f"{price:.2f}" if price else "N/A"

        dist_str = ""
        if price and tgt and tgt > 0:
            dist_pct = (tgt - price) / price * 100
            dist_str = f"{dist_pct:+.1f}% al target"

        ai_badge = '<span style="background:#8B5CF622;color:#8B5CF6;border:1px solid #8B5CF644;padding:1px 7px;border-radius:20px;font-size:.62rem;font-weight:700;">🤖 AI</span>' if is_ai else '<span style="background:#3B82F622;color:#3B82F6;border:1px solid #3B82F644;padding:1px 7px;border-radius:20px;font-size:.62rem;font-weight:700;">👤 MIO</span>'

        strat = item.get("strategia","")
        orizz = item.get("orizzonte","")
        note  = item.get("note","")
        ai_note_section = ""
        if is_ai and note and not item.get("ai_pending"):
            ai_note_section = f'''<div style="margin-top:.6rem;background:rgba(139,92,246,.08);border:1px solid #8B5CF633;border-radius:6px;padding:.5rem .7rem;font-size:.75rem;color:#C4B5FD;line-height:1.5;">
<span style="font-size:.62rem;font-weight:700;color:#8B5CF6;text-transform:uppercase;letter-spacing:.06em;">💡 Perché nel tuo portafoglio</span><br>{note}</div>'''
        elif note and not is_ai:
            ai_note_section = f'<div style="margin-top:.5rem;font-size:.75rem;color:#94A3B8;border-top:1px solid #1E2D47;padding-top:.4rem;">{"⏳ " if item.get("ai_pending") else ""}{note}</div>'

        st.markdown(f'''<div style="background:#0F1829;border:1px solid {sc}44;border-left:3px solid {sc};border-radius:10px;padding:1rem;margin-bottom:.5rem;">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.4rem;">
  <span style="font-family:'JetBrains Mono',monospace;font-weight:700;color:{sc};">{item.get("ticker","")}</span>
  <div style="display:flex;gap:4px;align-items:center;">
    {ai_badge}
    <span style="background:{sc}22;color:{sc};border:1px solid {sc}44;padding:1px 7px;border-radius:20px;font-size:.65rem;font-weight:700;">{sig_display}</span>
  </div>
</div>
<div style="font-size:.85rem;font-weight:600;color:#E8EDF5;margin-bottom:.7rem;">{item.get("nome","")}</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:.35rem;font-size:.78rem;">
  <div><span style="color:#64748B;">Prezzo: </span><span style="font-family:'JetBrains Mono',monospace;">{price_d}</span></div>
  <div><span style="color:#64748B;">RSI: </span><span>{tech_em} {rsi_str}</span></div>
  <div><span style="color:#64748B;">Ingresso: </span><span style="color:#60A5FA;font-family:'JetBrains Mono',monospace;">{ing_d}</span></div>
  <div><span style="color:#64748B;">Target: </span><span style="color:#10B981;font-family:'JetBrains Mono',monospace;">{tgt_d}</span></div>
  <div><span style="color:#64748B;">Stop: </span><span style="color:#EF4444;font-family:'JetBrains Mono',monospace;">{sl_d}</span></div>
  <div><span style="color:#64748B;">Strategia: </span><span style="color:#94A3B8;">{strat if strat else "—"}</span></div>
</div>
{f'<div style="margin-top:.3rem;font-size:.72rem;color:#64748B;">⏱ {orizz}</div>' if orizz else ""}
{f'<div style="margin-top:.3rem;font-size:.72rem;color:#10B981;">{dist_str}</div>' if dist_str else ""}
{ai_note_section}
</div>''', unsafe_allow_html=True)

        ba, bb = st.columns(2)
        with ba:
            if anthropic_key and st.button("🤖 Rianalizza", key=f"rai_{card_idx}", use_container_width=True):
                with st.spinner("AI..."):
                    td_r = get_technical(item["ticker"])
                    ctx_r = f"Prezzo:{td_r['price']:.2f}, RSI:{td_r['rsi']:.0f}, Supp:{td_r['support']:.2f}, Res:{td_r['resistance']:.2f}" if td_r else "N/A"
                    pf_ctx = f"Portafoglio: {df_main.groupby('Categoria')['CV €'].sum().to_dict()}"
                    try:
                        pf_alloc_r = df_main.groupby("Categoria")["CV €"].sum().to_dict() if not df_main.empty else {}
                        pf_ctx_r = ", ".join([f"{k}:{v:.0f}euro" for k,v in pf_alloc_r.items()])
                        cl_r = anthropic.Anthropic(api_key=anthropic_key)
                        ai_r = cl_r.messages.create(
                            model="claude-sonnet-4-20250514", max_tokens=700,
                            system="Sei un analista finanziario senior. Rispondi SOLO in JSON valido senza markdown.",
                            messages=[{"role":"user","content":
                                f'Analizza {item["nome"]} ({item["ticker"]}) per investitore con portafoglio: {pf_ctx_r}. '
                                f'Dati tecnici ora: {ctx_r}. '
                                f'Rispondi con SOLO questo JSON (tutti i valori numerici devono essere numeri float, non stringhe): '
                                f'{{"segnale":"COMPRA","ingresso":0.0,"prezzo_target":0.0,"stop_loss":0.0,"strategia":"Lungo termine","orizzonte":"Medio (3-12 mesi)","note":"Scrivi 3 frasi in italiano semplice: 1) Cosa sta succedendo a questo titolo o nel suo settore in questo momento. 2) Perche il segnale e questo. 3) Come si inserisce nel portafoglio e cosa potrebbe portare."}}. '
                                f'segnale: COMPRA, MONITORA o NON_CONSIDERARE. strategia: Breve termine oppure Medio termine oppure Lungo termine.'}]
                        ).content[0].text.strip()
                        ai_d = json.loads(ai_r)
                        idx_r = next(k for k,x in enumerate(st.session_state.data["watchlist"]) if x.get("ticker")==item.get("ticker"))
                        st.session_state.data["watchlist"][idx_r].update(ai_d)
                        save_data(st.session_state.data); st.rerun()
                    except Exception as e:
                        st.error(f"Errore AI: {e}")
        with bb:
            if st.button("🗑️ Rimuovi", key=f"rw_{card_idx}", use_container_width=True):
                idx_rm = next((k for k,x in enumerate(st.session_state.data["watchlist"]) if x.get("ticker")==item.get("ticker")), None)
                if idx_rm is not None:
                    st.session_state.data["watchlist"].pop(idx_rm)
                    save_data(st.session_state.data); st.rerun()

    # ── RENDER SEZIONE I MIEI TITOLI ──────────────────────────────────────────
    if utente_filtered:
        st.markdown('''<div style="display:flex;align-items:center;gap:.5rem;margin:1.2rem 0 .6rem;">
<div style="width:3px;height:18px;background:#3B82F6;border-radius:2px;"></div>
<span style="font-size:.7rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#3B82F6;">👤 I miei titoli in watchlist</span>
<span style="font-size:.7rem;color:#64748B;">({len(utente_filtered)} titoli)</span>
</div>''', unsafe_allow_html=True)
        for i in range(0, len(utente_filtered), 3):
            row_w = utente_filtered[i:i+3]
            cols_w = st.columns(3)
            for j, item in enumerate(row_w):
                with cols_w[j]:
                    render_wl_card(item, f"u{i+j}", is_ai=False)

    # ── RENDER SEZIONE IDEE AI ────────────────────────────────────────────────
    if ai_filtered:
        st.markdown('''<div style="display:flex;align-items:center;gap:.5rem;margin:1.5rem 0 .6rem;">
<div style="width:3px;height:18px;background:#8B5CF6;border-radius:2px;"></div>
<span style="font-size:.7rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#8B5CF6;">🤖 Idee dagli agenti AI</span>
<span style="font-size:.7rem;color:#64748B;">({len(ai_filtered)} titoli)</span>
</div>''', unsafe_allow_html=True)
        st.markdown('<div style="background:rgba(139,92,246,.07);border:1px solid #8B5CF622;border-radius:8px;padding:.6rem 1rem;font-size:.78rem;color:#C4B5FD;margin-bottom:.8rem;">Questi titoli sono stati suggeriti dagli agenti AI nell\'ultima analisi del portafoglio, con motivazione specifica per la tua allocazione.</div>', unsafe_allow_html=True)
        for i in range(0, len(ai_filtered), 3):
            row_w = ai_filtered[i:i+3]
            cols_w = st.columns(3)
            for j, item in enumerate(row_w):
                with cols_w[j]:
                    render_wl_card(item, f"a{i+j}", is_ai=True)

    if not utente_filtered and not ai_filtered:
        st.info("Nessun titolo corrisponde ai filtri selezionati.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — BENCHMARK & SCENARI
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    bm_tab1, bm_tab2, bm_tab3 = st.tabs(["📊 Benchmark","🔮 What-If Scenari","📋 Storico Operazioni"])

    # ── BENCHMARK ─────────────────────────────────────────────────────────────
    with bm_tab1:
        st.markdown('<div class="section-hd">Confronto con benchmark di mercato</div>', unsafe_allow_html=True)
        period_sel = st.radio("Periodo:", ["3mo","6mo","1y"], horizontal=True, key="bm_period")

        df_bm = build_portfolio_df()
        fx_bm = get_fx_rates()

        # Simulate portfolio performance: use tradeable items' price history
        # Build a weighted return series
        bm_data = get_benchmark_history(period_sel)

        # Portfolio vs benchmarks chart
        fig_bm = go.Figure()
        colors_bm = {"MSCI World":"#3B82F6","S&P 500":"#10B981","Obblig. Globali":"#F59E0B"}
        for name, series in bm_data.items():
            norm = (series / series.iloc[0] - 1) * 100
            fig_bm.add_trace(go.Scatter(x=series.index, y=norm, name=name,
                line=dict(color=colors_bm.get(name,"#64748B"), width=2, dash="dot")))

        # Add portfolio line using tradeable items
        try:
            portfolio_returns = []
            total_w = df_bm["CV €"].sum()
            for _, row in df_bm.iterrows():
                if row["Ticker"] == "N/A": continue
                weight = row["CV €"] / total_w
                hist = yf.Ticker(row["Ticker"]).history(period=period_sel)["Close"]
                if not hist.empty:
                    portfolio_returns.append((hist / hist.iloc[0] - 1) * weight)
            if portfolio_returns:
                pf_series = sum(portfolio_returns) * 100
                fig_bm.add_trace(go.Scatter(x=pf_series.index, y=pf_series,
                    name="Il tuo portafoglio",
                    line=dict(color="#E8EDF5", width=2.5)))
        except: pass

        fig_bm.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(22,32,53,.6)",
            font_color="#E8EDF5",
            xaxis=dict(gridcolor="#1E2D47"), yaxis=dict(gridcolor="#1E2D47", ticksuffix="%"),
            legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.02),
            height=340, margin=dict(t=10,b=10))
        st.plotly_chart(fig_bm, use_container_width=True)

        # KPI comparison
        st.markdown('<div class="section-hd">Performance relativa</div>', unsafe_allow_html=True)
        bm_kpis = st.columns(4)
        pf_pnl_pct = (df_bm["P&L €"].sum() / (df_bm["CV €"].sum() - df_bm["P&L €"].sum()) * 100) if df_bm["CV €"].sum() > 0 else 0
        bm_returns = {}
        for name, series in bm_data.items():
            bm_returns[name] = (series.iloc[-1] / series.iloc[0] - 1) * 100 if len(series) > 1 else 0
        msci_ret = bm_returns.get("MSCI World", 0)
        alpha = pf_pnl_pct - msci_ret

        for col, (label, val, color) in zip(bm_kpis, [
            ("Tuo portafoglio", f"{pf_pnl_pct:+.2f}%", "#10B981" if pf_pnl_pct>=0 else "#EF4444"),
            ("MSCI World", f"{msci_ret:+.2f}%", "#3B82F6"),
            ("Alpha vs MSCI", f"{alpha:+.2f}%", "#10B981" if alpha>=0 else "#EF4444"),
            ("S&P 500", f"{bm_returns.get('S&P 500',0):+.2f}%", "#10B981"),
        ]):
            with col:
                st.markdown(f"""<div style="background:#0F1829;border:1px solid #243352;border-radius:10px;padding:.9rem;text-align:center;">
<div style="font-size:.65rem;color:#64748B;text-transform:uppercase;letter-spacing:.08em;">{label}</div>
<div style="font-family:'JetBrains Mono',monospace;font-weight:700;font-size:1.3rem;color:{color};">{val}</div></div>""", unsafe_allow_html=True)

        # 60/40 comparison
        st.markdown('<div class="section-hd">Confronto con portafoglio 60/40 standard</div>', unsafe_allow_html=True)
        eq_ret  = bm_returns.get("S&P 500", 0)
        bnd_ret = bm_returns.get("Obblig. Globali", 0)
        port_6040 = eq_ret * 0.6 + bnd_ret * 0.4
        alloc_pct = (df_bm.groupby("Categoria")["CV €"].sum() / df_bm["CV €"].sum() * 100).to_dict()
        azioni_pct = alloc_pct.get("Azioni",0) + alloc_pct.get("ETF",0) + alloc_pct.get("Crypto",0) + alloc_pct.get("Materie Prime",0)
        obblig_pct = alloc_pct.get("Obbligazioni",0) + alloc_pct.get("Certificati",0)

        cmp1, cmp2 = st.columns(2)
        with cmp1:
            st.markdown(f"""<div class="ai-block">
<div style="font-size:.7rem;color:#64748B;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.8rem;">Il tuo portafoglio</div>
<div style="display:flex;justify-content:space-between;margin-bottom:.4rem;font-size:.85rem;">
  <span>Componente rischio (azioni+crypto+MP)</span>
  <span style="font-family:'JetBrains Mono',monospace;color:#3B82F6;">{azioni_pct:.1f}%</span>
</div>
<div style="display:flex;justify-content:space-between;font-size:.85rem;">
  <span>Componente difensiva (obblig+cert)</span>
  <span style="font-family:'JetBrains Mono',monospace;color:#F59E0B;">{obblig_pct:.1f}%</span>
</div>
<div style="margin-top:1rem;padding-top:.8rem;border-top:1px solid #2E4480;font-family:'JetBrains Mono',monospace;font-size:1rem;color:#10B981;">
  Performance: {pf_pnl_pct:+.2f}%
</div></div>""", unsafe_allow_html=True)
        with cmp2:
            st.markdown(f"""<div class="ai-block">
<div style="font-size:.7rem;color:#64748B;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.8rem;">Portafoglio 60/40 standard</div>
<div style="display:flex;justify-content:space-between;margin-bottom:.4rem;font-size:.85rem;">
  <span>Azioni (S&P 500)</span>
  <span style="font-family:'JetBrains Mono',monospace;color:#3B82F6;">60%</span>
</div>
<div style="display:flex;justify-content:space-between;font-size:.85rem;">
  <span>Obbligazioni (Global Bond)</span>
  <span style="font-family:'JetBrains Mono',monospace;color:#F59E0B;">40%</span>
</div>
<div style="margin-top:1rem;padding-top:.8rem;border-top:1px solid #2E4480;font-family:'JetBrains Mono',monospace;font-size:1rem;color:{'#10B981' if port_6040>=0 else '#EF4444'};">
  Performance: {port_6040:+.2f}%
</div></div>""", unsafe_allow_html=True)

    # ── WHAT-IF SCENARI ───────────────────────────────────────────────────────
    with bm_tab2:
        st.markdown('<div class="section-hd">Simulazione scenari di mercato</div>', unsafe_allow_html=True)
        st.caption("Scorri gli slider per simulare come il tuo portafoglio reagirebbe a diversi scenari di mercato.")

        df_sc = build_portfolio_df()
        total_sc = df_sc["CV €"].sum()
        alloc_sc = (df_sc.groupby("Categoria")["CV €"].sum() / total_sc).to_dict()

        col_sc1, col_sc2 = st.columns([1,1])
        with col_sc1:
            st.markdown("**Imposta uno scenario personalizzato**")
            sc_azioni  = st.slider("Azioni (±%)", -60, 60, 0, key="sc_az")
            sc_etf     = st.slider("ETF (±%)",    -50, 50, 0, key="sc_etf")
            sc_obbl    = st.slider("Obbligazioni (±%)", -30, 30, 0, key="sc_ob")
            sc_crypto  = st.slider("Crypto (±%)", -90, 200, 0, key="sc_cr")
            sc_mp      = st.slider("Materie Prime (±%)", -40, 80, 0, key="sc_mp")
            sc_cert    = st.slider("Certificati (±%)", -30, 30, 0, key="sc_ct")

        sc_map = {"Azioni":sc_azioni,"ETF":sc_etf,"Obbligazioni":sc_obbl,
                  "Crypto":sc_crypto,"Materie Prime":sc_mp,"Certificati":sc_cert}

        delta_eur = sum(alloc_sc.get(cat,0) * total_sc * (pct/100) for cat, pct in sc_map.items())
        new_total = total_sc + delta_eur
        delta_pct = delta_eur / total_sc * 100 if total_sc > 0 else 0

        with col_sc2:
            st.markdown("**Risultato scenario**")
            res_color = "#10B981" if delta_eur >= 0 else "#EF4444"
            st.markdown(f"""<div style="background:#0F1829;border:2px solid {res_color}44;border-radius:12px;padding:1.5rem;text-align:center;margin-bottom:1rem;">
<div style="font-size:.7rem;color:#64748B;text-transform:uppercase;letter-spacing:.1em;">Variazione portafoglio</div>
<div style="font-family:'JetBrains Mono',monospace;font-size:2.5rem;font-weight:700;color:{res_color};">
{'+' if delta_eur>=0 else ''}€{delta_eur:,.0f}</div>
<div style="font-family:'JetBrains Mono',monospace;font-size:1.2rem;color:{res_color};">{delta_pct:+.2f}%</div>
<div style="font-size:.82rem;color:#64748B;margin-top:.5rem;">Nuovo totale: <b style="color:#E8EDF5;">€{new_total:,.0f}</b></div>
</div>""", unsafe_allow_html=True)

            # Breakdown per categoria
            for cat, pct in sc_map.items():
                if pct == 0: continue
                cat_v = alloc_sc.get(cat,0) * total_sc
                cat_d = cat_v * (pct/100)
                cat_col = "#10B981" if cat_d >= 0 else "#EF4444"
                cat_color_brand = CATEGORY_COLORS.get(cat,"#64748B")
                st.markdown(f"""<div style="display:flex;align-items:center;gap:.8rem;background:#0F1829;border:1px solid #243352;border-radius:8px;padding:.5rem .8rem;margin-bottom:.4rem;">
<div style="width:8px;height:8px;border-radius:50%;background:{cat_color_brand};flex-shrink:0;"></div>
<div style="font-size:.8rem;color:#E8EDF5;flex:1;">{cat}</div>
<div style="font-size:.78rem;color:#64748B;">{pct:+.0f}%</div>
<div style="font-family:'JetBrains Mono',monospace;font-size:.8rem;color:{cat_col};">{'+' if cat_d>=0 else ''}€{cat_d:,.0f}</div>
</div>""", unsafe_allow_html=True)

        # Scenari predefiniti
        st.markdown('<div class="section-hd">Scenari predefiniti</div>', unsafe_allow_html=True)
        scenari = [
            {"nome":"🔴 Recessione grave (-30%)", "desc":"Calo azionario profondo, fuga verso sicurezza",
             "Azioni":-35,"ETF":-25,"Obbligazioni":+10,"Crypto":-60,"Materie Prime":-15,"Certificati":-5},
            {"nome":"🟡 Correzione moderata (-15%)", "desc":"Sell-off tecnico, volatilità elevata",
             "Azioni":-18,"ETF":-15,"Obbligazioni":+3,"Crypto":-35,"Materie Prime":-8,"Certificati":-3},
            {"nome":"🟢 Rally azionario (+20%)", "desc":"Risk-on, crescita economica forte",
             "Azioni":+22,"ETF":+18,"Obbligazioni":-5,"Crypto":+45,"Materie Prime":+12,"Certificati":+5},
            {"nome":"📈 Boom crypto (×2)", "desc":"Ciclo rialzista crypto, correlazione positiva",
             "Azioni":+8,"ETF":+6,"Obbligazioni":-2,"Crypto":+100,"Materie Prime":+5,"Certificati":0},
            {"nome":"💶 Crisi EUR/USD (-10%)", "desc":"Indebolimento euro, boost asset USD",
             "Azioni":+5,"ETF":+3,"Obbligazioni":-3,"Crypto":0,"Materie Prime":+8,"Certificati":-2},
            {"nome":"🏦 Crisi obbligazionaria", "desc":"Rialzo tassi improvviso, pressione su bond",
             "Azioni":-8,"ETF":-6,"Obbligazioni":-20,"Crypto":+10,"Materie Prime":+15,"Certificati":-15},
        ]
        sc_cols = st.columns(3)
        for i, sc in enumerate(scenari):
            with sc_cols[i%3]:
                sc_d = sum(alloc_sc.get(cat,0) * total_sc * (pct/100) for cat,pct in sc.items() if cat not in ["nome","desc"])
                sc_p = sc_d/total_sc*100 if total_sc>0 else 0
                sc_c = "#10B981" if sc_d>=0 else "#EF4444"
                st.markdown(f"""<div style="background:#0F1829;border:1px solid #243352;border-radius:10px;padding:1rem;margin-bottom:.6rem;">
<div style="font-size:.85rem;font-weight:600;color:#E8EDF5;margin-bottom:.3rem;">{sc['nome']}</div>
<div style="font-size:.75rem;color:#64748B;margin-bottom:.7rem;">{sc['desc']}</div>
<div style="display:flex;justify-content:space-between;align-items:center;">
<div style="font-family:'JetBrains Mono',monospace;color:{sc_c};font-weight:700;">{'+' if sc_d>=0 else ''}€{sc_d:,.0f}</div>
<div style="font-family:'JetBrains Mono',monospace;font-size:.8rem;color:{sc_c};">{sc_p:+.1f}%</div>
</div></div>""", unsafe_allow_html=True)

    # ── STORICO OPERAZIONI ────────────────────────────────────────────────────
    with bm_tab3:
        st.markdown('<div class="section-hd">Storico operazioni</div>', unsafe_allow_html=True)
        trade_history = st.session_state.data.get("trade_history", [])

        if not trade_history:
            st.info("Nessuna operazione registrata. Le future operazioni dalla tab Gestione verranno tracciate qui.")
        else:
            # Summary KPIs
            total_trades = len(trade_history)
            realized_pnl = sum((t.get("pnl_realizzato") or 0) for t in trade_history)
            buys  = sum(1 for t in trade_history if t.get("tipo")=="acquisto")
            sells = sum(1 for t in trade_history if t.get("tipo")=="vendita")

            th1,th2,th3,th4 = st.columns(4)
            with th1: st.metric("Operazioni totali", total_trades)
            with th2: st.metric("P&L realizzato", f"€ {realized_pnl:+,.0f}")
            with th3: st.metric("Acquisti", buys)
            with th4: st.metric("Vendite/Uscite", sells)

            # Timeline
            for t in reversed(trade_history[-30:]):
                tipo = t.get("tipo","acquisto")
                tipo_color = "#10B981" if tipo=="acquisto" else ("#EF4444" if tipo=="vendita" else "#3B82F6")
                pnl = t.get("pnl_realizzato")
                pnl_str = f" · P&L: <span style='color:{'#10B981' if (pnl or 0)>=0 else '#EF4444'};font-family:var(--mono);'>€{pnl:+,.0f}</span>" if pnl is not None else ""
                st.markdown(f"""<div style="background:#0F1829;border:1px solid #243352;border-left:3px solid {tipo_color};border-radius:8px;padding:.6rem 1rem;margin-bottom:.4rem;display:flex;align-items:center;gap:1rem;font-size:.82rem;">
<div style="color:#64748B;min-width:90px;font-family:'JetBrains Mono',monospace;font-size:.75rem;">{t.get('data','')}</div>
<span style="background:{tipo_color}22;color:{tipo_color};border:1px solid {tipo_color}44;padding:1px 8px;border-radius:20px;font-size:.68rem;font-weight:700;text-transform:uppercase;">{tipo}</span>
<div style="flex:1;color:#E8EDF5;"><b>{t.get('nome','')}</b> ({t.get('ticker','')})</div>
<div style="color:#94A3B8;font-family:'JetBrains Mono',monospace;font-size:.78rem;">{t.get('quantita',0)} @ {t.get('prezzo',0):.3f} {t.get('valuta','EUR')}{pnl_str}</div>
</div>""", unsafe_allow_html=True)

        # Export
        if trade_history:
            df_export = pd.DataFrame(trade_history)
            csv = df_export.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Esporta CSV", csv, "operazioni.csv", "text/csv")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — GESTIONE
# ══════════════════════════════════════════════════════════════════════════════
with tab7:
    g1, g2, g3 = st.tabs(["➕ Nuova operazione", "📋 Modifica posizioni", "📧 Alert Email"])

    with g1:
        st.markdown('<div class="section-hd">Registra acquisto o vendita</div>', unsafe_allow_html=True)
        fc1,fc2,fc3 = st.columns(3)
        with fc1:
            gn  = st.text_input("Nome asset *", key="gn")
            gt  = st.text_input("Ticker Yahoo Finance *", placeholder="AAPL · LDO.MI · BTC-EUR", key="gt")
            gc  = st.selectbox("Categoria *", ["Azioni","ETF","Obbligazioni","Crypto","Certificati","Materie Prime"], key="gc")
        with fc2:
            gv  = st.selectbox("Valuta *", ["EUR","USD","GBP","DKK","CHF"], key="gv")
            gp  = st.number_input("Prezzo medio *", min_value=0.0, step=0.001, format="%.3f", key="gp")
            gq  = st.number_input("Quantità *",     min_value=0.0, step=0.001, format="%.4f", key="gq")
        with fc3:
            gop = st.radio("Tipo", ["Nuovo acquisto","Incrementa esistente","Vendi/Elimina"], key="gop")
            st.markdown("""<div class="tooltip-box">💡 Ticker Yahoo Finance:<br>
🇮🇹 IT: LDO.MI · ENI.MI · UCG.MI<br>
🇺🇸 USA: AAPL · MSFT · NVDA<br>
🌍 EU: AIR.PA · SIE.DE<br>
📊 ETF: SWDA.MI · VWCE.DE<br>
🪙 Crypto: BTC-EUR · ETH-EUR<br>
<a href="https://finance.yahoo.com" target="_blank" style="color:#3B82F6;">Cerca su Yahoo →</a></div>""", unsafe_allow_html=True)

        if st.button("✅ Registra operazione", key="btn_op"):
            if gn and gt and gp > 0 and gq > 0:
                existing_idx = next((i for i,p in enumerate(st.session_state.data["portfolio"]) if p["ticker"].upper()==gt.upper()), None)
                # Record in trade history
                trade_entry = {"data":datetime.now().strftime("%d/%m/%Y %H:%M"),
                               "tipo":"vendita" if gop=="Vendi/Elimina" else "acquisto",
                               "nome":gn,"ticker":gt.upper(),"quantita":gq,
                               "prezzo":gp,"valuta":gv,"categoria":gc,"pnl_realizzato":None}
                if gop == "Vendi/Elimina" and existing_idx is not None:
                    old = st.session_state.data["portfolio"][existing_idx]
                    fx_cur = get_fx_rates()
                    pnl_r = to_eur((gp - old["prezzo_carico"]) * gq, gv, fx_cur)
                    trade_entry["pnl_realizzato"] = round(pnl_r, 2)
                    st.session_state.data["portfolio"].pop(existing_idx)
                    st.session_state.data["trade_history"].append(trade_entry)
                    save_data(st.session_state.data); st.cache_data.clear()
                    st.success(f"✅ {gt} venduto · P&L realizzato: €{pnl_r:+,.0f}"); st.rerun()
                elif gop == "Incrementa esistente" and existing_idx is not None:
                    old = st.session_state.data["portfolio"][existing_idx]
                    nq = old["quantita"] + gq
                    np_ = (old["prezzo_carico"]*old["quantita"] + gp*gq) / nq
                    st.session_state.data["portfolio"][existing_idx].update({"quantita":nq,"prezzo_carico":np_})
                    st.session_state.data["trade_history"].append(trade_entry)
                    save_data(st.session_state.data); st.cache_data.clear()
                    st.success(f"✅ {gt} incrementato · Nuovo p.medio: {np_:.3f}"); st.rerun()
                else:
                    st.session_state.data["portfolio"].append(
                        {"nome":gn,"ticker":gt.upper(),"valuta":gv,"prezzo_carico":gp,
                         "quantita":gq,"categoria":gc,"prezzo_manuale":None})
                    st.session_state.data["trade_history"].append(trade_entry)
                    save_data(st.session_state.data); st.cache_data.clear()
                    st.success(f"✅ {gn} aggiunto"); st.rerun()
            else:
                st.error("Compila tutti i campi obbligatori (*)")

    with g2:
        portfolio = st.session_state.data["portfolio"]
        needs = [p for p in portfolio if p["ticker"]=="N/A" and not (p.get("prezzo_manuale") or 0)>0]
        has_m = [p for p in portfolio if (p.get("prezzo_manuale") or 0)>0]
        has_l = [p for p in portfolio if p["ticker"]!="N/A"]

        sc1,sc2,sc3 = st.columns(3)
        for col,(cnt,lbl,color) in zip([sc1,sc2,sc3],[
            (len(has_l),"🔵 Prezzi automatici","#3B82F6"),
            (len(has_m),"✏️ Prezzi manuali","#F59E0B"),
            (len(needs),"🔴 Da aggiornare","#EF4444")]):
            with col:
                st.markdown(f'<div style="background:{color}12;border:1px solid {color}33;border-radius:10px;padding:.7rem;text-align:center;"><div style="font-size:1.3rem;font-weight:700;color:{color};font-family:\'JetBrains Mono\',monospace;">{cnt}</div><div style="font-size:.72rem;color:#64748B;">{lbl}</div></div>', unsafe_allow_html=True)

        # ── AGGIORNAMENTO RAPIDO ───────────────────────────────────────────────
        if needs:
            st.markdown('<div class="section-hd">⚡ Aggiornamento rapido prezzi mancanti</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="background:rgba(239,68,68,.1);border:1px solid #EF444444;border-radius:8px;padding:.7rem 1rem;font-size:.82rem;color:#EF4444;margin-bottom:.8rem;">🔴 <b>{len(needs)} asset</b> senza prezzo — inserisci qui tutti i valori e salva in un click</div>', unsafe_allow_html=True)
            quick_vals = {}
            qcols = st.columns(3)
            for qi, qitem in enumerate(needs):
                with qcols[qi%3]:
                    hint = "% nominale (es. 98.50)" if qitem["categoria"]=="Obbligazioni" else "prezzo attuale"
                    quick_vals[qi] = st.number_input(
                        qitem["nome"][:30], min_value=0.0, step=0.01, format="%.3f",
                        key=f"qp_{qi}", help=f"{qitem['ticker']} · {qitem['categoria']} · {hint}")
            if st.button("💾 Salva tutti i prezzi", key="btn_quick_save"):
                saved = 0
                for qi, qitem in enumerate(needs):
                    if quick_vals[qi] > 0:
                        idx_q = st.session_state.data["portfolio"].index(qitem)
                        st.session_state.data["portfolio"][idx_q]["prezzo_manuale"] = quick_vals[qi]
                        saved += 1
                if saved:
                    save_data(st.session_state.data); st.cache_data.clear()
                    st.success(f"✅ {saved} prezzi aggiornati!"); st.rerun()
                else:
                    st.warning("Nessun valore inserito")
            st.markdown("---")

        # ── MODIFICA SINGOLA POSIZIONE ─────────────────────────────────────────
        cats = sorted(set(p["categoria"] for p in portfolio))
        for cat in cats:
            cat_items = [p for p in portfolio if p["categoria"]==cat]
            cat_col = CATEGORY_COLORS.get(cat,"#64748B")
            issues = sum(1 for p in cat_items if p["ticker"]=="N/A" and not (p.get("prezzo_manuale") or 0)>0)
            badge = f" 🔴 {issues} da aggiornare" if issues else " ✅"
            st.markdown(f'<div style="color:{cat_col};font-weight:700;font-size:.78rem;letter-spacing:.1em;text-transform:uppercase;margin:1rem 0 .4rem;">{cat} ({len(cat_items)}){badge}</div>', unsafe_allow_html=True)
            for item in cat_items:
                idx = portfolio.index(item)
                pm = item.get("prezzo_manuale") or 0
                lp = get_price(item["ticker"]) if item["ticker"]!="N/A" else None
                if item["ticker"]!="N/A" and lp:   dot,slbl,sc_="🔵",f"Live: {lp:,.3f}","#3B82F6"
                elif pm > 0:                        dot,slbl,sc_="✏️",f"Manuale: {pm:,.3f}","#F59E0B"
                else:                              dot,slbl,sc_="🔴","PREZZO MANCANTE","#EF4444"
                with st.expander(f"{dot} {item['nome']} — {slbl}"):
                    if item["ticker"]=="N/A" and pm==0:
                        st.markdown('<div style="background:rgba(239,68,68,.12);border:1px solid #EF4444;border-radius:7px;padding:.5rem .8rem;font-size:.8rem;color:#EF4444;margin-bottom:.7rem;">⚠️ Inserisci il prezzo attuale (obbligazioni: % del nominale, es. 98.50)</div>', unsafe_allow_html=True)
                    elif pm > 0:
                        st.markdown(f'<div style="background:rgba(245,158,11,.1);border:1px solid #F59E0B44;border-radius:7px;padding:.5rem .8rem;font-size:.8rem;color:#F59E0B;margin-bottom:.7rem;">✏️ Prezzo manuale: {pm:,.3f}</div>', unsafe_allow_html=True)
                    elif lp:
                        st.markdown(f'<div style="background:rgba(59,130,246,.1);border:1px solid #3B82F644;border-radius:7px;padding:.5rem .8rem;font-size:.8rem;color:#60A5FA;margin-bottom:.7rem;">🔵 Live: {lp:,.3f}</div>', unsafe_allow_html=True)
                    e1,e2,e3 = st.columns(3)
                    with e1:
                        nn = st.text_input("Nome",        value=item["nome"],         key=f"en_{idx}")
                        nt = st.text_input("Ticker Yahoo",value=item["ticker"],        key=f"et_{idx}")
                    with e2:
                        npc= st.number_input("P.carico",  value=float(item["prezzo_carico"]),step=0.001,format="%.3f",key=f"ep_{idx}")
                        nq = st.number_input("Quantità",  value=float(item["quantita"]),     step=0.001,format="%.4f",key=f"eq_{idx}")
                    with e3:
                        vl = ["EUR","USD","GBP","DKK","CHF"]
                        nv = st.selectbox("Valuta",vl,index=vl.index(item["valuta"]) if item["valuta"] in vl else 0,key=f"ev_{idx}")
                        nm = st.number_input("✏️ Prezzo manuale" if item["ticker"]=="N/A" else "P.manuale (sovrascrive Yahoo)",
                            value=float(pm),step=0.001,format="%.3f",key=f"em_{idx}",
                            help="Obbligazioni: % del nominale (es. 98.50)")
                    b1,b2 = st.columns(2)
                    with b1:
                        if st.button("💾 Salva", key=f"sv_{idx}"):
                            st.session_state.data["portfolio"][idx].update(
                                {"nome":nn,"ticker":nt,"prezzo_carico":npc,"quantita":nq,"valuta":nv,
                                 "prezzo_manuale":nm if nm>0 else None})
                            save_data(st.session_state.data); st.cache_data.clear()
                            st.success("✅ Salvato!"); st.rerun()
                    with b2:
                        if st.button("🗑️ Elimina", key=f"dl_{idx}"):
                            st.session_state.data["portfolio"].pop(idx)
                            save_data(st.session_state.data); st.cache_data.clear(); st.rerun()

    with g3:
        st.markdown('<div class="section-hd">Configurazione alert email giornaliero</div>', unsafe_allow_html=True)

        em_sett_cur = st.session_state.data.get("email_settings", {})
        if em_sett_cur.get("from_email"):
            st.markdown(f'<div style="background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.3);border-radius:8px;padding:.7rem 1rem;font-size:.82rem;color:#10B981;margin-bottom:1rem;">'                f'✅ Email configurata — mittente: <b>{em_sett_cur["from_email"]}</b> → destinatario: <b>{em_sett_cur["to_email"]}</b></div>', unsafe_allow_html=True)

        c_em1, c_em2 = st.columns(2)
        with c_em1:
            st.markdown("**Impostazioni mittente**")
            new_from = st.text_input("Gmail mittente", value=em_sett_cur.get("from_email",""), placeholder="tuo@gmail.com", key="g3_from")
            new_pass = st.text_input("App Password Gmail", type="password",
                value=em_sett_cur.get("app_password",""), placeholder="xxxx xxxx xxxx xxxx", key="g3_pass",
                help="Non è la tua password Gmail normale. Vedi istruzioni a destra.")
            new_to = st.text_input("Email destinatario", value=em_sett_cur.get("to_email",""), placeholder="tuo@email.com", key="g3_to")
            if st.button("💾 Salva configurazione email", key="btn_save_email", use_container_width=True):
                if new_from and new_pass and new_to:
                    st.session_state.data["email_settings"] = {"from_email":new_from,"app_password":new_pass,"to_email":new_to}
                    save_data(st.session_state.data)
                    st.success("✅ Configurazione salvata!")
                    st.rerun()
                else:
                    st.error("Compila tutti i campi")

        with c_em2:
            st.markdown("**Come ottenere la App Password Gmail**")
            st.markdown('<div class="ai-block" style="font-size:.82rem;line-height:1.9;">'
                '<b>Passo 1</b> — Vai su <a href="https://myaccount.google.com/security" target="_blank" style="color:#60A5FA;">myaccount.google.com/security</a><br>'
                '<b>Passo 2</b> — Clicca <b>Verifica in due passaggi</b> e attivala (se non attiva)<br>'
                '<b>Passo 3</b> — Torna in Sicurezza e cerca <b>Password per le app</b><br>'
                '<b>Passo 4</b> — Nel campo nome scrivi <b>Dashboard</b> e clicca <b>Crea</b><br>'
                '<b>Passo 5</b> — Google mostra una password di <b>16 caratteri</b> (es. abcd efgh ijkl mnop)<br>'
                '<b>Passo 6</b> — Copiala <b>senza spazi</b> e incollala nel campo qui a sinistra'
                '</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="section-hd">Invia report ora</div>', unsafe_allow_html=True)
        if st.session_state.data.get("email_settings",{}).get("from_email"):
            col_s1, col_s2 = st.columns([1,2])
            with col_s1:
                if st.button("📧 Invia report ora", key="btn_send_email", use_container_width=True):
                    df_em2 = build_portfolio_df()
                    mkt_em2 = get_market_data()
                    hs_em2, _ = compute_health_score(df_em2, mkt_em2)
                    cache_em2 = st.session_state.data.get("agent_cache",{}).get("results")
                    html2 = build_daily_email(df_em2, mkt_em2, hs_em2, cache_em2)
                    ok2, msg2 = send_email_alert(
                        st.session_state.data["email_settings"],
                        f"📈 Report Portafoglio {datetime.now().strftime('%d/%m/%Y')}",
                        html2)
                    if ok2: st.success("✅ " + msg2)
                    else:   st.error("❌ Errore: " + msg2)
            with col_s2:
                st.markdown('<div class="tooltip-box">Il report include: totale portafoglio, P&L, VIX, score di salute, best/worst performer e piano operativo AI.</div>', unsafe_allow_html=True)
        else:
            st.info("Configura prima l'email qui sopra per abilitare l'invio.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 — OPPORTUNITÀ
# ══════════════════════════════════════════════════════════════════════════════
with tab8:

    # ── Universe di titoli da scansionare nel mondo ──────────────────────────
    # Titoli fuori dal portafoglio: watchlist + universo globale predefinito
    GLOBAL_UNIVERSE = [
        # USA Large Cap Tech
        ("AAPL","Apple","Azioni","USD"), ("MSFT","Microsoft","Azioni","USD"),
        ("NVDA","NVIDIA","Azioni","USD"), ("AMZN","Amazon","Azioni","USD"),
        ("GOOG","Alphabet","Azioni","USD"), ("META","Meta","Azioni","USD"),
        ("TSLA","Tesla","Azioni","USD"), ("AVGO","Broadcom","Azioni","USD"),
        # USA Healthcare/Pharma
        ("LLY","Eli Lilly","Azioni","USD"), ("NVO","Novo Nordisk","Azioni","USD"),
        ("REGN","Regeneron","Azioni","USD"), ("ISRG","Intuitive Surgical","Azioni","USD"),
        ("VRTX","Vertex Pharma","Azioni","USD"), ("ABBV","AbbVie","Azioni","USD"),
        # USA Finance
        ("BRK-B","Berkshire Hathaway","Azioni","USD"), ("JPM","JPMorgan","Azioni","USD"),
        ("V","Visa","Azioni","USD"), ("MA","Mastercard","Azioni","USD"),
        ("PYPL","PayPal","Azioni","USD"), ("HLNE","Hamilton Lane","Azioni","USD"),
        # USA Consumer/Industrial
        ("NKE","Nike","Azioni","USD"), ("DIS","Walt Disney","Azioni","USD"),
        ("MELI","MercadoLibre","Azioni","USD"), ("DAL","Delta Airlines","Azioni","USD"),
        # USA Small/Mid Cap Innovazione
        ("RDDT","Reddit","Azioni","USD"), ("IONQ","IonQ","Azioni","USD"),
        ("XPEL","XPEL","Azioni","USD"), ("ICLR","Icon PLC","Azioni","USD"),
        # Europa
        ("ASML","ASML Holding","Azioni","EUR"), ("SAP","SAP SE","Azioni","EUR"),
        ("AMP.MI","Amplifon","Azioni","EUR"), ("ENEL.MI","Enel","Azioni","EUR"),
        ("LDO.MI","Leonardo","Azioni","EUR"), ("IP.MI","Interpump","Azioni","EUR"),
        ("ARIS.MI","Ariston","Azioni","EUR"), ("MAIRE.MI","Maire","Azioni","EUR"),
        ("SES.MI","Sesa","Azioni","EUR"), ("PRT.MI","Esprinet","Azioni","EUR"),
        ("IPS.PA","Ipsos","Azioni","EUR"),
        # ETF tematici
        ("KOID","KraneShares Humanoid","ETF","USD"), ("NLR","VanEck Uranium","ETF","USD"),
        ("BOTZ","Global Robotics ETF","ETF","USD"), ("ARKK","ARK Innovation","ETF","USD"),
        ("ICLN","iShares Clean Energy","ETF","USD"), ("SOXX","iShares Semiconductors","ETF","USD"),
        # Materie Prime
        ("GLD","SPDR Gold","Materie Prime","USD"), ("SLV","iShares Silver","Materie Prime","USD"),
        ("COPA.L","WisdomTree Copper","Materie Prime","EUR"),
        # Asia / Emergenti
        ("XX25.MI","Xtrackers MSCI China","ETF","EUR"),
        ("XMJP.MI","iShares MSCI Japan","ETF","EUR"),
    ]

    fx_opp = get_fx_rates()
    df_opp = build_portfolio_df()
    total_opp    = df_opp["CV €"].sum() if not df_opp.empty else 0
    liquidity_opp = 16000.0
    portfolio_tickers = {p["ticker"].upper() for p in st.session_state.data["portfolio"]
                         if p.get("ticker","N/A") not in ("N/A","",None)}

    st.markdown('<div class="section-hd">💡 Opportunità del giorno — scanner globale automatico</div>', unsafe_allow_html=True)
    st.caption("Scansiona watchlist + 50 titoli globali selezionati. Zero costo API. Esclusi i titoli già in portafoglio.")

    # Selezione universe
    col_u1, col_u2 = st.columns([3,1])
    with col_u1:
        scan_mode = st.radio("Fonte titoli da scansionare:",
            ["🌍 Universo globale (50 titoli)", "👁️ Solo watchlist mia", "🔀 Entrambi"],
            horizontal=True, key="scan_mode")
    with col_u2:
        if st.button("🔄 Aggiorna scan", key="btn_scan_opp", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # Build candidates list
    all_candidates = []
    seen_add = set()
    # Watchlist tickers set — usato per escluderli dalla modalità globale
    watchlist_tickers = {w.get("ticker","").upper() for w in st.session_state.data["watchlist"]
                         if w.get("ticker","N/A") not in ("N/A","",None)}

    def add_candidate(ticker, nome, categoria, valuta, fonte):
        t = ticker.upper()
        if t in seen_add or t in portfolio_tickers or t in ("N/A","",None): return
        seen_add.add(t)
        all_candidates.append({"ticker":ticker,"nome":nome,"categoria":categoria,
                                "valuta":valuta,"fonte":fonte})

    if scan_mode in ["👁️ Solo watchlist mia", "🔀 Entrambi"]:
        for w in st.session_state.data["watchlist"]:
            tk = w.get("ticker","N/A")
            if tk in ("N/A","",None): continue
            if any(sfx in tk for sfx in [".MI",".PA",".AS",".DE",".L",".CO",".SG"]):
                val_w = "GBP" if ".L" in tk else ("DKK" if ".CO" in tk else "EUR")
            else:
                val_w = "USD"
            add_candidate(tk, w["nome"], w.get("categoria","Azioni"), val_w, "watchlist")

    if scan_mode in ["🌍 Universo globale (50 titoli)", "🔀 Entrambi"]:
        for tk, nm, cat, val in GLOBAL_UNIVERSE:
            # In modalità globale pura, salta i ticker già nella watchlist personale
            if scan_mode == "🌍 Universo globale (50 titoli)" and tk.upper() in watchlist_tickers:
                continue
            add_candidate(tk, nm, cat, val, "globale")

    # ── Scan tecnico ──────────────────────────────────────────────────────────
    opp_results = []
    progress_opp = st.progress(0)
    status_opp   = st.empty()

    for qi, c in enumerate(all_candidates):
        progress_opp.progress(int((qi+1)/max(len(all_candidates),1)*100))
        status_opp.markdown(f'<div style="font-size:.72rem;color:#64748B;">Analisi: {c["ticker"]} — {c["nome"]}...</div>', unsafe_allow_html=True)
        td = get_technical(c["ticker"])
        if not td: continue

        p_now = td["price"]; rsi = td["rsi"]; macd = td["macd_h"]
        sup = td["support"]; res = td["resistance"]
        ma50 = td["ma50"]; ma200 = td["ma200"]; cross = td["cross"]

        signals = []; score = 0

        if rsi < 40 and macd > 0:
            signals.append(("🔄 Rimbalzo in corso", f"RSI {rsi:.0f} (ipervenduto) con MACD appena tornato positivo — classico segnale di inversione rialzista. Il mercato ha smesso di vendere e inizia a comprare."))
            score += 3
        elif rsi < 35:
            signals.append(("📉 Ipervenduto estremo", f"RSI {rsi:.0f} — venduto in eccesso rispetto alla norma storica. Spesso precede un rimbalzo, ma verifica che non ci siano notizie negative sull'azienda."))
            score += 2

        if p_now > 0 and abs(p_now - sup) / p_now < 0.03:
            signals.append(("🎯 Su supporto chiave", f"Prezzo {p_now:.2f} vicino al supporto {sup:.2f} ({abs(p_now-sup)/p_now*100:.1f}% di distanza) — zona storica dove gli acquirenti si fanno avanti."))
            score += 2

        if cross == "golden":
            signals.append(("🌟 Golden Cross", "La media a 50 giorni ha superato quella a 200 giorni — segnale di forza di lungo periodo, seguito dai grandi fondi istituzionali."))
            score += 3

        if td.get("vol_ratio",1) > 1.5:
            signals.append(("📊 Volume anomalo", f"Volume {td['vol_ratio']:.1f}x la media — possibile accumulo istituzionale. Quando i grandi fondi entrano, il volume sale prima del prezzo."))
            score += 1

        if ma50 and ma200 and p_now > ma50 and p_now > ma200:
            signals.append(("📈 Trend confermato", f"Sopra MA50 ({ma50:.2f}) e MA200 ({ma200:.2f}) — il titolo è in trend positivo su tutti gli orizzonti temporali."))
            score += 2

        if 45 < rsi < 62 and macd > 0 and (not ma50 or p_now > ma50):
            signals.append(("⚡ Setup pulito", f"RSI {rsi:.0f} neutro + MACD positivo + trend favorevole — buon punto di ingresso senza surriscaldamento."))
            score += 1

        if score < 2: continue

        # Currency detection dalla valuta del candidato
        val_cur = c.get("valuta","USD")
        fx_r = fx_opp.get(val_cur, 1.0)

        stop_est = round(sup * 0.97, 2)
        ps = calc_position_size(
            portfolio_total_eur = total_opp + liquidity_opp,
            current_price       = p_now,
            stop_loss_price     = stop_est,
            risk_pct_per_trade  = 1.0,
            fx_rate             = fx_r,
        )

        up_pct = (res * 0.99 - p_now) / p_now * 100 if p_now > 0 else 0
        dn_pct = (p_now - stop_est) / p_now * 100 if p_now > 0 else 0
        rr     = up_pct / dn_pct if dn_pct > 0 else 0

        opp_results.append({
            "ticker":c["ticker"], "nome":c["nome"], "categoria":c["categoria"],
            "fonte":c["fonte"], "score":score, "price":p_now, "rsi":rsi, "macd":macd,
            "support":sup, "resistance":res, "stop_est":stop_est,
            "target":round(res*0.99,2), "signals":signals, "ps":ps,
            "cross":cross, "up_pct":up_pct, "dn_pct":dn_pct, "rr":rr,
        })

    progress_opp.empty()
    status_opp.empty()
    opp_results.sort(key=lambda x: -x["score"])

    # ── Summary ───────────────────────────────────────────────────────────────
    n_strong = sum(1 for o in opp_results if o["score"] >= 4)
    n_mod    = sum(1 for o in opp_results if 2 <= o["score"] < 4)

    if not opp_results:
        st.info("Nessuna opportunità tecnica rilevante trovata al momento. Riprova dopo aggiornamento dati.")
    else:
        fonte_icons = {"watchlist":"👁️","globale":"🌍"}
        st.markdown(f"""
<div style="background:#0F1829;border:1px solid #2E4070;border-radius:12px;padding:1rem 1.4rem;margin-bottom:1rem;display:flex;gap:2.5rem;align-items:center;flex-wrap:wrap;">
  <div style="text-align:center;">
    <div style="font-size:2.2rem;font-weight:700;color:#10B981;font-family:'JetBrains Mono',monospace;">{n_strong}</div>
    <div style="font-size:.68rem;color:#64748B;text-transform:uppercase;">Opportunità forti (score ≥4)</div>
  </div>
  <div style="text-align:center;">
    <div style="font-size:2.2rem;font-weight:700;color:#F59E0B;font-family:'JetBrains Mono',monospace;">{n_mod}</div>
    <div style="font-size:.68rem;color:#64748B;text-transform:uppercase;">Opportunità moderate</div>
  </div>
  <div style="width:1px;height:44px;background:#1E2D47;"></div>
  <div style="font-size:.8rem;color:#94A3B8;flex:1;line-height:1.6;">
    <b style="color:#E8EDF5;">Come usare:</b> ogni card mostra i segnali rilevati, il prezzo di ingresso consigliato, target, stop loss, rapporto rischio/rendimento, e quante quote comprare per rischiare esattamente l'1% del portafoglio.<br>
    <span style="color:#64748B;">Tutti i titoli in portafoglio sono esclusi automaticamente. Score massimo 7/7.</span>
  </div>
</div>""", unsafe_allow_html=True)

        # ── TABELLA RIEPILOGATIVA ─────────────────────────────────────────────
        st.markdown('<div class="section-hd">📋 Riepilogo migliori opportunità</div>', unsafe_allow_html=True)

        table_rows = []
        for o in opp_results[:20]:
            ideal_e = round(min(o["support"]*1.01, o["price"]*0.99), 2)
            rr_str  = f"{o['rr']:.1f}:1"
            rr_icon = "🟢" if o["rr"] >= 2 else ("🟡" if o["rr"] >= 1 else "🔴")
            segnali_breve = " · ".join([s[0] for s in o["signals"]])
            ps = o["ps"]
            qty_str = str(ps["n_shares"]) if ps else "—"
            table_rows.append({
                "Score": f"{'★'*min(o['score'],5)}{'☆'*(5-min(o['score'],5))}",
                "Ticker": o["ticker"],
                "Nome": o["nome"][:22],
                "Categoria": o["categoria"],
                "Fonte": {"watchlist":"👁️ WL","globale":"🌍 Globale"}.get(o["fonte"],o["fonte"]),
                "Prezzo": f"{o['price']:.2f}",
                "Ingresso": f"{ideal_e:.2f}",
                "Target": f"{o['target']:.2f}  +{o['up_pct']:.1f}%",
                "Stop": f"{o['stop_est']:.2f}  -{o['dn_pct']:.1f}%",
                "R/R": f"{rr_icon} {rr_str}",
                "Qty (1% rischio)": qty_str,
                "Segnali": segnali_breve,
            })

        if table_rows:
            df_table = pd.DataFrame(table_rows)
            st.dataframe(df_table, use_container_width=True, hide_index=True,
                         column_config={
                             "Score": st.column_config.TextColumn("⭐ Score", width="small"),
                             "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                             "Nome": st.column_config.TextColumn("Nome"),
                             "Categoria": st.column_config.TextColumn("Categoria", width="small"),
                             "Fonte": st.column_config.TextColumn("Fonte", width="small"),
                             "Prezzo": st.column_config.TextColumn("Prezzo", width="small"),
                             "Ingresso": st.column_config.TextColumn("Ingresso ideale", width="small"),
                             "Target": st.column_config.TextColumn("Target"),
                             "Stop": st.column_config.TextColumn("Stop loss"),
                             "R/R": st.column_config.TextColumn("R/R ratio", width="small"),
                             "Qty (1% rischio)": st.column_config.TextColumn("Quote da comprare", width="small"),
                             "Segnali": st.column_config.TextColumn("Segnali tecnici"),
                         })
            st.caption("Qty = quante quote acquistare per rischiare esattamente l'1% del portafoglio su ogni operazione. R/R = rapporto guadagno potenziale / rischio (verde ≥2:1 = ottimo).")

        st.markdown('<div class="section-hd">📄 Dettaglio per ogni opportunità</div>', unsafe_allow_html=True)

        # Filtro per categoria
        cats_found = sorted(set(o["categoria"] for o in opp_results))
        fonti_found = sorted(set(o["fonte"] for o in opp_results))
        fc1_opp, fc2_opp = st.columns(2)
        with fc1_opp:
            filter_cat = st.multiselect("Filtra per categoria:", cats_found, default=cats_found, key="opp_cat_filter")
        with fc2_opp:
            filter_fonte = st.multiselect("Filtra per fonte:", fonti_found, default=fonti_found, key="opp_fonte_filter")

        filtered_opps = [o for o in opp_results if o["categoria"] in filter_cat and o["fonte"] in filter_fonte]

        for i, o in enumerate(filtered_opps):
            sc_score = o["score"]
            sc = "#10B981" if sc_score >= 4 else "#F59E0B"
            fonte_label = {"watchlist":"👁️ Watchlist","globale":"🌍 Universo globale"}.get(o["fonte"], o["fonte"])
            fonte_color = "#10B981" if o["fonte"]=="watchlist" else "#8B5CF6"

            signals_html = "".join([
                f'<div style="padding:.4rem .6rem;margin-bottom:.3rem;background:#162035;border-radius:6px;border-left:2px solid {sc};font-size:.79rem;"><b style="color:{sc};">{icon}</b> — <span style="color:#94A3B8;">{desc}</span></div>'
                for icon, desc in o["signals"]
            ])

            ps = o["ps"]
            if ps:
                ps_block = (
                    f'<div style="background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.3);border-radius:8px;padding:.7rem .9rem;margin-top:.6rem;">'
                    f'<div style="font-size:.63rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#3B82F6;margin-bottom:.5rem;">📐 Position Sizing — 1% di rischio per operazione</div>'
                    f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:.5rem;font-size:.78rem;">'
                    f'<div><span style="color:#64748B;">Quantità</span><br><b style="color:#E8EDF5;font-size:1.15rem;">{ps["n_shares"]}</b><span style="color:#64748B;font-size:.7rem;"> quote</span></div>'
                    f'<div><span style="color:#64748B;">Investimento</span><br><b style="color:#E8EDF5;">€{ps["position_eur"]:,.0f}</b><br><span style="color:#64748B;font-size:.7rem;">{ps["position_pct"]:.1f}% del portafoglio</span></div>'
                    f'<div><span style="color:#64748B;">Rischio max</span><br><b style="color:#EF4444;">€{ps["risk_eur"]:,.0f}</b><br><span style="color:#64748B;font-size:.7rem;">= 1% del totale</span></div>'
                    f'</div>'
                    f'<div style="font-size:.7rem;color:#64748B;margin-top:.4rem;">Se il prezzo scende fino a {o["stop_est"]:.2f} (stop loss), la perdita massima è €{ps["risk_eur"]:,.0f}.</div>'
                    f'</div>'
                )
            else:
                ps_block = '<div style="font-size:.72rem;color:#64748B;margin-top:.4rem;padding:.5rem;background:#162035;border-radius:6px;">Position sizing non calcolabile — dati insufficienti.</div>'

            rr_color = "#10B981" if o["rr"] >= 2 else ("#F59E0B" if o["rr"] >= 1 else "#EF4444")
            rr_label = "ottimo" if o["rr"] >= 2 else ("accettabile" if o["rr"] >= 1 else "basso")

            # Ingresso ideale
            ideal_entry = round(min(o["support"]*1.01, o["price"]*0.99), 2)

            st.markdown(f"""
<div style="background:#0F1829;border:1px solid {sc}44;border-left:4px solid {sc};border-radius:12px;padding:1.1rem 1.2rem;margin-bottom:1rem;">
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.7rem;flex-wrap:wrap;gap:.4rem;">
  <div style="display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;">
    <span style="font-family:'JetBrains Mono',monospace;font-weight:700;font-size:1.05rem;color:{sc};">{o["ticker"]}</span>
    <span style="font-size:.88rem;font-weight:600;color:#E8EDF5;">{o["nome"]}</span>
    <span style="background:{fonte_color}22;color:{fonte_color};border:1px solid {fonte_color}44;padding:1px 7px;border-radius:20px;font-size:.62rem;font-weight:700;">{fonte_label}</span>
    <span style="background:#24335222;color:#94A3B8;border:1px solid #243352;padding:1px 7px;border-radius:20px;font-size:.62rem;">{o["categoria"]}</span>
  </div>
  <span style="background:{sc}22;color:{sc};border:1px solid {sc}44;padding:2px 12px;border-radius:20px;font-size:.72rem;font-weight:700;">Score {sc_score}/7</span>
</div>
<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:.45rem;margin-bottom:.7rem;">
  <div style="background:#162035;border-radius:6px;padding:.45rem;text-align:center;">
    <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;">Prezzo ora</div>
    <div style="font-weight:700;font-size:.9rem;">{o["price"]:.2f}</div>
  </div>
  <div style="background:#162035;border-radius:6px;padding:.45rem;text-align:center;">
    <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;">Ingresso ideale</div>
    <div style="font-weight:700;color:#60A5FA;font-size:.9rem;">{ideal_entry:.2f}</div>
  </div>
  <div style="background:#162035;border-radius:6px;padding:.45rem;text-align:center;">
    <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;">Target</div>
    <div style="font-weight:700;color:#10B981;font-size:.9rem;">{o["target"]:.2f} <span style="font-size:.65rem;">+{o["up_pct"]:.1f}%</span></div>
  </div>
  <div style="background:#162035;border-radius:6px;padding:.45rem;text-align:center;">
    <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;">Stop loss</div>
    <div style="font-weight:700;color:#EF4444;font-size:.9rem;">{o["stop_est"]:.2f} <span style="font-size:.65rem;">-{o["dn_pct"]:.1f}%</span></div>
  </div>
  <div style="background:#162035;border-radius:6px;padding:.45rem;text-align:center;">
    <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;">R/R ratio</div>
    <div style="font-weight:700;color:{rr_color};font-size:.9rem;">{o["rr"]:.1f}:1 <span style="font-size:.62rem;">{rr_label}</span></div>
  </div>
</div>
<div style="font-size:.72rem;color:#64748B;margin-bottom:.5rem;">RSI {o["rsi"]:.0f} · MACD {"↑ positivo" if o["macd"]>0 else "↓ negativo"} · {"🌟 Golden Cross attivo · " if o["cross"]=="golden" else ""}Volume {"anomalo" if td and td.get("vol_ratio",1)>1.5 else "normale"}</div>
{signals_html}
{ps_block}
</div>""", unsafe_allow_html=True)

    # ── FONDAMENTALI ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-hd">📊 Ratio fondamentali — P/E, PEG, ROE, Debt/Equity</div>', unsafe_allow_html=True)
    st.caption("Aggiornati ogni 24h da Yahoo Finance. Clicca per aggiornare.")
    with st.expander("📖 Come leggere i ratio"):
        fg1,fg2,fg3 = st.columns(3)
        for i,(t,d) in enumerate([
            ("P/E","Quanto paghi per ogni €1 di utile. Sotto 15 = economico. Sopra 30 = caro. Dipende dal settore."),
            ("PEG","P/E diviso crescita attesa. Sotto 1 = conveniente. Sopra 2 = paghi troppo la crescita."),
            ("P/B","Prezzo diviso valore contabile. Sotto 1 = compri a sconto sul patrimonio."),
            ("Debt/Equity","Debito diviso capitale. Sopra 2 = molto indebitata. Sotto 0.5 = solida."),
            ("ROE","Rendimento sul capitale. Sopra 15% = eccellente. Warren Buffett: cerca ROE > 15% costante."),
            ("Rev Growth","Crescita del fatturato. Positivo e in accelerazione = ottimo segnale.")
        ]):
            with [fg1,fg2,fg3][i%3]:
                st.markdown(f'<div class="tooltip-box" style="margin-bottom:.5rem;"><b>{t}</b><br>{d}</div>', unsafe_allow_html=True)

    fund_tickers = [o["ticker"] for o in opp_results[:15]]
    if not fund_tickers:
        fund_tickers = [w["ticker"] for w in st.session_state.data["watchlist"]
                        if w.get("ticker","N/A") not in ("N/A","",None)][:12]

    fund_rows = []
    for ticker in fund_tickers:
        fd = get_fundamentals(ticker)
        if not fd: continue
        nome_f = next((o["nome"] for o in opp_results if o["ticker"]==ticker),
                      next((w["nome"] for w in st.session_state.data["watchlist"] if w["ticker"]==ticker), ticker))
        def fmt_f(v, mult=1, suffix="", dec=1):
            try: return f"{float(v)*mult:.{dec}f}{suffix}" if v is not None else "—"
            except: return "—"
        pe_v = fd["pe"]
        peg_v = fd["peg"]
        roe_v = fd["roe"]
        fund_rows.append({
            "Ticker": ticker, "Nome": str(nome_f)[:20],
            "P/E":       fmt_f(pe_v, dec=1),
            "PEG":       fmt_f(peg_v, dec=2),
            "P/B":       fmt_f(fd["pb"], dec=1),
            "D/E":       fmt_f(fd["de"], dec=2),
            "ROE":       fmt_f(roe_v, mult=100, suffix="%", dec=1),
            "Rev Gr.":   fmt_f(fd["rev_growth"], mult=100, suffix="%", dec=1),
            "Settore":   (fd["sector"] or "—")[:16],
        })
    if fund_rows:
        st.dataframe(pd.DataFrame(fund_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Nessun dato fondamentale disponibile per i titoli selezionati.")

    # ── EARNINGS CALENDAR ─────────────────────────────────────────────────────
    st.markdown('<div class="section-hd">📅 Earnings — prossime date utili</div>', unsafe_allow_html=True)
    st.caption("Non entrare mai in posizione 2-3 giorni prima degli earnings senza saperlo.")

    earn_all_tickers = tuple(set(
        [p["ticker"] for p in st.session_state.data["portfolio"] if p.get("ticker","N/A") not in ("N/A","",None)] +
        [w["ticker"] for w in st.session_state.data["watchlist"] if w.get("ticker","N/A") not in ("N/A","",None)]
    ))
    earn_cal = get_earnings_calendar(earn_all_tickers)
    if earn_cal:
        earn_items = sorted(earn_cal.items(), key=lambda x: x[1])
        ec = st.columns(3)
        for i,(tk,dt) in enumerate(earn_items[:12]):
            nm_e = next((w["nome"] for w in st.session_state.data["watchlist"] if w["ticker"]==tk),
                        next((p["nome"] for p in st.session_state.data["portfolio"] if p["ticker"]==tk), tk))
            in_pf = tk in portfolio_tickers
            ec_col = "#F59E0B" if in_pf else "#3B82F6"
            with ec[i%3]:
                st.markdown(f'<div style="background:#0F1829;border:1px solid {ec_col}33;border-left:3px solid {ec_col};border-radius:8px;padding:.65rem .9rem;margin-bottom:.4rem;"><div style="font-size:.7rem;color:{ec_col};font-weight:700;">📅 {dt}</div><div style="font-size:.82rem;font-weight:600;color:#E8EDF5;">{str(nm_e)[:22]}</div><div style="font-size:.68rem;color:#64748B;">{tk} · {"💼 portafoglio" if in_pf else "👁️ watchlist"}</div></div>', unsafe_allow_html=True)
    else:
        st.info("Date earnings non disponibili da Yahoo Finance per questi ticker. Verifica su earnings.com.")

    # ── VOLATILITÀ ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-hd">📉 Volatilità e drawdown massimo — titoli portafoglio</div>', unsafe_allow_html=True)
    vol_data = []
    for item in st.session_state.data["portfolio"]:
        if item.get("ticker","N/A") in ("N/A","",None,"Liquidità"): continue
        vd = get_volatility(item["ticker"])
        if not vd: continue
        vol_data.append({"Nome":item["nome"][:22],"_vol":vd["vol_ann"],"_dd":vd["max_drawdown"],
                          "Vol annua":f"{vd['vol_ann']:.1f}%","Max Drawdown":f"{vd['max_drawdown']:.1f}%"})
    if vol_data:
        vol_data.sort(key=lambda x: -x["_vol"])
        vc1,vc2 = st.columns(2)
        with vc1:
            st.markdown("**Più volatili** (oscillano di più)")
            for v in vol_data[:6]:
                c_ = "#EF4444" if v["_vol"]>40 else ("#F59E0B" if v["_vol"]>20 else "#10B981")
                st.markdown(f'<div style="display:flex;justify-content:space-between;padding:.35rem .6rem;background:#0F1829;border-radius:6px;margin-bottom:.25rem;font-size:.8rem;"><span style="color:#94A3B8;">{v["Nome"]}</span><span style="color:{c_};font-weight:700;">{v["Vol annua"]}</span></div>', unsafe_allow_html=True)
        with vc2:
            st.markdown("**Peggiori drawdown 1 anno**")
            for v in sorted(vol_data, key=lambda x: x["_dd"])[:6]:
                c_ = "#EF4444" if v["_dd"]<-40 else ("#F59E0B" if v["_dd"]<-20 else "#10B981")
                st.markdown(f'<div style="display:flex;justify-content:space-between;padding:.35rem .6rem;background:#0F1829;border-radius:6px;margin-bottom:.25rem;font-size:.8rem;"><span style="color:#94A3B8;">{v["Nome"]}</span><span style="color:{c_};font-weight:700;">{v["Max Drawdown"]}</span></div>', unsafe_allow_html=True)
    else:
        st.info("Dati volatilità non disponibili.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 9 — REVERSAL RADAR
# ══════════════════════════════════════════════════════════════════════════════
with tab9:

    # ── Helper: scarica dati intraday ─────────────────────────────────────────
    @st.cache_data(ttl=300)
    def get_intraday(ticker, interval="1h", period="5d"):
        """Scarica candele intraday. interval: 1h, 15m, 5m."""
        if ticker in ("N/A","",None): return None
        try:
            h = yf.Ticker(ticker).history(period=period, interval=interval)
            return h if not h.empty else None
        except: return None

    @st.cache_data(ttl=3600)
    def get_daily(ticker, period="6mo"):
        if ticker in ("N/A","",None): return None
        try:
            h = yf.Ticker(ticker).history(period=period)
            return h if not h.empty else None
        except: return None

    def compute_key_levels(h_daily, h_hourly):
        """
        Calcola livelli chiave da dati giornalieri + orari.
        Restituisce dict con: supporti, resistenze, pivot, zone.
        """
        levels = {"supports":[], "resistances":[], "pivot":None,
                  "s1":None,"s2":None,"r1":None,"r2":None,
                  "week_high":None,"week_low":None,
                  "month_high":None,"month_low":None,
                  "vwap":None}

        if h_daily is not None and len(h_daily) >= 5:
            c = h_daily["Close"]
            # Rolling pivots (ultima settimana = 5 giorni)
            last5 = h_daily.tail(5)
            levels["week_high"] = float(last5["High"].max())
            levels["week_low"]  = float(last5["Low"].min())
            last20 = h_daily.tail(20)
            levels["month_high"] = float(last20["High"].max())
            levels["month_low"]  = float(last20["Low"].min())

            # Pivot Point classico (su dati ieri)
            prev = h_daily.iloc[-2]
            H, L, C_prev = float(prev["High"]), float(prev["Low"]), float(prev["Close"])
            P  = (H + L + C_prev) / 3
            R1 = 2*P - L;  S1 = 2*P - H
            R2 = P + (H-L); S2 = P - (H-L)
            levels["pivot"] = round(P,2)
            levels["r1"] = round(R1,2); levels["r2"] = round(R2,2)
            levels["s1"] = round(S1,2); levels["s2"] = round(S2,2)

            # Supporti e resistenze dinamici (ultime 20 candele)
            highs = h_daily["High"].tail(20).values
            lows  = h_daily["Low"].tail(20).values
            # Cerca swing high/low semplici
            for i in range(1, len(highs)-1):
                if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                    levels["resistances"].append(round(float(highs[i]),2))
                if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                    levels["supports"].append(round(float(lows[i]),2))
            # Deduplicazione livelli vicini (cluster a 0.5%)
            def cluster(lst, tol=0.005):
                if not lst: return []
                lst = sorted(set(lst))
                out = [lst[0]]
                for v in lst[1:]:
                    if abs(v - out[-1]) / out[-1] > tol:
                        out.append(v)
                return out
            levels["supports"]   = cluster(levels["supports"])[-5:]   # ultimi 5
            levels["resistances"]= cluster(levels["resistances"])[:5]  # primi 5

        if h_hourly is not None and len(h_hourly) >= 10:
            # VWAP intraday (ultime 48 ore)
            try:
                typical = (h_hourly["High"] + h_hourly["Low"] + h_hourly["Close"]) / 3
                vwap_v  = (typical * h_hourly["Volume"]).cumsum() / h_hourly["Volume"].cumsum()
                levels["vwap"] = round(float(vwap_v.iloc[-1]), 2)
            except: pass

        return levels

    def reversal_signal(price, levels, rsi, macd, prev_close=None):
        """
        Genera segnale ENTRA / ASPETTA / ESCI con motivazione dettagliata.
        Restituisce: (segnale, colore, forza 1-5, motivazioni[], avvisi[])
        """
        score = 0; motivazioni = []; avvisi = []
        p = price

        # 1. Vicinanza al supporto (±1.5%)
        for sup in levels["supports"]:
            if abs(p - sup) / p < 0.015:
                score += 2
                dist = (p - sup)/p*100
                motivazioni.append(f"🎯 Prezzo su supporto storico {sup:.2f} (distanza {abs(dist):.1f}%) — zona dove storicamente gli acquirenti si fanno avanti")
                break

        # 2. Vicinanza alla resistenza (±1.5%)
        for res in levels["resistances"]:
            if abs(p - res) / p < 0.015:
                score -= 2
                dist = (res - p)/p*100
                avvisi.append(f"⚠️ Prezzo su resistenza storica {res:.2f} (distanza {abs(dist):.1f}%) — zona dove storicamente i venditori bloccano il rialzo")
                break

        # 3. Pivot Point
        if levels["pivot"] and abs(p - levels["pivot"])/p < 0.01:
            motivazioni.append(f"⚖️ Prezzo sul Pivot Point {levels['pivot']:.2f} — livello di equilibrio calcolato sui dati di ieri (H+L+C/3). Zona di indecisione.")

        # 4. S1/S2/R1/R2
        if levels["s1"] and abs(p - levels["s1"])/p < 0.015:
            score += 1
            motivazioni.append(f"🟢 Su S1={levels['s1']:.2f} — primo supporto pivot. Zona di potenziale rimbalzo.")
        if levels["r1"] and abs(p - levels["r1"])/p < 0.015:
            score -= 1
            avvisi.append(f"🔴 Su R1={levels['r1']:.2f} — prima resistenza pivot. Zona di potenziale blocco.")

        # 5. VWAP
        if levels["vwap"]:
            if p < levels["vwap"] * 0.98:
                score += 1
                motivazioni.append(f"📊 Prezzo sotto il VWAP ({levels['vwap']:.2f}) — i compratori intraday sono in vantaggio se il prezzo risale sopra il VWAP")
            elif p > levels["vwap"] * 1.02:
                score -= 1
                avvisi.append(f"📊 Prezzo sopra il VWAP ({levels['vwap']:.2f}) — i venditori intraday hanno ancora spazio prima di trovare resistenza")

        # 6. RSI
        if rsi < 30:
            score += 2
            motivazioni.append(f"💎 RSI {rsi:.0f} — titolo ipervenduto. Storicamente a questi livelli segue un rimbalzo tecnico.")
        elif rsi < 40:
            score += 1
            motivazioni.append(f"📉 RSI {rsi:.0f} — zona di debolezza ma non estrema. Monitorare se scende ancora.")
        elif rsi > 70:
            score -= 2
            avvisi.append(f"🔥 RSI {rsi:.0f} — titolo ipercomprato. Il prezzo ha corso troppo velocemente, rischio di correzione.")
        elif rsi > 60:
            score -= 1
            avvisi.append(f"🌡️ RSI {rsi:.0f} — momentum elevato. Non inseguire il rialzo, aspetta un ritracciamento.")

        # 7. MACD
        if macd > 0:
            score += 1
            motivazioni.append(f"⚡ MACD positivo ({macd:+.3f}) — momentum rialzista attivo")
        else:
            score -= 1
            avvisi.append(f"⬇️ MACD negativo ({macd:+.3f}) — pressione ribassista prevalente")

        # 8. Minimo/massimo settimana
        if levels["week_low"] and abs(p - levels["week_low"])/p < 0.02:
            score += 1
            motivazioni.append(f"📅 Vicino al minimo settimanale ({levels['week_low']:.2f}) — zona di potenziale inversione di breve")
        if levels["week_high"] and abs(p - levels["week_high"])/p < 0.02:
            score -= 1
            avvisi.append(f"📅 Vicino al massimo settimanale ({levels['week_high']:.2f}) — zona di potenziale distribuzione")

        forza = min(5, max(1, abs(score) + 1))

        if score >= 2:
            return "ENTRA", "#10B981", forza, motivazioni, avvisi
        elif score <= -2:
            return "ESCI/ASPETTA", "#EF4444", forza, motivazioni, avvisi
        else:
            return "ASPETTA", "#F59E0B", forza, motivazioni, avvisi

    # ── UI ────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-hd">🎯 Reversal Radar — analisi intraday multi-timeframe</div>', unsafe_allow_html=True)
    st.caption("Giornaliero per i livelli storici · Orario per il timing intraday · Aggiornamento automatico ogni 5 minuti")

    # Raccoglie tutti i ticker
    radar_tickers = []
    seen_r = set()
    for p in st.session_state.data["portfolio"]:
        tk = p.get("ticker","N/A")
        if tk not in ("N/A","",None) and tk.upper() not in seen_r:
            radar_tickers.append({"ticker":tk,"nome":p["nome"],"fonte":"portafoglio"})
            seen_r.add(tk.upper())
    for w in st.session_state.data["watchlist"]:
        tk = w.get("ticker","N/A")
        if tk not in ("N/A","",None) and tk.upper() not in seen_r:
            radar_tickers.append({"ticker":tk,"nome":w["nome"],"fonte":"watchlist"})
            seen_r.add(tk.upper())

    # Selezione titolo
    sel_col1, sel_col2, sel_col3 = st.columns([3,1,1])
    with sel_col1:
        ticker_names = [f"{t['ticker']} — {t['nome']} ({'💼' if t['fonte']=='portafoglio' else '👁️'})" for t in radar_tickers]
        sel_radar = st.selectbox("Seleziona titolo da analizzare:", range(len(ticker_names)),
                                  format_func=lambda i: ticker_names[i], key="radar_sel")
    with sel_col2:
        tf_choice = st.selectbox("Timeframe intraday:", ["1h","30m","15m"], key="radar_tf",
                                  help="1h = visione 5 giorni · 30m = 2-3 giorni · 15m = ultima giornata")
    with sel_col3:
        period_map = {"1h":"5d","30m":"2d","15m":"1d"}
        st.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
        if st.button("🔄 Aggiorna", key="btn_radar_refresh", use_container_width=True):
            st.cache_data.clear()

    if sel_radar is not None and radar_tickers:
        selected = radar_tickers[sel_radar]
        tk_r = selected["ticker"]
        nome_r = selected["nome"]

        with st.spinner(f"Caricamento dati per {nome_r}..."):
            h_1d  = get_daily(tk_r, period="3mo")
            h_hr  = get_intraday(tk_r, interval=tf_choice, period=period_map[tf_choice])
            td_r  = get_technical(tk_r)

        if h_1d is None and h_hr is None:
            st.warning(f"Dati non disponibili per {tk_r}. Verifica che il ticker sia corretto su Yahoo Finance.")
        else:
            levels  = compute_key_levels(h_1d, h_hr)
            price_r = float(h_1d["Close"].iloc[-1]) if h_1d is not None else (float(h_hr["Close"].iloc[-1]) if h_hr is not None else 0)
            rsi_r   = td_r["rsi"]   if td_r else 50
            macd_r  = td_r["macd_h"] if td_r else 0

            segnale, sig_color, forza, motivazioni, avvisi = reversal_signal(price_r, levels, rsi_r, macd_r)

            # ── HEADER: semaforo + KPI ────────────────────────────────────────
            hdr1, hdr2, hdr3, hdr4, hdr5 = st.columns([2,1,1,1,1])
            with hdr1:
                forza_stars = "●" * forza + "○" * (5-forza)
                st.markdown(f"""
<div style="background:#0F1829;border:2px solid {sig_color};border-radius:14px;padding:1.2rem 1.4rem;text-align:center;">
  <div style="font-size:.65rem;color:#64748B;text-transform:uppercase;letter-spacing:.1em;margin-bottom:.4rem;">{nome_r} · {tk_r}</div>
  <div style="font-family:'JetBrains Mono',monospace;font-size:2rem;font-weight:700;color:{sig_color};">{segnale}</div>
  <div style="font-size:.82rem;color:{sig_color};margin-top:.3rem;">{forza_stars} forza {forza}/5</div>
</div>""", unsafe_allow_html=True)
            for col, (label, val, color) in zip([hdr2,hdr3,hdr4,hdr5],[
                ("Prezzo ora",   f"{price_r:.2f}", "#E8EDF5"),
                ("RSI",          f"{rsi_r:.0f}", "#EF4444" if rsi_r>70 else ("#10B981" if rsi_r<30 else "#E8EDF5")),
                ("Pivot",        f"{levels['pivot']:.2f}" if levels['pivot'] else "—", "#F59E0B"),
                ("VWAP",         f"{levels['vwap']:.2f}" if levels['vwap'] else "—", "#8B5CF6"),
            ]):
                with col:
                    st.markdown(f"""<div style="background:#0F1829;border:1px solid #243352;border-radius:10px;padding:.8rem;text-align:center;height:100%;">
<div style="font-size:.6rem;color:#64748B;text-transform:uppercase;margin-bottom:.3rem;">{label}</div>
<div style="font-family:'JetBrains Mono',monospace;font-size:1.1rem;font-weight:700;color:{color};">{val}</div>
</div>""", unsafe_allow_html=True)

            st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

            # ── GRAFICI AFFIANCATI ────────────────────────────────────────────
            g_col1, g_col2 = st.columns([1,1])

            # ── Grafico 1: Candele intraday + livelli ─────────────────────────
            with g_col1:
                st.markdown('<div style="font-size:.68rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#64748B;margin-bottom:.4rem;">Candele intraday + livelli chiave</div>', unsafe_allow_html=True)
                if h_hr is not None and len(h_hr) > 0:
                    fig_intra = go.Figure()

                    # Candele
                    fig_intra.add_trace(go.Candlestick(
                        x=h_hr.index, open=h_hr["Open"], high=h_hr["High"],
                        low=h_hr["Low"], close=h_hr["Close"], name="Prezzo",
                        increasing_line_color="#10B981", decreasing_line_color="#EF4444",
                        increasing_fillcolor="#10B981", decreasing_fillcolor="#EF4444"))

                    # Livelli pivot
                    if levels["pivot"]:
                        fig_intra.add_hline(y=levels["pivot"], line_color="#F59E0B", line_dash="dot", line_width=1.5,
                            annotation_text=f"Pivot {levels['pivot']:.2f}", annotation_font_color="#F59E0B", annotation_font_size=10)
                    if levels["r1"]:
                        fig_intra.add_hline(y=levels["r1"], line_color="#EF4444", line_dash="dash", line_width=1,
                            annotation_text=f"R1 {levels['r1']:.2f}", annotation_font_color="#EF4444", annotation_font_size=10)
                    if levels["r2"]:
                        fig_intra.add_hline(y=levels["r2"], line_color="#EF4444", line_dash="dot", line_width=1, opacity=0.6,
                            annotation_text=f"R2 {levels['r2']:.2f}", annotation_font_color="#EF4444", annotation_font_size=10)
                    if levels["s1"]:
                        fig_intra.add_hline(y=levels["s1"], line_color="#10B981", line_dash="dash", line_width=1,
                            annotation_text=f"S1 {levels['s1']:.2f}", annotation_font_color="#10B981", annotation_font_size=10)
                    if levels["s2"]:
                        fig_intra.add_hline(y=levels["s2"], line_color="#10B981", line_dash="dot", line_width=1, opacity=0.6,
                            annotation_text=f"S2 {levels['s2']:.2f}", annotation_font_color="#10B981", annotation_font_size=10)

                    # VWAP
                    if levels["vwap"]:
                        fig_intra.add_hline(y=levels["vwap"], line_color="#8B5CF6", line_dash="dash", line_width=1.5,
                            annotation_text=f"VWAP {levels['vwap']:.2f}", annotation_font_color="#8B5CF6", annotation_font_size=10)

                    # Zone supporto/resistenza storiche (semitrasparenti)
                    for sup in levels["supports"]:
                        fig_intra.add_hrect(y0=sup*0.998, y1=sup*1.002,
                            fillcolor="rgba(16,185,129,0.12)", line_width=0)
                    for res in levels["resistances"]:
                        fig_intra.add_hrect(y0=res*0.998, y1=res*1.002,
                            fillcolor="rgba(239,68,68,0.12)", line_width=0)

                    fig_intra.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(22,32,53,.8)",
                        font_color="#E8EDF5", xaxis_rangeslider_visible=False,
                        xaxis=dict(gridcolor="#1E2D47", color="#64748B"),
                        yaxis=dict(gridcolor="#1E2D47"),
                        legend=dict(bgcolor="rgba(0,0,0,0)"),
                        height=380, margin=dict(t=5,b=5,l=5,r=80))
                    st.plotly_chart(fig_intra, use_container_width=True)
                else:
                    st.info("Dati intraday non disponibili per questo ticker.")

            # ── Grafico 2: Giornaliero 3 mesi + supporti/resistenze storici ──
            with g_col2:
                st.markdown('<div style="font-size:.68rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#64748B;margin-bottom:.4rem;">Giornaliero 3 mesi + struttura di mercato</div>', unsafe_allow_html=True)
                if h_1d is not None and len(h_1d) > 10:
                    fig_daily = go.Figure()

                    fig_daily.add_trace(go.Candlestick(
                        x=h_1d.index, open=h_1d["Open"], high=h_1d["High"],
                        low=h_1d["Low"], close=h_1d["Close"], name="Giornaliero",
                        increasing_line_color="#10B981", decreasing_line_color="#EF4444",
                        increasing_fillcolor="#10B981", decreasing_fillcolor="#EF4444"))

                    # MA50 e MA200
                    c_d = h_1d["Close"]
                    if len(c_d) >= 50:
                        fig_daily.add_trace(go.Scatter(x=h_1d.index, y=c_d.rolling(50).mean(),
                            name="MA50", line=dict(color="#F59E0B", width=1.5, dash="dot")))
                    if len(c_d) >= 200:
                        fig_daily.add_trace(go.Scatter(x=h_1d.index, y=c_d.rolling(200).mean(),
                            name="MA200", line=dict(color="#8B5CF6", width=1.5, dash="dash")))

                    # Supporti e resistenze storici come zone
                    for sup in levels["supports"]:
                        fig_daily.add_hrect(y0=sup*0.997, y1=sup*1.003,
                            fillcolor="rgba(16,185,129,0.15)", line_color="#10B981", line_width=1,
                            annotation_text=f"Sup {sup:.2f}", annotation_font_color="#10B981", annotation_font_size=9)
                    for res in levels["resistances"]:
                        fig_daily.add_hrect(y0=res*0.997, y1=res*1.003,
                            fillcolor="rgba(239,68,68,0.15)", line_color="#EF4444", line_width=1,
                            annotation_text=f"Res {res:.2f}", annotation_font_color="#EF4444", annotation_font_size=9)

                    # Bande di Bollinger
                    bm = c_d.rolling(20).mean(); bs = c_d.rolling(20).std()
                    fig_daily.add_trace(go.Scatter(x=h_1d.index, y=bm+2*bs,
                        name="Boll+", line=dict(color="#3B82F6",width=1,dash="dot"), opacity=0.5))
                    fig_daily.add_trace(go.Scatter(x=h_1d.index, y=bm-2*bs,
                        name="Boll-", line=dict(color="#3B82F6",width=1,dash="dot"),
                        fill="tonexty", fillcolor="rgba(59,130,246,0.05)", opacity=0.5))

                    fig_daily.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(22,32,53,.8)",
                        font_color="#E8EDF5", xaxis_rangeslider_visible=False,
                        xaxis=dict(gridcolor="#1E2D47", color="#64748B"),
                        yaxis=dict(gridcolor="#1E2D47"),
                        legend=dict(bgcolor="rgba(0,0,0,0)", font_size=9),
                        height=380, margin=dict(t=5,b=5,l=5,r=80))
                    st.plotly_chart(fig_daily, use_container_width=True)

            # ── RSI intraday subplot ──────────────────────────────────────────
            if h_hr is not None and len(h_hr) > 14:
                c_h = h_hr["Close"]
                d_h = c_h.diff()
                rsi_h = 100 - 100/(1 + d_h.clip(lower=0).rolling(14).mean() /
                                   (-d_h.clip(upper=0)).rolling(14).mean().replace(0,1e-9))
                fig_rsi_h = go.Figure()
                fig_rsi_h.add_trace(go.Scatter(x=h_hr.index, y=rsi_h,
                    line=dict(color="#3B82F6",width=2), fill="tonexty",
                    fillcolor="rgba(59,130,246,0.08)", name="RSI"))
                fig_rsi_h.add_hline(y=70, line_color="#EF4444", line_dash="dot",
                    annotation_text="Ipercomprato 70", annotation_font_color="#EF4444", annotation_font_size=10)
                fig_rsi_h.add_hline(y=30, line_color="#10B981", line_dash="dot",
                    annotation_text="Ipervenduto 30", annotation_font_color="#10B981", annotation_font_size=10)
                fig_rsi_h.add_hline(y=50, line_color="#64748B", line_dash="dot", opacity=0.5)
                fig_rsi_h.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(22,32,53,.8)",
                    font_color="#E8EDF5", showlegend=False,
                    xaxis=dict(gridcolor="#1E2D47"), yaxis=dict(gridcolor="#1E2D47", range=[0,100]),
                    height=120, margin=dict(t=0,b=5,l=5,r=80),
                    title=dict(text="RSI intraday", font=dict(size=10,color="#64748B"), x=0))
                st.plotly_chart(fig_rsi_h, use_container_width=True)

            # ── SPIEGAZIONE TESTUALE ──────────────────────────────────────────
            st.markdown('<div class="section-hd">🧠 Analisi — cosa sta succedendo e cosa fare</div>', unsafe_allow_html=True)

            exp_col1, exp_col2 = st.columns(2)

            with exp_col1:
                if motivazioni:
                    st.markdown(f'<div style="background:rgba(16,185,129,.08);border:1px solid rgba(16,185,129,.3);border-radius:10px;padding:1rem 1.1rem;">'
                        f'<div style="font-size:.65rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#10B981;margin-bottom:.6rem;">✅ Segnali a favore di un ingresso</div>'
                        + "".join([f'<div style="font-size:.81rem;color:#94A3B8;padding:.35rem 0;border-bottom:1px solid #1E2D47;">{m}</div>' for m in motivazioni])
                        + '</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div style="background:#0F1829;border:1px solid #243352;border-radius:10px;padding:.9rem;font-size:.82rem;color:#64748B;">Nessun segnale rialzista rilevante al momento.</div>', unsafe_allow_html=True)

            with exp_col2:
                if avvisi:
                    st.markdown(f'<div style="background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.3);border-radius:10px;padding:1rem 1.1rem;">'
                        f'<div style="font-size:.65rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#EF4444;margin-bottom:.6rem;">⚠️ Segnali di cautela o uscita</div>'
                        + "".join([f'<div style="font-size:.81rem;color:#94A3B8;padding:.35rem 0;border-bottom:1px solid #1E2D47;">{a}</div>' for a in avvisi])
                        + '</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div style="background:#0F1829;border:1px solid #243352;border-radius:10px;padding:.9rem;font-size:.82rem;color:#64748B;">Nessun segnale ribassista rilevante al momento.</div>', unsafe_allow_html=True)

            # ── RIEPILOGO LIVELLI ─────────────────────────────────────────────
            st.markdown('<div class="section-hd">📐 Mappa dei livelli — dove si trova il prezzo</div>', unsafe_allow_html=True)

            all_levels_map = []
            if levels["r2"]: all_levels_map.append(("R2 — Resistenza forte",  levels["r2"], "#EF4444", "Zona di forte pressione ribassista. Se superata con volume, segnale molto rialzista."))
            if levels["r1"]: all_levels_map.append(("R1 — Resistenza pivot",  levels["r1"], "#EF4444", "Prima resistenza pivot giornaliera. Spesso il prezzo si ferma qui."))
            for res in reversed(levels["resistances"][-3:]):
                all_levels_map.append((f"Resistenza storica {res:.2f}", res, "#F97316", "Swing high recente — zona dove i venditori hanno prevalso in passato."))
            if levels["vwap"]: all_levels_map.append(("VWAP", levels["vwap"], "#8B5CF6", "Prezzo medio ponderato per volume — benchmark intraday degli istituzionali."))
            if levels["pivot"]: all_levels_map.append(("Pivot Point", levels["pivot"], "#F59E0B", "Livello di equilibrio calcolato da dati di ieri (H+L+C)/3."))
            for sup in levels["supports"][-3:]:
                all_levels_map.append((f"Supporto storico {sup:.2f}", sup, "#10B981", "Swing low recente — zona dove gli acquirenti hanno prevalso in passato."))
            if levels["s1"]: all_levels_map.append(("S1 — Supporto pivot",  levels["s1"], "#10B981", "Primo supporto pivot — zona di potenziale rimbalzo giornaliero."))
            if levels["s2"]: all_levels_map.append(("S2 — Supporto forte",  levels["s2"], "#10B981", "Zona di supporto forte. Rottura al ribasso = segnale molto negativo."))

            # Sort by level value descending (dal più alto al più basso)
            all_levels_map.sort(key=lambda x: -x[1])

            for label, lv, color, desc in all_levels_map:
                is_current = abs(price_r - lv) / price_r < 0.02 if price_r > 0 else False
                highlight = f"border:2px solid {color};" if is_current else f"border:1px solid {color}33;"
                bg = f"background:rgba(59,130,246,.08);" if is_current else "background:#0F1829;"
                arrow = f"<span style='font-size:.9rem;'>◄ PREZZO QUI</span> " if is_current else ""
                dist_str = ""
                if price_r > 0:
                    dist = (lv - price_r) / price_r * 100
                    dist_str = f"<span style='color:#64748B;font-size:.72rem;'> {dist:+.1f}%</span>"
                st.markdown(
                    f'<div style="{bg}{highlight}border-radius:8px;padding:.55rem 1rem;margin-bottom:.3rem;display:flex;align-items:center;gap:.8rem;">'
                    f'<div style="width:8px;height:8px;border-radius:50%;background:{color};flex-shrink:0;"></div>'
                    f'<div style="flex:1;font-size:.8rem;color:#E8EDF5;font-weight:{"700" if is_current else "400"};">'
                    f'{arrow}{label} — <b style="color:{color};">{lv:.2f}</b>{dist_str}'
                    f'</div>'
                    f'<div style="font-size:.72rem;color:#64748B;max-width:300px;text-align:right;">{desc}</div>'
                    f'</div>', unsafe_allow_html=True)

            # ── ALERT CONFIGURAZIONE ──────────────────────────────────────────
            st.markdown('<div class="section-hd">🔔 Alert automatico email quando il prezzo tocca un livello</div>', unsafe_allow_html=True)
            em_cfg = st.session_state.data.get("email_settings",{})
            if not em_cfg.get("from_email"):
                st.info("Configura prima l'email nel tab ✏️ Gestione → Alert Email per abilitare gli alert automatici.")
            else:
                al1, al2, al3 = st.columns(3)
                with al1:
                    alert_level = st.number_input("Livello di prezzo da monitorare", value=float(levels["s1"] or price_r),
                                                   step=0.01, format="%.2f", key="alert_level_r")
                with al2:
                    alert_dir = st.selectbox("Direzione alert:", ["Sotto (rimbalzo — entra)", "Sopra (resistenza — esci/attenzione)"], key="alert_dir_r")
                with al3:
                    st.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
                    if st.button("📧 Invia alert se tocca questo livello", key="btn_alert_r", use_container_width=True):
                        dir_label = "scende sotto" if "Sotto" in alert_dir else "sale sopra"
                        action    = "🟢 POSSIBILE INGRESSO — il prezzo è su supporto" if "Sotto" in alert_dir else "🔴 ATTENZIONE — il prezzo ha raggiunto resistenza"
                        html_alert = f"""
<div style="font-family:Inter,sans-serif;background:#070D1A;color:#E8EDF5;padding:1.5rem;border-radius:10px;max-width:520px;">
  <div style="font-size:1rem;font-weight:700;margin-bottom:1rem;">🎯 Reversal Radar Alert</div>
  <div style="background:#0F1829;border-radius:8px;padding:1rem;margin-bottom:.8rem;">
    <div style="font-size:.8rem;color:#64748B;">Titolo monitorato</div>
    <div style="font-size:1.1rem;font-weight:700;">{nome_r} ({tk_r})</div>
  </div>
  <div style="font-size:.9rem;line-height:1.8;color:#94A3B8;">
    Il prezzo ha {dir_label} il livello <b style="color:#E8EDF5;">{alert_level:.2f}</b>.<br>
    Prezzo attuale: <b style="color:#E8EDF5;">{price_r:.2f}</b><br><br>
    <b style="color:#E8EDF5;">{action}</b>
  </div>
</div>"""
                        ok_a, msg_a = send_email_alert(em_cfg,
                            f"🎯 Alert {nome_r}: prezzo su livello {alert_level:.2f}",
                            html_alert)
                        if ok_a: st.success(f"✅ Alert inviato a {em_cfg['to_email']}")
                        else:    st.error(f"❌ {msg_a}")
                        st.info("💡 Per alert automatici ricorrenti (quando il prezzo tocca il livello durante il giorno), configura uno scheduler esterno o controlla manualmente.")

    # ── RADAR VELOCE: semaforo su tutti i titoli ──────────────────────────────
    st.markdown('<div class="section-hd">⚡ Radar veloce — semaforo su tutti i titoli</div>', unsafe_allow_html=True)
    st.caption("Panoramica rapida dello stato di ogni titolo rispetto ai livelli chiave. Clicca su un titolo per l'analisi completa.")

    if st.button("🔄 Calcola semaforo su tutti i titoli", key="btn_radar_all"):
        radar_rows = []
        prog_r = st.progress(0)
        for qi2, t_item in enumerate(radar_tickers[:25]):  # max 25 per performance
            prog_r.progress(int((qi2+1)/min(len(radar_tickers),25)*100))
            td2 = get_technical(t_item["ticker"])
            if not td2: continue
            h1d2 = get_daily(t_item["ticker"], period="3mo")
            h1h2 = get_intraday(t_item["ticker"], interval="1h", period="5d")
            lv2  = compute_key_levels(h1d2, h1h2)
            p2   = td2["price"]
            sig2, col2, forza2, mot2, avv2 = reversal_signal(p2, lv2, td2["rsi"], td2["macd_h"])
            near_sup = any(abs(p2-s)/p2 < 0.02 for s in lv2["supports"] if s > 0)
            near_res = any(abs(p2-r)/p2 < 0.02 for r in lv2["resistances"] if r > 0)
            radar_rows.append({
                "Segnale":   f"{'🟢' if sig2=='ENTRA' else ('🔴' if sig2=='ESCI/ASPETTA' else '🟡')} {sig2}",
                "Ticker":    t_item["ticker"],
                "Nome":      t_item["nome"][:20],
                "Fonte":     "💼" if t_item["fonte"]=="portafoglio" else "👁️",
                "Prezzo":    f"{p2:.2f}",
                "RSI":       f"{td2['rsi']:.0f}",
                "MACD":      "↑" if td2["macd_h"]>0 else "↓",
                "Su supporto": "✅" if near_sup else "—",
                "Su resistenza": "⚠️" if near_res else "—",
                "Forza":     "●"*forza2+"○"*(5-forza2),
            })
        prog_r.empty()
        if radar_rows:
            df_radar = pd.DataFrame(radar_rows)
            st.dataframe(df_radar, use_container_width=True, hide_index=True, height=500)
        else:
            st.info("Nessun dato disponibile.")
