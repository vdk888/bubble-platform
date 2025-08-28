# 📋 Development Navigation

**📄 Documentation Structure:**
- **[spec.md](./spec.md)** - Original product specification and system requirements
- **[jira.md](./jira.md)** *(current)* - User stories and acceptance criteria organized by epics
- **[roadmap.md](./roadmap.md)** - Version roadmap (MVP → V1 → V2) with epic distribution
- **[plan_overview.md](./plan_overview.md)** - High-level architecture vision and microservices overview  
- **[plan_phased.md](./plan_phased.md)** - Detailed implementation plan with file structure and development phases
- **[plan_detailed.md](./plan_detailed.md)** - Complete technical specification with microservices architecture

---

# Jira Backlog – Investment Strategy App (Updated with Screener)
Epic 1 – Universe Management (Advanced with Screener)

User Stories

As a user, I want to define a custom investment universe by manually selecting assets so that I can control which assets are included in my strategy.

Acceptance Criteria:

Users can add/remove assets manually.

Universes are saved, edited, and retrievable via API.

As a user, I want to filter and screen assets based on metrics (e.g., sector, market cap, P/E ratio, ROIC) so that I can create a universe using advanced criteria.

Acceptance Criteria:

Screener allows filtering by multiple metrics.

Filtered results can be added directly to the universe.

Screener results update dynamically.

As a user, I want to view my universe in a clean interface so that I can validate the assets I selected or filtered.

Acceptance Criteria:

Table view of assets with key metrics.

Editable list (add/remove from universe).

**As a user, I want to view my universe evolution over time so that I can understand how my investment universe has changed and avoid survivorship bias in backtesting.**

**Temporal Universe Acceptance Criteria:**

- **Users can view universe evolution timeline (monthly/quarterly snapshots)**
- **Timeline shows assets added/removed in each period with turnover rates**  
- **Universe screening creates historical snapshots, not just current updates**
- **Each snapshot preserves point-in-time composition with metadata (screening criteria, performance metrics)**
- **Users can view universe composition at any historical date**
- **Backtest validation includes turnover impact analysis with transaction cost estimates**
- **Universe changes are tracked with reasons (screening results, manual additions/removals)**
- **Timeline interface allows drilling down into specific periods to see detailed asset changes**

Epic 2 – Indicators & Signals

User Stories

As a user, I want to attach indicators to my universe so that I can generate buy/sell signals.

Acceptance Criteria:

**Technical Implementation:**
- RSI calculation matches industry standards (14-period default, verified via unit tests)
- MACD signals generated using 12,26,9 default parameters with crossover detection
- Momentum indicators with configurable lookback periods and ±2% signal thresholds
- Signal output format: pandas Series with standardized -1, 0, 1 values

**Data Validation & Quality:**
- Market data freshness validation (reject data older than 15 minutes)
- Input validation for OHLCV format, timestamp ordering, and data completeness
- Signal conflict resolution with priority hierarchy: MACD > RSI > Momentum
- All signal generation events logged with timestamps, parameters, and audit trail

**Performance Requirements:**
- Indicator calculations complete within 2 seconds for 1000 assets
- API endpoints respond within 500ms (95th percentile)
- Graceful error handling when indicator calculations fail

**API Functionality:**
- GET /api/v1/indicators/default returns proper configuration objects
- POST /api/v1/indicators/calculate processes market data and returns indicator signals
- POST /api/v1/signals/generate creates weighted composite signals from multiple indicators

As a user, I want to visualize signals on interactive charts so that I can understand when trades are triggered.

Acceptance Criteria:

Chart displays asset price with overlaid buy/sell markers.

Signals update dynamically when parameters change.

**As a user, I want access to professional-grade financial data through OpenBB integration so that I have institutional-quality data for analysis.**

**OpenBB Integration Acceptance Criteria:**

**Data Integration & Quality:**
- OpenBB Terminal SDK integrated as primary data provider with fallback chain
- Fundamental data includes financial statements, ratios, and sector comparisons
- Economic indicators (GDP, inflation, unemployment) available for macro analysis
- News sentiment analysis provides scored sentiment data for assets
- Analyst estimates and insider trading data accessible through unified API
- Data quality monitoring compares OpenBB results with Yahoo/Alpha Vantage for validation

**Performance & Reliability:**
- OpenBB data requests complete within 1 second for fundamental data
- Error handling: Graceful fallback to Yahoo Finance if OpenBB fails
- Cost tracking: Monitor OpenBB usage to optimize between free and premium tiers
- Provider health monitoring with automatic failover

**API Enhancement Requirements:**
- GET /api/v1/market-data/fundamentals returns OpenBB fundamental data
- GET /api/v1/market-data/economics provides economic indicator time series
- GET /api/v1/market-data/news-sentiment delivers scored news sentiment
- GET /api/v1/market-data/analyst-estimates provides consensus analyst data
- GET /api/v1/market-data/insider-trading provides insider activity tracking
- All endpoints maintain consistent response format with existing APIs

**Integration Testing:**
- Triple-provider fallback chain (OpenBB → Yahoo → Alpha Vantage) tested under failure scenarios
- Data consistency validation between providers with conflict resolution
- Performance benchmarks for all new OpenBB endpoints
- Cost monitoring and usage optimization for OpenBB API calls

Epic 3 – Portfolio Strategy

User Stories

As a user, I want to define allocation rules so that I can control how much of each asset is bought.

Acceptance Criteria:

User can set rules (weights, max drawdown constraints, etc.).

Portfolio weights are stored and retrievable.

As a user, I want to run a backtest of my portfolio so that I can validate its performance.

Acceptance Criteria:

Backtest runs on historical data.

Metrics (CAGR, Sharpe, drawdown) are displayed.

Equity curve and rolling stats are shown on graphs.

As a user, I want to see the live performance of my portfolio so that I can track it against the backtest.

Acceptance Criteria:

Live P&L and allocation updates daily.

Results shown in both numbers and charts.

Epic 4 – Risk Parity Master Portfolio

User Stories

As a user, I want to integrate all my validated pockets into a risk parity master portfolio so that my risk is balanced across strategies.

Acceptance Criteria:

Pockets can be added/removed from the master portfolio.

Capital allocation is determined by risk parity methodology.

As a user, I want to see the backtest of my master portfolio so that I can validate global performance.

Acceptance Criteria:

Master portfolio backtest shows equity curve, risk, and metrics.

As a user, I want to monitor the live performance of the master portfolio so that I know how it evolves in real time.

Acceptance Criteria:

Daily updates of weights, P&L, and allocation charts.

Epic 5 – Broker Execution

User Stories

As a user, I want the app to rebalance my portfolio daily so that I always follow the strategy without manual effort.

Acceptance Criteria:

Rebalancing occurs automatically once per day.

Orders are generated and sent to broker via API.

Execution summary is displayed.

As a user, I want to receive notifications when trades are executed so that I am informed of portfolio changes.

Acceptance Criteria:

Notifications are sent (email/push).

Trade details are included (symbol, quantity, price).

Epic 6 – Backtesting & Performance Visualization

User Stories

As a user, I want to see pocket backtests so that I can compare individual strategies.

Acceptance Criteria:

Graphs show equity curve, drawdown, rolling Sharpe, etc.

As a user, I want to see live pocket performance so that I can validate robustness.

Acceptance Criteria:

Daily updates shown on performance graphs.

As a user, I want to compare master portfolio backtest vs live so that I can measure tracking error.

Acceptance Criteria:

Both curves are visible on one chart.

Key metrics are recalculated daily.

Epic 7 – User Management

User Stories

As a user, I want to create an account so that my portfolios and preferences are stored.

Acceptance Criteria:

Registration/login with email & password.

Secure storage of user data.

As a user, I want to manage my subscriptions so that I can control my access.

Acceptance Criteria:

Subscription tier visible in profile.

User can upgrade/downgrade.

Epic 8 – AI Agent Interface

User Stories

As a user, I want to interact with the platform through natural language so that I can manage my portfolios conversationally.

Acceptance Criteria:

Chat interface available on all pages.

Natural language commands translate to API calls.

Multi-modal responses (text, charts, tables).

As a user, I want the AI agent to execute platform operations through tool calling so that I can perform complex workflows through conversation.

Acceptance Criteria:

AI agent can create universes, run backtests, and generate visualizations.

Tool calls are executed with proper error handling.

Results are displayed in chat with interactive elements.

As a user, I want critical actions to require confirmation so that I'm protected from accidental financial operations.

Acceptance Criteria:

Rebalancing, order placement, and portfolio modifications require explicit confirmation.

Confirmation dialogs show detailed action summaries and costs.

Users can approve or cancel critical actions.

As a user, I want to switch between traditional UI and chat interface so that I can choose my preferred interaction method.

Acceptance Criteria:

Mode toggle available (Traditional UI ↔ Chat).

Interface preferences are saved per user.

Full-screen chat mode available as alternative to traditional dashboard.

As a user, I want conversation history and context management so that the AI remembers our previous interactions.

Acceptance Criteria:

Conversation history is saved and searchable.

AI maintains context about my portfolios and preferences.

Context-aware suggestions and proactive insights.

Epic 9 – Payments

User Stories

As a user, I want to subscribe via Stripe so that I can pay securely.

Acceptance Criteria:

Payments processed via Stripe API.

Receipts emailed automatically.

✅ This structure gives you:

Epics = 9 big chunks of work.

Stories = concrete deliverables.

Acceptance Criteria = testable "definition of done."