
import os
import json
import math
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from agno.models.google import Gemini
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
 import openai

# --- Config & environ ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OUTPUTS_DIR = Path("./outputs")
OUTPUTS_DIR.mkdir(exist_ok=True)

# --- Mock internal data 
data_internal = [
    {
        "client_id": "c123",
        "name": "Alice Dupont",
        "profile": {
            "age": 52,
            "risk_tolerance": "moderate",
            "investment_horizon_years": 8,
            "portfolio": {"AAPL": 0.15, "MSFT": 0.10}
        },
        "notes": "Client prefers tech stocks, long-term horizon. Constraint: avoid crypto."
    }
]

# --- Simple web search mock 
sample_web_results = [
    {"title": "Alice Dupont linked to tech investments", "link": "https://example.com/news1", "snippet": "Alice invests in technology."},
    {"title": "Interview: Alice Dupont on portfolio", "link": "https://example.com/news2", "snippet": "Interview about long-term strategy."}
]

# --- Dataclasses pour structurer le résultat ---
@dataclass
class FinancialIndicators:
    ticker: str
    last_close: Optional[float] = None
    sma20: Optional[float] = None
    sma50: Optional[float] = None
    volatility_annual: Optional[float] = None
    error: Optional[str] = None

@dataclass
class PipelineReport:
    client_id: str
    name: str
    profile: Dict[str, Any]
    notes: str
    web_mentions: List[Dict[str, Any]]
    tickers_of_interest: List[str]
    web_coverage: int
    synthesis: str
    financials: Dict[str, Any]
    recommendation: Dict[str, Any]

# ----------------------------
# AGENT 1: Internal Search (mock)
# ----------------------------
def get_client_internal_data(client_id: str) -> Optional[Dict[str, Any]]:
    for c in data_internal:
        if c["client_id"] == client_id:
            return c
    return None

# ----------------------------
# AGENT 2: Web Search (mock) 
# ----------------------------
def web_search_for_client(client_name: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Recherche web simple - ici on renvoie sample_web_results.
    Pour production: intégrer SerpApi ou un scraper respectant robots.txt.
    """
    return sample_web_results[:max_results]

# ----------------------------
# AGENT 3: Client Research (fusion + synthèse)
# ----------------------------
def synthesize_client_report(internal: Dict[str, Any], web_hits: List[Dict[str, Any]]) -> Dict[str, Any]:
    report = {}
    report['client_id'] = internal.get('client_id')
    report['name'] = internal.get('name')
    report['profile'] = internal.get('profile', {})
    report['notes'] = internal.get('notes', "")
    report['web_mentions'] = web_hits
    tickers = list(internal.get('profile', {}).get('portfolio', {}).keys())
    report['tickers_of_interest'] = tickers
    report['web_coverage'] = len(web_hits)
    report['synthesis'] = (
        f"Client {report['name']} — Risk: {report['profile'].get('risk_tolerance', 'unknown')}. "
        f"Portfolio tickers: {report['tickers_of_interest']}. Public sources found: {report['web_coverage']}."
    )
    return report

# ----------------------------
# AGENT 4: Financial Data (yfinance)
# ----------------------------
def analyze_ticker(ticker: str, period: str = '1y') -> FinancialIndicators:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period, interval='1d')
        if hist.empty or len(hist) < 10:
            return FinancialIndicators(ticker=ticker, error="no or insufficient data")
        hist = hist.dropna(subset=['Close'])
        # Indicators
        sma20 = hist['Close'].rolling(window=20).mean().iloc[-1] if len(hist) >= 20 else None
        sma50 = hist['Close'].rolling(window=50).mean().iloc[-1] if len(hist) >= 50 else None
        returns = hist['Close'].pct_change().dropna()
        vol_annual = float(returns.std() * math.sqrt(252)) if not returns.empty else None
        last_close = float(hist['Close'].iloc[-1])
        return FinancialIndicators(
            ticker=ticker,
            last_close=last_close,
            sma20=float(sma20) if sma20 is not None and not np.isnan(sma20) else None,
            sma50=float(sma50) if sma50 is not None and not np.isnan(sma50) else None,
            volatility_annual=vol_annual
        )
    except Exception as e:
        return FinancialIndicators(ticker=ticker, error=str(e))

# ----------------------------
# AGENT 5: Recommendation (règles + option LLM)
# ----------------------------
def rule_based_recommendation(report: Dict[str, Any], fin: FinancialIndicators) -> Dict[str, Any]:
    vol = fin.volatility_annual or 0.0
    sma20 = fin.sma20
    sma50 = fin.sma50
    recommendation = "Hold"
    reasons = []
    confidence = 0.5

    # règle simple de volatilité (seuils arbitraires pour prototype)
    if vol is not None and vol > 0.6:
        recommendation = "Conserver (Hold)"
        reasons.append("Volatilité annualisée élevée (>0.6)")
        confidence = 0.6
    else:
        if sma20 is not None and sma50 is not None:
            if sma20 > sma50:
                recommendation = "Acheter (Buy)"
                reasons.append("Momentum positif (SMA20 > SMA50)")
                confidence = 0.65
            else:
                recommendation = "Conserver (Hold)"
                reasons.append("Momentum neutre/negatif (SMA20 <= SMA50)")
                confidence = 0.55
        else:
            reasons.append("Données SMA insuffisantes")
            confidence = 0.45

    return {"method": "rules", "recommendation": recommendation, "reasons": reasons, "confidence": confidence, "ticker": fin.ticker}

def llm_recommendation(report: Dict[str, Any], fin: FinancialIndicators) -> Optional[Dict[str, Any]]:

    if not GEMINI_API_KEY:
        return None
    try:
        gemini.api_key = GEMINI_API_KEY
        prompt = (
            "Tu es un conseiller financier. Utilise uniquement les données fournies ci-dessous. "
            "Donne une recommandation concise (Acheter / Conserver / Vendre), un court raisonnement, et un score de confiance (0-1).\n\n"
            f"Données client: {json.dumps({'client_id': report['client_id'], 'profile': report['profile'], 'notes': report['notes']}, ensure_ascii=False)}\n\n"
            f"Indicateurs financiers: {json.dumps(asdict(fin), ensure_ascii=False)}\n\n"
            "Réponse en JSON: {\"recommendation\":\"...\",\"rationale\":\"...\",\"confidence\":0.0}"
        )
        resp = openai.ChatCompletion.create(
            model="gemini-2.0-flash",  
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.0
        )
        txt = resp["choices"][0]["message"]["content"]
        # tenter un parse JSON — si non JSON, renvoyer brut
        try:
            parsed = json.loads(txt)
            return {"method": "llm", "llm_output": parsed}
        except Exception:
            return {"method": "llm", "llm_output_raw": txt}
    except Exception as e:
        return {"error": f"Gemini call failed: {str(e)}"}

def generate_recommendation(report: Dict[str, Any], fin: FinancialIndicators) -> Dict[str, Any]:
    # essayer LLM si dispo
    llm = llm_recommendation(report, fin)
    if llm and "error" not in llm:
        return llm
    # fallback rules
    return rule_based_recommendation(report, fin)

# ----------------------------
# Helpers: sauvegarde et utilitaires
# ----------------------------
def save_output(client_id: str, payload: Dict[str, Any]) -> str:
    p = OUTPUTS_DIR / f"report_{client_id}.json"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return str(p)

# ----------------------------
# Orchestrator séquentiel (exécution du pipeline)
# ----------------------------
def run_pipeline_for_client(client_id: str):
    internal = get_client_internal_data(client_id)
    if not internal:
        print(f"[ERROR] Client {client_id} non trouvé")
        return

    print("[INFO] AGENT 1 — Internal Search")
    time.sleep(0.2)
    # internal already loaded

    print("[INFO] AGENT 2 — Web Search (mock)")
    web = web_search_for_client(internal["name"])

    print("[INFO] AGENT 3 — Client Research (fusion)")
    report = synthesize_client_report(internal, web)

    print("[INFO] AGENT 4 — Financial Data")
    financials = {}
    for t in report["tickers_of_interest"]:
        print(f"  - Analyse {t} ...")
        fin = analyze_ticker(t)
        financials[t] = asdict(fin)

    # choisir premier ticker pour recommandation 
    first_ticker = report["tickers_of_interest"][0] if report["tickers_of_interest"] else None
    fin_obj = None
    if first_ticker:
        fin_obj = FinancialIndicators(**financials[first_ticker])

    print("[INFO] AGENT 5 — Recommendation")
    rec = generate_recommendation(report, fin_obj) if fin_obj else {"error": "no ticker to analyze"}

    pipeline = PipelineReport(
        client_id=report["client_id"],
        name=report["name"],
        profile=report["profile"],
        notes=report["notes"],
        web_mentions=report["web_mentions"],
        tickers_of_interest=report["tickers_of_interest"],
        web_coverage=report["web_coverage"],
        synthesis=report["synthesis"],
        financials=financials,
        recommendation=rec
    )

    out_path = save_output(client_id, asdict(pipeline))
    print(f"[DONE] Pipeline terminé. Rapport sauvegardé -> {out_path}")

# ----------------------------
# Exécution principale
# ----------------------------
if __name__ == "__main__":
    # par défaut on exécute pour c123 
    run_pipeline_for_client("c123")
