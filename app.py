import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import json, requests, time
from datetime import datetime, timedelta
from pathlib import Path
import anthropic

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Investment Intelligence", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

# ── GLOBAL STYLES ─────────────────────────────────────────────────────────────
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
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [class*="css"] { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); }
.stApp { background: var(--bg); }
.main .block-container { padding: 1rem 1.5rem 2rem; max-width: 1800px; }
section[data-testid="stSidebar"] { background: var(--s1) !important; border-right: 1px solid var(--border); }
section[data-testid="stSidebar"] * { color: var(--text) !important; }
/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: var(--s1); border: 1px solid var(--border); border-radius: 10px; padding: 3px; gap: 2px; }
.stTabs [data-baseweb="tab"] { background: transparent; color: var(--text3); border-radius: 8px; font-size: 0.82rem; font-weight: 500; padding: 0.4rem 0.9rem; }
.stTabs [aria-selected="true"] { background: var(--accent) !important; color: #fff !important; }
/* Metrics */
[data-testid="metric-container"] { background: var(--s1); border: 1px solid var(--border); border-radius: 10px; padding: 0.9rem 1rem; }
[data-testid="stMetricValue"] { font-family: var(--mono); font-size: 1.3rem !important; }
/* Inputs */
.stTextInput input, .stNumberInput input, .stSelectbox > div > div { background: var(--s2) !important; border: 1px solid var(--border) !important; color: var(--text) !important; border-radius: 8px !important; }
/* Buttons */
.stButton > button { background: var(--accent); color: #fff; border: none; border-radius: 8px; font-weight: 600; font-size: 0.82rem; padding: 0.45rem 1rem; transition: all .15s; }
.stButton > button:hover { background: var(--accent2); transform: translateY(-1px); }
/* Expanders */
.streamlit-expanderHeader { background: var(--s2) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; color: var(--text) !important; }
.streamlit-expanderContent { background: var(--s2) !important; border: 1px solid var(--border) !important; border-top: none !important; border-radius: 0 0 8px 8px !important; }
/* DataFrames */
.stDataFrame { border-radius: 10px; overflow: hidden; }
iframe[title="st.dataframe"] { border-radius: 10px; }
/* Radio */
.stRadio > div { gap: 0.5rem; }
.stRadio label { color: var(--text2) !important; font-size: 0.85rem; }
/* Hide branding */
#MainMenu, footer, header { visibility: hidden; }
/* Custom components */
.kpi-card { background: var(--s1); border: 1px solid var(--border); border-radius: 12px; padding: 1rem 1.2rem; }
.kpi-label { font-size: 0.68rem; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; color: var(--text3); margin-bottom: .35rem; }
.kpi-value { font-family: var(--mono); font-size: 1.5rem; font-weight: 600; color: var(--text); }
.kpi-delta { font-family: var(--mono); font-size: 0.78rem; margin-top: .2rem; }
.up { color: var(--green); } .dn { color: var(--red); }
.section-hd { font-size: .7rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: var(--text3); padding: .5rem 0 .4rem; border-bottom: 1px solid var(--border); margin-bottom: .8rem; margin-top: 1.2rem; }
.badge-green { background: rgba(16,185,129,.15); color: #10B981; border: 1px solid rgba(16,185,129,.3); padding: 2px 8px; border-radius: 20px; font-size: .72rem; font-weight: 700; }
.badge-yellow { background: rgba(245,158,11,.15); color: #F59E0B; border: 1px solid rgba(245,158,11,.3); padding: 2px 8px; border-radius: 20px; font-size: .72rem; font-weight: 700; }
.badge-red { background: rgba(239,68,68,.15); color: #EF4444; border: 1px solid rgba(239,68,68,.3); padding: 2px 8px; border-radius: 20px; font-size: .72rem; font-weight: 700; }
.badge-blue { background: rgba(59,130,246,.15); color: #60A5FA; border: 1px solid rgba(59,130,246,.3); padding: 2px 8px; border-radius: 20px; font-size: .72rem; font-weight: 700; }
.ai-block { background: linear-gradient(135deg,#0D1526 0%,#16213E 100%); border: 1px solid #2E4480; border-radius: 12px; padding: 1.2rem 1.4rem; line-height: 1.75; font-size: .9rem; }
.tooltip-box { background: var(--s3); border: 1px solid var(--border2); border-radius: 8px; padding: .6rem .8rem; font-size: .78rem; color: var(--text2); line-height: 1.5; margin-top: .3rem; }
.agent-card { background: var(--s2); border: 1px solid var(--border); border-radius: 10px; padding: 1rem; margin-bottom: .5rem; }
.agent-tag { font-size: .65rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.status-live { color: var(--accent2); } .status-manual { color: var(--yellow); } .status-missing { color: var(--red); }
</style>
""", unsafe_allow_html=True)

# ── DATA ──────────────────────────────────────────────────────────────────────
DATA_FILE = Path("data/portfolio.json")
DATA_FILE.parent.mkdir(exist_ok=True)

CATEGORY_COLORS = {"Azioni":"#3B82F6","ETF":"#10B981","Obbligazioni":"#F59E0B","Crypto":"#8B5CF6","Certificati":"#06B6D4","Materie Prime":"#F97316"}

DEFAULT_DATA = {
    "portfolio": [
        {"nome":"Leonardo","ticker":"LDO.MI","valuta":"EUR","prezzo_carico":20.640,"quantita":33,"categoria":"Azioni","prezzo_manuale":None},
        {"nome":"Ipsos","ticker":"IPS.PA","valuta":"EUR","prezzo_carico":46.053,"quantita":30,"categoria":"Azioni","prezzo_manuale":None},
        {"nome":"Trigano","ticker":"TRI.PA","valuta":"EUR","prezzo_carico":106.19,"quantita":5,"categoria":"Azioni","prezzo_manuale":None},
        {"nome":"Pinduoduo (PDD)","ticker":"PDD","valuta":"USD","prezzo_carico":100.377,"quantita":7,"categoria":"Azioni","prezzo_manuale":None},
        {"nome":"Global Ship Lease","ticker":"GSL","valuta":"USD","prezzo_carico":19.140,"quantita":36,"categoria":"Azioni","prezzo_manuale":None},
        {"nome":"Cal-Maine Foods","ticker":"CALM","valuta":"USD","prezzo_carico":93.73,"quantita":16,"categoria":"Azioni","prezzo_manuale":None},
        {"nome":"Zealand Pharma","ticker":"ZEAL.CO","valuta":"DKK","prezzo_carico":421.95,"quantita":22,"categoria":"Azioni","prezzo_manuale":None},
        {"nome":"Adobe","ticker":"ADBE","valuta":"USD","prezzo_carico":272.47,"quantita":4,"categoria":"Azioni","prezzo_manuale":None},
        {"nome":"BSKT/BARC 2028","ticker":"N/A","valuta":"EUR","prezzo_carico":97.09,"quantita":14,"categoria":"Certificati","prezzo_manuale":None},
        {"nome":"Von Expe 2027","ticker":"N/A","valuta":"EUR","prezzo_carico":980.84,"quantita":2,"categoria":"Certificati","prezzo_manuale":None},
        {"nome":"Von Expe 2029","ticker":"N/A","valuta":"EUR","prezzo_carico":99.10,"quantita":14,"categoria":"Certificati","prezzo_manuale":None},
        {"nome":"BTP 4.00% 2037","ticker":"N/A","valuta":"EUR","prezzo_carico":98.097,"quantita":7000,"categoria":"Obbligazioni","prezzo_manuale":None},
        {"nome":"BTP 4.45% 2043","ticker":"N/A","valuta":"EUR","prezzo_carico":100.140,"quantita":6000,"categoria":"Obbligazioni","prezzo_manuale":None},
        {"nome":"BTP 4.50% 2053","ticker":"N/A","valuta":"EUR","prezzo_carico":100.020,"quantita":6000,"categoria":"Obbligazioni","prezzo_manuale":None},
        {"nome":"BTP 4.15% 2039","ticker":"N/A","valuta":"EUR","prezzo_carico":98.409,"quantita":6000,"categoria":"Obbligazioni","prezzo_manuale":None},
        {"nome":"Romania 5.25% 2032","ticker":"N/A","valuta":"EUR","prezzo_carico":99.94,"quantita":1000,"categoria":"Obbligazioni","prezzo_manuale":None},
        {"nome":"USA T-Bond 4.00% 2030","ticker":"N/A","valuta":"USD","prezzo_carico":98.71,"quantita":6000,"categoria":"Obbligazioni","prezzo_manuale":None},
        {"nome":"Barclays 30GE45 100C","ticker":"N/A","valuta":"GBP","prezzo_carico":97.30,"quantita":1000,"categoria":"Obbligazioni","prezzo_manuale":None},
        {"nome":"CSIF MSCI USA Small Cap ESG","ticker":"CUSS.SW","valuta":"EUR","prezzo_carico":156.660,"quantita":14,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"Lyxor MSCI Emerging Markets","ticker":"LEM.PA","valuta":"EUR","prezzo_carico":13.183,"quantita":115,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"iShares MSCI World Value Factor","ticker":"IWVL.AS","valuta":"EUR","prezzo_carico":42.429,"quantita":36,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"iShares MSCI India","ticker":"NDIA.L","valuta":"EUR","prezzo_carico":8.594,"quantita":176,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"Xtrackers World Consumer Staples","ticker":"XCS6.DE","valuta":"EUR","prezzo_carico":43.306,"quantita":45,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"Xtrackers Healthcare","ticker":"XDWH.DE","valuta":"EUR","prezzo_carico":47.717,"quantita":38,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"Xtrackers II Global Gov. Bond","ticker":"XGSG.DE","valuta":"EUR","prezzo_carico":221.001,"quantita":18,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"iShares Core MSCI World","ticker":"SWDA.MI","valuta":"EUR","prezzo_carico":82.363,"quantita":53,"categoria":"ETF","prezzo_manuale":None},
        {"nome":"Ethereum (ETH)","ticker":"ETH-EUR","valuta":"USD","prezzo_carico":3099.44,"quantita":0.48,"categoria":"Crypto","prezzo_manuale":None},
        {"nome":"Bitcoin (BTC)","ticker":"BTC-EUR","valuta":"USD","prezzo_carico":56403.66,"quantita":0.26,"categoria":"Crypto","prezzo_manuale":None},
        {"nome":"Ripple (XRP)","ticker":"XRP-EUR","valuta":"USD","prezzo_carico":2.35,"quantita":638.87,"categoria":"Crypto","prezzo_manuale":None},
        {"nome":"Oro (Gold ETC)","ticker":"PHAU.MI","valuta":"EUR","prezzo_carico":1580.000,"quantita":0.47,"categoria":"Materie Prime","prezzo_manuale":None},
        {"nome":"WisdomTree Copper","ticker":"COPA.MI","valuta":"EUR","prezzo_carico":38.070,"quantita":27,"categoria":"Materie Prime","prezzo_manuale":None},
        {"nome":"WisdomTree Physical Gold","ticker":"PHGP.MI","valuta":"EUR","prezzo_carico":173.300,"quantita":21,"categoria":"Materie Prime","prezzo_manuale":None},
    ],
    "watchlist": [],
    "agent_cache": {}
}

def load_data():
    if DATA_FILE.exists():
        d = json.loads(DATA_FILE.read_text())
        if "agent_cache" not in d: d["agent_cache"] = {}
        return d
    return DEFAULT_DATA.copy()

def save_data(d):
    DATA_FILE.write_text(json.dumps(d, indent=2, ensure_ascii=False))

if "data" not in st.session_state:
    st.session_state.data = load_data()

# ── MARKET DATA ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_market_data():
    tickers = {"VIX":"^VIX","S&P 500":"^GSPC","FTSE MIB":"FTSEMIB.MI","Nasdaq":"^IXIC","EUR/USD":"EURUSD=X","Oro":"GC=F"}
    out = {}
    for name, t in tickers.items():
        try:
            h = yf.Ticker(t).history(period="5d")
            if len(h) >= 2:
                c, p = float(h["Close"].iloc[-1]), float(h["Close"].iloc[-2])
                out[name] = {"value": c, "delta": (c-p)/p*100}
            elif len(h) == 1:
                out[name] = {"value": float(h["Close"].iloc[-1]), "delta": 0}
            else:
                out[name] = {"value": 0, "delta": 0}
        except:
            out[name] = {"value": 0, "delta": 0}
    return out

@st.cache_data(ttl=300)
def get_fx_rates():
    pairs = {"USD":"EURUSD=X","GBP":"EURGBP=X","DKK":"EURDKK=X","CHF":"EURCHF=X"}
    fb = {"USD":1.08,"GBP":0.85,"DKK":7.46,"CHF":0.95}
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
    except:
        return None

def to_eur(amount, currency, fx):
    return amount if currency == "EUR" else amount / fx.get(currency, 1.0)

# ── PORTFOLIO ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_index_history():
    out = {}
    for name, t in {"S&P 500":"^GSPC","Nasdaq":"^IXIC","FTSE MIB":"FTSEMIB.MI"}.items():
        try:
            h = yf.Ticker(t).history(period="1mo")
            if not h.empty: out[name] = h["Close"]
        except: pass
    return out

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
        rows.append({
            "Nome": item["nome"], "Ticker": item["ticker"], "Categoria": cat, "Valuta": val,
            "P.Carico": pc, "P.Attuale": price_loc, "Fonte": src,
            "Quantità": qty, "CV €": cv_eur, "P&L €": pnl,
            "P&L %": (pnl/ca_eur*100) if ca_eur > 0 else 0
        })
    return pd.DataFrame(rows)

# ── TECHNICAL ANALYSIS ────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_technical(ticker):
    if ticker == "N/A": return None
    try:
        h = yf.Ticker(ticker).history(period="1y")
        if len(h) < 30: return None
        c = h["Close"]
        ma50  = c.rolling(50).mean().iloc[-1]  if len(c) >= 50  else None
        ma200 = c.rolling(200).mean().iloc[-1] if len(c) >= 200 else None
        price = float(c.iloc[-1])
        d = c.diff()
        rsi = float((100 - 100/(1 + d.clip(lower=0).rolling(14).mean()/(-d.clip(upper=0)).rolling(14).mean())).iloc[-1])
        ema12 = c.ewm(span=12).mean(); ema26 = c.ewm(span=26).mean()
        macd = ema12 - ema26; sig = macd.ewm(span=9).mean()
        macd_h = float((macd - sig).iloc[-1])
        boll_mid = c.rolling(20).mean(); boll_std = c.rolling(20).std()
        boll_up = float((boll_mid + 2*boll_std).iloc[-1]); boll_dn = float((boll_mid - 2*boll_std).iloc[-1])
        support = float(c.rolling(20).min().iloc[-1]); resistance = float(c.rolling(20).max().iloc[-1])
        cross = None
        if ma50 and ma200:
            p50 = c.rolling(50).mean().iloc[-2]; p200 = c.rolling(200).mean().iloc[-2]
            if p50 < p200 and ma50 >= ma200: cross = "golden"
            elif p50 > p200 and ma50 <= ma200: cross = "death"
        vol_avg = float(h["Volume"].rolling(20).mean().iloc[-1]) if "Volume" in h else 0
        vol_cur = float(h["Volume"].iloc[-1]) if "Volume" in h else 0
        return {"price":price,"ma50":float(ma50) if ma50 else None,"ma200":float(ma200) if ma200 else None,
                "rsi":rsi,"macd_h":macd_h,"boll_up":boll_up,"boll_dn":boll_dn,
                "support":support,"resistance":resistance,"cross":cross,
                "vol_ratio": vol_cur/vol_avg if vol_avg > 0 else 1.0,
                "history":h}
    except: return None

def tech_signal(td):
    if not td: return "⚪","N/D","Dati non disponibili"
    score = 0; reasons = []
    if td["ma50"] and td["price"] > td["ma50"]: score+=1; reasons.append(f"▲ MA50")
    elif td["ma50"]: score-=1; reasons.append(f"▼ MA50")
    if td["ma200"] and td["price"] > td["ma200"]: score+=2; reasons.append(f"▲ MA200")
    elif td["ma200"]: score-=2; reasons.append(f"▼ MA200")
    if td["cross"] == "golden": score+=2; reasons.append("Golden Cross 🌟")
    elif td["cross"] == "death": score-=2; reasons.append("Death Cross ⚠️")
    r = td["rsi"]
    if r > 70: score-=1; reasons.append(f"RSI {r:.0f} ipercomprato")
    elif r < 30: score+=1; reasons.append(f"RSI {r:.0f} ipervenduto")
    else: reasons.append(f"RSI {r:.0f}")
    if td["macd_h"] > 0: score+=1; reasons.append("MACD ↑")
    else: score-=1; reasons.append("MACD ↓")
    if td["price"] > td["boll_up"]: score-=1; reasons.append("Sopra Boll.sup")
    elif td["price"] < td["boll_dn"]: score+=1; reasons.append("Sotto Boll.inf")
    if td["vol_ratio"] > 1.5: reasons.append(f"Volume ×{td['vol_ratio']:.1f}")
    if score >= 3: return "🟢","INCREMENTA",", ".join(reasons[:4])
    elif score >= 1: return "🟡","TIENI",", ".join(reasons[:4])
    elif score >= -1: return "🟡","ATTENZIONE",", ".join(reasons[:4])
    else: return "🔴","ALLEGGERISCI",", ".join(reasons[:4])

@st.cache_data(ttl=3600)
def get_correlation(tickers_tuple):
    try:
        data = {}
        for name, ticker in tickers_tuple:
            h = yf.Ticker(ticker).history(period="6mo")
            if not h.empty: data[name[:12]] = h["Close"].pct_change()
        if len(data) < 2: return None
        return pd.DataFrame(data).dropna().corr()
    except: return None

@st.cache_data(ttl=3600)
def get_news(api_key, query="economy inflation market geopolitics", days=2):
    if not api_key: return []
    try:
        from_dt = (datetime.now()-timedelta(days=days)).strftime("%Y-%m-%d")
        r = requests.get(f"https://newsapi.org/v2/everything?q={query}&from={from_dt}&sortBy=relevancy&language=en&pageSize=20&apiKey={api_key}", timeout=10)
        return [{"title":a["title"],"description":a.get("description",""),"source":a["source"]["name"],"url":a["url"]} for a in r.json().get("articles",[])[:15]]
    except: return []

# ── MULTI-AGENT AI ────────────────────────────────────────────────────────────
def call_agent(client, system_prompt, user_prompt, max_tokens=800):
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role":"user","content":user_prompt}]
        )
        return msg.content[0].text
    except Exception as e:
        return f"Errore agente: {e}"

def run_multi_agent_analysis(api_key, portfolio_df, market_data, watchlist, news_items):
    client = anthropic.Anthropic(api_key=api_key)
    results = {}
    progress = st.progress(0)
    status_box = st.empty()

    # ── AGENT 1: MACRO ────────────────────────────────────────────────────────
    status_box.markdown('<div class="agent-card"><span class="agent-tag" style="color:#10B981;">▶ AGENTE 1/5</span> <b>Analista Macro</b> — analizza contesto economico globale...</div>', unsafe_allow_html=True)
    vix = market_data.get("VIX",{}).get("value",20)
    sp500 = market_data.get("S&P 500",{}).get("delta",0)
    news_text = "\n".join([f"- {n['title']}" for n in news_items[:10]]) if news_items else "Notizie non disponibili"
    results["macro"] = call_agent(client,
        "Sei un economista macro di livello istituzionale. Analisi concise, dati precisi, outlook chiaro.",
        f"""DATI MERCATO: VIX={vix:.1f}, S&P500={sp500:+.2f}%, EUR/USD={market_data.get('EUR/USD',{}).get('value',1.08):.4f}
NOTIZIE: {news_text}
Fornisci: 1) Regime macro attuale (risk-on/off) 2) 3 rischi principali 3) 3 opportunità macro 4) Impatto su: azioni EU, azioni USA, obbligazioni, crypto, materie prime. Max 300 parole, in italiano.""")
    progress.progress(20)

    # ── AGENT 2: TECHNICAL ────────────────────────────────────────────────────
    status_box.markdown('<div class="agent-card"><span class="agent-tag" style="color:#3B82F6;">▶ AGENTE 2/5</span> <b>Analista Tecnico</b> — scansiona tutti i titoli...</div>', unsafe_allow_html=True)
    tradeable = [(r["Nome"], r["Ticker"]) for _, r in portfolio_df.iterrows() if r["Ticker"] != "N/A"]
    tech_summary = []
    for nome, ticker in tradeable[:12]:
        td = get_technical(ticker)
        if td:
            emoji, label, reason = tech_signal(td)
            tech_summary.append(f"{nome} ({ticker}): {label} | RSI={td['rsi']:.0f} | MACD_H={td['macd_h']:+.3f} | {reason}")
    results["tecnica"] = call_agent(client,
        "Sei un analista tecnico senior con 20 anni di esperienza su mercati globali. Pattern recognition, livelli chiave, momentum.",
        f"""ANALISI TECNICA PORTAFOGLIO:
{chr(10).join(tech_summary)}
Fornisci: 1) Top 3 titoli con setup tecnico più forte (BUY) 2) Top 3 titoli con segnali di deterioramento (cautela/uscita) 3) Pattern di mercato generale che emerge 4) Livelli chiave da monitorare. Max 300 parole, in italiano.""")
    progress.progress(40)

    # ── AGENT 3: RISK ─────────────────────────────────────────────────────────
    status_box.markdown('<div class="agent-card"><span class="agent-tag" style="color:#F59E0B;">▶ AGENTE 3/5</span> <b>Risk Manager</b> — valuta esposizione e concentrazione...</div>', unsafe_allow_html=True)
    alloc = portfolio_df.groupby("Categoria")["CV €"].sum()
    total = alloc.sum()
    alloc_str = "\n".join([f"- {cat}: €{v:,.0f} ({v/total*100:.1f}%)" for cat, v in alloc.items()])
    fx = get_fx_rates()
    val_exp = portfolio_df.groupby("Valuta")["CV €"].sum()
    val_str = "\n".join([f"- {v}: €{amt:,.0f} ({amt/total*100:.1f}%)" for v, amt in val_exp.items()])
    top3 = portfolio_df.nlargest(3,"CV €")[["Nome","CV €"]].to_string(index=False)
    results["rischio"] = call_agent(client,
        "Sei un risk manager istituzionale. Identifica rischi di concentrazione, correlazione, valuta e liquidità.",
        f"""PORTAFOGLIO TOTALE: €{total:,.0f}
ALLOCAZIONE PER CATEGORIA:\n{alloc_str}
ESPOSIZIONE VALUTARIA:\n{val_str}
TOP 3 POSIZIONI:\n{top3}
VIX: {vix:.1f}
Fornisci: 1) Livello di rischio complessivo (1-10) con motivazione 2) Principali rischi di concentrazione 3) Rischio valutario 4) Raccomandazioni di ribilanciamento specifiche 5) Hedging suggerito. Max 300 parole, in italiano.""")
    progress.progress(60)

    # ── AGENT 4: SENTIMENT ────────────────────────────────────────────────────
    status_box.markdown('<div class="agent-card"><span class="agent-tag" style="color:#8B5CF6;">▶ AGENTE 4/5</span> <b>Sentiment Analyst</b> — legge il sentiment di mercato...</div>', unsafe_allow_html=True)
    results["sentiment"] = call_agent(client,
        "Sei un esperto di sentiment analysis e behavioral finance. Leggi il mercato attraverso il comportamento degli investitori.",
        f"""VIX: {vix:.1f} ({'paura elevata' if vix > 25 else 'calmo' if vix < 15 else 'neutro'})
S&P500 oggi: {sp500:+.2f}%
NOTIZIE RECENTI:\n{news_text}
Fornisci: 1) Sentiment attuale (Fear/Greed index stimato 0-100) 2) Posizionamento degli investitori istituzionali 3) Rischi comportamentali per il portafoglio 4) Opportunità contrarian. Max 250 parole, in italiano.""")
    progress.progress(80)

    # ── AGENT 5: PORTFOLIO OPTIMIZER ──────────────────────────────────────────
    status_box.markdown('<div class="agent-card"><span class="agent-tag" style="color:#F97316;">▶ AGENTE 5/5</span> <b>Portfolio Optimizer</b> — genera raccomandazioni finali...</div>', unsafe_allow_html=True)
    watchlist_str = "\n".join([f"- {w['ticker']} ({w['nome']}): {w['segnale']} | Target: {w.get('prezzo_target')} | {w.get('note','')}" for w in watchlist]) if watchlist else "Nessun titolo in watchlist"
    results["ottimizzazione"] = call_agent(client,
        "Sei il gestore di un family office con AUM di €500M. Combini macro, tecnica, rischio e sentiment per raccomandazioni azionabili.",
        f"""SINTESI AGENTI PRECEDENTI:
MACRO: {results['macro'][:400]}
TECNICA: {results['tecnica'][:400]}
RISCHIO: {results['rischio'][:400]}
SENTIMENT: {results['sentiment'][:300]}
WATCHLIST: {watchlist_str}
Fornisci il piano operativo finale:
1) VENDI SUBITO: titoli da liquidare con motivazione
2) RIDUCI: posizioni da alleggerire del 30-50%
3) TIENI: posizioni da mantenere invariate
4) INCREMENTA: posizioni da aumentare con % suggerita
5) NUOVI ACQUISTI: 3-5 nuovi titoli/ETF con ticker, prezzo ingresso, target, stop, orizzonte
6) ASSET ALLOCATION TARGET suggerita per i prossimi 3 mesi
Max 500 parole, in italiano. Sii specifico con i numeri.""", max_tokens=1200)
    progress.progress(100)
    status_box.empty()
    progress.empty()
    return results

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Impostazioni")
    anthropic_key = st.text_input("Chiave Anthropic API", type="password", placeholder="sk-ant-...", key="ant_key")
    news_api_key  = st.text_input("Chiave NewsAPI", type="password", placeholder="newsapi key...", key="news_key")
    st.markdown("---")
    now = datetime.now()
    st.markdown(f"**{now.strftime('%A %d %B %Y')}**")
    st.markdown(f"**Ore:** {now.strftime('%H:%M')}")
    st.markdown(f"**Asset:** {len(st.session_state.data['portfolio'])}")
    st.markdown(f"**Watchlist:** {len(st.session_state.data['watchlist'])}")
    st.markdown("---")
    if st.button("🔄 Aggiorna dati", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── HEADER ────────────────────────────────────────────────────────────────────
mkt = get_market_data()
vix_now = mkt.get("VIX",{}).get("value",20)
vix_color = "#EF4444" if vix_now > 25 else "#F59E0B" if vix_now > 15 else "#10B981"

st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;padding-bottom:.8rem;border-bottom:1px solid #1E2D47;">
  <div style="display:flex;align-items:center;gap:10px;">
    <span style="font-size:1.4rem;">📈</span>
    <div>
      <div style="font-size:1.1rem;font-weight:700;letter-spacing:-.02em;">Investment Intelligence</div>
      <div style="font-size:.72rem;color:#64748B;font-family:'JetBrains Mono',monospace;">Sistema Multi-Agente AI — Portafoglio Personale</div>
    </div>
  </div>
  <div style="display:flex;gap:1.5rem;align-items:center;">
    <div style="text-align:center;">
      <div style="font-size:.65rem;color:#64748B;text-transform:uppercase;letter-spacing:.08em;">VIX</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;color:{vix_color};font-size:1rem;">{vix_now:.1f}</div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:.65rem;color:#64748B;text-transform:uppercase;letter-spacing:.08em;">S&P 500</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;color:{'#10B981' if mkt.get('S&P 500',{}).get('delta',0)>=0 else '#EF4444'};font-size:1rem;">{mkt.get('S&P 500',{}).get('delta',0):+.2f}%</div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:.65rem;color:#64748B;text-transform:uppercase;letter-spacing:.08em;">EUR/USD</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;font-size:1rem;">{mkt.get('EUR/USD',{}).get('value',1.08):.4f}</div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:.65rem;color:#64748B;text-transform:uppercase;letter-spacing:.08em;">FTSE MIB</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;color:{'#10B981' if mkt.get('FTSE MIB',{}).get('delta',0)>=0 else '#EF4444'};font-size:1rem;">{mkt.get('FTSE MIB',{}).get('delta',0):+.2f}%</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1,tab2,tab3,tab4,tab5,tab6 = st.tabs(["🌍 Mercati","💼 Portafoglio","📡 Tecnica & Rischio","🤖 Analisi Multi-Agente","👁️ Watchlist","✏️ Gestione"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — MERCATI
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-hd">Panoramica mercati</div>', unsafe_allow_html=True)
    cols = st.columns(6)
    for i,(name,d) in enumerate(mkt.items()):
        with cols[i]:
            sign = "▲" if d["delta"]>=0 else "▼"
            dc = "up" if d["delta"]>=0 else "dn"
            st.markdown(f"""<div class="kpi-card"><div class="kpi-label">{name}</div>
<div class="kpi-value">{d['value']:,.2f}</div>
<div class="kpi-delta {dc}">{sign} {abs(d['delta']):.2f}%</div></div>""", unsafe_allow_html=True)

    c1,c2 = st.columns([1,2])
    with c1:
        st.markdown('<div class="section-hd">Indice VIX — Fear & Greed</div>', unsafe_allow_html=True)
        fig_vix = go.Figure(go.Indicator(mode="gauge+number", value=vix_now,
            gauge={"axis":{"range":[0,80],"tickcolor":"#64748B"},"bar":{"color":"#3B82F6"},
                   "steps":[{"range":[0,15],"color":"rgba(16,185,129,.2)"},{"range":[15,25],"color":"rgba(245,158,11,.2)"},{"range":[25,80],"color":"rgba(239,68,68,.2)"}]},
            number={"font":{"color":"#E8EDF5","family":"JetBrains Mono"}}))
        fig_vix.update_layout(paper_bgcolor="rgba(0,0,0,0)",font_color="#E8EDF5",height=200,margin=dict(t=20,b=0,l=20,r=20))
        st.plotly_chart(fig_vix, use_container_width=True)
        vix_label = ("🟢 Calmo — mercato ottimista","#10B981") if vix_now<15 else (("🟡 Moderato — attenzione ai rischi","#F59E0B") if vix_now<25 else ("🔴 Paura — opportunità contrarian","#EF4444"))
        st.markdown(f'<div style="text-align:center;font-size:.82rem;color:{vix_label[1]};font-weight:600;margin-top:-.5rem;">{vix_label[0]}</div>',unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="section-hd">Andamento indici — 1 mese (normalizzato %)</div>', unsafe_allow_html=True)
        idx_data = get_index_history()
        if idx_data:
            fig_idx = go.Figure()
            for i,(name,s) in enumerate(idx_data.items()):
                norm = (s/s.iloc[0]-1)*100
                fig_idx.add_trace(go.Scatter(x=s.index,y=norm,name=name,line=dict(color=["#3B82F6","#10B981","#F59E0B"][i],width=2)))
            fig_idx.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(22,32,53,.6)",font_color="#E8EDF5",
                xaxis=dict(gridcolor="#1E2D47",color="#64748B"),yaxis=dict(gridcolor="#1E2D47",ticksuffix="%"),
                legend=dict(bgcolor="rgba(0,0,0,0)",orientation="h",yanchor="bottom",y=1.02),height=230,margin=dict(t=10,b=10))
            st.plotly_chart(fig_idx, use_container_width=True)

    # Stagionalità
    st.markdown('<div class="section-hd">Stagionalità — pattern storici di marzo</div>', unsafe_allow_html=True)
    hints = [
        ("Azionario","Correzioni tipiche a marzo. Attenzione ai rimbalzi tecnici dopo sell-off.","#F59E0B"),
        ("Obbligazioni","Fed meeting in arrivo — volatilità sui tassi. Favorire duration breve.","#F59E0B"),
        ("Oro","Storicamente forte Q1. Funzione di hedging attiva in periodi di incertezza.","#10B981"),
        ("Crypto","Alta volatilità stagionale. Q2 storicamente più debole di Q1.","#EF4444"),
    ]
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
    best = df.nlargest(1,"P&L %").iloc[0]
    worst = df.nsmallest(1,"P&L %").iloc[0]

    # FX bar
    fx_parts = " · ".join([f"{k}/EUR: <b style='color:#E8EDF5'>{v:.4f}</b>" for k,v in fx.items() if k!="EUR"])
    st.markdown(f'<div style="background:#0F1829;border:1px solid #243352;border-radius:8px;padding:.5rem 1rem;font-size:.75rem;color:#64748B;margin-bottom:.8rem;">💱 Cambi live — {fx_parts} · Tutti i valori in EUR</div>', unsafe_allow_html=True)

    k1,k2,k3,k4 = st.columns(4)
    with k1: st.metric("💼 Totale portafoglio",f"€ {total:,.0f}")
    with k2: st.metric("📈 P&L totale",f"€ {pnl_tot:,.0f}",f"{pnl_pct:+.2f}%")
    with k3: st.metric("🏆 Best performer",best["Nome"][:18],f"{best['P&L %']:+.1f}%")
    with k4: st.metric("⚠️ Worst performer",worst["Nome"][:18],f"{worst['P&L %']:+.1f}%")

    c1,c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-hd">Allocazione per categoria</div>', unsafe_allow_html=True)
        alloc = df.groupby("Categoria")["CV €"].sum().reset_index()
        fig_pie = go.Figure(go.Pie(labels=alloc["Categoria"],values=alloc["CV €"],hole=.55,
            marker_colors=[CATEGORY_COLORS.get(c,"#64748B") for c in alloc["Categoria"]],
            hovertemplate="%{label}<br>€ %{value:,.0f}<br>%{percent}<extra></extra>"))
        fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)",font_color="#E8EDF5",showlegend=True,
            legend=dict(bgcolor="rgba(0,0,0,0)",font_size=10),height=280,margin=dict(t=0,b=0))
        st.plotly_chart(fig_pie,use_container_width=True)
    with c2:
        st.markdown('<div class="section-hd">P&L per posizione</div>', unsafe_allow_html=True)
        ds = df.sort_values("P&L €")
        fig_bar = go.Figure(go.Bar(x=ds["P&L €"],y=ds["Nome"].str[:18],orientation="h",
            marker_color=["#EF4444" if x<0 else "#10B981" for x in ds["P&L €"]],
            hovertemplate="%{y}<br>€ %{x:,.0f}<extra></extra>"))
        fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(22,32,53,.6)",font_color="#E8EDF5",
            xaxis=dict(gridcolor="#1E2D47",tickprefix="€"),yaxis=dict(tickfont_size=9),height=280,margin=dict(t=0,b=0,l=5))
        st.plotly_chart(fig_bar,use_container_width=True)

    # Esposizione valutaria
    st.markdown('<div class="section-hd">Esposizione valutaria</div>', unsafe_allow_html=True)
    val_exp = df.groupby("Valuta")["CV €"].sum()
    vc = st.columns(len(val_exp))
    vcols = {"EUR":"#10B981","USD":"#3B82F6","GBP":"#F59E0B","DKK":"#8B5CF6"}
    for i,(v,amt) in enumerate(val_exp.items()):
        with vc[i]:
            c = vcols.get(v,"#64748B")
            st.markdown(f"""<div style="background:{c}12;border:1px solid {c}33;border-radius:10px;padding:.8rem;text-align:center;">
<div style="font-family:'JetBrains Mono',monospace;font-weight:700;color:{c};font-size:1.1rem;">{v}</div>
<div style="font-weight:600;color:#E8EDF5;">€ {amt:,.0f}</div>
<div style="font-size:.75rem;color:#64748B;">{amt/total*100:.1f}%</div></div>""", unsafe_allow_html=True)

    # Table
    st.markdown('<div class="section-hd">Dettaglio posizioni</div>', unsafe_allow_html=True)
    src_map = {"live":"🔵 live","carico":"🟡 carico","manuale":"✏️ manuale"}
    disp = df.copy()
    disp["CV €"] = disp["CV €"].apply(lambda x: f"€ {x:,.0f}")
    disp["P&L €"] = disp["P&L €"].apply(lambda x: f"€ {x:+,.0f}")
    disp["P&L %"] = disp["P&L %"].apply(lambda x: f"{x:+.2f}%")
    disp["P.Carico"] = disp["P.Carico"].apply(lambda x: f"{x:,.3f}")
    disp["P.Attuale"] = disp["P.Attuale"].apply(lambda x: f"{x:,.3f}")
    disp["Fonte"] = disp["Fonte"].map(src_map)
    st.dataframe(disp[["Nome","Categoria","Valuta","P.Carico","P.Attuale","Fonte","Quantità","CV €","P&L €","P&L %"]],
        use_container_width=True, hide_index=True, height=380)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — TECNICA & RISCHIO
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-hd">Semaforo tecnico — tutte le posizioni</div>', unsafe_allow_html=True)

    # Legenda indicatori
    with st.expander("📖 Legenda indicatori tecnici — clicca per leggere"):
        l1,l2,l3 = st.columns(3)
        with l1:
            st.markdown("""<div class="tooltip-box"><b>RSI — Relative Strength Index</b><br>
Misura la velocità e intensità dei movimenti di prezzo. Va da 0 a 100.<br>
• <span style="color:#EF4444">RSI &gt; 70</span> = ipercomprato (titolo salito troppo, rischio correzione)<br>
• <span style="color:#10B981">RSI &lt; 30</span> = ipervenduto (titolo sceso troppo, possibile rimbalzo)<br>
• RSI 40-60 = zona neutrale, nessun segnale estremo</div>""", unsafe_allow_html=True)
            st.markdown("""<div class="tooltip-box" style="margin-top:.5rem;"><b>MA50 / MA200 — Medie Mobili</b><br>
La media dei prezzi degli ultimi 50 o 200 giorni di borsa.<br>
• Prezzo sopra MA50 = trend di breve positivo<br>
• Prezzo sopra MA200 = trend di lungo positivo<br>
• Entrambe in ordine (MA50 &gt; MA200) = trend solido</div>""", unsafe_allow_html=True)
        with l2:
            st.markdown("""<div class="tooltip-box"><b>MACD — Moving Average Convergence Divergence</b><br>
Misura la differenza tra due medie mobili esponenziali (12 e 26 giorni).<br>
• MACD Histogram &gt; 0 = momentum positivo, forza crescente<br>
• MACD Histogram &lt; 0 = momentum negativo, forza calante<br>
• Più grande è il valore, più forte è il segnale</div>""", unsafe_allow_html=True)
            st.markdown("""<div class="tooltip-box" style="margin-top:.5rem;"><b>Golden Cross / Death Cross</b><br>
Segnali rari ma molto significativi.<br>
• <span style="color:#F59E0B">Golden Cross 🌟</span> = MA50 supera MA200 dal basso → forte segnale rialzista<br>
• <span style="color:#EF4444">Death Cross ⚠️</span> = MA50 scende sotto MA200 → forte segnale ribassista<br>
• Usato da fondi istituzionali come filtro di trend</div>""", unsafe_allow_html=True)
        with l3:
            st.markdown("""<div class="tooltip-box"><b>Bande di Bollinger</b><br>
Canale statistico attorno al prezzo (media ± 2 deviazioni standard).<br>
• Prezzo sopra banda superiore = possibile ipercomprato<br>
• Prezzo sotto banda inferiore = possibile ipervenduto<br>
• Bande strette = bassa volatilità, spesso precede un movimento forte</div>""", unsafe_allow_html=True)
            st.markdown("""<div class="tooltip-box" style="margin-top:.5rem;"><b>Supporto / Resistenza</b><br>
Livelli di prezzo dove il titolo ha storicamente rimbalzato (supporto) o si è fermato (resistenza).<br>
• Supporto = pavimento del prezzo, zona di acquisto<br>
• Resistenza = soffitto del prezzo, zona di vendita<br>
• Una resistenza rotta diventa supporto e viceversa</div>""", unsafe_allow_html=True)

        st.markdown("""<div class="tooltip-box" style="margin-top:.5rem;">
<b>Come leggere il semaforo</b><br>
🟢 <b>INCREMENTA</b> — multipli indicatori allineati al rialzo (score ≥ 3)<br>
🟡 <b>TIENI / ATTENZIONE</b> — segnali misti, nessuna azione urgente (score -1/+2)<br>
🔴 <b>ALLEGGERISCI</b> — multipli indicatori deteriorati (score ≤ -2)<br>
⚪ <b>N/D</b> — asset senza ticker (obbligazioni, certificati): inserisci prezzo manuale in Gestione</div>""", unsafe_allow_html=True)

    tradeable_items = [p for p in st.session_state.data["portfolio"] if p["ticker"] != "N/A"]
    non_tradeable = [p for p in st.session_state.data["portfolio"] if p["ticker"] == "N/A"]

    tech_rows = []
    with st.spinner("Calcolo indicatori..."):
        for item in tradeable_items:
            td = get_technical(item["ticker"])
            em, label, reason = tech_signal(td)
            tech_rows.append({
                "Segnale": em, "Nome": item["nome"][:22], "Ticker": item["ticker"],
                "Raccomandazione": label,
                "RSI": f"{td['rsi']:.0f}" if td else "—",
                "MACD Hist": f"{td['macd_h']:+.3f}" if td else "—",
                "MA50": f"{td['ma50']:,.2f}" if td and td["ma50"] else "—",
                "MA200": f"{td['ma200']:,.2f}" if td and td["ma200"] else "—",
                "Cross": ("🌟 Golden" if td["cross"]=="golden" else "💀 Death") if td and td["cross"] else "—",
                "Vol×": f"{td['vol_ratio']:.1f}x" if td else "—",
                "Motivazione": reason,
            })
    if tech_rows:
        st.dataframe(pd.DataFrame(tech_rows), use_container_width=True, hide_index=True, height=380)

    # Assets senza ticker
    if non_tradeable:
        st.markdown('<div class="section-hd">Asset senza prezzo automatico — aggiornamento manuale richiesto</div>', unsafe_allow_html=True)
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
{'✏️ Manuale: ' + f"{pm:,.3f}" if ok else '🔴 Prezzo non inserito → vai in Gestione'}</div></div>""", unsafe_allow_html=True)

    # Grafico tecnico singolo
    st.markdown('<div class="section-hd">Grafico tecnico dettagliato</div>', unsafe_allow_html=True)
    t_names = [p["nome"] for p in tradeable_items]
    t_tickers = [p["ticker"] for p in tradeable_items]
    sel = st.selectbox("Seleziona titolo", range(len(t_names)), format_func=lambda i: f"{t_names[i]} ({t_tickers[i]})", key="sel_chart")
    if sel is not None:
        td = get_technical(t_tickers[sel])
        if td and "history" in td:
            h = td["history"]; c = h["Close"]
            fig_c = go.Figure()
            fig_c.add_trace(go.Candlestick(x=h.index,open=h["Open"],high=h["High"],low=h["Low"],close=c,name="Prezzo",
                increasing_line_color="#10B981",decreasing_line_color="#EF4444"))
            if td["ma50"]: fig_c.add_trace(go.Scatter(x=h.index,y=c.rolling(50).mean(),name="MA50",line=dict(color="#F59E0B",width=1.5,dash="dot")))
            if td["ma200"]: fig_c.add_trace(go.Scatter(x=h.index,y=c.rolling(200).mean(),name="MA200",line=dict(color="#8B5CF6",width=1.5,dash="dash")))
            bm = c.rolling(20).mean(); bs = c.rolling(20).std()
            fig_c.add_trace(go.Scatter(x=h.index,y=bm+2*bs,name="Boll.Sup",line=dict(color="#3B82F6",width=1,dash="dot"),opacity=.6))
            fig_c.add_trace(go.Scatter(x=h.index,y=bm-2*bs,name="Boll.Inf",line=dict(color="#3B82F6",width=1,dash="dot"),fill="tonexty",fillcolor="rgba(59,130,246,.05)",opacity=.6))
            fig_c.add_hline(y=td["support"],line_color="#10B981",line_dash="dot",annotation_text=f"Supporto {td['support']:.2f}",annotation_font_color="#10B981")
            fig_c.add_hline(y=td["resistance"],line_color="#EF4444",line_dash="dot",annotation_text=f"Resistenza {td['resistance']:.2f}",annotation_font_color="#EF4444")
            fig_c.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(22,32,53,.8)",font_color="#E8EDF5",
                xaxis_rangeslider_visible=False,xaxis=dict(gridcolor="#1E2D47"),yaxis=dict(gridcolor="#1E2D47"),
                legend=dict(bgcolor="rgba(0,0,0,0)",orientation="h"),height=360,margin=dict(t=5,b=5))
            st.plotly_chart(fig_c,use_container_width=True)
            # RSI
            d = c.diff(); rsi_s = 100-100/(1+d.clip(lower=0).rolling(14).mean()/(-d.clip(upper=0)).rolling(14).mean())
            fig_rsi = go.Figure(go.Scatter(x=h.index,y=rsi_s,line=dict(color="#3B82F6",width=2),fill="tonexty",fillcolor="rgba(59,130,246,.08)"))
            fig_rsi.add_hline(y=70,line_color="#EF4444",line_dash="dot",annotation_text="Ipercomprato 70")
            fig_rsi.add_hline(y=30,line_color="#10B981",line_dash="dot",annotation_text="Ipervenduto 30")
            fig_rsi.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(22,32,53,.8)",font_color="#E8EDF5",
                xaxis=dict(gridcolor="#1E2D47"),yaxis=dict(gridcolor="#1E2D47",range=[0,100]),height=150,margin=dict(t=0,b=5),showlegend=False)
            st.plotly_chart(fig_rsi,use_container_width=True)

    # Risk Management
    st.markdown('<div class="section-hd">Risk management</div>', unsafe_allow_html=True)
    df2 = build_portfolio_df()
    r1,r2 = st.columns(2)
    with r1:
        st.markdown("**Peso % per posizione**")
        dw = df2[["Nome","Categoria","CV €"]].copy()
        dw["Peso %"] = dw["CV €"]/dw["CV €"].sum()*100
        dw = dw.sort_values("Peso %",ascending=False)
        fig_w = go.Figure(go.Bar(x=dw["Nome"].str[:16],y=dw["Peso %"],
            marker_color=[CATEGORY_COLORS.get(c,"#64748B") for c in dw["Categoria"]],
            hovertemplate="%{x}<br>%{y:.1f}%<extra></extra>"))
        fig_w.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(22,32,53,.6)",font_color="#E8EDF5",
            xaxis=dict(tickangle=-40,gridcolor="#1E2D47",tickfont_size=9),yaxis=dict(gridcolor="#1E2D47",ticksuffix="%"),
            height=260,margin=dict(t=5,b=70))
        st.plotly_chart(fig_w,use_container_width=True)
        top3 = dw.head(3)["Peso %"].sum()
        if top3 > 40: st.warning(f"⚠️ Top 3 posizioni = {top3:.1f}% del portafoglio — concentrazione elevata")
    with r2:
        st.markdown("**Heatmap correlazioni (6 mesi)**")
        valid_t = tuple((p["nome"][:12],p["ticker"]) for p in tradeable_items[:14])
        corr = get_correlation(valid_t)
        if corr is not None:
            fig_h = go.Figure(go.Heatmap(z=corr.values,x=corr.columns,y=corr.index,
                colorscale=[[0,"#EF4444"],[0.5,"#162035"],[1,"#10B981"]],zmid=0,zmin=-1,zmax=1,
                text=corr.round(2).values,texttemplate="%{text}",
                hovertemplate="%{x}/%{y}<br>Corr: %{z:.2f}<extra></extra>"))
            fig_h.update_layout(paper_bgcolor="rgba(0,0,0,0)",font_color="#E8EDF5",font_size=8,height=260,margin=dict(t=5,b=5))
            st.plotly_chart(fig_h,use_container_width=True)
            st.caption("🟢 Correlazione alta = si muovono insieme (meno diversificazione) | 🔴 Negativa = hedging naturale")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — MULTI-AGENT AI
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    if not anthropic_key:
        st.warning("⚠️ Inserisci la chiave Anthropic API nella sidebar per attivare il sistema multi-agente.")
        st.markdown("""<div class="ai-block">
<b>Come funziona il sistema multi-agente:</b><br><br>
🔵 <b>Agente Macro</b> — Analizza il contesto economico globale (inflazione, tassi, geopolitica) e definisce il regime di mercato<br>
🔵 <b>Agente Tecnico</b> — Scansiona tutti i titoli del portafoglio e identifica i setup tecnici migliori e peggiori<br>
🟡 <b>Agente Rischio</b> — Valuta concentrazione, esposizione valutaria, drawdown e suggerisce ribilanciamento<br>
🟣 <b>Agente Sentiment</b> — Legge il Fear & Greed Index, il posizionamento istituzionale e i rischi comportamentali<br>
🟠 <b>Agente Portfolio Optimizer</b> — Combina tutti gli input e genera il piano operativo finale con acquisti, vendite e nuove opportunità</div>""", unsafe_allow_html=True)
    else:
        df_ai = build_portfolio_df()
        news = get_news(news_api_key) if news_api_key else []
        cache = st.session_state.data.get("agent_cache", {})
        cache_date = cache.get("date","")
        today = datetime.now().strftime("%Y-%m-%d")
        cache_valid = cache_date == today and "results" in cache

        col_btn1, col_btn2 = st.columns([2,3])
        with col_btn1:
            run_btn = st.button("🚀 Avvia analisi multi-agente completa", use_container_width=True)
        with col_btn2:
            if cache_valid:
                st.markdown(f'<div style="padding:.45rem .8rem;font-size:.8rem;color:#10B981;">✅ Analisi di oggi già disponibile — aggiornata alle {cache.get("time","—")}</div>', unsafe_allow_html=True)

        if run_btn:
            with st.spinner(""):
                results = run_multi_agent_analysis(anthropic_key, df_ai, mkt, st.session_state.data["watchlist"], news)
                st.session_state.data["agent_cache"] = {"date": today, "time": datetime.now().strftime("%H:%M"), "results": results}
                save_data(st.session_state.data)
                cache_valid = True
                cache = st.session_state.data["agent_cache"]

        if cache_valid:
            results = cache["results"]
            agent_tabs = st.tabs(["🌍 Macro","📡 Tecnica","⚖️ Rischio","🧠 Sentiment","🎯 Piano Operativo"])
            labels = ["macro","tecnica","rischio","sentiment","ottimizzazione"]
            icons = ["🌍","📡","⚖️","🧠","🎯"]
            for i, (at, lbl) in enumerate(zip(agent_tabs, labels)):
                with at:
                    st.markdown(f'<div class="ai-block">{results.get(lbl,"Dati non disponibili")}</div>', unsafe_allow_html=True)

        # News section
        if news:
            st.markdown('<div class="section-hd">Radar notizie economiche</div>', unsafe_allow_html=True)
            nc = st.columns(3)
            for i, n in enumerate(news[:9]):
                with nc[i%3]:
                    st.markdown(f"""<div style="background:#0F1829;border:1px solid #1E2D47;border-radius:8px;padding:.8rem;margin-bottom:.5rem;min-height:110px;">
<div style="font-size:.7rem;color:#3B82F6;font-weight:600;margin-bottom:.3rem;">{n['source']}</div>
<div style="font-size:.78rem;color:#E8EDF5;line-height:1.4;font-weight:500;">{n['title'][:100]}{'...' if len(n['title'])>100 else ''}</div></div>""", unsafe_allow_html=True)
        elif not news_api_key:
            st.info("Inserisci la chiave NewsAPI nella sidebar per vedere le notizie.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — WATCHLIST
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    watchlist = st.session_state.data["watchlist"]
    buy_c = sum(1 for w in watchlist if w["segnale"]=="COMPRA")
    mon_c = sum(1 for w in watchlist if w["segnale"]=="MONITORA")
    sel_c = sum(1 for w in watchlist if w["segnale"]=="VENDI")

    sb1,sb2,sb3 = st.columns(3)
    for col,(cnt,label,color) in zip([sb1,sb2,sb3],[(buy_c,"🟢 Da comprare","#10B981"),(mon_c,"🟡 Monitorare","#F59E0B"),(sel_c,"🔴 Da vendere","#EF4444")]):
        with col:
            st.markdown(f"""<div style="background:{color}12;border:1px solid {color}33;border-radius:10px;padding:.8rem;text-align:center;">
<div style="font-size:1.5rem;font-weight:700;color:{color};font-family:'JetBrains Mono',monospace;">{cnt}</div>
<div style="font-size:.72rem;color:#64748B;">{label}</div></div>""", unsafe_allow_html=True)
    st.markdown("")

    filtro = st.radio("Filtra:", ["Tutti","🟢 COMPRA","🟡 MONITORA","🔴 VENDI"], horizontal=True)
    fm = {"Tutti":None,"🟢 COMPRA":"COMPRA","🟡 MONITORA":"MONITORA","🔴 VENDI":"VENDI"}
    filtered = [w for w in watchlist if fm[filtro] is None or w["segnale"]==fm[filtro]]

    if not filtered:
        st.info("Nessun titolo in watchlist. Aggiungine uno qui sotto.")

    cols_r = 3
    for i in range(0, len(filtered), cols_r):
        row_w = filtered[i:i+cols_r]
        cols_w = st.columns(cols_r)
        for j, item in enumerate(row_w):
            with cols_w[j]:
                sig = item["segnale"]
                sc = {"COMPRA":"#10B981","MONITORA":"#F59E0B","VENDI":"#EF4444"}[sig]
                price = get_price(item["ticker"]) if item["ticker"] != "N/A" else None
                td_w = get_technical(item["ticker"]) if item["ticker"] != "N/A" else None
                tech_em, _, _ = tech_signal(td_w)
                score = 5
                if td_w:
                    if td_w["price"] > (td_w["ma50"] or 0): score+=1
                    if td_w["price"] > (td_w["ma200"] or 0): score+=1
                    if td_w["rsi"] < 40: score+=1
                    if td_w["macd_h"] > 0: score+=1
                    if td_w["rsi"] > 70: score-=2
                    score = max(1,min(10,score))
                sc2 = "#10B981" if score>=7 else ("#F59E0B" if score>=4 else "#EF4444")
                dist_str = ""
                if price and item.get("prezzo_target"):
                    dist = (item["prezzo_target"]-price)/price*100
                    dist_str = f"{dist:+.1f}% al target"
                st.markdown(f"""<div style="background:#0F1829;border:1px solid {sc}44;border-left:3px solid {sc};border-radius:10px;padding:1rem;margin-bottom:.5rem;">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem;">
<span style="font-family:'JetBrains Mono',monospace;font-weight:700;color:{sc};">{item['ticker']}</span>
<div style="display:flex;gap:5px;">
<span style="background:{sc2}22;color:{sc2};border:1px solid {sc2}44;padding:1px 7px;border-radius:20px;font-size:.68rem;font-weight:700;">Score {score}/10</span>
<span style="background:{sc}22;color:{sc};border:1px solid {sc}44;padding:1px 7px;border-radius:20px;font-size:.68rem;font-weight:700;">{sig}</span>
</div></div>
<div style="font-size:.85rem;font-weight:600;color:#E8EDF5;margin-bottom:.6rem;">{item['nome']}</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:.4rem;font-size:.78rem;">
<div><span style="color:#64748B;">Prezzo: </span><span style="font-family:'JetBrains Mono',monospace;">{f'{price:,.2f}' if price else 'N/A'}</span></div>
<div><span style="color:#64748B;">Target: </span><span style="color:{sc};">{item.get('prezzo_target','—')}</span></div>
<div><span style="color:#64748B;">Stop: </span><span style="color:#EF4444;">{item.get('stop_loss','—')}</span></div>
<div><span style="color:#64748B;">Tecnica: </span><span>{tech_em} RSI {td_w['rsi']:.0f if td_w else '—'}</span></div>
</div>
{f'<div style="margin-top:.5rem;font-size:.72rem;color:#64748B;">{dist_str}</div>' if dist_str else ''}
{f'<div style="margin-top:.5rem;font-size:.75rem;color:#94A3B8;border-top:1px solid #1E2D47;padding-top:.4rem;">{item["note"]}</div>' if item.get("note") else ''}
</div>""", unsafe_allow_html=True)
                if st.button("🗑️ Rimuovi", key=f"rw_{i+j}"):
                    idx = st.session_state.data["watchlist"].index(item)
                    st.session_state.data["watchlist"].pop(idx)
                    save_data(st.session_state.data)
                    st.rerun()

    # Add to watchlist
    st.markdown('<div class="section-hd">Aggiungi alla watchlist</div>', unsafe_allow_html=True)
    with st.expander("➕ Nuovo titolo"):
        wc1,wc2,wc3 = st.columns(3)
        with wc1:
            wt = st.text_input("Ticker *", key="wt")
            wn = st.text_input("Nome *", key="wn")
            wcat = st.selectbox("Categoria", ["Azioni","ETF","Crypto","Obbligazioni","Materie Prime"], key="wcat")
        with wc2:
            wsig = st.selectbox("Segnale *", ["COMPRA","MONITORA","VENDI"], key="wsig")
            wtgt = st.number_input("Target price", min_value=0.0, step=0.01, key="wtgt")
            wsl = st.number_input("Stop loss", min_value=0.0, step=0.01, key="wsl")
        with wc3:
            wor = st.selectbox("Orizzonte", ["Breve (< 3 mesi)","Medio (3-12 mesi)","Lungo (> 1 anno)"], key="wor")
            wnote = st.text_area("Note / motivazione", key="wnote", height=90)
        if st.button("➕ Aggiungi", key="btn_wl"):
            if wt and wn:
                st.session_state.data["watchlist"].append({"ticker":wt.upper(),"nome":wn,"categoria":wcat,"segnale":wsig,"prezzo_target":wtgt,"stop_loss":wsl,"orizzonte":wor,"note":wnote})
                save_data(st.session_state.data)
                st.success(f"✅ {wn} aggiunto!")
                st.rerun()
            else:
                st.error("Inserisci almeno Ticker e Nome")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — GESTIONE
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    g1,g2 = st.tabs(["➕ Nuova operazione","📋 Modifica posizioni esistenti"])

    with g1:
        st.markdown('<div class="section-hd">Registra acquisto o vendita</div>', unsafe_allow_html=True)
        fc1,fc2,fc3 = st.columns(3)
        with fc1:
            gn = st.text_input("Nome asset *", key="gn")
            gt = st.text_input("Ticker Yahoo Finance *", placeholder="es. AAPL, LDO.MI, BTC-EUR", key="gt")
            gc = st.selectbox("Categoria *", ["Azioni","ETF","Obbligazioni","Crypto","Certificati","Materie Prime"], key="gc")
        with fc2:
            gv = st.selectbox("Valuta *", ["EUR","USD","GBP","DKK","CHF"], key="gv")
            gp = st.number_input("Prezzo medio carico *", min_value=0.0, step=0.001, format="%.3f", key="gp")
            gq = st.number_input("Quantità *", min_value=0.0, step=0.001, format="%.4f", key="gq")
        with fc3:
            gop = st.radio("Tipo operazione", ["Nuovo acquisto","Incrementa posizione esistente","Vendi (elimina posizione)"], key="gop")
            st.markdown("""<div class="tooltip-box">💡 Ticker su Yahoo Finance:<br>
• IT: LDO.MI · ENI.MI · UCG.MI<br>
• USA: AAPL · MSFT · NVDA<br>
• EU: AIR.PA · SIE.DE<br>
• ETF: SWDA.MI · VWCE.DE<br>
• Crypto: BTC-EUR · ETH-EUR<br>
• <a href="https://finance.yahoo.com" target="_blank" style="color:#3B82F6;">Cerca su Yahoo →</a></div>""", unsafe_allow_html=True)

        if st.button("✅ Registra operazione", key="btn_op"):
            if gn and gt and gp > 0 and gq > 0:
                existing_idx = next((i for i,p in enumerate(st.session_state.data["portfolio"]) if p["ticker"].upper()==gt.upper()), None)
                if gop == "Vendi (elimina posizione)" and existing_idx is not None:
                    st.session_state.data["portfolio"].pop(existing_idx)
                    save_data(st.session_state.data); st.cache_data.clear()
                    st.success(f"✅ Posizione {gt} eliminata"); st.rerun()
                elif gop == "Incrementa posizione esistente" and existing_idx is not None:
                    old = st.session_state.data["portfolio"][existing_idx]
                    nq = old["quantita"]+gq
                    np_ = (old["prezzo_carico"]*old["quantita"]+gp*gq)/nq
                    st.session_state.data["portfolio"][existing_idx].update({"quantita":nq,"prezzo_carico":np_})
                    save_data(st.session_state.data); st.cache_data.clear()
                    st.success(f"✅ {gt} incrementato — nuovo p.medio: {np_:.3f}"); st.rerun()
                else:
                    st.session_state.data["portfolio"].append({"nome":gn,"ticker":gt.upper(),"valuta":gv,"prezzo_carico":gp,"quantita":gq,"categoria":gc,"prezzo_manuale":None})
                    save_data(st.session_state.data); st.cache_data.clear()
                    st.success(f"✅ {gn} aggiunto"); st.rerun()
            else:
                st.error("Compila tutti i campi obbligatori (*)")

    with g2:
        portfolio = st.session_state.data["portfolio"]
        needs = [p for p in portfolio if p["ticker"]=="N/A" and not (p.get("prezzo_manuale") or 0)>0]
        has_m  = [p for p in portfolio if (p.get("prezzo_manuale") or 0)>0]
        has_l  = [p for p in portfolio if p["ticker"]!="N/A"]

        sc1,sc2,sc3 = st.columns(3)
        for col,(cnt,lbl,color) in zip([sc1,sc2,sc3],[
            (len(has_l),"🔵 Prezzi automatici","#3B82F6"),
            (len(has_m),"✏️ Prezzi manuali","#F59E0B"),
            (len(needs),"🔴 Da aggiornare","#EF4444")]):
            with col:
                st.markdown(f"""<div style="background:{color}12;border:1px solid {color}33;border-radius:10px;padding:.7rem;text-align:center;">
<div style="font-size:1.3rem;font-weight:700;color:{color};font-family:'JetBrains Mono',monospace;">{cnt}</div>
<div style="font-size:.72rem;color:#64748B;">{lbl}</div></div>""", unsafe_allow_html=True)

        if needs:
            st.error(f"⚠️ {len(needs)} asset senza prezzo attuale — espandili qui sotto e inserisci il prezzo manuale")

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
                lp = get_price(item["ticker"]) if item["ticker"] != "N/A" else None
                if item["ticker"] != "N/A" and lp: dot,slbl,sc = "🔵",f"Live: {lp:,.3f}","#3B82F6"
                elif pm > 0:                        dot,slbl,sc = "✏️",f"Manuale: {pm:,.3f}","#F59E0B"
                else:                              dot,slbl,sc = "🔴","PREZZO MANCANTE","#EF4444"

                with st.expander(f"{dot} {item['nome']} — {slbl}"):
                    if item["ticker"]=="N/A" and pm==0:
                        st.markdown('<div style="background:rgba(239,68,68,.12);border:1px solid #EF4444;border-radius:7px;padding:.5rem .8rem;font-size:.8rem;color:#EF4444;margin-bottom:.7rem;">⚠️ Inserisci il prezzo attuale nel campo qui sotto (obbligazioni: % del nominale, es. 98.50)</div>', unsafe_allow_html=True)
                    elif pm > 0:
                        st.markdown(f'<div style="background:rgba(245,158,11,.1);border:1px solid #F59E0B44;border-radius:7px;padding:.5rem .8rem;font-size:.8rem;color:#F59E0B;margin-bottom:.7rem;">✏️ Prezzo manuale: {pm:,.3f} — aggiornalo quando cambia</div>', unsafe_allow_html=True)
                    elif lp:
                        st.markdown(f'<div style="background:rgba(59,130,246,.1);border:1px solid #3B82F644;border-radius:7px;padding:.5rem .8rem;font-size:.8rem;color:#60A5FA;margin-bottom:.7rem;">🔵 Prezzo live da Yahoo Finance: {lp:,.3f} — aggiornato automaticamente</div>', unsafe_allow_html=True)

                    e1,e2,e3 = st.columns(3)
                    with e1:
                        nn = st.text_input("Nome", value=item["nome"], key=f"en_{idx}")
                        nt = st.text_input("Ticker Yahoo", value=item["ticker"], key=f"et_{idx}")
                    with e2:
                        npc = st.number_input("Prezzo carico", value=float(item["prezzo_carico"]), step=0.001, format="%.3f", key=f"ep_{idx}")
                        nq = st.number_input("Quantità/Nominale", value=float(item["quantita"]), step=0.001, format="%.4f", key=f"eq_{idx}")
                    with e3:
                        val_list = ["EUR","USD","GBP","DKK","CHF"]
                        nv = st.selectbox("Valuta", val_list, index=val_list.index(item["valuta"]) if item["valuta"] in val_list else 0, key=f"ev_{idx}")
                        nm = st.number_input("✏️ Prezzo attuale manuale" if item["ticker"]=="N/A" else "Prezzo manuale (sovrascrive Yahoo)", value=float(pm), step=0.001, format="%.3f", key=f"em_{idx}", help="Obbligazioni: inserisci la % del nominale (es. 98.50)")
                    b1,b2 = st.columns(2)
                    with b1:
                        if st.button("💾 Salva", key=f"sv_{idx}"):
                            st.session_state.data["portfolio"][idx].update({"nome":nn,"ticker":nt,"prezzo_carico":npc,"quantita":nq,"valuta":nv,"prezzo_manuale":nm if nm>0 else None})
                            save_data(st.session_state.data); st.cache_data.clear(); st.success("✅ Salvato!"); st.rerun()
                    with b2:
                        if st.button("🗑️ Elimina", key=f"dl_{idx}"):
                            st.session_state.data["portfolio"].pop(idx)
                            save_data(st.session_state.data); st.cache_data.clear(); st.rerun()
