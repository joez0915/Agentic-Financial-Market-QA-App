import json
import time
import concurrent.futures
from dataclasses import dataclass, field
from config import client, ACTIVE_MODEL
from tools import ALL_TOOL_FUNCTIONS
from schemas import *

@dataclass
class AgentResult:
    agent_name: str
    answer: str
    tools_called: list = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)
    confidence: float = 0.0
    issues_found: list = field(default_factory=list)
    reasoning: str = ""

def run_specialist_agent(agent_name: str, system_prompt: str, task: str,
                         tool_schemas: list, max_iters: int = 8, verbose: bool = True) -> AgentResult:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task}
    ]
    tools_called = []
    raw_data = {}

    for _ in range(max_iters):
        kwargs = {"model": ACTIVE_MODEL, "messages": messages, "temperature": 0.0}
        if tool_schemas:
            kwargs["tools"] = tool_schemas
            kwargs["tool_choice"] = "auto"

        response = client.chat.completions.create(**kwargs)
        msg = response.choices[0].message
        messages.append(msg)

        if msg.tool_calls:
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except:
                    args = {}

                if verbose:
                    print(f"  [{agent_name}] Tool Call: {fn_name}({args})")

                tools_called.append(fn_name)
                fn = ALL_TOOL_FUNCTIONS.get(fn_name)
                result = fn(**args) if fn else {"error": f"Unknown tool {fn_name}"}
                raw_data[fn_name] = result

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": fn_name,
                    "content": json.dumps(result)
                })
        else:
            return AgentResult(agent_name=agent_name, answer=msg.content or "",
                             tools_called=tools_called, raw_data=raw_data)

    return AgentResult(agent_name=agent_name, answer="Max iterations reached.",
                      tools_called=tools_called, raw_data=raw_data)

# Baseline Agent
def run_baseline(question: str, verbose: bool = True) -> AgentResult:
    return run_specialist_agent(
        agent_name="Baseline",
        system_prompt="You are a helpful financial assistant answering questions accurately. If you don't know, say so.",
        task=question,
        tool_schemas=[],
        verbose=verbose
    )

# Single Agent
SINGLE_AGENT_PROMPT = """You are a financial AI agent with access to 7 data lookup tools. Think step by step.

Tool selection guide:
- Sector/group queries → call `get_tickers_by_sector` or `query_local_db` FIRST to get real tickers. Never guess tickers.
- Database sector names: Technology, Energy, Healthcare, Financial Services, Consumer Cyclical, Consumer Defensive, Industrials, Basic Materials, Real Estate, Communication Services, Utilities. Use the closest match.
- Price performance → `get_price_performance` with the correct period (1mo, 3mo, 6mo, ytd, 1y).
- P/E, EPS, market cap, 52-week range → `get_company_overview` for each ticker.
- News sentiment → `get_news_sentiment` for each ticker.
- Market open/close → `get_market_status`.

CRITICAL ERROR HANDLING:
- When a ticker returns {"error": "..."}, that ticker is PERMANENTLY UNAVAILABLE. Remove it from your list immediately.
- NEVER call get_price_performance again with tickers that already returned errors.
- If 3 out of 90 tickers fail, use the 87 successful ones. Do NOT retry the 3 failed ones.

Accuracy rules:
- If a tool returns an error or empty data, state clearly the data is unavailable. NEVER fabricate numbers.
- For multi-ticker comparisons, fetch data for ALL tickers, then compare.
- Report exact values returned by the tools.
- For multi-step questions (e.g. "top 3 by X, then get Y for each"), complete ALL steps — do not stop after the first."""

def run_single_agent(question: str, verbose: bool = True) -> AgentResult:
    return run_specialist_agent(
        agent_name="Single Agent",
        system_prompt=SINGLE_AGENT_PROMPT,
        task=question,
        tool_schemas=ALL_SCHEMAS,
        max_iters=10,
        verbose=verbose
    )

# Multi-Agent
_SPECIALIST_PROMPTS = {
    'Market': """You are a Market data specialist with access to stock database and price tools.
Rules:
- For sector/group queries, ALWAYS call `get_tickers_by_sector` or `query_local_db` FIRST to get real tickers. Never guess tickers.
- Note: database sector names are: Technology, Energy, Healthcare, Financial Services, Consumer Cyclical, Consumer Defensive, Industrials, Basic Materials, Real Estate, Communication Services, Utilities. Use the closest match.
- If a tool returns an error or empty data, state clearly that the data is unavailable. NEVER fabricate numbers.
- For multi-stock comparisons, fetch data for ALL requested tickers.
- Report exact numbers returned by tools.""",

    'Fundamentals': """You are a Fundamentals specialist with access to company overview and database tools.
Rules:
- Use `get_company_overview` to fetch P/E ratio, EPS, market cap, 52-week high/low.
- If the API returns an error or rate-limit message, state the data is unavailable. NEVER invent financial metrics.
- For multi-ticker questions, call `get_company_overview` for EACH ticker separately.
- Report exact values from the API response.""",

    'Sentiment': """You are a News Sentiment specialist with access to sentiment and database tools.
Rules:
- Use `get_news_sentiment` to fetch recent headlines and sentiment labels.
- If no articles are returned, state that no recent news data is available. NEVER fabricate headlines.
- For multi-ticker questions, call `get_news_sentiment` for EACH ticker separately.
- Report the sentiment label and score exactly as returned.""",
}

def run_multi_agent(question: str, verbose: bool = True) -> dict:
    start_time = time.time()

    # Orchestrator
    orch_prompt = """You are an orchestrator routing queries.
Analyze the following user question and decide which data experts must be consulted.
Output ONLY a JSON object with key "domains" containing an array of strings from: ["Market", "Fundamentals", "Sentiment"]. For example: {"domains": ["Market", "Fundamentals"]}"""

    resp = client.chat.completions.create(
        model=ACTIVE_MODEL,
        messages=[
            {"role":"system", "content":orch_prompt},
            {"role":"user", "content":question}
        ],
        response_format={"type": "json_object"}
    )

    content = resp.choices[0].message.content or ""
    domains = ['Market', 'Fundamentals', 'Sentiment']
    try:
        parsed = json.loads(content)
        tasks = parsed.get("domains", domains)
        tasks = [d for d in tasks if d in domains]
        if not tasks:
            tasks = domains
    except:
        tasks = domains

    agents_config = {
       'Market': ('Market Agent', [SCHEMA_TICKERS, SCHEMA_PRICE, SCHEMA_STATUS, SCHEMA_MOVERS, SCHEMA_SQL]),
       'Fundamentals': ('Fundamentals Agent', [SCHEMA_OVERVIEW, SCHEMA_SQL, SCHEMA_TICKERS]),
       'Sentiment': ('Sentiment Agent', [SCHEMA_NEWS, SCHEMA_SQL])
    }

    def call_specialist(domain):
       name, schemas = agents_config[domain]
       return run_specialist_agent(
           agent_name=name,
           system_prompt=_SPECIALIST_PROMPTS[domain],
           task=question,
           tool_schemas=schemas,
           max_iters=8,
           verbose=verbose
       )

    with concurrent.futures.ThreadPoolExecutor() as executor:
        agent_results = list(executor.map(call_specialist, tasks))

    # Synthesizer
    synth_prompt = """You are a final synthesizer. Combine ALL useful information from the specialists into a single coherent answer.
Rules:
- Write a professional, human-readable response using Markdown formatting (bullet points, bold text, etc.).
- Include ALL specific data points (numbers, tickers, percentages, dates) the specialists provided.
- Only say "data unavailable" for specific fields that NO specialist could retrieve. Do not discard partial results.
- Do NOT output raw python dictionaries or raw arrays. Format the data into readable text or markdown tables.
- You MUST output a valid JSON object with EXACTLY two keys: "final_answer" (string containing your formatted markdown answer) and "confidence" (float 0.0-1.0)."""

    context = "\n\n".join([f"[{r.agent_name}]: {r.answer}" for r in agent_results])
    resp_syn = client.chat.completions.create(
        model=ACTIVE_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role":"system", "content":synth_prompt},
            {"role":"user", "content":f"Question: {question}\n\nSpecialists Context:\n{context}"}
        ]
    )

    try:
        res_data = json.loads(resp_syn.choices[0].message.content or "{}")
        final_answer = res_data.get("final_answer") or res_data.get("answer") or res_data.get("text") or ""
        confidence = float(res_data.get("confidence", 0.0))
    except:
        final_answer = resp_syn.choices[0].message.content or ""
        confidence = 0.0

    final_answer = str(final_answer)

    return {
        "final_answer": final_answer,
        "agent_results": agent_results,
        "confidence": confidence,
        "elapsed_sec": time.time() - start_time,
        "architecture": "Parallel Specialists"
    }
