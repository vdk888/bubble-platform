# Directory Structure

```
bubble-platform/
├── services/
│   ├── auth-service/
│   │   ├── app/
│   │   │   ├── models/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   │   ├── auth/
│   │   │   │   ├── permissions/
│   │   │   │   └── tenancy/
│   │   │   ├── services/
│   │   │   ├── config/
│   │   │   └── utils/
│   │   └── tests/
│   │       ├── unit/
│   │       └── integration/
│   ├── billing-service/
│   │   ├── app/
│   │   │   ├── models/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   │   ├── stripe/
│   │   │   │   ├── billing/
│   │   │   │   ├── quotas/
│   │   │   │   └── notifications/
│   │   │   ├── services/
│   │   │   ├── config/
│   │   │   └── utils/
│   │   └── tests/
│   │       ├── unit/
│   │       └── integration/
│   ├── pocket-factory-service/
│   │   ├── app/
│   │   │   ├── models/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   │   ├── indicators/
│   │   │   │   ├── universe/
│   │   │   │   │   ├── screeners/
│   │   │   │   │   ├── evolution/
│   │   │   │   │   └── data_sources/
│   │   │   │   └── backtest/
│   │   │   │       └── engines/
│   │   │   ├── services/
│   │   │   ├── config/
│   │   │   └── utils/
│   │   └── tests/
│   │       ├── unit/
│   │       └── integration/
│   ├── master-portfolio-service/
│   │   ├── app/
│   │   │   ├── models/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   │   ├── allocators/
│   │   │   │   ├── rebalancing/
│   │   │   │   ├── risk/
│   │   │   │   └── performance/
│   │   │   ├── services/
│   │   │   ├── config/
│   │   │   └── utils/
│   │   └── tests/
│   │       ├── unit/
│   │       └── integration/
│   ├── execution-service/
│   │   ├── app/
│   │   │   ├── models/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   │   ├── brokers/
│   │   │   │   ├── routing/
│   │   │   │   ├── execution/
│   │   │   │   └── risk/
│   │   │   ├── services/
│   │   │   ├── config/
│   │   │   └── utils/
│   │   └── tests/
│   │       ├── unit/
│   │       └── integration/
│   ├── data-service/
│   │   ├── app/
│   │   │   ├── models/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   │   ├── providers/
│   │   │   │   ├── cache/
│   │   │   │   ├── aggregation/
│   │   │   │   ├── validation/
│   │   │   │   └── streaming/
│   │   │   ├── services/
│   │   │   ├── config/
│   │   │   └── utils/
│   │   └── tests/
│   │       ├── unit/
│   │       └── integration/
│   ├── notification-service/
│   │   ├── app/
│   │   │   ├── models/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   │   ├── channels/
│   │   │   │   ├── rules/
│   │   │   │   ├── engines/
│   │   │   │   ├── templates/
│   │   │   │   └── processors/
│   │   │   ├── services/
│   │   │   ├── config/
│   │   │   └── utils/
│   │   └── tests/
│   │       ├── unit/
│   │       └── integration/
│   └── ai-agent-service/
│       ├── app/
│       │   ├── models/
│       │   ├── api/
│       │   ├── core/
│       │   │   ├── claude/
│       │   │   ├── tools/
│       │   │   ├── processors/
│       │   │   ├── memory/
│       │   │   ├── security/
│       │   │   └── workflows/
│       │   ├── services/
│       │   ├── config/
│       │   └── utils/
│       └── tests/
│           ├── unit/
│           │   └── test_tools/
│           └── integration/
├── shared/
│   ├── core/
│   │   ├── domain/
│   │   ├── interfaces/
│   │   ├── exceptions/
│   │   └── utils/
│   ├── events/
│   ├── database/
│   │   ├── models/
│   │   ├── migrations/
│   │   │   └── versions/
│   │   └── repositories/
│   └── monitoring/
│       ├── metrics/
│       ├── logging/
│       ├── tracing/
│       ├── health/
│       └── dashboards/
│           ├── grafana/
│           └── prometheus/
├── web/
│   ├── pocket-factory-ui/
│   │   ├── public/
│   │   └── src/
│   │       ├── components/
│   │       │   ├── UniverseSelector/
│   │       │   │   ├── StaticUniverse/
│   │       │   │   └── DynamicUniverse/
│   │       │   │       └── ScreenResults/
│   │       │   ├── IndicatorConfig/
│   │       │   ├── BacktestResults/
│   │       │   ├── StrategyBuilder/
│   │       │   ├── AIChat/
│   │       │   │   ├── ToolExecution/
│   │       │   │   ├── Visualizations/
│   │       │   │   ├── ConversationHistory/
│   │       │   │   ├── InterfaceModes/
│   │       │   │   ├── QuickActions/
│   │       │   │   └── Settings/
│   │       │   └── shared/
│   │       ├── hooks/
│   │       ├── services/
│   │       ├── utils/
│   │       ├── styles/
│   │       └── types/
│   ├── master-portfolio-ui/
│   │   ├── public/
│   │   └── src/
│   │       ├── components/
│   │       │   ├── PortfolioDashboard/
│   │       │   ├── AllocationMatrix/
│   │       │   ├── RebalancingControls/
│   │       │   ├── OrderExecution/
│   │       │   ├── PerformanceAnalytics/
│   │       │   ├── BillingManager/
│   │       │   └── shared/
│   │       ├── hooks/
│   │       ├── services/
│   │       ├── utils/
│   │       ├── styles/
│   │       └── types/
│   └── shared-components/
│       ├── src/
│       │   ├── components/
│       │   │   ├── ui/
│       │   │   │   ├── Button/
│       │   │   │   ├── Input/
│       │   │   │   ├── Modal/
│       │   │   │   ├── Table/
│       │   │   │   └── Form/
│       │   │   ├── charts/
│       │   │   │   ├── LineChart/
│       │   │   │   ├── PieChart/
│       │   │   │   ├── BarChart/
│       │   │   │   ├── Heatmap/
│       │   │   │   └── CandlestickChart/
│       │   │   ├── finance/
│       │   │   │   ├── MetricCard/
│       │   │   │   ├── PerformanceChart/
│       │   │   │   ├── AllocationPie/
│       │   │   │   ├── RiskGauge/
│       │   │   │   ├── OrderTable/
│       │   │   │   ├── BillingComponents/
│       │   │   │   │   ├── SubscriptionCard/
│       │   │   │   │   ├── PlanCard/
│       │   │   │   │   ├── UsageBar/
│       │   │   │   │   └── PaymentForm/
│       │   │   │   └── ChatComponents/
│       │   │   │       ├── MessageBubble/
│       │   │   │       ├── ChatInput/
│       │   │   │       ├── ToolCallRenderer/
│       │   │   │       ├── ConversationList/
│       │   │   │       ├── ConfirmationDialog/
│       │   │   │       └── ChatVisualization/
│       │   │   └── layout/
│       │   │       ├── Header/
│       │   │       ├── Sidebar/
│       │   │       ├── Layout/
│       │   │       └── Navigation/
│       │   ├── hooks/
│       │   ├── utils/
│       │   ├── styles/
│       │   │   └── themes/
│       │   └── types/
│       ├── .storybook/
│       └── stories/
└── infrastructure/
    ├── docker/
    │   ├── services/
    │   ├── web/
    │   └── infrastructure/
    ├── kubernetes/
    │   ├── namespaces/
    │   ├── services/
    │   │   ├── pocket-factory/
    │   │   ├── master-portfolio/
    │   │   ├── execution/
    │   │   ├── data/
    │   │   └── notification/
    │   ├── databases/
    │   │   ├── postgres/
    │   │   └── redis/
    │   ├── ingress/
    │   ├── monitoring/
    │   │   ├── prometheus/
    │   │   ├── grafana/
    │   │   └── jaeger/
    │   └── secrets/
    ├── terraform/
    │   ├── modules/
    │   │   ├── vpc/
    │   │   ├── eks/
    │   │   ├── rds/
    │   │   └── elasticache/
    │   ├── environments/
    │   │   ├── dev/
    │   │   ├── staging/
    │   │   └── prod/
    │   └── scripts/
    ├── monitoring/
    │   ├── prometheus/
    │   ├── grafana/
    │   │   ├── dashboards/
    │   │   ├── datasources/
    │   │   └── provisioning/
    │   ├── loki/
    │   ├── jaeger/
    │   └── alertmanager/
    │       └── templates/
    ├── ci-cd/
    │   ├── github-actions/
    │   │   ├── .github/
    │   │   │   └── workflows/
    │   │   └── scripts/
    │   ├── jenkins/
    │   │   └── scripts/
    │   └── argocd/
    │       ├── applications/
    │       └── projects/
    ├── security/
    │   ├── policies/
    │   ├── secrets/
    │   │   ├── sealed-secrets/
    │   │   └── vault/
    │   └── certificates/
    ├── backup/
    │   ├── database/
    │   │   └── restore-scripts/
    │   ├── volumes/
    │   │   └── velero/
    │   └── configurations/
    └── scripts/
        ├── setup/
        ├── maintenance/
        ├── migration/
        └── monitoring/
```