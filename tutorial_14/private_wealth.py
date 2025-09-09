from agno.agent import Agent
from agno.memory.v2.db.sqlite import SqliteMemoryDb   
from agno.memory.v2.memory import Memory
from agno.team.team import Team
from agno.storage.agent.sqlite import SqliteAgentStorage  
from agno.models.google import Gemini
from agno.tools.yfinance import YFinanceTools
from agno.tools.reasoning import ReasoningTools
import os 
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()  

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError(
        "Missing GOOGLE_API_KEY environment variable. "
        "Crée une clé dans Google AI Studio et exporte-la (voir doc)."
    )

# === Initialize Gemini model ===
gemini_model = Gemini(id="gemini-2.0-flash", api_key=GOOGLE_API_KEY)

# === DB / Memory ===
db_url = "sqlite:///wealth_memory.db"   
memory = Memory(
    model=Gemini(id="gemini-2.0-flash", api_key=GOOGLE_API_KEY),
    db=SqliteMemoryDb(table_name="user_memories", db_url=db_url),
    delete_memories=False,
    clear_memories=False,
)

# === Agents ===
client_profile_agent = Agent(
    name="ClientProfileAgent",
    role="Collect client data (age, horizon, risk tolerance) and output structured profile JSON.",
    agent_id="profile_agent",
    model=Gemini(id="gemini-1.5-flash", api_key=GOOGLE_API_KEY),
    instructions=[
        "Ask or parse: age, investable_assets, risk_tolerance (conservative/moderate/aggressive), tax_region, horizon_years",
        "Return a JSON with those keys."
    ],
    memory=memory,
    markdown=False,
)

portfolio_agent = Agent(
    name="PortfolioAgent",
    role="Fetch market data, compute allocation, returns, volatility and Sharpe. Suggest rebalancing.",
    agent_id="portfolio_agent",
    model=Gemini(id="gemini-1.5-flash", api_key=GOOGLE_API_KEY),
    tools=[YFinanceTools(stock_price=True, stock_fundamentals=True, company_news=True)],
    storage=SqliteAgentStorage(db_url=db_url, table_name="portfolio_agent_sessions"),
    memory=memory,
    instructions=[
        "Input: 'TICKER:shares' pairs. Compute current value using latest price, percent allocation, 1Y return, annualized volatility, Sharpe ratio (use risk-free ~ 3% if unknown).",
        "Output: Markdown table + rebalancing steps (concrete buy/sell quantities) and sources (news + data timestamps)."
    ],
    markdown=True,
)

tax_agent = Agent(
    name="TaxAgent",
    role="Provide high-level tax-aware suggestions (sell/hold timing), country-specific considerations.",
    agent_id="tax_agent",
    model=Gemini(id="gemini-1.5-flash", api_key=GOOGLE_API_KEY),
    instructions=[
        "Ask for client's tax_region and give non-binding high-level advice (e.g., long-term capital gains in X).",
        "Always recommend consulting a human tax advisor for compliance."
    ],
    memory=memory,
)

# === Team (coordinator) ===
wealth_team = Team(
    name="PrivateWealthManager",
    mode="coordinate",
    team_id="private_wealth_team",
    model=gemini_model,  
    members=[client_profile_agent, portfolio_agent, tax_agent],
    tools=[ReasoningTools(add_instructions=True)],
    instructions=[
        "Produce a client-ready wealth management report: summary, numeric metrics, rebalancing plan, risk assessment, and an action checklist.",
        "Ensure all numeric claims include sources and data timestamps. No emojis."
    ],
    storage=SqliteAgentStorage(db_url=db_url, table_name="wealth_team_sessions"),
    memory=memory,
    enable_team_history=True,
    markdown=True,
)

# === Main execution ===
if __name__ == "__main__":
    prompt = (
        "Client: Alice, investable 100k, horizon 10y, risk: moderate. "
        "Portefeuille: AAPL:50, MSFT:30, BND:20. "
        "Fournis un rapport complet (tableau, metrics, rééquilibrage, sources)."
    )

    # Use print_response to get the full report
    response = wealth_team.print_response(prompt, stream=False)
    print(response)
