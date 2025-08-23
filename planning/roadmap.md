# 📋 Development Navigation

**📄 Documentation Structure:**
- **[spec.md](./spec.md)** - Original product specification and system requirements
- **[jira.md](./jira.md)** - User stories and acceptance criteria organized by epics
- **[roadmap.md](./roadmap.md)** *(current)* - Version roadmap (MVP → V1 → V2) with epic distribution
- **[plan_overview.md](./plan_overview.md)** - High-level architecture vision and microservices overview  
- **[plan_phased.md](./plan_phased.md)** - Detailed implementation plan with file structure and development phases
- **[plan_detailed.md](./plan_detailed.md)** - Complete technical specification with microservices architecture

---

| Version | Focus                                         | Epics / Features                                                                                                                                                                                                                                                                       |
| ------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **MVP** | Core automation + basic visualization         | - Universe Management (manual selection only) <br> - Indicators & Signals (basic) <br> - Portfolio Strategy (weights + simple backtest) <br> - Risk Parity Master Portfolio aggregation <br> - Daily rebalancing + notifications <br> - **AI Agent Interface (basic chat with tool calling)** <br> - Basic user management                          |
| **v1**  | Advanced universe filtering + live monitoring | - Universe Management (screener/filtering by metrics) <br> - Enhanced indicators (multiple indicators + chart overlays) <br> - Pocket live performance visualization <br> - Master portfolio live tracking <br> - Improved backtesting charts (equity curve, drawdown, rolling Sharpe) <br> - **AI Agent Advanced Features (workflow orchestration, proactive insights, enhanced interface modes)** |
| **v2**  | Full product polish + payments & scalability  | - Payment integration (Stripe) <br> - Subscription tier management <br> - Full API modularization for universes, signals, strategies, master portfolio <br> - **AI Agent Microservice (dedicated service extraction, enterprise security, multi-tenant context)** <br> - Notifications and reporting enhancements <br> - Scalability and performance optimization                                 |
