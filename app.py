import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import json, requests, time, smtplib, ssl, re, base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path
import anthropic

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Investment Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── GLOBAL STYLES ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
:root {
  --bg:#070D1A; --s1:#0F1829; --s2:#162035; --s3:#1E2D47;
  --bd:#243352; --bd2:#2E4070;
  --accent:#3B82F6; --accent2:#60A5FA;
  --green:#10B981; --yellow:#F59E0B; --red:#EF4444; --purple:#8B5CF6;
  --text:#E8EDF5; --text2:#94A3B8; --text3:#64748B;
  --mono:'JetBrains Mono',monospace;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body,[class*="css"]{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text)}
.stApp{background:var(--bg)}
.main .block-container{padding:1rem 1.5rem 2rem;max-width:1800px}
section[data-testid="stSidebar"]{background:var(--s1)!important;border-right:1px solid var(--bd)}
section[data-testid="stSidebar"] *{color:var(--text)!important}
.stTabs [data-baseweb="tab-list"]{background:var(--s1);border:1px solid var(--bd);border-radius:10px;padding:3px;gap:2px}
.stTabs [data-baseweb="tab"]{background:transparent;color:var(--text3);border-radius:8px;font-size:.82rem;font-weight:500;padding:.4rem .9rem}
.stTabs [aria-selected="true"]{background:var(--accent)!important;color:#fff!important}
[data-testid="metric-container"]{background:var(--s1);border:1px solid var(--bd);border-radius:10px;padding:.9rem 1rem}
[data-testid="stMetricValue"]{font-family:var(--mono);font-size:1.3rem!important}
.stTextInput input,.stNumberInput input,.stSelectbox>div>div{background:var(--s2)!important;border:1px solid var(--bd)!important;color:var(--text)!important;border-radius:8px!important}
.stButton>button{background:var(--accent);color:#fff;border:none;border-radius:8px;font-weight:600;font-size:.82rem;padding:.45rem 1rem;transition:all .15s}
.stButton>button:hover{background:var(--accent2);transform:translateY(-1px)}
.streamlit-expanderHeader{background:var(--s2)!important;border:1px solid var(--bd)!important;border-radius:8px!important;color:var(--text)!important}
.streamlit-expanderContent{background:var(--s2)!important;border:1px solid var(--bd)!important;border-top:none!important;border-radius:0 0 8px 8px!important}
.stDataFrame{border-radius:10px;overflow:hidden}
.stRadio>div{gap:.5rem}
.stRadio label{color:var(--text2)!important;font-size:.85rem}
#MainMenu,footer,header{visibility:hidden}
.section-hd{font-size:.7rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--text3);padding:.5rem 0 .4rem;border-bottom:1px solid var(--bd);margin-bottom:.8rem;margin-top:1.2rem}
.card{background:var(--s1);border:1px solid var(--bd);border-radius:12px;padding:1rem 1.2rem}
.tooltip-box{background:var(--s3);border:1px solid var(--bd2);border-radius:8px;padding:.6rem .8rem;font-size:.78rem;color:var(--text2);line-height:1.5;margin-top:.3rem}
.action-box{border-radius:10px;padding:.8rem 1rem;margin-bottom:.5rem;font-size:.84rem;line-height:1.6}
.quindi{background:rgba(59,130,246,.08);border-left:3px solid #3B82F6;border-radius:0 8px 8px 0;padding:.6rem .9rem;margin-top:.5rem;font-size:.83rem;color:#E8EDF5}
</style>
""", unsafe_allow_html=True)

# ── CATEGORY COLORS ───────────────────────────────────────────────────────────
CAT_COLORS = {
    "Azioni":"#3B82F6","ETF":"#10B981","Obbligazioni":"#F59E0B",
    "Crypto":"#8B5CF6","Certificati":"#06B6D4","Materie Prime":"#F97316",
    "Liquidita":"#94A3B8"
}

# ── DEFAULT DATA ──────────────────────────────────────────────────────────────
DEFAULT_DATA = {
    "portfolio": [
        # AZIONI
        {"nome":"Leonardo","ticker":"LDO.MI","valuta":"EUR","prezzo_carico":20.640,"quantita":33,"categoria":"Azioni","prezzo_manuale":None},
        {"nome":"Ipsos","ticker":"IPS.PA","valuta":"EUR","prezzo_carico":46.053,"quantita":30,"categoria":"Azioni","prezzo_manuale":None},
        {"nome":"Trigano","ticker":"TRI.PA","valuta":"EUR","prezzo_carico":106.19,"quantita":5,"categoria":"Azioni","prezzo_manuale":None},
        {"nome":"Pinduoduo","ticker":"PDD","valuta":"USD","prezzo_carico":100.377,"quantita":7,"categoria":"Azioni","prezzo_manuale":None},
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
        {"nome":"Lyxor MSCI Emerging Markets","ticker":"LEM.PA","valuta":"EUR","prezzo_carico":13.183,"quantita":115,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"iShares MSCI World Value Factor","ticker":"IWVL.L","valuta":"EUR","prezzo_carico":42.429,"quantita":36,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"iShares MSCI India","ticker":"NDIA.L","valuta":"EUR","prezzo_carico":8.594,"quantita":176,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"Xtrackers World Consumer Staples","ticker":"XDWS.L","valuta":"EUR","prezzo_carico":43.306,"quantita":45,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"Xtrackers Healthcare","ticker":"XDWH.L","valuta":"EUR","prezzo_carico":47.717,"quantita":38,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"Xtrackers II Global Gov. Bond","ticker":"XGSH.MI","valuta":"EUR","prezzo_carico":221.001,"quantita":18,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"iShares Core MSCI World","ticker":"SWDA.MI","valuta":"EUR","prezzo_carico":82.363,"quantita":53,"categoria":"ETF","prezzo_manuale":None},
        # CRYPTO
        {"nome":"Ethereum","ticker":"ETH-USD","valuta":"USD","prezzo_carico":3099.44,"quantita":0.48,"categoria":"Crypto","prezzo_manuale":None},
        {"nome":"Bitcoin","ticker":"BTC-USD","valuta":"USD","prezzo_carico":56403.66,"quantita":0.03,"categoria":"Crypto","prezzo_manuale":None},
        {"nome":"Ripple (XRP)","ticker":"XRP-USD","valuta":"USD","prezzo_carico":2.35,"quantita":668.09,"categoria":"Crypto","prezzo_manuale":None},
        # MATERIE PRIME
        {"nome":"Oro (Futures)","ticker":"GC=F","valuta":"USD","prezzo_carico":1580.00,"quantita":0.47,"categoria":"Materie Prime","prezzo_manuale":None},
        {"nome":"WisdomTree Copper","ticker":"COPA.L","valuta":"EUR","prezzo_carico":38.070,"quantita":27,"categoria":"Materie Prime","prezzo_manuale":None},
        {"nome":"WisdomTree Physical Gold","ticker":"PHAU.L","valuta":"EUR","prezzo_carico":173.300,"quantita":21,"categoria":"Materie Prime","prezzo_manuale":None},
        # LIQUIDITA
        {"nome":"Liquidita","ticker":"N/A","valuta":"EUR","prezzo_carico":1.0,"quantita":16000,"categoria":"Liquidita","prezzo_manuale":1.0},
    ],
    "watchlist": [
        {"ticker":"MSFT","nome":"Microsoft","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"DAL","nome":"Delta Airlines","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"RDDT","nome":"Reddit","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"DIS","nome":"Walt Disney","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"KOID","nome":"KraneShares Humanoid","categoria":"ETF","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"NLR","nome":"VanEck Uranium Nuclear","categoria":"ETF","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"MELI","nome":"MercadoLibre","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"AMP.MI","nome":"Amplifon","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"ENEL.MI","nome":"Enel","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"SES.MI","nome":"Sesa","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"NVDA","nome":"NVIDIA","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"XPEL","nome":"XPEL Inc.","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"ICLR","nome":"Icon PLC","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"IP.MI","nome":"Interpump Group","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"AMZN","nome":"Amazon","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"PYPL","nome":"PayPal","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"IONQ","nome":"IonQ","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"SLV","nome":"iShares Silver Trust","categoria":"Materie Prime","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"Proxy argento","ai_pending":False},
        {"ticker":"NVO","nome":"Novo Nordisk","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"LLY","nome":"Eli Lilly","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"REGN","nome":"Regeneron Pharma","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"XX25.MI","nome":"Xtrackers MSCI China","categoria":"ETF","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"GOOG","nome":"Alphabet (Google)","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"XMJP.MI","nome":"iShares MSCI Japan","categoria":"ETF","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"NKE","nome":"Nike","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"HLNE","nome":"Hamilton Lane","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"ARIS.MI","nome":"Ariston Holding","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"MAIRE.MI","nome":"Maire","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
        {"ticker":"N/A","nome":"Klarna (IPO attesa)","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"Non quotata. Segui IPO NYSE 2025.","ai_pending":False},
        {"ticker":"PRT.MI","nome":"Esprinet","categoria":"Azioni","sorgente":"utente","segnale":"MONITORA","prezzo_target":None,"stop_loss":None,"ingresso":None,"strategia":None,"orizzonte":None,"note":"","ai_pending":False},
    ],
    "agent_cache": {},
    "trade_history": [],
    "email_settings": {}
}

# ── GITHUB PERSISTENCE ────────────────────────────────────────────────────────
_GH_FILE = "data/portfolio_data.json"

def _gh_token():
    try:
        return str(st.secrets.get("GITHUB_TOKEN","") or "").strip() if hasattr(st,"secrets") else ""
    except: return ""

def _gh_repo():
    try:
        return str(st.secrets.get("GITHUB_REPO","salvasime/Trading-AI") or "salvasime/Trading-AI").strip() if hasattr(st,"secrets") else "salvasime/Trading-AI"
    except: return "salvasime/Trading-AI"

def _gh_read():
    token = _gh_token()
    if not token: return None, None
    try:
        r = requests.get(
            f"https://api.github.com/repos/{_gh_repo()}/contents/{_GH_FILE}",
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
            timeout=8)
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            return json.loads(content), data["sha"]
        return None, None
    except: return None, None

def _gh_write(d, sha=None):
    token = _gh_token()
    if not token: return False
    try:
        content = base64.b64encode(
            json.dumps(d, indent=2, ensure_ascii=False).encode("utf-8")
        ).decode("utf-8")
        payload = {"message": f"Update {datetime.now().strftime('%Y-%m-%d %H:%M')}", "content": content}
        if sha: payload["sha"] = sha
        r = requests.put(
            f"https://api.github.com/repos/{_gh_repo()}/contents/{_GH_FILE}",
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
            json=payload, timeout=12)
        return r.status_code in (200, 201)
    except: return False

def _merge_defaults(d):
    for k in ["agent_cache","trade_history","email_settings","watchlist"]:
        if k not in d: d[k] = {} if k in ["agent_cache","email_settings"] else []
    existing_t = {p.get("ticker","") for p in d.get("portfolio",[])}
    for item in DEFAULT_DATA["portfolio"]:
        if item.get("ticker","N/A") not in existing_t: d["portfolio"].append(item)
    existing_wl = {w.get("ticker","") for w in d.get("watchlist",[])}
    for wl in DEFAULT_DATA["watchlist"]:
        if wl.get("ticker","") not in existing_wl: d["watchlist"].append(wl)
    return d

def load_data():
    d_gh, _ = _gh_read()
    if d_gh: return _merge_defaults(d_gh)
    p = Path("data/portfolio.json")
    if p.exists():
        try: return _merge_defaults(json.loads(p.read_text()))
        except: pass
    return DEFAULT_DATA.copy()

def save_data(d):
    saved = False
    if _gh_token():
        try:
            d_save = {k:v for k,v in d.items() if k != "agent_cache"}
            _, sha = _gh_read()
            saved = _gh_write(d_save, sha)
            if not saved: st.session_state["_save_err"] = "GitHub save failed"
        except Exception as e:
            st.session_state["_save_err"] = str(e)[:120]
    try:
        Path("data").mkdir(exist_ok=True)
        Path("data/portfolio.json").write_text(json.dumps(d, indent=2, ensure_ascii=False))
    except: pass
    return saved

# ── API KEY LOADING (always before sidebar) ───────────────────────────────────
def _load_keys():
    try:
        if not hasattr(st,"secrets"): return
        ant  = str(st.secrets.get("ANTHROPIC_API_KEY","") or "").strip()
        news = str(st.secrets.get("NEWS_API_KEY","") or "").strip()
        if ant:  st.session_state["_ant_key"]  = ant
        if news: st.session_state["_news_key"] = news
    except: pass

_load_keys()

if "data" not in st.session_state:
    st.session_state.data = load_data()


# ── MARKET & FINANCE HELPERS ──────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_market_data():
    tickers = {"VIX":"^VIX","S&P 500":"^GSPC","FTSE MIB":"FTSEMIB.MI","Nasdaq":"^IXIC","EUR/USD":"EURUSD=X","Oro":"GC=F"}
    out = {}
    for name, t in tickers.items():
        try:
            h = yf.Ticker(t).history(period="5d")
            if len(h) >= 2:
                c,p = float(h["Close"].iloc[-1]),float(h["Close"].iloc[-2])
                out[name] = {"value":c,"delta":(c-p)/p*100}
            elif len(h)==1:
                out[name] = {"value":float(h["Close"].iloc[-1]),"delta":0}
            else: out[name] = {"value":0,"delta":0}
        except: out[name] = {"value":0,"delta":0}
    return out

@st.cache_data(ttl=300)
def get_fx_rates():
    pairs = {"USD":"EURUSD=X","GBP":"EURGBP=X","DKK":"EURDKK=X","CHF":"EURCHF=X"}
    fb    = {"USD":1.08,"GBP":0.85,"DKK":7.46,"CHF":0.95}
    rates = {"EUR":1.0}
    for cur,t in pairs.items():
        try:
            h = yf.Ticker(t).history(period="2d")
            rates[cur] = float(h["Close"].iloc[-1]) if not h.empty else fb[cur]
        except: rates[cur] = fb[cur]
    return rates

@st.cache_data(ttl=300)
def get_price(ticker):
    if not ticker or ticker=="N/A": return None
    try:
        h = yf.Ticker(ticker).history(period="2d")
        return float(h["Close"].iloc[-1]) if not h.empty else None
    except: return None

def to_eur(amount, currency, fx):
    return amount if currency=="EUR" else amount/fx.get(currency,1.0)

@st.cache_data(ttl=3600)
def get_technical(ticker):
    if not ticker or ticker=="N/A": return None
    try:
        h = yf.Ticker(ticker).history(period="1y")
        if len(h)<30: return None
        c = h["Close"]
        ma50  = float(c.rolling(50).mean().iloc[-1])  if len(c)>=50  else None
        ma200 = float(c.rolling(200).mean().iloc[-1]) if len(c)>=200 else None
        price = float(c.iloc[-1])
        d = c.diff()
        gain = d.clip(lower=0).rolling(14).mean()
        loss = (-d.clip(upper=0)).rolling(14).mean().replace(0,1e-9)
        rsi = float((100-100/(1+gain/loss)).iloc[-1])
        ema12=c.ewm(span=12).mean(); ema26=c.ewm(span=26).mean()
        macd=ema12-ema26; sig=macd.ewm(span=9).mean()
        macd_h = float((macd-sig).iloc[-1])
        bm=c.rolling(20).mean(); bs=c.rolling(20).std()
        boll_up=float((bm+2*bs).iloc[-1]); boll_dn=float((bm-2*bs).iloc[-1])
        support=float(c.rolling(20).min().iloc[-1])
        resistance=float(c.rolling(20).max().iloc[-1])
        cross=None
        if ma50 and ma200:
            p50=c.rolling(50).mean().iloc[-2]; p200=c.rolling(200).mean().iloc[-2]
            if p50<p200 and ma50>=ma200: cross="golden"
            elif p50>p200 and ma50<=ma200: cross="death"
        vol_avg=float(h["Volume"].rolling(20).mean().iloc[-1]) if "Volume" in h else 0
        vol_cur=float(h["Volume"].iloc[-1]) if "Volume" in h else 0
        return {"price":price,"ma50":ma50,"ma200":ma200,"rsi":rsi,"macd_h":macd_h,
                "boll_up":boll_up,"boll_dn":boll_dn,"support":support,"resistance":resistance,
                "cross":cross,"vol_ratio":vol_cur/vol_avg if vol_avg>0 else 1.0}
    except: return None

def tech_signal(td):
    if not td: return "⚪","N/D","Dati non disponibili"
    score=0; reasons=[]
    if td["ma50"]:
        if td["price"]>td["ma50"]: score+=1; reasons.append("sopra MA50")
        else: score-=1; reasons.append("sotto MA50")
    if td["ma200"]:
        if td["price"]>td["ma200"]: score+=2; reasons.append("sopra MA200")
        else: score-=2; reasons.append("sotto MA200")
    if td["cross"]=="golden": score+=2; reasons.append("Golden Cross")
    elif td["cross"]=="death": score-=2; reasons.append("Death Cross")
    r=td["rsi"]
    if r>70: score-=1; reasons.append(f"RSI {r:.0f} alto")
    elif r<30: score+=1; reasons.append(f"RSI {r:.0f} basso")
    if td["macd_h"]>0: score+=1; reasons.append("MACD positivo")
    else: score-=1; reasons.append("MACD negativo")
    if score>=3:   return "🟢","INCREMENTA",", ".join(reasons[:4])
    elif score>=1: return "🟡","TIENI",", ".join(reasons[:4])
    elif score>=-1: return "🟡","ATTENZIONE",", ".join(reasons[:4])
    else:           return "🔴","ALLEGGERISCI",", ".join(reasons[:4])

def signal_to_plain(label, td, nome):
    """Traduce il segnale tecnico in linguaggio semplice con il QUINDI."""
    if not td: return f"{nome}: dati non disponibili."
    rsi=td["rsi"]; macd=td["macd_h"]; p=td["price"]
    ma50=td["ma50"]; ma200=td["ma200"]
    parts=[]
    if ma50 and ma200:
        if p>ma50 and p>ma200: parts.append("sta salendo sia nel breve che nel lungo periodo")
        elif p<ma50 and p<ma200: parts.append("e' in calo sia nel breve che nel lungo periodo")
        else: parts.append("da' segnali contrastanti tra breve e lungo periodo")
    if rsi>70: parts.append(f"e' salito molto velocemente (RSI {rsi:.0f}) — potrebbe correggere")
    elif rsi<30: parts.append(f"e' stato venduto in eccesso (RSI {rsi:.0f}) — possibile rimbalzo")
    if macd>0: parts.append("con momentum positivo")
    else: parts.append("con momentum debole")
    desc = f"{nome} " + " e ".join(parts) + "."
    if label=="INCREMENTA":
        quindi = "Se vuoi aggiungere, e' tecnicamente un buon momento. Ingresso ideale vicino al supporto a " + f"{td['support']:.2f}."
    elif label=="TIENI":
        quindi = "Tienilo in portafoglio senza fretta di fare nulla. Rivaluta se scende sotto " + f"{td['support']:.2f}."
    elif label=="ATTENZIONE":
        quindi = "Attenzione: non aggiungere ora. Osserva nelle prossime settimane prima di decidere."
    else:
        quindi = "Valuta di ridurre la posizione, specialmente se sei in guadagno. Il momento non e' favorevole."
    return desc, quindi

def build_portfolio_df():
    fx=get_fx_rates(); rows=[]
    for item in st.session_state.data["portfolio"]:
        cat,val,pc,qty = item["categoria"],item["valuta"],item["prezzo_carico"],item["quantita"]
        pm=item.get("prezzo_manuale") or 0
        if pm>0: price_loc,src=pm,"manuale"
        elif item["ticker"]!="N/A":
            price_loc=get_price(item["ticker"]); src="live" if price_loc else "carico"
            if not price_loc: price_loc=pc
        else: price_loc,src=pc,"carico"
        if cat=="Obbligazioni":
            cv_eur=to_eur((price_loc/100)*qty,val,fx); ca_eur=to_eur((pc/100)*qty,val,fx)
        else:
            cv_eur=to_eur(price_loc*qty,val,fx); ca_eur=to_eur(pc*qty,val,fx)
        pnl=cv_eur-ca_eur
        rows.append({"Nome":item["nome"],"Ticker":item["ticker"],"Categoria":cat,
                     "Valuta":val,"P.Carico":pc,"P.Attuale":price_loc,"Fonte":src,
                     "Quantita":qty,"CV €":cv_eur,"P&L €":pnl,
                     "P&L %":(pnl/ca_eur*100) if ca_eur>0 else 0})
    return pd.DataFrame(rows)

@st.cache_data(ttl=300)
def get_news(api_key, query="economy market finance", days=2):
    if not api_key: return []
    try:
        from_dt=(datetime.now()-timedelta(days=days)).strftime("%Y-%m-%d")
        r=requests.get(
            f"https://newsapi.org/v2/everything?q={query}&from={from_dt}"
            f"&sortBy=relevancy&language=en&pageSize=15&apiKey={api_key}",timeout=10)
        return [{"title":a["title"],"source":a["source"]["name"],"url":a["url"]}
                for a in r.json().get("articles",[])[:12]]
    except: return []

def compute_health_score(df, mkt):
    score=50; components={}
    pnl_pct=df["P&L %"].mean() if not df.empty else 0
    pnl_score=max(-20,min(20,pnl_pct*2)); score+=pnl_score
    components["P&L medio"]={"val":f"{pnl_pct:+.1f}%","pts":pnl_score}
    tradeable=[p for p in st.session_state.data["portfolio"] if p["ticker"]!="N/A"]
    green=yellow=red=0
    for item in tradeable[:10]:
        td=get_technical(item["ticker"]); em,_,_=tech_signal(td)
        if em=="🟢": green+=1
        elif em=="🔴": red+=1
        else: yellow+=1
    total_t=green+yellow+red
    tech_pts=((green-red)/total_t)*20 if total_t>0 else 0
    score+=tech_pts
    components["Segnali tecnici"]={"val":f"{green}verde {yellow}neutro {red}rosso","pts":tech_pts}
    vix=mkt.get("VIX",{}).get("value",20)
    vix_pts=10 if vix<15 else (0 if vix<25 else -10); score+=vix_pts
    components["VIX"]={"val":f"{vix:.1f}","pts":vix_pts}
    if not df.empty:
        top_w=df["CV €"].max()/df["CV €"].sum()*100 if df["CV €"].sum()>0 else 0
        conc_pts=0 if top_w<15 else (-5 if top_w<25 else -10); score+=conc_pts
        components["Concentrazione"]={"val":f"Top {top_w:.1f}%","pts":conc_pts}
    missing=sum(1 for p in st.session_state.data["portfolio"] if p["ticker"]=="N/A" and not (p.get("prezzo_manuale") or 0)>0)
    miss_pts=min(0,-missing*2); score+=miss_pts
    if missing>0: components["Prezzi mancanti"]={"val":f"{missing} asset","pts":miss_pts}
    return max(0,min(100,round(score))), components

def calc_position_size(portfolio_total_eur, current_price, stop_loss_price, risk_pct=1.0, fx_rate=1.0, max_position_pct=2.5):
    """
    Position sizing con doppio vincolo:
    1) Rischio max = risk_pct% del portafoglio (default 1%)
    2) Posizione max = max_position_pct% del portafoglio (default 2.5%)
    Il piu restrittivo dei due vince.
    """
    if not stop_loss_price or not current_price or current_price<=stop_loss_price: return None
    risk_eur=portfolio_total_eur*(risk_pct/100)
    risk_per_share=(current_price-stop_loss_price)/fx_rate
    if risk_per_share<=0: return None
    # Calcola quote da rischio
    n_by_risk=max(1,int(risk_eur/risk_per_share))
    # Calcola quote massime per il cap percentuale
    max_pos_eur=portfolio_total_eur*(max_position_pct/100)
    n_by_cap=max(1,int(max_pos_eur*fx_rate/current_price))
    # Prendi il minore
    n=min(n_by_risk,n_by_cap)
    pos_eur=n*current_price/fx_rate
    actual_risk=n*risk_per_share  # rischio reale con il cap applicato
    return {"n_shares":n,"risk_eur":actual_risk,"position_eur":pos_eur,
            "position_pct":pos_eur/portfolio_total_eur*100,
            "capped":n<n_by_risk}  # True se il cap ha ridotto le quote

@st.cache_data(ttl=86400)
def get_fundamentals(ticker):
    if not ticker or ticker=="N/A": return None
    try:
        i=yf.Ticker(ticker).info
        if not i: return None
        def _f(k): return i.get(k)
        return {"pe":_f("trailingPE") or _f("forwardPE"),"peg":_f("pegRatio"),
                "pb":_f("priceToBook"),"de":_f("debtToEquity"),
                "roe":_f("returnOnEquity"),"rev_growth":_f("revenueGrowth"),
                "sector":_f("sector"),"mktcap":_f("marketCap")}
    except: return None

# ── EARNINGS DATA ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=21600)  # 6h cache
def get_earnings_data(ticker):
    """
    Recupera dati trimestrali da Yahoo Finance:
    - Data prossima trimestrale
    - Ultime 4 trimestrali: EPS atteso vs reale, surprise %
    - Trend revenue
    """
    if not ticker or ticker == "N/A": return None
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}

        # Prossima data trimestrale
        next_earnings_ts = info.get("earningsTimestamp") or info.get("earningsTimestampStart")
        next_earnings_str = None
        days_to_earnings = None
        if next_earnings_ts:
            try:
                from datetime import timezone
                next_dt = datetime.fromtimestamp(int(next_earnings_ts), tz=timezone.utc)
                next_dt_naive = next_dt.replace(tzinfo=None)
                days_to_earnings = (next_dt_naive - datetime.now()).days
                next_earnings_str = next_dt_naive.strftime("%d/%m/%Y")
            except: pass

        # Ultime trimestrali (earnings history)
        history = []
        try:
            eq = t.quarterly_earnings
            if eq is not None and not eq.empty:
                for idx_e, row_e in eq.tail(4).iterrows():
                    eps_actual   = row_e.get("Reported EPS", row_e.get("Actual", None))
                    eps_estimate = row_e.get("Estimated EPS", row_e.get("Estimate", None))
                    if eps_actual is None or eps_estimate is None: continue
                    try:
                        actual_f   = float(eps_actual)
                        estimate_f = float(eps_estimate)
                        if estimate_f != 0:
                            surprise_pct = (actual_f - estimate_f) / abs(estimate_f) * 100
                        else:
                            surprise_pct = 0
                        beat = actual_f >= estimate_f
                        history.append({
                            "period":   str(idx_e)[:7] if idx_e else "—",
                            "actual":   round(actual_f, 3),
                            "estimate": round(estimate_f, 3),
                            "surprise": round(surprise_pct, 1),
                            "beat":     beat,
                        })
                    except: pass
        except: pass

        # Revenue trend
        rev_growth = info.get("revenueGrowth")
        eps_growth = info.get("earningsGrowth")

        return {
            "next_date":        next_earnings_str,
            "days_to_earnings": days_to_earnings,
            "history":          history,
            "rev_growth":       rev_growth,
            "eps_growth":       eps_growth,
            "sector":           info.get("sector"),
        }
    except: return None

def earnings_alert_html(ticker, compact=False):
    """
    Genera HTML con avviso trimestrale.
    compact=True: solo badge colorato per watchlist/scanner
    compact=False: blocco completo per timing tab
    """
    ed = get_earnings_data(ticker)
    if not ed: return ""

    days = ed.get("days_to_earnings")
    next_date = ed.get("next_date", "—")
    history = ed.get("history", [])

    # Colore e livello di allerta in base ai giorni
    if days is not None and 0 <= days <= 7:
        alert_c = "#EF4444"; alert_icon = "🔴"
        alert_lbl = f"Trimestrale tra {days} giorni ({next_date}) — RISCHIO ALTO"
        alert_desc = "Entrare ora significa esporsi alla trimestrale. Anche con segnali tecnici perfetti, un dato deludente puo annullare settimane di trend in una seduta."
        alert_rec  = "Aspetta la pubblicazione prima di entrare, oppure usa uno stop molto stretto."
    elif days is not None and 8 <= days <= 21:
        alert_c = "#F59E0B"; alert_icon = "🟡"
        alert_lbl = f"Trimestrale tra {days} giorni ({next_date}) — ATTENZIONE"
        alert_desc = "La trimestrale e imminente. Il mercato potrebbe gia prezzare aspettative alte o basse."
        alert_rec  = "Considera di aspettare o di ridurre la dimensione della posizione."
    elif days is not None and days > 21:
        alert_c = "#10B981"; alert_icon = "🟢"
        alert_lbl = f"Prossima trimestrale: {next_date} (tra {days} giorni)"
        alert_desc = "Sufficiente distanza dalla trimestrale. Il rischio evento e basso."
        alert_rec  = ""
    elif days is not None and days < 0:
        alert_c = "#64748B"; alert_icon = "⚪"
        alert_lbl = f"Trimestrale appena pubblicata ({next_date})"
        alert_desc = "I risultati sono gia nel prezzo. Momento tipicamente piu stabile."
        alert_rec  = ""
    else:
        alert_c = "#64748B"; alert_icon = "⚪"
        alert_lbl = "Data trimestrale non disponibile"
        alert_desc = "Yahoo Finance non ha la data della prossima trimestrale per questo titolo."
        alert_rec  = ""

    if compact:
        return (f'<span style="background:{alert_c}22;color:{alert_c};border:1px solid {alert_c}44;'
                f'padding:1px 7px;border-radius:20px;font-size:.62rem;font-weight:700;margin-left:.3rem;">'
                f'{alert_icon} {alert_lbl}</span>')

    # Storico trimestrali
    hist_html = ""
    if history:
        beats = sum(1 for h in history if h["beat"])
        hist_rows = ""
        for h in reversed(history):
            bc = "#10B981" if h["beat"] else "#EF4444"
            bl = "BEAT" if h["beat"] else "MISS"
            hist_rows += (f'<div style="display:grid;grid-template-columns:80px 70px 70px 60px 60px;'
                          f'gap:.3rem;font-size:.75rem;padding:.25rem 0;border-bottom:1px solid #1E2D47;">'
                          f'<span style="color:#64748B;">{h["period"]}</span>'
                          f'<span>EPS: <b>{h["actual"]:.2f}</b></span>'
                          f'<span>Att.: {h["estimate"]:.2f}</span>'
                          f'<span style="color:{bc};">{h["surprise"]:+.1f}%</span>'
                          f'<span style="background:{bc}22;color:{bc};border-radius:4px;padding:0 5px;font-size:.68rem;font-weight:700;">{bl}</span>'
                          f'</div>')
        hist_html = (f'<div style="margin-top:.6rem;">'
                     f'<div style="font-size:.65rem;color:#64748B;text-transform:uppercase;margin-bottom:.3rem;">'
                     f'Ultime {len(history)} trimestrali — {beats}/{len(history)} beat aspettative</div>'
                     + hist_rows + '</div>')

    rev_g = ed.get("rev_growth")
    eps_g = ed.get("eps_growth")
    growth_html = ""
    if rev_g is not None or eps_g is not None:
        parts = []
        if rev_g is not None:
            rc = "#10B981" if rev_g > 0 else "#EF4444"
            parts.append(f'<span>Ricavi: <b style="color:{rc};">{rev_g*100:+.1f}% YoY</b></span>')
        if eps_g is not None:
            ec = "#10B981" if eps_g > 0 else "#EF4444"
            parts.append(f'<span>EPS: <b style="color:{ec};">{eps_g*100:+.1f}% YoY</b></span>')
        growth_html = '<div style="display:flex;gap:1rem;font-size:.77rem;margin-top:.4rem;">' + " · ".join(parts) + '</div>'

    return (f'<div style="background:rgba({",".join(str(int(alert_c.lstrip("#")[i:i+2],16)) for i in (0,2,4))},.08);'
            f'border:1px solid {alert_c}44;border-radius:8px;padding:.8rem 1rem;margin:.5rem 0;">'
            f'<div style="font-size:.72rem;font-weight:700;color:{alert_c};margin-bottom:.3rem;">{alert_icon} {alert_lbl}</div>'
            f'<div style="font-size:.8rem;color:#94A3B8;line-height:1.6;">{alert_desc}'
            + (f'<br><b style="color:#E8EDF5;">Suggerimento:</b> {alert_rec}' if alert_rec else "")
            + '</div>' + hist_html + growth_html + '</div>')

# ── EMAIL ─────────────────────────────────────────────────────────────────────
def send_email_alert(settings, subject, html_body):
    try:
        msg=MIMEMultipart("alternative"); msg["Subject"]=subject
        msg["From"]=settings["from_email"]; msg["To"]=settings["to_email"]
        msg.attach(MIMEText(html_body,"html"))
        ctx=ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com",465,context=ctx) as s:
            s.login(settings["from_email"],settings["app_password"])
            s.sendmail(settings["from_email"],settings["to_email"],msg.as_string())
        return True,"Email inviata"
    except Exception as e: return False,str(e)

# ── AI HELPERS ────────────────────────────────────────────────────────────────
def ai_call(prompt, system="Sei un analista finanziario. Rispondi in italiano.", max_tokens=800):
    """Single AI call with key from session_state."""
    key = str(st.session_state.get("_ant_key","") or "").strip()
    if not key: return None, "Chiave API mancante"
    try:
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=max_tokens,
            system=system, messages=[{"role":"user","content":prompt}])
        return msg.content[0].text, None
    except Exception as e: return None, str(e)

def ai_call_json(prompt, max_tokens=600):
    """AI call expecting JSON response."""
    key = str(st.session_state.get("_ant_key","") or "").strip()
    if not key: return None, "Chiave API mancante"
    try:
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=max_tokens,
            system="Rispondi SOLO con JSON valido, nessun testo prima o dopo, nessun backtick.",
            messages=[{"role":"user","content":prompt}])
        txt = msg.content[0].text.strip().replace("```json","").replace("```","").strip()
        return json.loads(txt), None
    except Exception as e: return None, str(e)


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Configurazione")

    # GitHub save status
    if _gh_token():
        st.markdown('<div style="background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.3);border-radius:8px;padding:.5rem .8rem;font-size:.72rem;color:#10B981;margin-bottom:.4rem;">Salvataggio attivo</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);border-radius:8px;padding:.5rem .8rem;font-size:.72rem;color:#F59E0B;margin-bottom:.4rem;">GITHUB_TOKEN mancante</div>', unsafe_allow_html=True)

    # API keys
    try:
        _sec_ant  = str(st.secrets.get("ANTHROPIC_API_KEY","") or "").strip() if hasattr(st,"secrets") else ""
        _sec_news = str(st.secrets.get("NEWS_API_KEY","") or "").strip()      if hasattr(st,"secrets") else ""
    except: _sec_ant=""; _sec_news=""

    if _sec_ant:
        st.session_state["_ant_key"]  = _sec_ant
        st.session_state["_news_key"] = _sec_news
        preview = _sec_ant[:8]+"..."+_sec_ant[-4:] if len(_sec_ant)>12 else "***"
        st.markdown(f'<div style="background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.3);border-radius:8px;padding:.5rem .8rem;font-size:.72rem;color:#10B981;">Anthropic: <code>{preview}</code></div>', unsafe_allow_html=True)
        st.text_input("Anthropic API Key", value="configurata", disabled=True, key="ant_key_sb")
        st.text_input("NewsAPI Key", value="configurata" if _sec_news else "non impostata", disabled=True, key="news_key_sb")
    else:
        _inp = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...", key="ant_key_sb")
        _inp2 = st.text_input("NewsAPI Key", type="password", placeholder="newsapi key", key="news_key_sb")
        if _inp:  st.session_state["_ant_key"]  = _inp.strip()
        if _inp2: st.session_state["_news_key"] = _inp2.strip()

    anthropic_key = str(st.session_state.get("_ant_key","") or "").strip()
    news_api_key  = str(st.session_state.get("_news_key","") or "").strip()

    if st.session_state.get("_save_err"):
        st.error(st.session_state["_save_err"])
        if st.button("OK", key="clr_err"): del st.session_state["_save_err"]

    st.markdown("---")
    st.caption("Investment Intelligence v2.0")


# ── LOAD DATA ─────────────────────────────────────────────────────────────────
mkt    = get_market_data()
df_main= build_portfolio_df()
fx     = get_fx_rates()
total_pf = df_main["CV €"].sum() if not df_main.empty else 0
pnl_tot  = df_main["P&L €"].sum() if not df_main.empty else 0
health_score, health_components = compute_health_score(df_main, mkt)
news_items = get_news(news_api_key) if news_api_key else []

# ── HEADER ────────────────────────────────────────────────────────────────────
vix_v  = mkt.get("VIX",{}).get("value",0)
sp_v   = mkt.get("S&P 500",{}).get("delta",0)
eur_v  = mkt.get("EUR/USD",{}).get("value",1.08)
pnl_c  = "#10B981" if pnl_tot>=0 else "#EF4444"
hs_c   = "#10B981" if health_score>=70 else ("#F59E0B" if health_score>=40 else "#EF4444")
vix_c  = "#10B981" if vix_v<15 else ("#EF4444" if vix_v>25 else "#F59E0B")

st.markdown(f'''
<div style="background:#0F1829;border:1px solid #243352;border-radius:14px;padding:1rem 1.4rem;margin-bottom:1rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.8rem;">
  <div style="display:flex;align-items:center;gap:.8rem;">
    <span style="font-size:1.4rem;">📈</span>
    <div>
      <div style="font-weight:700;font-size:1rem;color:#E8EDF5;">Investment Intelligence</div>
      <div style="font-size:.7rem;color:#64748B;">{datetime.now().strftime("%A %d %B %Y — %H:%M")}</div>
    </div>
  </div>
  <div style="display:flex;gap:1.5rem;align-items:center;flex-wrap:wrap;">
    <div style="text-align:center;">
      <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;">Portafoglio</div>
      <div style="font-family:\'JetBrains Mono\',monospace;font-weight:700;font-size:1.1rem;">€{total_pf:,.0f}</div>
      <div style="font-family:\'JetBrains Mono\',monospace;font-size:.78rem;color:{pnl_c};">{pnl_tot:+,.0f} €</div>
    </div>
    <div style="width:1px;height:35px;background:#243352;"></div>
    <div style="text-align:center;">
      <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;">Salute</div>
      <div style="font-family:\'JetBrains Mono\',monospace;font-weight:700;font-size:1.1rem;color:{hs_c};">{health_score}/100</div>
    </div>
    <div style="width:1px;height:35px;background:#243352;"></div>
    <div style="text-align:center;">
      <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;">VIX</div>
      <div style="font-family:\'JetBrains Mono\',monospace;font-weight:700;font-size:1.1rem;color:{vix_c};">{vix_v:.1f}</div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;">S&P 500</div>
      <div style="font-family:\'JetBrains Mono\',monospace;font-weight:700;font-size:1.1rem;color:{"#10B981" if sp_v>=0 else "#EF4444"};">{sp_v:+.2f}%</div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;">EUR/USD</div>
      <div style="font-family:\'JetBrains Mono\',monospace;font-weight:700;font-size:1.1rem;">{eur_v:.4f}</div>
    </div>
  </div>
</div>
''', unsafe_allow_html=True)

# ── 5 TABS ────────────────────────────────────────────────────────────────────
tab1,tab2,tab3,tab4,tab5 = st.tabs([
    "🏠 Dashboard",
    "💼 Portafoglio",
    "🔍 Opportunita e Watchlist",
    "🤖 Analisi AI",
    "⚙️ Gestione"
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab1:

    # ── COSA FARE OGGI ────────────────────────────────────────────────────────
    # Counter bar
    _tradeable_cnt = [p for p in st.session_state.data["portfolio"] if p["ticker"] not in ("N/A","") and p["categoria"]!="Liquidita"]
    _wl_total = [w for w in st.session_state.data["watchlist"] if w.get("ticker","N/A")!="N/A"]
    _missing_cnt = sum(1 for p in st.session_state.data["portfolio"] if p["ticker"]=="N/A" and not (p.get("prezzo_manuale") or 0)>0)
    _liq_val = next((p.get("quantita",0) for p in st.session_state.data["portfolio"] if p["categoria"]=="Liquidita"), 0)
    _pnl_c2 = "#10B981" if pnl_tot>=0 else "#EF4444"
    _cnt_items = [
        ("Portafoglio", f"euro{total_pf:,.0f}", "#3B82F6"),
        ("P&L totale", f"{'+' if pnl_tot>=0 else ''}{pnl_tot:,.0f}", _pnl_c2),
        ("Liquidita", f"euro{_liq_val:,.0f}", "#94A3B8"),
        ("Titoli", str(len(_tradeable_cnt)), "#10B981"),
        ("Watchlist", str(len(_wl_total)), "#8B5CF6"),
        ("Score salute", f"{health_score}/100", hs_c),
        ("VIX oggi", f"{vix_v:.1f}", vix_c),
        ("Prezzi mancanti", str(_missing_cnt), "#EF4444" if _missing_cnt>0 else "#10B981"),
    ]
    _db_cols = st.columns(len(_cnt_items))
    for _col, (_lbl, _val, _clr) in zip(_db_cols, _cnt_items):
        _val2 = _val.replace("euro", "€")
        _html = ('<div style="background:#0F1829;border:1px solid #243352;border-radius:10px;padding:.65rem .5rem;text-align:center;">'
                 f'<div style="font-size:.58rem;color:#64748B;text-transform:uppercase;letter-spacing:.07em;margin-bottom:.25rem;">{_lbl}</div>'
                 f'<div style="font-family:JetBrains Mono,monospace;font-weight:700;font-size:.95rem;color:{_clr};">{_val2}</div>'
                 '</div>')
        _col.markdown(_html, unsafe_allow_html=True)
    st.markdown("")
    st.markdown('<div class="section-hd">Cosa fare oggi</div>', unsafe_allow_html=True)
    st.caption("Azioni prioritarie basate sull'analisi tecnica del tuo portafoglio e della watchlist.")

    actions = []
    # Analizza titoli portafoglio per azioni urgenti
    tradeable_pf = [p for p in st.session_state.data["portfolio"] if p["ticker"] not in ("N/A","") and p["categoria"]!="Liquidita"]
    for item in tradeable_pf[:12]:
        td = get_technical(item["ticker"])
        if not td: continue
        em,lbl,_ = tech_signal(td)
        rsi=td["rsi"]; p=td["price"]; sup=td["support"]; res=td["resistance"]
        if lbl=="ALLEGGERISCI":
            actions.append(("🔴","Valuta di alleggerire",item["nome"],
                f"Segnali tecnici deteriorati. RSI {rsi:.0f}, sotto le medie. "
                f"Se sei in guadagno potrebbe essere il momento di prendere profitto.","alta"))
        elif lbl=="INCREMENTA" and rsi<45:
            actions.append(("🟢","Opportunita di incremento",item["nome"],
                f"Segnali positivi con RSI ancora basso ({rsi:.0f}) — non ancora surriscaldato. "
                f"Ingresso tecnico ideale vicino a {sup:.2f}.","media"))
        elif abs(p-sup)/p<0.02:
            actions.append(("🟡","Su supporto chiave",item["nome"],
                f"Il prezzo e' vicino al supporto storico ({sup:.2f}). "
                f"Se regge e' un segnale positivo, se lo rompe rivaluta la posizione.","media"))
        elif abs(p-res)/p<0.02:
            actions.append(("🟡","Su resistenza",item["nome"],
                f"Il prezzo ha raggiunto la resistenza storica ({res:.2f}). "
                f"Zona dove spesso arrivano venditori — attenzione se vuoi incrementare.","bassa"))

    # Watchlist con segnali positivi
    for wl in st.session_state.data["watchlist"][:15]:
        if wl.get("ticker","N/A")=="N/A": continue
        td = get_technical(wl["ticker"])
        if not td: continue
        em,lbl,_ = tech_signal(td)
        if lbl=="INCREMENTA":
            actions.append(("🟢","Watchlist: momento favorevole",wl["nome"],
                f"Titolo che stai seguendo con segnali positivi. "
                f"RSI {td['rsi']:.0f}, trend in crescita. Potrebbe essere un buon ingresso.","media"))

    # Prezzi mancanti
    missing = [p for p in st.session_state.data["portfolio"] if p["ticker"]=="N/A" and not (p.get("prezzo_manuale") or 0)>0]
    if missing:
        actions.append(("⚪","Prezzi da aggiornare",f"{len(missing)} asset",
            f"Obbligazioni e certificati senza prezzo manuale riducono l'accuratezza del portafoglio. "
            f"Vai in Gestione per aggiornarli.","bassa"))

    if not actions:
        st.markdown('<div class="card" style="text-align:center;padding:1.5rem;"><div style="font-size:1.5rem;margin-bottom:.5rem;">✅</div><div style="color:#10B981;font-weight:600;">Nessuna azione urgente</div><div style="color:#64748B;font-size:.82rem;margin-top:.3rem;">Il portafoglio e\' in equilibrio. Continua a monitorare.</div></div>', unsafe_allow_html=True)
    else:
        priority_order = {"alta":0,"media":1,"bassa":2}
        actions.sort(key=lambda x: priority_order.get(x[4],2))
        for icon,tipo,nome,desc,priority in actions[:6]:
            prio_color = "#EF4444" if priority=="alta" else ("#F59E0B" if priority=="media" else "#64748B")
            st.markdown(f'''
<div class="action-box" style="background:#0F1829;border:1px solid {prio_color}33;border-left:4px solid {prio_color};">
  <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.3rem;">
    <span style="font-size:1rem;">{icon}</span>
    <span style="font-weight:600;color:#E8EDF5;">{tipo}:</span>
    <span style="color:#60A5FA;font-weight:600;">{nome}</span>
    <span style="margin-left:auto;background:{prio_color}22;color:{prio_color};border:1px solid {prio_color}44;padding:1px 7px;border-radius:20px;font-size:.62rem;font-weight:700;">{priority.upper()}</span>
  </div>
  <div style="color:#94A3B8;font-size:.82rem;">{desc}</div>
</div>''', unsafe_allow_html=True)

    # ── SALUTE PORTAFOGLIO ────────────────────────────────────────────────────
    st.markdown('<div class="section-hd">Salute del portafoglio</div>', unsafe_allow_html=True)
    hc1,hc2 = st.columns([1,2])
    with hc1:
        hs_label = "Eccellente" if health_score>=80 else ("Buona" if health_score>=60 else ("Discreta" if health_score>=40 else "Attenzione"))
        st.markdown(f'''
<div class="card" style="text-align:center;padding:1.5rem;">
  <div style="font-size:.65rem;color:#64748B;text-transform:uppercase;letter-spacing:.1em;margin-bottom:.5rem;">Score di salute</div>
  <div style="font-family:\'JetBrains Mono\',monospace;font-size:3.5rem;font-weight:700;color:{hs_c};line-height:1;">{health_score}</div>
  <div style="font-size:.85rem;color:{hs_c};margin-top:.3rem;">{hs_label}</div>
  <div style="background:#1E2D47;border-radius:8px;height:8px;margin-top:.8rem;">
    <div style="width:{health_score}%;height:8px;background:{hs_c};border-radius:8px;transition:width .5s;"></div>
  </div>
</div>''', unsafe_allow_html=True)
    with hc2:
        for comp_name, comp_data in health_components.items():
            pts = comp_data["pts"]; val = comp_data["val"]
            bar_c = "#10B981" if pts>0 else ("#EF4444" if pts<0 else "#64748B")
            bar_w = min(100,abs(int(pts/20*100)))
            st.markdown(f'''
<div style="display:flex;align-items:center;gap:.8rem;padding:.35rem 0;border-bottom:1px solid #1E2D47;font-size:.8rem;">
  <div style="min-width:130px;color:#94A3B8;">{comp_name}</div>
  <div style="flex:1;background:#1E2D47;border-radius:4px;height:6px;">
    <div style="width:{bar_w}%;height:6px;background:{bar_c};border-radius:4px;"></div>
  </div>
  <div style="min-width:80px;text-align:right;color:#64748B;font-size:.75rem;">{val}</div>
  <div style="min-width:50px;text-align:right;font-family:\'JetBrains Mono\',monospace;color:{bar_c};font-size:.78rem;">{pts:+.0f}</div>
</div>''', unsafe_allow_html=True)

    # ── MERCATI ───────────────────────────────────────────────────────────────
    st.markdown('<div class="section-hd">Mercati oggi</div>', unsafe_allow_html=True)
    market_items = [
        ("VIX","VIX — paura del mercato",
         "Sotto 15 = calmo, 15-25 = normale, sopra 25 = nervoso"),
        ("S&P 500","S&P 500","Indice delle 500 maggiori aziende USA"),
        ("FTSE MIB","FTSE MIB","Borsa italiana"),
        ("Nasdaq","Nasdaq","Tecnologia USA"),
        ("EUR/USD","Euro/Dollaro","Cambia il valore delle tue posizioni in USD"),
        ("Oro","Oro","Bene rifugio — sale in periodi di incertezza"),
    ]
    mc = st.columns(6)
    for col,(key,label,desc) in zip(mc,market_items):
        d = mkt.get(key,{})
        v = d.get("value",0); delta = d.get("delta",0)
        c = "#10B981" if delta>=0 else "#EF4444"
        with col:
            st.markdown(f'''
<div class="card" style="text-align:center;padding:.7rem .5rem;">
  <div style="font-size:.6rem;color:#64748B;text-transform:uppercase;margin-bottom:.3rem;">{label}</div>
  <div style="font-family:\'JetBrains Mono\',monospace;font-weight:700;font-size:.95rem;">{v:.2f}</div>
  <div style="font-family:\'JetBrains Mono\',monospace;font-size:.72rem;color:{c};">{delta:+.2f}%</div>
  <div style="font-size:.6rem;color:#64748B;margin-top:.3rem;line-height:1.3;">{desc}</div>
</div>''', unsafe_allow_html=True)

    # ── NOTIZIE ───────────────────────────────────────────────────────────────
    if news_items:
        st.markdown('<div class="section-hd">Notizie rilevanti</div>', unsafe_allow_html=True)
        for n in news_items[:5]:
            st.markdown(f'<div style="background:#0F1829;border:1px solid #243352;border-radius:8px;padding:.6rem .9rem;margin-bottom:.35rem;font-size:.82rem;"><a href="{n["url"]}" target="_blank" style="color:#60A5FA;text-decoration:none;">{n["title"]}</a><span style="color:#64748B;font-size:.72rem;margin-left:.5rem;">— {n["source"]}</span></div>', unsafe_allow_html=True)
    elif not news_api_key:
        st.info("Aggiungi la chiave NewsAPI nella sidebar per vedere le notizie di mercato.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PORTAFOGLIO
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    pt1,pt2,pt3 = st.tabs(["Panoramica","Analisi tecnica","Benchmark"])

    # ── PANORAMICA ────────────────────────────────────────────────────────────
    with pt1:
        if df_main.empty:
            st.info("Nessun dato di portafoglio disponibile.")
        else:
            # KPI row
            k1,k2,k3,k4 = st.columns(4)
            liq_row = df_main[df_main["Categoria"].str.lower().str.contains("liquid",na=False)]
            liq_eur = float(liq_row["CV €"].sum()) if not liq_row.empty else 0
            inv_eur = total_pf - liq_eur
            with k1: st.metric("Totale portafoglio", f"€{total_pf:,.0f}")
            with k2: st.metric("Investito", f"€{inv_eur:,.0f}", delta=f"{pnl_tot:+,.0f} P&L")
            with k3: st.metric("Liquidita", f"€{liq_eur:,.0f}")
            with k4:
                best = df_main.nlargest(1,"P&L %")
                worst = df_main.nsmallest(1,"P&L %")
                if not best.empty:
                    st.metric("Miglior titolo", best.iloc[0]["Nome"][:16], delta=f"{best.iloc[0]['P&L %']:+.1f}%")

            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.markdown('<div class="section-hd">Allocazione per categoria</div>', unsafe_allow_html=True)
                alloc = df_main[df_main["CV €"]>0].groupby("Categoria")["CV €"].sum()
                fig_alloc = go.Figure(go.Pie(
                    labels=alloc.index, values=alloc.values,
                    marker_colors=[CAT_COLORS.get(c,"#64748B") for c in alloc.index],
                    hole=0.55, textinfo="label+percent", textfont_size=11))
                fig_alloc.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#E8EDF5",showlegend=False,height=300,margin=dict(t=5,b=5,l=5,r=5))
                st.plotly_chart(fig_alloc,use_container_width=True)

            with col_chart2:
                st.markdown('<div class="section-hd">P&L per titolo</div>', unsafe_allow_html=True)
                df_pnl = df_main[df_main["Categoria"].str.lower().str.contains("liquid",na=False)==False].copy()
                df_pnl = df_pnl.nlargest(15,"CV €")
                colors = ["#10B981" if x>=0 else "#EF4444" for x in df_pnl["P&L €"]]
                fig_pnl = go.Figure(go.Bar(
                    x=df_pnl["Nome"].str[:16], y=df_pnl["P&L €"],
                    marker_color=colors, text=[f"{v:+,.0f}" for v in df_pnl["P&L €"]],
                    textposition="outside", textfont_size=9))
                fig_pnl.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(22,32,53,.8)",
                    font_color="#E8EDF5",xaxis=dict(gridcolor="#1E2D47"),yaxis=dict(gridcolor="#1E2D47"),
                    height=300,margin=dict(t=5,b=5,l=5,r=5),showlegend=False)
                st.plotly_chart(fig_pnl,use_container_width=True)

            # Esposizione valutaria
            st.markdown('<div class="section-hd">Esposizione valutaria</div>', unsafe_allow_html=True)
            if total_pf>0:
                val_exp = (df_main.groupby("Valuta")["CV €"].sum()/total_pf*100).sort_values(ascending=False)
                vc1,vc2,vc3,vc4 = st.columns(4)
                val_colors={"EUR":"#10B981","USD":"#3B82F6","GBP":"#F59E0B","DKK":"#8B5CF6"}
                for col,(val_k,pct) in zip([vc1,vc2,vc3,vc4],val_exp.items()):
                    vc=val_colors.get(val_k,"#64748B")
                    with col:
                        st.markdown(f'<div class="card" style="text-align:center;padding:.7rem;"><div style="font-size:.65rem;color:#64748B;text-transform:uppercase;">{val_k}</div><div style="font-family:\'JetBrains Mono\',monospace;font-size:1.4rem;font-weight:700;color:{vc};">{pct:.1f}%</div></div>', unsafe_allow_html=True)

            # Tabella posizioni
            st.markdown('<div class="section-hd">Tutte le posizioni</div>', unsafe_allow_html=True)
            df_show = df_main.rename(columns={"Nome":"Titolo","P&L %":"P&L %","CV €":"Valore €","P&L €":"Guadagno/Perdita €"})
            df_show = df_show[["Titolo","Categoria","Valore €","P.Attuale","P.Carico","Guadagno/Perdita €","P&L %","Fonte"]]
            st.dataframe(df_show,use_container_width=True,hide_index=True)

    # ── ANALISI TECNICA ───────────────────────────────────────────────────────
    with pt2:
        st.caption("Ogni titolo mostra il segnale tecnico con una spiegazione in linguaggio semplice.")

        tradeable_items = [p for p in st.session_state.data["portfolio"]
                           if p["ticker"] not in ("N/A","") and p["categoria"]!="Liquidita"]

        tech_rows=[]
        with st.spinner("Calcolo segnali..."):
            for item in tradeable_items:
                td=get_technical(item["ticker"])
                em,lbl,reason=tech_signal(td)
                tech_rows.append({"Segnale":em,"Titolo":item["nome"][:20],"Ticker":item["ticker"],
                    "Raccomandazione":lbl,
                    "RSI":f"{td['rsi']:.0f}" if td else "--",
                    "MACD":"pos" if (td and td["macd_h"]>0) else "neg",
                    "Motivo":reason})

        if tech_rows:
            df_tech=pd.DataFrame(tech_rows)
            n_incr=(df_tech["Raccomandazione"]=="INCREMENTA").sum()
            n_alle=(df_tech["Raccomandazione"]=="ALLEGGERISCI").sum()
            n_mid =len(df_tech)-n_incr-n_alle
            _tc = st.columns(4)
            for _tcol, (_tl, _tv, _tclr) in zip(_tc, [
                ("Da incrementare", str(n_incr), "#10B981"),
                ("Neutrali", str(n_mid), "#F59E0B"),
                ("Da alleggerire", str(n_alle), "#EF4444"),
                ("Totale", str(len(df_tech)), "#3B82F6"),
            ]):
                _tcol.markdown(
                    '<div style="background:#0F1829;border:1px solid #243352;border-radius:10px;padding:.7rem;text-align:center;">' +
                    f'<div style="font-size:.6rem;color:#64748B;text-transform:uppercase;margin-bottom:.25rem;">{_tl}</div>' +
                    f'<div style="font-family:JetBrains Mono,monospace;font-size:1.8rem;font-weight:700;color:{_tclr};">{_tv}</div>' +
                    '</div>', unsafe_allow_html=True)
            st.markdown("")
            st.dataframe(df_tech,use_container_width=True,hide_index=True,height=300)

        st.markdown('<div class="section-hd">Dettaglio per titolo</div>', unsafe_allow_html=True)
        for i,item in enumerate(tradeable_items):
            td=get_technical(item["ticker"])
            em,lbl,_=tech_signal(td)
            lbl_c={"INCREMENTA":"#10B981","TIENI":"#F59E0B","ATTENZIONE":"#F59E0B","ALLEGGERISCI":"#EF4444"}.get(lbl,"#64748B")

            # Posizione reale
            match = df_main[df_main["Ticker"]==item["ticker"]]
            cv_this = float(match.iloc[0]["CV €"]) if not match.empty else None
            pnl_this = float(match.iloc[0]["P&L %"]) if not match.empty else None
            peso = (cv_this/total_pf*100) if cv_this and total_pf>0 else None

            with st.expander(f"{em} {item['nome']} ({item['ticker']}) — {lbl}"):
                ec1,ec2 = st.columns([1,1])
                with ec1:
                    # Spiegazione in linguaggio semplice
                    if td:
                        desc, quindi = signal_to_plain(lbl, td, item["nome"])
                        pos_html = ""
                        if cv_this:
                            pnl_c2 = "#10B981" if (pnl_this or 0)>=0 else "#EF4444"
                            pos_html = f'<div style="background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.3);border-radius:8px;padding:.6rem .8rem;margin-bottom:.5rem;font-size:.8rem;"><b style="color:#60A5FA;">La tua posizione:</b> hai investito <b>€{cv_this:,.0f}</b> ({peso:.1f}% del portafoglio) con una performance di <b style="color:{pnl_c2};">{pnl_this:+.1f}%</b>.</div>'
                        st.markdown(pos_html, unsafe_allow_html=True)
                        st.markdown(f'<div style="background:#0F1829;border:1px solid #243352;border-radius:8px;padding:.8rem;font-size:.83rem;color:#94A3B8;line-height:1.7;">{desc}<div class="quindi"><b>Quindi:</b> {quindi}</div></div>', unsafe_allow_html=True)

                        # Avviso concentrazione
                        if peso and peso>15 and lbl=="INCREMENTA":
                            st.warning(f"Attenzione: {item['nome']} pesa gia' il {peso:.1f}% del portafoglio. Incrementare ulteriormente aumenta la concentrazione del rischio.")
                    else:
                        st.info("Dati tecnici non disponibili per questo ticker.")

                with ec2:
                    if td:
                        # Grafico candele + indicatori
                        try:
                            h=yf.Ticker(item["ticker"]).history(period="3mo")
                            fig=go.Figure()
                            fig.add_trace(go.Candlestick(x=h.index,open=h["Open"],high=h["High"],
                                low=h["Low"],close=h["Close"],name="Prezzo",
                                increasing_line_color="#10B981",decreasing_line_color="#EF4444",
                                increasing_fillcolor="#10B981",decreasing_fillcolor="#EF4444"))
                            c=h["Close"]
                            if len(c)>=50:
                                fig.add_trace(go.Scatter(x=h.index,y=c.rolling(50).mean(),
                                    name="MA50",line=dict(color="#F59E0B",width=1.5,dash="dot")))
                            if len(c)>=200:
                                fig.add_trace(go.Scatter(x=h.index,y=c.rolling(200).mean(),
                                    name="MA200",line=dict(color="#8B5CF6",width=1.5,dash="dash")))
                            fig.add_hline(y=td["support"],line_color="#10B981",line_dash="dot",line_width=1,
                                annotation_text=f"Sup {td['support']:.2f}",annotation_font_color="#10B981",annotation_font_size=9)
                            fig.add_hline(y=td["resistance"],line_color="#EF4444",line_dash="dot",line_width=1,
                                annotation_text=f"Res {td['resistance']:.2f}",annotation_font_color="#EF4444",annotation_font_size=9)
                            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(22,32,53,.8)",
                                font_color="#E8EDF5",xaxis_rangeslider_visible=False,
                                xaxis=dict(gridcolor="#1E2D47"),yaxis=dict(gridcolor="#1E2D47"),
                                legend=dict(bgcolor="rgba(0,0,0,0)",font_size=9),
                                height=280,margin=dict(t=5,b=5,l=5,r=60))
                            st.plotly_chart(fig,use_container_width=True)
                        except: st.caption("Grafico non disponibile")

                        # Dati tecnici numerici in expander
                        with st.expander("Dati tecnici dettagliati"):
                            d1,d2,d3,d4 = st.columns(4)
                            d1.metric("Prezzo",f"{td['price']:.2f}")
                            d2.metric("RSI",f"{td['rsi']:.0f}")
                            d3.metric("Supporto",f"{td['support']:.2f}")
                            d4.metric("Resistenza",f"{td['resistance']:.2f}")

                        # Bottone AI opzionale per notizie
                        ai_cache_key = f"ai_tech_{item['ticker'].replace('=','X')}"
                        if st.session_state.get(ai_cache_key):
                            st.markdown(f'<div style="background:rgba(139,92,246,.08);border:1px solid rgba(139,92,246,.3);border-radius:8px;padding:.7rem;font-size:.8rem;line-height:1.7;margin-top:.4rem;"><b style="color:#8B5CF6;">Notizie e contesto AI:</b><br>{st.session_state[ai_cache_key]}</div>', unsafe_allow_html=True)
                        elif anthropic_key:
                            if st.button(f"Aggiungi notizie AI (~0.01 EUR)", key=f"aibtn_{i}"):
                                with st.spinner("AI..."):
                                    rsp,err = ai_call(
                                        f"Dai 3 notizie/eventi recenti rilevanti per {item['nome']} ({item['ticker']}) e come impattano sull'investimento. RSI {td['rsi']:.0f}, prezzo {td['price']:.2f}. Sii breve e pratico.",
                                        max_tokens=400)
                                    if rsp: st.session_state[ai_cache_key]=rsp; st.rerun()
                                    else: st.error(f"Errore: {err}")

    # ── BENCHMARK ─────────────────────────────────────────────────────────────
    with pt3:
        st.markdown('<div class="section-hd">Come sta andando il tuo portafoglio rispetto al mercato</div>', unsafe_allow_html=True)
        st.caption("Confronto degli ultimi 6 mesi con i principali indici globali.")

        period_bm = st.select_slider("Periodo:", ["3mo","6mo","1y"], value="6mo", key="bm_period")
        with st.spinner("Caricamento benchmark..."):
            try:
                bm_data={}
                for name,t in {"MSCI World":"SWDA.MI","S&P 500":"^GSPC","Obblig. Globali":"XGSH.MI"}.items():
                    h=yf.Ticker(t).history(period=period_bm)
                    if not h.empty: bm_data[name]=(h["Close"]/h["Close"].iloc[0]-1)*100

                # Portafoglio performance (approssimata dai titoli liquid)
                pf_hist={}
                for item in tradeable_items[:8]:
                    h=yf.Ticker(item["ticker"]).history(period=period_bm)
                    if not h.empty:
                        pf_hist[item["ticker"]]=(h["Close"]/h["Close"].iloc[0]-1)*100

                fig_bm=go.Figure()
                if pf_hist:
                    pf_avg=pd.DataFrame(pf_hist).mean(axis=1)
                    fig_bm.add_trace(go.Scatter(x=pf_avg.index,y=pf_avg.values,
                        name="Il tuo portafoglio (media)",line=dict(color="#3B82F6",width=2.5)))
                for name,series in bm_data.items():
                    c={"MSCI World":"#10B981","S&P 500":"#F59E0B","Obblig. Globali":"#8B5CF6"}.get(name,"#64748B")
                    fig_bm.add_trace(go.Scatter(x=series.index,y=series.values,
                        name=name,line=dict(color=c,width=1.5,dash="dot")))

                fig_bm.add_hline(y=0,line_color="#64748B",line_dash="dot",line_width=1)
                fig_bm.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(22,32,53,.8)",
                    font_color="#E8EDF5",xaxis=dict(gridcolor="#1E2D47"),yaxis=dict(gridcolor="#1E2D47",ticksuffix="%"),
                    legend=dict(bgcolor="rgba(0,0,0,0)"),height=350,margin=dict(t=5,b=5,l=5,r=5))
                st.plotly_chart(fig_bm,use_container_width=True)
                st.caption("Nota: il tuo portafoglio e' approssimato dalla media dei titoli azionari/ETF quotati. Obbligazioni e certificati non sono inclusi nel grafico.")
            except Exception as e:
                st.info(f"Grafico benchmark non disponibile: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — OPPORTUNITA E WATCHLIST
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    wt1,wt2,wt3 = st.tabs(["Watchlist personale","Scanner opportunita","Timing di ingresso"])

    # ── WATCHLIST ─────────────────────────────────────────────────────────────
    with wt1:
        watchlist = st.session_state.data["watchlist"]
        portfolio_tickers_set = {p["ticker"].upper() for p in st.session_state.data["portfolio"]}

        # Allocazione settoriale portafoglio (per contesto)
        alloc_cat = df_main.groupby("Categoria")["CV €"].sum().to_dict() if not df_main.empty else {}

        col_add, col_batch = st.columns([3,2])
        with col_add:
            with st.expander("Aggiungi titolo alla watchlist"):
                wa1,wa2 = st.columns(2)
                with wa1:
                    new_wl_name = st.text_input("Nome",key="wl_add_name")
                    new_wl_ticker = st.text_input("Ticker Yahoo Finance",key="wl_add_ticker")
                with wa2:
                    new_wl_cat = st.selectbox("Categoria",["Azioni","ETF","Materie Prime","Crypto"],key="wl_add_cat")
                    if st.button("Aggiungi",key="wl_add_btn"):
                        if new_wl_name and new_wl_ticker:
                            st.session_state.data["watchlist"].append({
                                "ticker":new_wl_ticker.upper(),"nome":new_wl_name,
                                "categoria":new_wl_cat,"sorgente":"utente",
                                "segnale":"MONITORA","prezzo_target":None,"stop_loss":None,
                                "ingresso":None,"strategia":None,"orizzonte":None,
                                "note":"","ai_pending":False})
                            save_data(st.session_state.data); st.rerun()

        with col_batch:
            has_key = bool(anthropic_key)
            btn_lbl = "Analizza tutti con AI" if has_key else "Calcola segnali (gratis)"
            if st.button(btn_lbl, key="wl_batch_btn", use_container_width=True):
                prog = st.progress(0)
                items_to_analyze = [w for w in st.session_state.data["watchlist"]
                                    if w.get("ticker","N/A") not in ("N/A","",None)]
                for qi,item_a in enumerate(items_to_analyze):
                    prog.progress(int((qi+1)/max(len(items_to_analyze),1)*100))
                    tk_a = item_a["ticker"]
                    td_a = get_technical(tk_a)
                    if not td_a: continue
                    p_a=td_a["price"]; rsi_a=td_a["rsi"]; macd_a=td_a["macd_h"]
                    sup_a=td_a["support"]; res_a=td_a["resistance"]
                    ma50_a=td_a["ma50"]; ma200_a=td_a["ma200"]
                    _,sig_lbl_a,_=tech_signal(td_a)
                    seg_a="COMPRA" if sig_lbl_a=="INCREMENTA" else ("NON_CONSIDERARE" if sig_lbl_a=="ALLEGGERISCI" else "MONITORA")
                    ingresso_a=round(min(sup_a*1.01,p_a*0.99),2)
                    target_a=round(res_a*0.99,2); stop_a=round(sup_a*0.96,2)

                    if has_key:
                        # Analisi AI contestuale
                        pf_alloc_str = ", ".join([f"{k}:{v:.0f}EUR" for k,v in alloc_cat.items()])
                        pf_settori = ", ".join([p["nome"] for p in st.session_state.data["portfolio"]
                                                if p["categoria"]=="Azioni"][:8])
                        ai_d,err = ai_call_json(
                            f'Analizza {item_a["nome"]} ({tk_a}) per un investitore con questo portafoglio:\n'
                            f'Allocazione: {pf_alloc_str}\n'
                            f'Titoli azionari gia in portafoglio: {pf_settori}\n'
                            f'Dati tecnici: RSI {rsi_a:.0f}, prezzo {p_a:.2f}, '
                            f'MA50 {"sopra" if ma50_a and p_a>ma50_a else "sotto"}, '
                            f'MA200 {"sopra" if ma200_a and p_a>ma200_a else "sotto"}, '
                            f'MACD {"positivo" if macd_a>0 else "negativo"}.\n\n'
                            f'Tieni conto di:\n'
                            f'1) Il contesto geopolitico e macroeconomico attuale\n'
                            f'2) Se il portafoglio e gia sovraesposto al settore di questo titolo\n'
                            f'3) Se il segnale tecnico e coerente con la situazione fondamentale\n\n'
                            f'Rispondi con JSON:\n'
                            f'{{"segnale":"COMPRA","ingresso":{ingresso_a},"prezzo_target":{target_a},'
                            f'"stop_loss":{stop_a},"orizzonte":"da determinare in base al titolo",'
                            f'"note":"3 frasi: 1) cosa sta succedendo al titolo/settore. '
                            f'2) perche questo segnale considerando portafoglio e macro. '
                            f'3) rischi principali da monitorare."}}',
                            max_tokens=500)
                        if ai_d:
                            idx_wa=next((k for k,x in enumerate(st.session_state.data["watchlist"]) if x.get("ticker")==tk_a),None)
                            if idx_wa is not None:
                                st.session_state.data["watchlist"][idx_wa].update({**ai_d,"ai_pending":False})
                            continue
                    # Fallback tecnica
                    rsi_note="ipercomprato" if rsi_a>70 else ("ipervenduto" if rsi_a<30 else "neutro")
                    note_a=f"RSI {rsi_a:.0f} ({rsi_note}), trend {'positivo' if (ma50_a and p_a>ma50_a) else 'negativo'}. Supporto a {sup_a:.2f}."
                    idx_wa=next((k for k,x in enumerate(st.session_state.data["watchlist"]) if x.get("ticker")==tk_a),None)
                    if idx_wa is not None:
                        st.session_state.data["watchlist"][idx_wa].update({
                            "segnale":seg_a,"ingresso":ingresso_a,"prezzo_target":target_a,
                            "stop_loss":stop_a,"note":note_a,"ai_pending":False})
                prog.empty()
                save_data(st.session_state.data)
                st.success("Analisi completata!"); st.rerun()

        # Counter bar watchlist
        _wl_c = sum(1 for w in watchlist if w.get("segnale")=="COMPRA")
        _wl_m = sum(1 for w in watchlist if w.get("segnale")=="MONITORA")
        _wl_n = sum(1 for w in watchlist if w.get("segnale")=="NON_CONSIDERARE")
        _wl_ai2 = sum(1 for w in watchlist if w.get("sorgente")=="ai")
        _wl_pf2 = sum(1 for w in watchlist if w.get("ticker","N/A")!="N/A" and w["ticker"].upper() in portfolio_tickers_set)
        _wc = st.columns(5)
        for _wcol,(_wl,_wv,_wclr) in zip(_wc,[
            ("Compra", str(_wl_c), "#10B981"),
            ("Monitora", str(_wl_m), "#F59E0B"),
            ("Non considerare", str(_wl_n), "#EF4444"),
            ("Idee AI", str(_wl_ai2), "#8B5CF6"),
            ("Gia in portafoglio", str(_wl_pf2), "#3B82F6"),
        ]):
            _wcol.markdown(
                '<div style="background:#0F1829;border:1px solid #243352;border-radius:10px;padding:.65rem .5rem;text-align:center;">' +
                f'<div style="font-size:.58rem;color:#64748B;text-transform:uppercase;margin-bottom:.2rem;">{_wl}</div>' +
                f'<div style="font-family:JetBrains Mono,monospace;font-size:1.6rem;font-weight:700;color:{_wclr};">{_wv}</div>' +
                '</div>', unsafe_allow_html=True)
        st.markdown("")
        # Filtri
        wf1,wf2 = st.columns(2)
        with wf1: filt_seg=st.radio("Segnale:",["Tutti","COMPRA","MONITORA","NON_CONSIDERARE"],horizontal=True,key="wl_filt_seg")
        with wf2: filt_src=st.radio("Fonte:",["Tutti","Miei","AI"],horizontal=True,key="wl_filt_src")

        filtered_wl = [w for w in watchlist
                       if (filt_seg=="Tutti" or w.get("segnale","")==filt_seg)
                       and (filt_src=="Tutti"
                            or (filt_src=="Miei" and w.get("sorgente","utente")=="utente")
                            or (filt_src=="AI" and w.get("sorgente","")=="ai"))]

        if not filtered_wl:
            st.info("Nessun titolo corrisponde ai filtri selezionati.")
        else:
            for card_i, item in enumerate(filtered_wl):
                tk=item.get("ticker","N/A"); sig=item.get("segnale","MONITORA")
                sig_c={"COMPRA":"#10B981","MONITORA":"#F59E0B","NON_CONSIDERARE":"#EF4444"}.get(sig,"#64748B")
                is_in_pf = tk.upper() in portfolio_tickers_set if tk!="N/A" else False
                price=get_price(tk) if tk!="N/A" else None
                earn_badge = earnings_alert_html(tk, compact=True) if tk not in ("N/A","") else ""
                note=item.get("note",""); ing=item.get("ingresso"); tgt=item.get("prezzo_target"); sl=item.get("stop_loss")

                price_str=f"{price:.2f}" if price else "--"
                ing_str=f"{ing:.2f}" if ing else "--"
                tgt_str=f"{tgt:.2f}" if tgt else "--"
                sl_str=f"{sl:.2f}" if sl else "--"

                pf_badge = '<span style="background:#3B82F622;color:#3B82F6;border:1px solid #3B82F644;padding:1px 6px;border-radius:20px;font-size:.62rem;font-weight:700;">GIA IN PORTAFOGLIO</span> ' if is_in_pf else ""

                with st.expander(f"{item['nome']} ({tk}) — {sig}"):
                    ex1,ex2 = st.columns([3,1])
                    with ex1:
                        note_html = f'<div style="background:#162035;border-radius:6px;padding:.5rem .7rem;font-size:.8rem;color:#94A3B8;line-height:1.6;">{note}</div>' if note else ""
                        pf_warn_html = '<div style="background:rgba(59,130,246,.07);border-radius:6px;padding:.4rem .7rem;font-size:.78rem;color:#94A3B8;margin-top:.4rem;">Questo titolo e gia nel tuo portafoglio. Considera questo prima di aggiungere ancora.</div>' if is_in_pf else ""
                        cat_str = item.get("categoria","")
                        st.markdown(
                            f'<div style="background:#0F1829;border:1px solid {sig_c}33;border-left:4px solid {sig_c};border-radius:8px;padding:.8rem 1rem;margin-bottom:.5rem;">' +
                            f'<div style="display:flex;gap:.5rem;align-items:center;flex-wrap:wrap;margin-bottom:.4rem;">' +
                            f'<span style="background:{sig_c}22;color:{sig_c};border:1px solid {sig_c}44;padding:2px 10px;border-radius:20px;font-size:.72rem;font-weight:700;">{sig}</span>' +
                            pf_badge +
                            f'<span style="color:#64748B;font-size:.75rem;">{cat_str}</span>' +
                        earn_badge +
                            '</div>' +
                            '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:.4rem;font-size:.78rem;margin-bottom:.5rem;">' +
                            f'<div><span style="color:#64748B;">Prezzo</span><br><b>{price_str}</b></div>' +
                            f'<div><span style="color:#64748B;">Ingresso ideale</span><br><b style="color:#60A5FA;">{ing_str}</b></div>' +
                            f'<div><span style="color:#64748B;">Target</span><br><b style="color:#10B981;">{tgt_str}</b></div>' +
                            f'<div><span style="color:#64748B;">Stop loss</span><br><b style="color:#EF4444;">{sl_str}</b></div>' +
                            '</div>' +
                            note_html + pf_warn_html +
                            '</div>',
                            unsafe_allow_html=True)

                    with ex2:
                        # Bottone Rianalizza
                        _key_rai = str(st.session_state.get("_ant_key","") or "").strip()
                        if _key_rai and st.button("Rianalizza con AI", key=f"rai_{card_i}", use_container_width=True):
                            with st.spinner("AI..."):
                                td_r=get_technical(tk)
                                ctx_r=f"RSI {td_r['rsi']:.0f}, prezzo {td_r['price']:.2f}, MA50 {'sopra' if td_r['ma50'] and td_r['price']>td_r['ma50'] else 'sotto'}, MACD {'pos' if td_r['macd_h']>0 else 'neg'}" if td_r else "N/A"
                                pf_str=", ".join([f"{k}:{v:.0f}EUR" for k,v in alloc_cat.items()])
                                azioni_pf=", ".join([p["nome"] for p in st.session_state.data["portfolio"] if p["categoria"]=="Azioni"][:6])
                                ai_d,err=ai_call_json(
                                    f'Analizza {item["nome"]} ({tk}).\n'
                                    f'Portafoglio investitore: {pf_str}\nAzioni gia in portafoglio: {azioni_pf}\n'
                                    f'Tecnica: {ctx_r}\n{"ATTENZIONE: titolo gia in portafoglio." if is_in_pf else ""}\n'
                                    f'Considera contesto macro, geopolitica, settore, composizione portafoglio.\n'
                                    f'JSON: {{"segnale":"COMPRA","ingresso":0.0,"prezzo_target":0.0,"stop_loss":0.0,'
                                    f'"orizzonte":"specifica in base al titolo",'
                                    f'"note":"3 frasi: cosa sta succedendo, perche questo segnale, rischi principali."}}',
                                    max_tokens=500)
                                if ai_d:
                                    idx_r=next((k for k,x in enumerate(st.session_state.data["watchlist"]) if x.get("ticker")==tk),None)
                                    if idx_r is not None:
                                        st.session_state.data["watchlist"][idx_r].update({**ai_d,"ai_pending":False})
                                    save_data(st.session_state.data); st.rerun()
                                else: st.error(f"Errore: {err}")
                        elif not _key_rai:
                            st.caption("Configura Anthropic API per usare la rianalisi AI")

                        if st.button("Rimuovi", key=f"rm_{card_i}", use_container_width=True):
                            idx_rm=next((k for k,x in enumerate(st.session_state.data["watchlist"]) if x.get("ticker")==tk),None)
                            if idx_rm is not None:
                                st.session_state.data["watchlist"].pop(idx_rm)
                                save_data(st.session_state.data); st.rerun()

    # ── SCANNER OPPORTUNITA ───────────────────────────────────────────────────
    with wt2:
        GLOBAL_UNIVERSE = [
            ("AAPL","Apple","Azioni","USD"),("META","Meta","Azioni","USD"),
            ("TSLA","Tesla","Azioni","USD"),("AVGO","Broadcom","Azioni","USD"),
            ("ISRG","Intuitive Surgical","Azioni","USD"),("VRTX","Vertex","Azioni","USD"),
            ("ABBV","AbbVie","Azioni","USD"),("JPM","JPMorgan","Azioni","USD"),
            ("V","Visa","Azioni","USD"),("MA","Mastercard","Azioni","USD"),
            ("ASML","ASML Holding","Azioni","EUR"),("SAP","SAP SE","Azioni","EUR"),
            ("BOTZ","Global Robotics ETF","ETF","USD"),("ARKK","ARK Innovation","ETF","USD"),
            ("ICLN","Clean Energy ETF","ETF","USD"),("SOXX","Semiconductors ETF","ETF","USD"),
            ("GLD","SPDR Gold ETF","Materie Prime","USD"),
            ("BRK-B","Berkshire Hathaway","Azioni","USD"),
            ("UNH","UnitedHealth","Azioni","USD"),("COST","Costco","Azioni","USD"),
        ]
        pf_tickers_all = {p["ticker"].upper() for p in st.session_state.data["portfolio"]}
        wl_tickers_all = {w["ticker"].upper() for w in st.session_state.data["watchlist"] if w.get("ticker","N/A")!="N/A"}

        st.caption("Scansione automatica di 20+ titoli globali + watchlist. Zero costo. Esclusi titoli gia in portafoglio.")
        scan_src = st.radio("Scansiona:",["Universo globale","Solo watchlist","Entrambi"],horizontal=True,key="scan_src")

        if st.button("Aggiorna scan", key="btn_scan"):
            st.cache_data.clear(); st.rerun()

        candidates=[]
        if scan_src in ["Universo globale","Entrambi"]:
            for tk,nm,cat,val in GLOBAL_UNIVERSE:
                if tk.upper() not in pf_tickers_all and tk.upper() not in wl_tickers_all:
                    candidates.append({"ticker":tk,"nome":nm,"categoria":cat,"valuta":val,"fonte":"globale"})
        if scan_src in ["Solo watchlist","Entrambi"]:
            for w in st.session_state.data["watchlist"]:
                tk=w.get("ticker","N/A")
                if tk not in ("N/A","") and tk.upper() not in pf_tickers_all:
                    val="EUR" if any(s in tk for s in [".MI",".PA",".AS",".DE"]) else ("GBP" if ".L" in tk else "USD")
                    candidates.append({"ticker":tk,"nome":w["nome"],"categoria":w.get("categoria","Azioni"),"valuta":val,"fonte":"watchlist"})

        opps=[]; prog2=st.progress(0); stat2=st.empty()
        seen_c=set()
        for qi,c in enumerate(candidates):
            if c["ticker"] in seen_c: continue
            seen_c.add(c["ticker"])
            prog2.progress(int((qi+1)/max(len(candidates),1)*100))
            stat2.caption(f"Analisi: {c['ticker']}...")
            td=get_technical(c["ticker"])
            if not td: continue
            p_n=td["price"]; rsi=td["rsi"]; macd=td["macd_h"]
            sup=td["support"]; res=td["resistance"]; cross=td["cross"]
            signals=[]; score=0
            if rsi<40 and macd>0: signals.append("Rimbalzo tecnico (RSI basso + MACD positivo)"); score+=3
            elif rsi<35: signals.append(f"Ipervenduto (RSI {rsi:.0f}) — possibile rimbalzo"); score+=2
            if p_n>0 and abs(p_n-sup)/p_n<0.03: signals.append(f"Su supporto storico {sup:.2f}"); score+=2
            if cross=="golden": signals.append("Golden Cross attivo"); score+=3
            if td.get("vol_ratio",1)>1.5: signals.append(f"Volume anomalo ({td['vol_ratio']:.1f}x media)"); score+=1
            if td["ma50"] and td["ma200"] and p_n>td["ma50"] and p_n>td["ma200"]: signals.append("Trend positivo confermato"); score+=2
            if 45<rsi<62 and macd>0: signals.append("Momentum sano senza surriscaldamento"); score+=1
            if score<2: continue
            fx_r=fx.get(c["valuta"],1.0)
            stop_e=round(sup*0.97,2)
            ps=calc_position_size(total_pf,p_n,stop_e,fx_rate=fx_r)
            up=(res*0.99-p_n)/p_n*100 if p_n>0 else 0
            dn=(p_n-stop_e)/p_n*100 if p_n>0 else 0
            opps.append({"ticker":c["ticker"],"nome":c["nome"],"score":score,
                         "price":p_n,"rsi":rsi,"signals":signals,"ps":ps,
                         "target":round(res*0.99,2),"stop":stop_e,
                         "ingresso":round(min(sup*1.01,p_n*0.99),2),
                         "up_pct":up,"dn_pct":dn,"rr":up/dn if dn>0 else 0,
                         "fonte":c["fonte"]})

        prog2.empty(); stat2.empty()
        opps.sort(key=lambda x:-x["score"])

        if not opps:
            st.info("Nessuna opportunita tecnica rilevante al momento. Prova ad aggiornare lo scan.")
        else:
            # Tabella riepilogativa
            _oc = st.columns(4)
            for _ocol,(_ol,_ov,_oclr) in zip(_oc,[
                ("Trovate", str(len(opps)), "#10B981"),
                ("Score alto >=4", str(sum(1 for o in opps if o["score"]>=4)), "#10B981"),
                ("Score medio 2-3", str(sum(1 for o in opps if 2<=o["score"]<4)), "#F59E0B"),
                ("Da watchlist", str(sum(1 for o in opps if o["fonte"]=="watchlist")), "#8B5CF6"),
            ]):
                _ocol.markdown(
                    '<div style="background:#0F1829;border:1px solid #243352;border-radius:10px;padding:.65rem .5rem;text-align:center;">' +
                    f'<div style="font-size:.58rem;color:#64748B;text-transform:uppercase;margin-bottom:.2rem;">{_ol}</div>' +
                    f'<div style="font-family:JetBrains Mono,monospace;font-size:1.6rem;font-weight:700;color:{_oclr};">{_ov}</div>' +
                    '</div>', unsafe_allow_html=True)
            st.markdown("")
            # Testo narrativo riepilogativo
            top3 = opps[:3]
            if top3:
                narrative_parts = []
                for o in top3:
                    rr_txt = "ottimo rapporto rischio/rendimento" if o["rr"]>=2 else "rapporto rischio/rendimento accettabile"
                    sig_summary = o["signals"][0] if o["signals"] else "segnali tecnici positivi"
                    narrative_parts.append(
                        f'<b style="color:#60A5FA;">{o["nome"]} ({o["ticker"]})</b> — '
                        f'ingresso ideale a <b>{o["ingresso"]:.2f}</b>, '
                        f'target <b style="color:#10B981;">{o["target"]:.2f} (+{o["up_pct"]:.1f}%)</b>, '
                        f'stop <b style="color:#EF4444;">{o["stop"]:.2f}</b>. '
                        f'{sig_summary}. {rr_txt.capitalize()}.')
                narrative_html = (
                    '<div style="background:linear-gradient(135deg,#0D1526,#16213E);border:1px solid #2E4480;'
                    'border-radius:10px;padding:1rem 1.2rem;margin-bottom:.8rem;">'
                    '<div style="font-size:.65rem;font-weight:700;color:#3B82F6;text-transform:uppercase;'
                    'letter-spacing:.08em;margin-bottom:.6rem;">Sintesi — cosa puoi considerare ora</div>'
                    + "".join([f'<div style="font-size:.83rem;color:#94A3B8;line-height:1.7;padding:.3rem 0;'
                               f'border-bottom:1px solid #1E2D47;">{p}</div>' for p in narrative_parts])
                    + '</div>'
                )
                st.markdown(narrative_html, unsafe_allow_html=True)
            st.markdown('<div class="section-hd">Riepilogo opportunita</div>', unsafe_allow_html=True)
            tbl=[{"Score":"★"*min(o["score"],5),"Ticker":o["ticker"],"Nome":o["nome"][:20],
                  "Prezzo":f"{o['price']:.2f}","Ingresso":f"{o['ingresso']:.2f}",
                  "Target":f"{o['target']:.2f} +{o['up_pct']:.1f}%",
                  "Stop":f"{o['stop']:.2f} -{o['dn_pct']:.1f}%",
                  "R/R":f"{'ok' if o['rr']>=2 else 'low'} {o['rr']:.1f}:1",
                  "Quote (1% rischio)":str(o["ps"]["n_shares"]) if o["ps"] else "--",
                  "Segnali":" · ".join(o["signals"][:2])} for o in opps[:15]]
            st.dataframe(pd.DataFrame(tbl),use_container_width=True,hide_index=True)
            st.caption("Quote = quante quote comprare per rischiare al massimo l'1% del portafoglio su questa operazione.")

            st.markdown('<div class="section-hd">Dettaglio opportunita</div>', unsafe_allow_html=True)
            filt_cat_s=st.multiselect("Filtra categoria:",sorted(set(o.get("nome","") for o in opps)),default=[],key="opp_cat_s",
                                       placeholder="Tutti")
            for o in opps[:10]:
                sc_c="#10B981" if o["score"]>=4 else "#F59E0B"
                rr_c="#10B981" if o["rr"]>=2 else ("#F59E0B" if o["rr"]>=1 else "#EF4444")
                ps=o["ps"]
                earn_b = earnings_alert_html(o["ticker"], compact=True)
                ps_html=""
                if ps:
                    ps_html=f'<div style="background:rgba(59,130,246,.07);border-radius:6px;padding:.5rem .7rem;font-size:.77rem;margin-top:.4rem;"><b style="color:#3B82F6;">Position sizing (1% rischio):</b> Compra <b>{ps["n_shares"]} quote</b> · Investimento €{ps["position_eur"]:,.0f} ({ps["position_pct"]:.1f}%) · Rischio max €{ps["risk_eur"]:,.0f}</div>'

                sigs_html="".join([f'<div style="padding:.25rem .4rem;margin-bottom:.2rem;background:#162035;border-radius:4px;font-size:.77rem;color:#94A3B8;">{s}</div>' for s in o["signals"]])
                st.markdown(f'''
<div style="background:#0F1829;border:1px solid {sc_c}33;border-left:4px solid {sc_c};border-radius:10px;padding:.9rem 1rem;margin-bottom:.7rem;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem;flex-wrap:wrap;gap:.3rem;">
    <div><b style="color:{sc_c};">{o["ticker"]}</b> <span style="color:#E8EDF5;">{o["nome"]}</span> <span style="background:{sc_c}22;color:{sc_c};border:1px solid {sc_c}44;padding:1px 8px;border-radius:20px;font-size:.65rem;font-weight:700;margin-left:.4rem;">Score {o["score"]}/7</span>{earn_b}</div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:.4rem;font-size:.78rem;margin-bottom:.5rem;">
    <div><span style="color:#64748B;">Prezzo</span><br><b>{o["price"]:.2f}</b></div>
    <div><span style="color:#64748B;">Ingresso</span><br><b style="color:#60A5FA;">{o["ingresso"]:.2f}</b></div>
    <div><span style="color:#64748B;">Target</span><br><b style="color:#10B981;">{o["target"]:.2f} (+{o["up_pct"]:.1f}%)</b></div>
    <div><span style="color:#64748B;">Stop</span><br><b style="color:#EF4444;">{o["stop"]:.2f} (-{o["dn_pct"]:.1f}%)</b></div>
    <div><span style="color:#64748B;">R/R</span><br><b style="color:{rr_c};">{o["rr"]:.1f}:1</b></div>
  </div>
  {sigs_html}
  {ps_html}
</div>''', unsafe_allow_html=True)

    # ── TIMING DI INGRESSO ────────────────────────────────────────────────────
    with wt3:
        st.markdown('<div class="section-hd">Timing di ingresso — quando e come entrare su un titolo</div>', unsafe_allow_html=True)
        st.caption("Analisi intraday con livelli precisi di ingresso e uscita. Funziona sia per operazioni swing (giorni) che intraday (ore).")

        # Seleziona titolo
        non_pf_items = [w for w in st.session_state.data["watchlist"]
                        if w.get("ticker","N/A") not in ("N/A","")
                        and w["ticker"].upper() not in portfolio_tickers_set]
        non_pf_items += [{"ticker":t,"nome":n,"categoria":c} for t,n,c,_ in GLOBAL_UNIVERSE
                         if t.upper() not in portfolio_tickers_set and t.upper() not in wl_tickers_all]

        if not non_pf_items:
            st.info("Tutti i titoli della watchlist sono gia in portafoglio.")
        else:
            timing_names = [f"{i['ticker']} — {i['nome']}" for i in non_pf_items[:30]]
            t_sel = st.selectbox("Titolo da analizzare:",range(len(timing_names)),
                                  format_func=lambda i: timing_names[i], key="timing_sel")
            t_item = non_pf_items[t_sel]
            tk_t = t_item["ticker"]

            with st.spinner(f"Caricamento dati per {tk_t}..."):
                td_t = get_technical(tk_t)
                try:
                    h_daily = yf.Ticker(tk_t).history(period="3mo")
                    h_hourly = yf.Ticker(tk_t).history(period="5d",interval="1h")
                except: h_daily=None; h_hourly=None

            if td_t:
                p=td_t["price"]; rsi=td_t["rsi"]; macd=td_t["macd_h"]
                sup=td_t["support"]; res=td_t["resistance"]
                em,lbl,_ = tech_signal(td_t)

                # Calcola pivot points da dati ieri
                pivot=r1=r2=s1=s2=None
                if h_daily is not None and len(h_daily)>=2:
                    prev=h_daily.iloc[-2]
                    H,L,C_p=float(prev["High"]),float(prev["Low"]),float(prev["Close"])
                    pivot=round((H+L+C_p)/3,2)
                    r1=round(2*pivot-L,2); r2=round(pivot+(H-L),2)
                    s1=round(2*pivot-H,2); s2=round(pivot-(H-L),2)

                # Segnale timing
                timing_signals=[]; timing_warnings=[]; t_score=0
                if rsi<35 and macd>0: timing_signals.append("RSI basso + MACD positivo = classico segnale di rimbalzo"); t_score+=3
                elif rsi<45: timing_signals.append(f"RSI {rsi:.0f} in zona interessante — non surriscaldato"); t_score+=1
                elif rsi>70: timing_warnings.append(f"RSI {rsi:.0f} — troppo alto, attendi un ritracciamento"); t_score-=2
                if abs(p-sup)/p<0.02: timing_signals.append(f"Prezzo vicino al supporto storico {sup:.2f}"); t_score+=2
                if s1 and abs(p-s1)/p<0.015: timing_signals.append(f"Su S1 (supporto pivot) = {s1:.2f}"); t_score+=1
                if r1 and abs(p-r1)/p<0.015: timing_warnings.append(f"Su R1 (resistenza pivot) = {r1:.2f}"); t_score-=1
                if td_t["cross"]=="golden": timing_signals.append("Golden Cross attivo"); t_score+=2
                if macd>0: timing_signals.append("Momentum positivo (MACD > 0)"); t_score+=1
                else: timing_warnings.append("Momentum negativo (MACD < 0)")

                verdict_txt = "BUON MOMENTO" if t_score>=3 else ("ASPETTA" if t_score>=-1 else "NON ORA")
                verdict_c = "#10B981" if t_score>=3 else ("#F59E0B" if t_score>=-1 else "#EF4444")
                verdict_desc = {
                    "BUON MOMENTO": "I segnali tecnici convergono. Il prezzo e' in una zona favorevole all'ingresso.",
                    "ASPETTA": "Segnali misti. Meglio osservare qualche giorno prima di decidere.",
                    "NON ORA": "Segnali negativi. Attendi un miglioramento prima di considerare l'ingresso."
                }[verdict_txt]

                # Layout
                tv1,tv2 = st.columns([1,2])
                with tv1:
                    st.markdown(f'''
<div class="card" style="text-align:center;padding:1.5rem;margin-bottom:.8rem;">
  <div style="font-size:.65rem;color:#64748B;text-transform:uppercase;margin-bottom:.5rem;">{t_item["nome"]}</div>
  <div style="font-family:\'JetBrains Mono\',monospace;font-size:2.2rem;font-weight:700;color:{verdict_c};">{verdict_txt}</div>
  <div style="font-size:.78rem;color:{verdict_c};margin-top:.3rem;">{verdict_desc}</div>
  <div style="margin-top:1rem;font-size:.82rem;color:#94A3B8;"><b>Prezzo:</b> {p:.2f} · <b>RSI:</b> {rsi:.0f}</div>
</div>''', unsafe_allow_html=True)

                    # Livelli chiave
                    levels_items = []
                    if r2: levels_items.append(("R2 resistenza forte",r2,"#EF4444"))
                    if r1: levels_items.append(("R1 resistenza pivot",r1,"#EF4444"))
                    levels_items.append(("Resistenza storica",res,"#F97316"))
                    if pivot: levels_items.append(("Pivot Point",pivot,"#F59E0B"))
                    levels_items.append(("Supporto storico",sup,"#10B981"))
                    if s1: levels_items.append(("S1 supporto pivot",s1,"#10B981"))
                    if s2: levels_items.append(("S2 supporto forte",s2,"#10B981"))
                    levels_items.sort(key=lambda x:-x[1])

                    st.markdown('<div style="font-size:.68rem;font-weight:700;color:#64748B;text-transform:uppercase;margin:.6rem 0 .3rem;">Mappa livelli</div>', unsafe_allow_html=True)
                    for lname,lval,lc in levels_items:
                        is_near = p>0 and abs(p-lval)/p<0.02
                        dist=(lval-p)/p*100 if p>0 else 0
                        border = f"border:2px solid {lc};" if is_near else f"border:1px solid {lc}33;"
                        arrow = " PREZZO QUI" if is_near else ""
                        st.markdown(f'<div style="background:#0F1829;{border}border-radius:6px;padding:.3rem .6rem;margin-bottom:.2rem;font-size:.75rem;display:flex;justify-content:space-between;"><span style="color:#94A3B8;">{lname}{arrow}</span><span style="color:{lc};font-weight:700;">{lval:.2f} <span style="color:#64748B;font-size:.68rem;">{dist:+.1f}%</span></span></div>', unsafe_allow_html=True)

                with tv2:
                    if timing_signals:
                        st.markdown('<div style="background:rgba(16,185,129,.07);border:1px solid rgba(16,185,129,.3);border-radius:8px;padding:.8rem 1rem;margin-bottom:.5rem;"><div style="font-size:.65rem;font-weight:700;color:#10B981;text-transform:uppercase;margin-bottom:.4rem;">Segnali favorevoli</div>' + "".join([f'<div style="font-size:.8rem;color:#94A3B8;padding:.2rem 0;">+ {s}</div>' for s in timing_signals]) + '</div>', unsafe_allow_html=True)
                    if timing_warnings:
                        st.markdown('<div style="background:rgba(239,68,68,.07);border:1px solid rgba(239,68,68,.3);border-radius:8px;padding:.8rem 1rem;margin-bottom:.5rem;"><div style="font-size:.65rem;font-weight:700;color:#EF4444;text-transform:uppercase;margin-bottom:.4rem;">Segnali di cautela</div>' + "".join([f'<div style="font-size:.8rem;color:#94A3B8;padding:.2rem 0;">- {s}</div>' for s in timing_warnings]) + '</div>', unsafe_allow_html=True)

                    # Grafico intraday
                    if h_hourly is not None and len(h_hourly)>5:
                        fig_h=go.Figure()
                        fig_h.add_trace(go.Candlestick(x=h_hourly.index,
                            open=h_hourly["Open"],high=h_hourly["High"],
                            low=h_hourly["Low"],close=h_hourly["Close"],
                            name="Prezzo (1h)",
                            increasing_line_color="#10B981",decreasing_line_color="#EF4444",
                            increasing_fillcolor="#10B981",decreasing_fillcolor="#EF4444"))
                        if pivot: fig_h.add_hline(y=pivot,line_color="#F59E0B",line_dash="dot",line_width=1,annotation_text=f"Pivot {pivot:.2f}",annotation_font_color="#F59E0B",annotation_font_size=9)
                        if r1: fig_h.add_hline(y=r1,line_color="#EF4444",line_dash="dash",line_width=1,annotation_text=f"R1 {r1:.2f}",annotation_font_color="#EF4444",annotation_font_size=9)
                        if s1: fig_h.add_hline(y=s1,line_color="#10B981",line_dash="dash",line_width=1,annotation_text=f"S1 {s1:.2f}",annotation_font_color="#10B981",annotation_font_size=9)
                        fig_h.add_hrect(y0=sup*0.998,y1=sup*1.002,fillcolor="rgba(16,185,129,0.12)",line_width=0)
                        fig_h.add_hrect(y0=res*0.998,y1=res*1.002,fillcolor="rgba(239,68,68,0.12)",line_width=0)
                        fig_h.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(22,32,53,.8)",
                            font_color="#E8EDF5",xaxis_rangeslider_visible=False,
                            xaxis=dict(gridcolor="#1E2D47"),yaxis=dict(gridcolor="#1E2D47"),
                            height=300,margin=dict(t=5,b=5,l=5,r=60),showlegend=False)
                        st.plotly_chart(fig_h,use_container_width=True)

                    # Position sizing
                    if td_t:
                        val_t="EUR" if any(s in tk_t for s in [".MI",".PA",".DE"]) else ("GBP" if ".L" in tk_t else "USD")
                        fx_t=fx.get(val_t,1.0)
                        ps_t=calc_position_size(total_pf,p,sup*0.97,fx_rate=fx_t)
                        if ps_t:
                            st.markdown(f'<div style="background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.3);border-radius:8px;padding:.7rem .9rem;"><div style="font-size:.65rem;font-weight:700;color:#3B82F6;text-transform:uppercase;margin-bottom:.4rem;">Se entrassi ora (1% di rischio)</div><div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:.5rem;font-size:.8rem;"><div><span style="color:#64748B;">Quante quote</span><br><b style="font-size:1.1rem;">{ps_t["n_shares"]}</b></div><div><span style="color:#64748B;">Investimento</span><br><b>€{ps_t["position_eur"]:,.0f}</b> ({ps_t["position_pct"]:.1f}%)</div><div><span style="color:#64748B;">Rischio max</span><br><b style="color:#EF4444;">€{ps_t["risk_eur"]:,.0f}</b></div></div><div style="font-size:.72rem;color:#64748B;margin-top:.4rem;">Stop a {sup*0.97:.2f}: se il prezzo scende fino li, perdi al massimo €{ps_t["risk_eur"]:,.0f} — cioe l\'1% del portafoglio.</div></div>', unsafe_allow_html=True)
                # Earnings block
                earn_full = earnings_alert_html(tk_t, compact=False)
                if earn_full:
                    st.markdown(earn_full, unsafe_allow_html=True)
            else:
                st.warning(f"Dati non disponibili per {tk_t}. Verifica il ticker su Yahoo Finance.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — ANALISI AI
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    if not anthropic_key:
        st.warning("Inserisci la chiave Anthropic API nella sidebar per usare l'analisi multi-agente.")
    else:
        st.caption("5 agenti specializzati analizzano il tuo portafoglio reale: macro, tecnica, rischio, sentiment e piano operativo.")

        cache = st.session_state.data.get("agent_cache",{})
        cached = cache.get("results") if cache else None
        cached_time = cache.get("timestamp","") if cache else ""

        if cached:
            st.markdown(f'<div style="background:rgba(16,185,129,.08);border:1px solid rgba(16,185,129,.3);border-radius:8px;padding:.5rem .9rem;font-size:.75rem;color:#10B981;margin-bottom:.6rem;">Analisi del {cached_time} — clicca Aggiorna per rieseguire</div>', unsafe_allow_html=True)

        if st.button("Avvia analisi multi-agente", key="btn_ai_full", use_container_width=True):

            # Prepara contesto
            pf_rows=[]
            for _,row in df_main.iterrows():
                pf_rows.append(f"  {row['Nome']} ({row['Ticker']}): {row['Categoria']} | €{row['CV €']:,.0f} | P&L {row['P&L %']:+.1f}%")
            pf_detail="\n".join(pf_rows) if pf_rows else "Vuoto"
            alloc=df_main.groupby("Categoria")["CV €"].sum()
            total_v=alloc.sum()
            alloc_str="\n".join([f"  {c}: {v/total_v*100:.1f}%" for c,v in alloc.items()]) if total_v>0 else "N/D"
            news_txt="\n".join([f"- {n['title']}" for n in news_items[:8]]) if news_items else "Nessuna notizia"
            vix_v2=mkt.get("VIX",{}).get("value",20); sp500_v=mkt.get("S&P 500",{}).get("delta",0)
            eurusd_v=mkt.get("EUR/USD",{}).get("value",1.08)

            results={}
            prog_ai=st.progress(0)

            agents=[
                ("macro","Analista Macro",
                 f"Portafoglio:\n{pf_detail}\nAllocazione:\n{alloc_str}\nVIX={vix_v2:.1f}, S&P500={sp500_v:+.2f}%, EUR/USD={eurusd_v:.4f}\nNotizie:\n{news_txt}\n\nAnalizza in italiano (max 350 parole):\n1) Situazione mercati oggi in parole semplici\n2) 3 rischi per QUESTO portafoglio specifico\n3) 3 opportunita concrete nei prossimi mesi"),
                ("tecnica","Analista Tecnico",
                 f"Portafoglio:\n{pf_detail}\nVIX={vix_v2:.1f}\n\nPer ogni titolo azionario/ETF in portafoglio (max 15) spiega in italiano semplice:\n- Cosa sta facendo (sale/scende/laterale)\n- Il segnale e perche\n- Un livello chiave da monitorare\nConcludi con top 3 setup migliori e top 3 piu rischiosi. Max 400 parole."),
                ("rischio","Gestore del Rischio",
                 f"Portafoglio:\n{pf_detail}\nAllocazione:\n{alloc_str}\nVIX={vix_v2:.1f}\n\nAnalizza in italiano (max 300 parole):\n1) Concentrazioni eccessive e rischi di portafoglio\n2) Rischio cambio (esposizione EUR/USD/GBP)\n3) Correlazioni pericolose tra posizioni\n4) Una raccomandazione pratica per ridurre il rischio"),
                ("sentiment","Analista Sentiment",
                 f"Notizie di mercato:\n{news_txt}\nPortafoglio:\n{pf_detail}\n\nAnalizza in italiano (max 300 parole):\n1) Sentiment generale del mercato oggi\n2) Quali settori/titoli del portafoglio sono piu esposti alle notizie attuali\n3) Cosa monitorare nelle prossime 2 settimane"),
                ("piano","Portfolio Strategist",
                 f"Portafoglio:\n{pf_detail}\nAllocazione:\n{alloc_str}\nVIX={vix_v2:.1f}, S&P500={sp500_v:+.2f}%\n\nCrea in italiano un piano operativo concreto (max 400 parole):\n1) Cosa fare questa settimana (azioni specifiche con ticker)\n2) Cosa monitorare nel medio termine (1-3 mesi)\n3) Come migliorare l'allocazione del portafoglio\nSii specifico con i titoli reali in portafoglio."),
            ]

            agent_icons={"macro":"🌍","tecnica":"📡","rischio":"⚖️","sentiment":"🧠","piano":"🎯"}
            for idx,(key,nome,prompt) in enumerate(agents):
                prog_ai.progress(int((idx+1)/5*100))
                with st.spinner(f"Agente {idx+1}/5: {nome}..."):
                    rsp,err=ai_call(prompt, max_tokens=900)
                    results[key]=rsp if rsp else f"Errore: {err}"

            prog_ai.empty()
            st.session_state.data["agent_cache"]={"results":results,"timestamp":datetime.now().strftime("%d/%m/%Y %H:%M")}
            save_data(st.session_state.data)
            cached=results
            st.rerun()

        if cached:
            ai_tabs=st.tabs(["🌍 Macro","📡 Tecnica","⚖️ Rischio","🧠 Sentiment","🎯 Piano operativo"])
            agent_keys=["macro","tecnica","rischio","sentiment","piano"]
            for ai_tab,k in zip(ai_tabs,agent_keys):
                with ai_tab:
                    txt=cached.get(k,"Non disponibile")
                    st.markdown(f'<div style="background:linear-gradient(135deg,#0D1526,#16213E);border:1px solid #2E4480;border-radius:12px;padding:1.2rem 1.4rem;line-height:1.8;font-size:.88rem;color:#94A3B8;">{txt.replace(chr(10),"<br>")}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — GESTIONE
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    mg1,mg2,mg3,mg4 = st.tabs(["Operazioni","Prezzi manuali","Storico","Alert email"])

    # ── OPERAZIONI ────────────────────────────────────────────────────────────
    with mg1:
        def get_liq_idx():
            return next((i for i,p in enumerate(st.session_state.data["portfolio"]) if p["categoria"]=="Liquidita"),None)
        def get_liq_eur():
            idx=get_liq_idx()
            if idx is None: return 0.0
            p=st.session_state.data["portfolio"][idx]
            return float(p.get("prezzo_manuale") or p.get("prezzo_carico",0) or 0)*float(p.get("quantita",1))
        def update_liq(delta):
            idx=get_liq_idx()
            if idx is None: return
            cur=get_liq_eur()
            st.session_state.data["portfolio"][idx]["quantita"]=max(0,round(cur+delta,2))

        liq_eur=get_liq_eur()
        op_type=st.radio("Tipo:",["Acquisto","Vendita","Cedola/Dividendo","Movimento liquidita"],horizontal=True,key="op_type")

        if op_type=="Acquisto":
            liq_c="#10B981" if liq_eur>1000 else ("#F59E0B" if liq_eur>0 else "#EF4444")
            st.markdown(f'<div style="background:{liq_c}12;border:1px solid {liq_c}33;border-radius:8px;padding:.5rem 1rem;font-size:.82rem;margin-bottom:.6rem;">Liquidita disponibile: <b style="color:{liq_c};">€{liq_eur:,.2f}</b></div>', unsafe_allow_html=True)
            fc1,fc2,fc3=st.columns(3)
            with fc1:
                gn=st.text_input("Nome *",key="gn")
                gt=st.text_input("Ticker Yahoo *",placeholder="AAPL, LDO.MI, N/A",key="gt")
                gc=st.selectbox("Categoria *",["Azioni","ETF","Obbligazioni","Crypto","Certificati","Materie Prime"],key="gc")
            with fc2:
                gv=st.selectbox("Valuta *",["EUR","USD","GBP","DKK","CHF"],key="gv")
                gp=st.number_input("Prezzo unitario *",min_value=0.0,step=0.001,format="%.3f",key="gp")
                gq=st.number_input("Quantita *",min_value=0.0,step=0.001,format="%.4f",key="gq")
            with fc3:
                gop=st.radio("Tipo acquisto",["Nuovo titolo","Incrementa esistente"],key="gop")
                comm_a=st.number_input("Commissione (EUR)",min_value=0.0,step=0.5,format="%.2f",key="comm_a")
                costo_preview=to_eur(gp*gq,gv,fx)+(comm_a or 0)
                st.markdown(f'<div class="tooltip-box">Costo stimato: <b>€{costo_preview:,.2f}</b></div>', unsafe_allow_html=True)
            if st.button("Registra acquisto",key="btn_buy"):
                if gn and gt and gp>0 and gq>0:
                    costo_eur=to_eur(gp*gq,gv,fx)+(comm_a or 0)
                    if liq_eur>0 and costo_eur>liq_eur:
                        st.error(f"Liquidita insufficiente: serve €{costo_eur:,.2f} ma hai €{liq_eur:,.2f}")
                    else:
                        existing_idx=next((i for i,p in enumerate(st.session_state.data["portfolio"]) if p["ticker"].upper()==gt.upper()),None)
                        te={"data":datetime.now().strftime("%d/%m/%Y %H:%M"),"tipo":"acquisto","nome":gn,
                            "ticker":gt.upper(),"quantita":gq,"prezzo":gp,"valuta":gv,"categoria":gc,
                            "commissione":comm_a,"pnl_realizzato":None}
                        if gop=="Incrementa esistente" and existing_idx is not None:
                            old=st.session_state.data["portfolio"][existing_idx]
                            nq=old["quantita"]+gq; np_=(old["prezzo_carico"]*old["quantita"]+gp*gq)/nq
                            st.session_state.data["portfolio"][existing_idx].update({"quantita":nq,"prezzo_carico":np_})
                        else:
                            st.session_state.data["portfolio"].append({"nome":gn,"ticker":gt.upper(),"valuta":gv,"prezzo_carico":gp,"quantita":gq,"categoria":gc,"prezzo_manuale":None})
                        update_liq(-costo_eur)
                        st.session_state.data["trade_history"].append(te)
                        save_data(st.session_state.data); st.cache_data.clear()
                        st.success(f"Acquisto registrato. Costo €{costo_eur:,.2f}. Liquidita residua €{get_liq_eur():,.2f}"); st.rerun()
                else: st.error("Compila tutti i campi obbligatori")

        elif op_type=="Vendita":
            sell_items=[(i,p) for i,p in enumerate(st.session_state.data["portfolio"]) if p["categoria"]!="Liquidita"]
            if not sell_items: st.info("Nessun titolo in portafoglio.")
            else:
                sell_names=[f"{p['nome']} ({p['ticker']}) — {p['quantita']} @ {p['prezzo_carico']:.3f}" for _,p in sell_items]
                s_sel=st.selectbox("Titolo da vendere *",range(len(sell_names)),format_func=lambda i:sell_names[i],key="s_sel")
                s_idx,s_item=sell_items[s_sel]
                sv1,sv2=st.columns(2)
                with sv1:
                    s_qty=st.number_input("Quantita",min_value=0.001,max_value=float(s_item["quantita"]),value=float(s_item["quantita"]),step=0.001,format="%.4f",key="s_qty")
                    s_price=st.number_input("Prezzo di vendita",min_value=0.001,value=float(s_item["prezzo_carico"]),step=0.001,format="%.3f",key="s_price")
                    s_comm=st.number_input("Commissione (EUR)",min_value=0.0,step=0.5,format="%.2f",key="s_comm")
                with sv2:
                    pnl_l=to_eur((s_price-s_item["prezzo_carico"])*s_qty,s_item["valuta"],fx)
                    inc_l=to_eur(s_price*s_qty,s_item["valuta"],fx)
                    tax_type=st.radio("Tassazione:",["26% (azioni/ETF)","12.5% (titoli stato)","0% (minus/esenzione)","Altro"],key="tax_t")
                    tax_pct=0.26 if "26" in tax_type else (0.125 if "12.5" in tax_type else (0.0 if "0%" in tax_type else st.number_input("Aliquota %",0.0,100.0,26.0,key="tax_c")/100))
                    tasse=round(max(0,pnl_l)*tax_pct,2); inc_n=inc_l-tasse-(s_comm or 0)
                    pnl_n=pnl_l-tasse-(s_comm or 0)
                    pnl_lc="#10B981" if pnl_l>=0 else "#EF4444"
                    st.markdown(f'<div class="card"><div style="font-size:.65rem;color:#64748B;text-transform:uppercase;margin-bottom:.5rem;">Riepilogo</div><div style="font-size:.82rem;line-height:2;"><div>P&L lordo: <b style="color:{pnl_lc};">€{pnl_l:+,.2f}</b></div><div>Tasse ({tax_pct*100:.1f}%): <b style="color:#EF4444;">-€{tasse:,.2f}</b></div><div>Commissione: <b style="color:#EF4444;">-€{s_comm or 0:.2f}</b></div><div style="border-top:1px solid #243352;margin-top:.3rem;padding-top:.3rem;">Incasso netto: <b style="color:#10B981;font-size:1rem;">€{inc_n:,.2f}</b></div></div></div>', unsafe_allow_html=True)
                if st.button("Registra vendita",key="btn_sell"):
                    te={"data":datetime.now().strftime("%d/%m/%Y %H:%M"),"tipo":"vendita",
                        "nome":s_item["nome"],"ticker":s_item["ticker"],"quantita":s_qty,
                        "prezzo":s_price,"valuta":s_item["valuta"],"categoria":s_item["categoria"],
                        "pnl_lordo":round(pnl_l,2),"tasse":tasse,"commissione":s_comm or 0,
                        "pnl_realizzato":round(pnl_n,2),"aliquota":f"{tax_pct*100:.1f}%"}
                    if s_qty>=s_item["quantita"]-0.0001: st.session_state.data["portfolio"].pop(s_idx)
                    else: st.session_state.data["portfolio"][s_idx]["quantita"]-=s_qty
                    update_liq(inc_n)
                    st.session_state.data["trade_history"].append(te)
                    save_data(st.session_state.data); st.cache_data.clear()
                    st.success(f"Vendita registrata. P&L netto €{pnl_n:+,.2f}. Liquidita +€{inc_n:,.2f}"); st.rerun()

        elif op_type=="Cedola/Dividendo":
            pf_names=[f"{p['nome']} ({p['ticker']})" for p in st.session_state.data["portfolio"] if p["categoria"]!="Liquidita"]
            if pf_names:
                ced_sel=st.selectbox("Titolo *",range(len(pf_names)),format_func=lambda i:pf_names[i],key="ced_sel")
                c1,c2=st.columns(2)
                with c1:
                    ced_amt=st.number_input("Importo lordo (EUR) *",min_value=0.01,step=1.0,format="%.2f",key="ced_amt")
                    ced_tipo=st.radio("Tipo",["Cedola","Dividendo","Distribuzione"],horizontal=True,key="ced_tipo")
                with c2:
                    ced_tax=st.radio("Ritenuta:",["26%","12.5%","0% (gia netto)","Altro"],key="ced_tax")
                    ctax=0.26 if "26" in ced_tax else (0.125 if "12.5" in ced_tax else (0.0 if "0%" in ced_tax else st.number_input("Ritenuta %",0.0,100.0,26.0,key="ctax_c")/100))
                    ced_netto=ced_amt*(1-ctax)
                    st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:.65rem;color:#64748B;text-transform:uppercase;">Netto in liquidita</div><div style="font-size:1.4rem;font-weight:700;color:#10B981;">+€{ced_netto:,.2f}</div></div>', unsafe_allow_html=True)
                if st.button("Registra",key="btn_ced"):
                    ced_item=[p for p in st.session_state.data["portfolio"] if p["categoria"]!="Liquidita"][ced_sel]
                    te={"data":datetime.now().strftime("%d/%m/%Y %H:%M"),"tipo":ced_tipo.lower(),
                        "nome":ced_item["nome"],"ticker":ced_item["ticker"],"quantita":0,"prezzo":0,
                        "valuta":"EUR","categoria":ced_item["categoria"],
                        "importo_lordo":round(ced_amt,2),"ritenuta":round(ced_amt*ctax,2),"pnl_realizzato":round(ced_netto,2)}
                    update_liq(ced_netto)
                    st.session_state.data["trade_history"].append(te)
                    save_data(st.session_state.data)
                    st.success(f"{ced_tipo} registrata. +€{ced_netto:.2f} in liquidita"); st.rerun()

        else:  # Movimento liquidita
            l1,l2=st.columns(2)
            with l1:
                liq_dir=st.radio("Tipo:",["Versamento (aggiungi)","Prelievo (togli)"],key="liq_dir")
                liq_amt=st.number_input("Importo (EUR) *",min_value=0.01,step=100.0,format="%.2f",key="liq_amt")
                liq_note=st.text_input("Note",key="liq_note")
            with l2:
                delta=liq_amt if "Versamento" in liq_dir else -liq_amt
                new_liq=liq_eur+delta; dc="#10B981" if delta>=0 else "#EF4444"
                st.markdown(f'<div class="card"><div style="font-size:.82rem;line-height:2;"><div>Attuale: <b>€{liq_eur:,.2f}</b></div><div>Movimento: <b style="color:{dc};">{"+€" if delta>=0 else "-€"}{abs(delta):,.2f}</b></div><div>Nuovo saldo: <b style="color:{dc};">€{max(0,new_liq):,.2f}</b></div></div></div>', unsafe_allow_html=True)
            if st.button("Registra",key="btn_liq"):
                update_liq(delta)
                te={"data":datetime.now().strftime("%d/%m/%Y %H:%M"),"tipo":"versamento" if delta>=0 else "prelievo",
                    "nome":"Liquidita","ticker":"N/A","quantita":0,"prezzo":0,"valuta":"EUR","categoria":"Liquidita",
                    "pnl_realizzato":None,"note":liq_note or ""}
                st.session_state.data["trade_history"].append(te)
                save_data(st.session_state.data)
                st.success(f"Movimento registrato. Nuova liquidita: €{get_liq_eur():,.2f}"); st.rerun()

    # ── PREZZI MANUALI ────────────────────────────────────────────────────────
    with mg2:
        needs=[p for p in st.session_state.data["portfolio"] if p["ticker"]=="N/A" and not (p.get("prezzo_manuale") or 0)>0]
        if needs:
            st.markdown(f'<div style="background:rgba(239,68,68,.1);border:1px solid #EF444444;border-radius:8px;padding:.6rem 1rem;font-size:.82rem;color:#EF4444;margin-bottom:.8rem;">{len(needs)} asset senza prezzo. Inseriscili qui per avere il portafoglio completo.</div>', unsafe_allow_html=True)
            qvals={}; qcols=st.columns(3)
            for qi,qitem in enumerate(needs):
                with qcols[qi%3]:
                    hint="% del nominale (es. 98.50)" if qitem["categoria"]=="Obbligazioni" else "prezzo attuale"
                    qvals[qi]=st.number_input(qitem["nome"][:28],min_value=0.0,step=0.01,format="%.3f",key=f"qp_{qi}",help=hint)
            if st.button("Salva tutti i prezzi",key="btn_qsave"):
                saved_c=0
                for qi,qitem in enumerate(needs):
                    if qvals[qi]>0:
                        idx_q=st.session_state.data["portfolio"].index(qitem)
                        st.session_state.data["portfolio"][idx_q]["prezzo_manuale"]=qvals[qi]; saved_c+=1
                if saved_c:
                    save_data(st.session_state.data); st.cache_data.clear()
                    st.success(f"{saved_c} prezzi salvati!"); st.rerun()
                else: st.warning("Nessun valore inserito")
            st.markdown("---")

        portfolio_all = st.session_state.data["portfolio"]
        cats_g=sorted(set(p["categoria"] for p in portfolio_all))
        for cat_g in cats_g:
            cat_items_g=[p for p in portfolio_all if p["categoria"]==cat_g]
            cat_col_g=CAT_COLORS.get(cat_g,"#64748B")
            st.markdown(f'<div style="color:{cat_col_g};font-weight:700;font-size:.78rem;text-transform:uppercase;letter-spacing:.1em;margin:1rem 0 .4rem;">{cat_g} ({len(cat_items_g)})</div>', unsafe_allow_html=True)
            for li,item_g in enumerate(cat_items_g):
                idx_g=portfolio_all.index(item_g)
                pm_g=item_g.get("prezzo_manuale") or 0
                lp_g=get_price(item_g["ticker"]) if item_g["ticker"]!="N/A" else None
                dot_g="🔵" if (item_g["ticker"]!="N/A" and lp_g) else ("✏️" if pm_g>0 else "🔴")
                lbl_g=f"Live: {lp_g:,.3f}" if lp_g else (f"Manuale: {pm_g:,.3f}" if pm_g>0 else "PREZZO MANCANTE")
                uniq_g=f"{cat_g}_{li}"
                with st.expander(f"{dot_g} {item_g['nome']} — {lbl_g}"):
                    e1,e2,e3=st.columns(3)
                    with e1:
                        nn=st.text_input("Nome",value=item_g["nome"],key=f"en_{uniq_g}")
                        nt=st.text_input("Ticker",value=item_g["ticker"],key=f"et_{uniq_g}")
                    with e2:
                        npc=st.number_input("Prezzo carico",value=float(item_g["prezzo_carico"]),step=0.001,format="%.3f",key=f"ep_{uniq_g}")
                        nq=st.number_input("Quantita",value=float(item_g["quantita"]),step=0.001,format="%.4f",key=f"eq_{uniq_g}")
                    with e3:
                        vl=["EUR","USD","GBP","DKK","CHF"]
                        nv=st.selectbox("Valuta",vl,index=vl.index(item_g["valuta"]) if item_g["valuta"] in vl else 0,key=f"ev_{uniq_g}")
                        nm=st.number_input("Prezzo manuale (0=auto)",value=float(pm_g),min_value=0.0,step=0.01,format="%.3f",key=f"em_{uniq_g}")
                    bc1,bc2=st.columns(2)
                    with bc1:
                        if st.button("Salva",key=f"sv_{uniq_g}"):
                            st.session_state.data["portfolio"][idx_g].update({"nome":nn,"ticker":nt,"prezzo_carico":npc,"quantita":nq,"valuta":nv,"prezzo_manuale":nm if nm>0 else None})
                            save_data(st.session_state.data); st.cache_data.clear(); st.rerun()
                    with bc2:
                        if st.button("Elimina",key=f"dl_{uniq_g}",type="secondary"):
                            st.session_state.data["portfolio"].pop(idx_g)
                            save_data(st.session_state.data); st.rerun()

    # ── STORICO ───────────────────────────────────────────────────────────────
    with mg3:
        th=st.session_state.data.get("trade_history",[])
        if not th:
            st.info("Nessuna operazione registrata.")
        else:
            t_pnl=sum((t.get("pnl_realizzato") or 0) for t in th if t.get("tipo")=="vendita")
            t_ced=sum((t.get("pnl_realizzato") or 0) for t in th if t.get("tipo") in ("cedola","dividendo","distribuzione"))
            hk1,hk2,hk3,hk4=st.columns(4)
            hk1.metric("Operazioni",len(th))
            hk2.metric("P&L vendite",f"€{t_pnl:+,.0f}")
            hk3.metric("Cedole/Dividendi",f"€{t_ced:,.0f}")
            hk4.metric("Acquisti",sum(1 for t in th if t.get("tipo")=="acquisto"))

            tipo_colors={"acquisto":"#3B82F6","vendita":"#10B981","cedola":"#F59E0B",
                         "dividendo":"#F59E0B","distribuzione":"#F59E0B","versamento":"#10B981","prelievo":"#EF4444"}
            for t in reversed(th[-40:]):
                tipo_t=t.get("tipo","acquisto"); tc=tipo_colors.get(tipo_t,"#64748B")
                pnl_t=t.get("pnl_realizzato")
                det=[]
                if t.get("quantita",0)>0: det.append(f"{t['quantita']} @ {t.get('prezzo',0):.3f}")
                if t.get("tasse"): det.append(f"tasse €{t['tasse']:.2f}")
                if t.get("commissione"): det.append(f"comm. €{t['commissione']:.2f}")
                if t.get("note"): det.append(t["note"])
                det_str=" · ".join(det)
                pnl_html="" if pnl_t is None else f' · <b style="color:{"#10B981" if pnl_t>=0 else "#EF4444"};">€{pnl_t:+,.2f}</b>'
                st.markdown(f'<div style="background:#0F1829;border:1px solid #243352;border-left:3px solid {tc};border-radius:8px;padding:.5rem .9rem;margin-bottom:.3rem;display:flex;align-items:center;gap:.8rem;font-size:.79rem;flex-wrap:wrap;"><div style="color:#64748B;min-width:95px;font-size:.72rem;">{t.get("data","")}</div><span style="background:{tc}22;color:{tc};border:1px solid {tc}44;padding:1px 6px;border-radius:20px;font-size:.67rem;font-weight:700;">{tipo_t.upper()}</span><div style="flex:1;color:#E8EDF5;"><b>{t.get("nome","")}</b></div><div style="color:#94A3B8;">{det_str}{pnl_html}</div></div>', unsafe_allow_html=True)

            df_exp=pd.DataFrame(th)
            csv=df_exp.to_csv(index=False).encode("utf-8")
            st.download_button("Esporta CSV",csv,"operazioni.csv","text/csv")

    # ── ALERT EMAIL ───────────────────────────────────────────────────────────
    with mg4:
        em_cfg=st.session_state.data.get("email_settings",{})
        e1,e2=st.columns(2)
        with e1:
            em_from=st.text_input("Gmail mittente",value=em_cfg.get("from_email",""),key="em_from",placeholder="tua@gmail.com")
            em_pass=st.text_input("App Password Gmail",type="password",value=em_cfg.get("app_password",""),key="em_pass")
            em_to=st.text_input("Destinatario",value=em_cfg.get("to_email",""),key="em_to")
        with e2:
            st.markdown('<div class="tooltip-box"><b>Come ottenere App Password:</b><br>1. Vai su myaccount.google.com<br>2. Sicurezza → Verifica in 2 passaggi (deve essere attiva)<br>3. Password per le app → crea nuova<br>4. Copia e incolla qui</div>', unsafe_allow_html=True)
        if st.button("Salva configurazione email",key="btn_em_save"):
            st.session_state.data["email_settings"]={"from_email":em_from,"app_password":em_pass,"to_email":em_to}
            save_data(st.session_state.data); st.success("Configurazione salvata")
        if em_cfg.get("from_email") and st.button("Invia report ora",key="btn_em_send"):
            pnl_t2=df_main["P&L €"].sum() if not df_main.empty else 0
            tot_v2=df_main["CV €"].sum() if not df_main.empty else 0
            best2=df_main.nlargest(1,"P&L %").iloc[0] if not df_main.empty else None
            worst2=df_main.nsmallest(1,"P&L %").iloc[0] if not df_main.empty else None
            html_rep=f"""<div style="font-family:Inter,sans-serif;background:#070D1A;color:#E8EDF5;padding:2rem;border-radius:12px;max-width:640px;">
<h2 style="margin-bottom:1rem;">📈 Report portafoglio {datetime.now().strftime('%d/%m/%Y')}</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem;">
<div style="background:#0F1829;border-radius:8px;padding:1rem;text-align:center;"><div style="color:#64748B;font-size:.75rem;">Totale</div><div style="font-size:1.3rem;font-weight:700;">€{tot_v2:,.0f}</div></div>
<div style="background:#0F1829;border-radius:8px;padding:1rem;text-align:center;"><div style="color:#64748B;font-size:.75rem;">P&L</div><div style="font-size:1.3rem;font-weight:700;color:{"#10B981" if pnl_t2>=0 else "#EF4444"};">€{pnl_t2:+,.0f}</div></div>
</div>
{f'<p>Miglior titolo: <b>{best2["Nome"]}</b> {best2["P&L %"]:+.1f}%</p>' if best2 is not None else ""}
{f'<p>Peggior titolo: <b>{worst2["Nome"]}</b> {worst2["P&L %"]:+.1f}%</p>' if worst2 is not None else ""}
<p style="color:#64748B;font-size:.8rem;">Score salute portafoglio: {health_score}/100</p>
</div>"""
            ok,msg=send_email_alert(st.session_state.data["email_settings"],f"Report Portafoglio {datetime.now().strftime('%d/%m/%Y')}",html_rep)
            st.success(f"Inviato: {msg}") if ok else st.error(f"Errore: {msg}")
