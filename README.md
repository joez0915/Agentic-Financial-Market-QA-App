# Agentic Financial Market QA System Workflow

## Overview

This project is a financial question-answering system that compares three LLM architectures:

1. Baseline LLM
2. Single tool-using agent
3. Multi-agent system with an orchestrator, specialist agents, external tools, and a final synthesizer

The system is designed to answer stock-market questions using a combination of LLM reasoning, tool calling, live market data, news sentiment, company fundamentals, and a local SQL database.

## Core Components

### Streamlit UI

The Streamlit interface receives the user query, lets the user choose an architecture, displays the final response, and shows execution metadata such as latency, number of tools used, and selected architecture.

### Baseline Agent

The Baseline Agent answers directly using the LLM without external tools. It is mainly used as a benchmark for comparing accuracy and reliability against the tool-augmented architectures.

### Single Agent

The Single Agent uses one LLM agent with access to all available tools. It selects tools dynamically, calls them through function calling, observes the returned data, and continues iterating until it produces a final answer.

### Multi-Agent System

The Multi-Agent System uses an orchestrator to decide which specialist agents should answer the query. The selected specialists run in parallel, each with a narrower financial domain and a focused tool set.

Specialist agents include:

- Market Agent: handles sector lookup, price performance, market status, top movers, and SQL database queries.
- Fundamentals Agent: handles company overview, P/E ratio, EPS, market cap, and 52-week range.
- Sentiment Agent: handles recent news headlines and sentiment scores.

### Tool Layer

The tool layer connects agents to structured financial data sources:

- yfinance for price data, fundamentals, top movers, and news.
- SQLite database for local stock metadata.
- Function schemas that define which tools the LLM can call and what arguments each tool requires.

### Synthesizer

The Synthesizer combines all specialist outputs into one final response. It preserves specific numbers, tickers, dates, tool results, and partial data instead of discarding incomplete but useful information.

## 🗺️ Architectural Workflows

```mermaid
flowchart TD
    A[User query] --> B[Streamlit UI]
    B --> C[Architecture selector]
    
    C -->|Baseline| D[Baseline Agent]
    C -->|Single Agent| E[Single Agent]
    C -->|Multi-Agent| F[Orchestrator]
    
    %% Baseline Path
    D --> D1[LLM-only response]
    D1 --> D2((Done))
    
    %% Single Agent Path
    E --> E1{Tool needed?}
    E1 -->|Yes| E2[Call selected financial tool]
    E1 -->|No| E5[Generate final answer]
    E2 --> E3[Observe tool output]
    E3 --> E4{Need another tool?}
    E4 -->|Yes| E2
    E4 -->|No| E5
    E5 --> E6((Done))
    
    %% Multi-Agent Path
    F --> F1{Select needed domains}
    F1 -->|Market| F2[Market Agent]
    F1 -->|Fundamentals| F3[Fundamentals Agent]
    F1 -->|Sentiment| F4[Sentiment Agent]
    
    F2 --> F5["Market tools<br>sector lookup, price performance,<br>market status, top movers, SQL"]
    F3 --> F6["Fundamentals tools<br>P/E ratio, EPS, market cap,<br>52-week range, SQL"]
    F4 --> F7["Sentiment tools<br>news headlines and sentiment scores"]
    
    F5 --> F8[Specialist results]
    F6 --> F8
    F7 --> F8
    
    F8 --> F9[Synthesizer]
    F9 --> F10[Final answer with confidence]
    F10 --> F11((Done))
```

## Why This Architecture Improves the System

The Baseline Agent is simple but cannot access fresh or structured financial data. The Single Agent improves grounding by using tools, but it must handle all financial reasoning in one broad prompt. The Multi-Agent System improves reliability by separating the task into domain-specific agents and letting each specialist focus on a narrower set of tools and rules.

This design supports the resume claims that the project improved query accuracy by comparing baseline, single-agent, and multi-agent architectures, reduced latency through agent orchestration and tool selection, and used a RAG-style architecture that integrates OpenAI GPT models, external APIs, and a local SQL database.

## Tool Summary

| Tool | Purpose |
|---|---|
| get_tickers_by_sector | Finds stocks by sector or industry from the local database |
| get_price_performance | Calculates stock price change over a selected time period |
| get_company_overview | Retrieves P/E ratio, EPS, market cap, and 52-week range |
| get_market_status | Checks whether major U.S. exchanges are open or closed |
| get_top_gainers_losers | Returns top gainers, losers, and active stocks |
| get_news_sentiment | Retrieves recent headlines and sentiment scores |
| query_local_db | Runs SELECT queries against the local SQLite stock database |

## ⚙️ How to Run

1. **Install Dependencies**: Ensure you have `streamlit`, `yfinance`, `pandas`, and your required LLM provider client installed.
2. **Set Environment Variables**: Configure `config.py` with your active LLM model and API keys.
3. **Run the App**:
   ```bash
   streamlit run app.py
   ```
4. **Interact**: Select an architecture from the sidebar and ask financial questions (e.g., "What is the P/E ratio for AAPL and MSFT?", "Which tech stocks are the top gainers today?").