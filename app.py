import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import json, requests, time, smtplib, ssl
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
                   "Crypto":"#8B5CF6","Certificati":"#06B6D4","Materie Prime":"#F97316"}

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
        {"nome":"Ethereum (ETH)","ticker":"ETH-EUR","valuta":"EUR","prezzo_carico":3099.44,"quantita":0.48,"categoria":"Crypto","prezzo_manuale":None},
        {"nome":"Bitcoin (BTC)","ticker":"BTC-EUR","valuta":"EUR","prezzo_carico":56403.66,"quantita":0.26,"categoria":"Crypto","prezzo_manuale":None},
        {"nome":"Ripple (XRP)","ticker":"XRP-EUR","valuta":"EUR","prezzo_carico":2.35,"quantita":638.87,"categoria":"Crypto","prezzo_manuale":None},
        {"nome":"Oro (Gold ETC)","ticker":"PHAU.MI","valuta":"EUR","prezzo_carico":1580.000,"quantita":0.47,"categoria":"Materie Prime","prezzo_manuale":None},
        {"nome":"WisdomTree Copper","ticker":"COPA.MI","valuta":"EUR","prezzo_carico":38.070,"quantita":27,"categoria":"Materie Prime","prezzo_manuale":None},
        {"nome":"WisdomTree Physical Gold","ticker":"PHGP.MI","valuta":"EUR","prezzo_carico":173.300,"quantita":21,"categoria":"Materie Prime","prezzo_manuale":None},
    ],
    "watchlist": [],
    "agent_cache": {},
    "trade_history": [],
    "email_settings": {}
}

def load_data():
    if DATA_FILE.exists():
        d = json.loads(DATA_FILE.read_text())
        for k in ["agent_cache","trade_history","email_settings","watchlist"]:
            if k not in d: d[k] = {} if k in ["agent_cache","email_settings"] else []
        return d
    return DEFAULT_DATA.copy()

def save_data(d):
    DATA_FILE.write_text(json.dumps(d, indent=2, ensure_ascii=False))

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
def call_agent(client, system_prompt, user_prompt, max_tokens=800):
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role":"user","content":user_prompt}])
        return msg.content[0].text
    except Exception as e:
        return f"Errore agente: {e}"

def run_multi_agent_analysis(api_key, portfolio_df, market_data, watchlist, news_items):
    client = anthropic.Anthropic(api_key=api_key)
    results = {}
    progress = st.progress(0)
    status_box = st.empty()
    vix = market_data.get("VIX",{}).get("value",20)
    sp500 = market_data.get("S&P 500",{}).get("delta",0)
    news_text = "\n".join([f"- {n['title']}" for n in news_items[:10]]) if news_items else "Non disponibile"

    def agent_step(n, total, tag, color, label, system, user, max_t=800):
        status_box.markdown(
            f'<div class="agent-card"><span style="color:{color};font-size:.65rem;font-weight:700;letter-spacing:.08em;">'
            f'▶ AGENTE {n}/{total}</span> <b>{label}</b></div>', unsafe_allow_html=True)
        result = call_agent(client, system, user, max_t)
        progress.progress(int(n/total*100))
        return result

    results["macro"] = agent_step(1,5,"macro","#10B981","Analista Macro",
        "Sei un economista macro istituzionale. Analisi concise, dati precisi, outlook chiaro.",
        f"""VIX={vix:.1f}, S&P500={sp500:+.2f}%, EUR/USD={market_data.get('EUR/USD',{}).get('value',1.08):.4f}
NOTIZIE:\n{news_text}
1) Regime macro (risk-on/off) 2) 3 rischi principali 3) 3 opportunità 4) Impatto per asset class. Max 300 parole, italiano.""")

    tradeable = [(r["Nome"],r["Ticker"]) for _,r in portfolio_df.iterrows() if r["Ticker"]!="N/A"]
    tech_summary = []
    for nome, ticker in tradeable[:12]:
        td = get_technical(ticker)
        if td:
            em, label, reason = tech_signal(td)
            tech_summary.append(f"{nome}: {label} | RSI={td['rsi']:.0f} | MACD={td['macd_h']:+.3f} | {reason}")
    results["tecnica"] = agent_step(2,5,"tecnica","#3B82F6","Analista Tecnico",
        "Sei un analista tecnico senior. Pattern recognition, livelli chiave, momentum.",
        f"""ANALISI TECNICA:\n{chr(10).join(tech_summary)}
1) Top 3 setup rialzisti 2) Top 3 deteriorati 3) Pattern generale 4) Livelli chiave. Max 300 parole, italiano.""")

    alloc = portfolio_df.groupby("Categoria")["CV €"].sum()
    total_v = alloc.sum()
    alloc_str = "\n".join([f"- {c}: €{v:,.0f} ({v/total_v*100:.1f}%)" for c,v in alloc.items()])
    top3 = portfolio_df.nlargest(3,"CV €")[["Nome","CV €"]].to_string(index=False)
    results["rischio"] = agent_step(3,5,"rischio","#F59E0B","Risk Manager",
        "Sei un risk manager istituzionale.",
        f"""TOTALE: €{total_v:,.0f}\nALLOCAZIONE:\n{alloc_str}\nTOP 3:\n{top3}\nVIX:{vix:.1f}
1) Score rischio 1-10 2) Concentrazione 3) Rischio valutario 4) Ribilanciamento 5) Hedging. Max 300 parole, italiano.""")

    results["sentiment"] = agent_step(4,5,"sentiment","#8B5CF6","Sentiment Analyst",
        "Sei esperto di sentiment e behavioral finance.",
        f"""VIX:{vix:.1f}, S&P500:{sp500:+.2f}%\nNOTIZIE:\n{news_text}
1) Fear/Greed 0-100 2) Posizionamento istituzionale 3) Rischi comportamentali 4) Opportunità contrarian. Max 250 parole, italiano.""")

    wl_str = "\n".join([f"- {w['ticker']}: {w.get('segnale','')} | {w.get('note','')}" for w in watchlist]) or "Nessun titolo"
    results["ottimizzazione"] = agent_step(5,5,"ottimizzatore","#F97316","Portfolio Optimizer",
        "Sei il gestore di un family office. Combini macro, tecnica, rischio e sentiment.",
        f"""SINTESI:\nMACRO: {results['macro'][:400]}\nTECNICA: {results['tecnica'][:400]}\n"""
        f"""RISCHIO: {results['rischio'][:400]}\nSENTIMENT: {results['sentiment'][:300]}\nWATCHLIST: {wl_str}
Piano operativo: VENDI/RIDUCI/TIENI/INCREMENTA per ogni posizione + 3-5 nuovi acquisti con ticker/ingresso/target/stop + asset allocation target. Max 500 parole, italiano.""",
        max_t=1200)

    progress.progress(100)
    status_box.empty()
    progress.empty()
    return results

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
    anthropic_key = st.text_input("Chiave Anthropic API", type="password", placeholder="sk-ant-...", key="ant_key")
    news_api_key  = st.text_input("Chiave NewsAPI",       type="password", placeholder="newsapi key...", key="news_key")
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
tab1,tab2,tab3,tab4,tab5,tab6,tab7 = st.tabs([
    "🌍 Mercati","💼 Portafoglio","📡 Tecnica","🤖 Multi-Agente AI",
    "👁️ Watchlist","📊 Benchmark & Scenari","✏️ Gestione"])

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
    buy_c = sum(1 for w in watchlist if w.get("segnale")=="COMPRA")
    mon_c = sum(1 for w in watchlist if w.get("segnale")=="MONITORA")
    sel_c = sum(1 for w in watchlist if w.get("segnale")=="VENDI")

    sb1,sb2,sb3 = st.columns(3)
    for col,(cnt,label,color) in zip([sb1,sb2,sb3],
        [(buy_c,"🟢 Da comprare","#10B981"),(mon_c,"🟡 Monitorare","#F59E0B"),(sel_c,"🔴 Da vendere","#EF4444")]):
        with col:
            st.markdown(f'<div style="background:{color}12;border:1px solid {color}33;border-radius:10px;padding:.8rem;text-align:center;"><div style="font-size:1.5rem;font-weight:700;color:{color};font-family:\'JetBrains Mono\',monospace;">{cnt}</div><div style="font-size:.72rem;color:#64748B;">{label}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-hd">Aggiungi titolo — l\'AI analizza tutto automaticamente</div>', unsafe_allow_html=True)
    wa,wb,wc_col,wd_col = st.columns([2,2,2,1])
    with wa: wt = st.text_input("Ticker Yahoo *", placeholder="es. NVDA, ENI.MI, BTC-EUR", key="wt")
    with wb: wn = st.text_input("Nome *", placeholder="es. NVIDIA Corporation", key="wn")
    with wc_col: wcat = st.selectbox("Categoria", ["Azioni","ETF","Crypto","Obbligazioni","Materie Prime"], key="wcat")
    with wd_col:
        st.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
        add_btn = st.button("➕ Aggiungi", key="btn_wl", use_container_width=True)

    if add_btn:
        if wt and wn:
            new_item = {"ticker":wt.upper(),"nome":wn,"categoria":wcat,
                        "segnale":"MONITORA","prezzo_target":None,"stop_loss":None,
                        "orizzonte":None,"note":"⏳ In attesa analisi AI...","ai_pending":True}
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
                            model="claude-sonnet-4-20250514", max_tokens=400,
                            system="Sei un analista finanziario. Rispondi SOLO in JSON valido senza markdown.",
                            messages=[{"role":"user","content":
                                f'Analizza {wn} ({wt.upper()}). Dati tecnici: {tech_ctx if tech_ctx else "N/A"}. '
                                f'Rispondi con SOLO questo JSON: {{"segnale":"COMPRA","prezzo_target":0.0,"stop_loss":0.0,"orizzonte":"Medio (3-12 mesi)","note":"motivazione max 120 caratteri italiano"}}. '
                                f'segnale: COMPRA, MONITORA o VENDI'}]
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
                st.success(f"✅ {wn} aggiunto (aggiungi chiave Anthropic per analisi AI)")
            st.rerun()
        else:
            st.error("Inserisci Ticker e Nome")

    st.markdown("")
    filtro = st.radio("Filtra:", ["Tutti","🟢 COMPRA","🟡 MONITORA","🔴 VENDI"], horizontal=True)
    fm = {"Tutti":None,"🟢 COMPRA":"COMPRA","🟡 MONITORA":"MONITORA","🔴 VENDI":"VENDI"}
    filtered = [w for w in watchlist if fm[filtro] is None or w.get("segnale")==fm[filtro]]
    if not filtered:
        st.info("Nessun titolo in watchlist.")

    for i in range(0, len(filtered), 3):
        row_w = filtered[i:i+3]
        cols_w = st.columns(3)
        for j, item in enumerate(row_w):
            with cols_w[j]:
                sig = item.get("segnale","MONITORA")
                sc = {"COMPRA":"#10B981","MONITORA":"#F59E0B","VENDI":"#EF4444"}.get(sig,"#F59E0B")
                price = get_price(item["ticker"]) if item.get("ticker","N/A") != "N/A" else None
                td_w = get_technical(item["ticker"]) if item.get("ticker","N/A") != "N/A" else None
                tech_em, _, _ = tech_signal(td_w)
                rsi_str = f"{td_w['rsi']:.0f}" if td_w else "—"
                score = 5
                if td_w:
                    if td_w["price"] > (td_w["ma50"] or 0): score+=1
                    if td_w["price"] > (td_w["ma200"] or 0): score+=1
                    if td_w["rsi"] < 40: score+=1
                    if td_w["macd_h"] > 0: score+=1
                    if td_w["rsi"] > 70: score-=2
                    score = max(1,min(10,score))
                sc2 = "#10B981" if score>=7 else ("#F59E0B" if score>=4 else "#EF4444")
                tgt = item.get("prezzo_target"); sl = item.get("stop_loss")
                dist_str = f"{(tgt-price)/price*100:+.1f}% al target" if price and tgt and tgt>0 else ""
                tgt_d = f"{tgt:.2f}" if tgt and tgt>0 else "—"
                sl_d  = f"{sl:.2f}"  if sl  and sl>0  else "—"
                price_d = f"{price:.2f}" if price else "N/A"
                note_h = f'<div style="margin-top:.5rem;font-size:.75rem;color:#94A3B8;border-top:1px solid #1E2D47;padding-top:.4rem;">{"⏳ " if item.get("ai_pending") else ""}{item.get("note","")}</div>' if item.get("note") else ""
                st.markdown(f"""<div style="background:#0F1829;border:1px solid {sc}44;border-left:3px solid {sc};border-radius:10px;padding:1rem;margin-bottom:.5rem;">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem;">
<span style="font-family:'JetBrains Mono',monospace;font-weight:700;color:{sc};">{item.get('ticker','')}</span>
<div style="display:flex;gap:4px;">
<span style="background:{sc2}22;color:{sc2};border:1px solid {sc2}44;padding:1px 7px;border-radius:20px;font-size:.65rem;font-weight:700;">Score {score}/10</span>
<span style="background:{sc}22;color:{sc};border:1px solid {sc}44;padding:1px 7px;border-radius:20px;font-size:.65rem;font-weight:700;">{sig}</span>
</div></div>
<div style="font-size:.85rem;font-weight:600;color:#E8EDF5;margin-bottom:.6rem;">{item.get('nome','')}</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:.4rem;font-size:.78rem;">
<div><span style="color:#64748B;">Prezzo: </span><span style="font-family:'JetBrains Mono',monospace;">{price_d}</span></div>
<div><span style="color:#64748B;">Target: </span><span style="color:{sc};">{tgt_d}</span></div>
<div><span style="color:#64748B;">Stop: </span><span style="color:#EF4444;">{sl_d}</span></div>
<div><span style="color:#64748B;">RSI: </span><span>{tech_em} {rsi_str}</span></div>
</div>
{f'<div style="margin-top:.3rem;font-size:.72rem;color:#64748B;">{dist_str}</div>' if dist_str else ""}
{f'<div style="margin-top:.3rem;font-size:.72rem;color:#64748B;">⏱ {item.get("orizzonte","")}</div>' if item.get("orizzonte") else ""}
{note_h}</div>""", unsafe_allow_html=True)
                ba, bb = st.columns(2)
                with ba:
                    if anthropic_key and st.button("🤖 Rianalizza", key=f"rai_{i+j}", use_container_width=True):
                        with st.spinner("AI..."):
                            td_r = get_technical(item["ticker"])
                            ctx_r = f"Prezzo:{td_r['price']:.2f}, RSI:{td_r['rsi']:.0f}" if td_r else "N/A"
                            try:
                                cl_r = anthropic.Anthropic(api_key=anthropic_key)
                                ai_r = cl_r.messages.create(
                                    model="claude-sonnet-4-20250514", max_tokens=300,
                                    system="Rispondi SOLO in JSON valido senza markdown.",
                                    messages=[{"role":"user","content":
                                        f'Rianalizza {item["nome"]} ({item["ticker"]}). Tecnica: {ctx_r}. '
                                        f'JSON: {{"segnale":"COMPRA","prezzo_target":0.0,"stop_loss":0.0,"orizzonte":"Medio (3-12 mesi)","note":"motivazione"}}'}]
                                ).content[0].text.strip()
                                ai_d = json.loads(ai_r)
                                wl_r_idx = next(k for k,x in enumerate(st.session_state.data["watchlist"]) if x.get("ticker")==item.get("ticker"))
                                st.session_state.data["watchlist"][wl_r_idx].update(ai_d)
                                save_data(st.session_state.data); st.rerun()
                            except: st.error("Errore AI")
                with bb:
                    if st.button("🗑️ Rimuovi", key=f"rw_{i+j}", use_container_width=True):
                        wl_rm = next((k for k,x in enumerate(st.session_state.data["watchlist"]) if x.get("ticker")==item.get("ticker")), None)
                        if wl_rm is not None:
                            st.session_state.data["watchlist"].pop(wl_rm)
                            save_data(st.session_state.data); st.rerun()

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
            realized_pnl = sum(t.get("pnl_realizzato",0) for t in trade_history)
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
    g1, g2 = st.tabs(["➕ Nuova operazione", "📋 Modifica posizioni"])

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
