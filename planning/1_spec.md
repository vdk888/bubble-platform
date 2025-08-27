# 📋 Development Navigation

**📄 Documentation Structure:**
- **[spec.md](./spec.md)** *(current)* - Original product specification and system requirements
- **[jira.md](./jira.md)** - User stories and acceptance criteria organized by epics
- **[roadmap.md](./roadmap.md)** - Version roadmap (MVP → V1 → V2) with epic distribution
- **[plan_overview.md](./plan_overview.md)** - High-level architecture vision and microservices overview  
- **[plan_phased.md](./plan_phased.md)** - Detailed implementation plan with file structure and development phases
- **[plan_detailed.md](./plan_detailed.md)** - Complete technical specification with microservices architecture

---

# Product Specification – Investment Strategy App
1. Overview

The application is a web-based investment platform (Flask or React frontend, API-based backend) designed to automate the construction, monitoring, and execution of investment strategies.
Its core objective is to:

Define investment universes,

Apply timing indicators,

Construct portfolio strategies,

Aggregate them into a risk parity master portfolio,

Automate rebalancing and broker execution,

Provide a clean and intuitive user interface.

2. Core Components

Universe Definition (What do I buy?)

Define a set of assets (e.g., ETFs, stocks, bonds, commodities) with temporal evolution tracking.

Each universe is flexible and customizable with time-series composition data.

**Temporal Universe Features:**
- **Universe snapshots stored for each rebalancing period (monthly/quarterly)**
- **Historical composition tracking to eliminate survivorship bias**
- **Turnover analysis between periods with cost impact estimation**
- **Dynamic screening application creating point-in-time snapshots**

API for creating, modifying, and retrieving universes and their historical evolution.

Indicators & Signals (When do I buy?)

**Technical Indicators:**
- **RSI (Relative Strength Index)**: 14-period default, signals on overbought (>70) / oversold (<30)
- **MACD (Moving Average Convergence Divergence)**: 12,26,9 parameters with crossover signals
- **Momentum**: Simple rate of change with configurable lookback periods (±2% thresholds)
- **ROIC-based filters**: Return on Invested Capital screening for asset selection

**Signal Generation:**
- **Output format**: Standardized signals (-1 = sell, 0 = hold, 1 = buy)
- **Composite signals**: Weighted combination of multiple indicators with configurable weights
- **Signal validation**: Real-time data freshness checks (reject data >15min old)
- **Conflict resolution**: Hierarchical priority system (MACD > RSI > Momentum)

**Data Quality Controls:**
- **Input validation**: OHLCV format verification, timestamp ordering, completeness checks
- **Error handling**: Graceful degradation when indicator calculations fail
- **Audit logging**: All signal generation events logged with timestamps and parameters

**API Endpoints:**
- **GET /api/v1/indicators/default** - Retrieve default indicator configurations
- **POST /api/v1/indicators/calculate** - Calculate individual indicators from market data
- **POST /api/v1/signals/generate** - Generate composite signals with custom weights

Visualize buy/sell signals on charts.

Portfolio Strategy (How much do I buy?)

Define allocation rules for a given universe and signals.

Simulate weights, performance, and risk.

Track weight evolution and universe composition evolution over time.

API for portfolio optimization and backtesting results.

Master Portfolio (Key Component)

Aggregates all validated strategies (“pockets”).

Allocates capital using risk parity methodology or another allocation strategy.

Continuously rebalanced based on performance and metrics from backtests and live data.

Serves as the user’s central investment portfolio.

API for allocation updates and execution signals.

3. System Flow (Architecture Diagram)
   ┌───────────────────┐
   │ Universe          │  (What do I buy?)  
   │  - ETFs, Stocks   │
   │  - Custom Assets  │
   └─────────┬─────────┘
             │
   ┌─────────▼─────────┐
   │ Indicators         │ (When do I buy?)  
   │  - Signals         │
   │  - Charts          │
   └─────────┬─────────┘
             │
   ┌─────────▼─────────┐
   │ Portfolio Strategy │ (How much do I buy?)  
   │  - Weights         │
   │  - Backtests       │
   └─────────┬─────────┘
             │
   ┌─────────▼─────────┐
   │ Allocator Master │ (Key component)  
   │ Portfolio          │
   │  - Aggregation     │
   │  - Rebalancing     │
   └─────────┬─────────┘
             │
   ┌─────────▼─────────┐
   │ Broker Execution   │
   │  - Orders sent     │
   │  - Notifications  │
   └───────────────────┘

4. User Interface Requirements

Step 1: Display universes (asset lists, filters).

Step 2: Show indicators and buy/sell signals on interactive charts.

Step 3: Display portfolio weights and their evolution.

Step 4: Show master portfolio allocation within risk parity.

Backtesting & Live Performance (Critical Feature):

Graphs for pocket backtest results.

Graphs for live performance of each pocket.

Graphs for master portfolio backtest results.

Graphs for live master portfolio performance.

Notifications for daily rebalancing and broker executions.

5. Daily Workflow

Aggregate updated positions from each selected pocket.

Compute new allocations for the risk parity master portfolio.

Send execution orders automatically to brokers via API.

Notify users of executed trades and portfolio changes.

6. Additional Features

User Management: Authentication, role management.

Payments: Subscription-based model (Stripe integration).

Backtesting Engine: Strategy simulation with performance and risk metrics. **Backtesting uses historical universe composition to avoid survivorship bias.**

Live Monitoring: Real-time tracking of strategies and portfolios.

Scalability: Modular APIs for universes, signals, strategies, and master portfolio.