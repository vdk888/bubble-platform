# 📋 Development Navigation

**📄 Documentation Structure:**
- **[spec.md](./spec.md)** - Original product specification and system requirements
- **[jira.md](./jira.md)** - User stories and acceptance criteria organized by epics
- **[roadmap.md](./roadmap.md)** - Version roadmap (MVP → V1 → V2) with epic distribution
- **[plan_overview.md](./plan_overview.md)** *(current)* - High-level architecture vision and microservices overview  
- **[plan_phased.md](./plan_phased.md)** - Detailed implementation plan with file structure and development phases
- **[plan_detailed.md](./plan_detailed.md)** - Complete technical specification with microservices architecture

---

# 🚀 **BUBBLE PLATFORM - ARCHITECTURE OVERVIEW**

## 🎯 **Vision System**

**Plateforme SaaS de trading algorithmique** avec 3 composants principaux :
- **Pocket Factory** : Création de stratégies avec screening dynamique (ROIC > sector median)
- **Master Portfolio** : Allocation et gestion de risque multi-stratégies
- **Execution Engine** : Exécution multi-broker temps réel

**Objectif** : Transformer l'idée → stratégie validée → portefeuille → ordres → notification en workflow automatisé et scalable.

---

## 🏗️ **Architecture Microservices (6 Services Core)**

### **🔐 Auth Service**
- **Rôle** : Authentification utilisateurs, permissions, isolation multi-tenant
- **APIs clés** : `/auth/login`, `/users/profile`, `/admin/users`
- **Features** : JWT tokens, OAuth (Google/GitHub), 2FA, RBAC, Row Level Security
- **Multi-tenancy** : Un utilisateur = un tenant avec isolation complète des données

### **💳 Billing Service** 
- **Rôle** : Abonnements SaaS, gestion paiements, quotas par plan
- **APIs clés** : `/subscriptions`, `/payments`, `/invoices`, `/webhooks/stripe`
- **Features** : Plans Free/Pro/Enterprise, intégration Stripe, quotas usage, factures PDF
- **Business** : Monétisation avec limites par plan (ex: 3 stratégies Free vs 50 Pro)

### **🏭 Pocket Factory Service**
- **Rôle** : Création stratégies, screening d'univers dynamique, backtesting
- **APIs clés** : `/universes`, `/strategies`, `/backtests`, `/indicators`
- **Features principales** :
  - **Screening dynamique** : ROIC > sector median, P/E, croissance, qualité
  - **Indicateurs** : Techniques (RSI, MACD) + alternatifs (Reddit sentiment)
  - **Moteurs backtest** : Basic, VectorBT, QuantConnect, custom
  - **Univers évolutifs** : Mise à jour mensuelle/trimestrielle avec turnover tracking
  - **🚀 NEW: Temporal Universe System** : Point-in-time snapshots, survivorship bias elimination, historical composition tracking

### **🏛️ Master Portfolio Service**
- **Rôle** : Allocation capital entre stratégies, risk parity, rééquilibrage automatique
- **APIs clés** : `/portfolios`, `/allocations`, `/rebalancing`, `/performance`
- **Features principales** :
  - **Allocateurs multiples** : Risk parity, equal weight, momentum, ML-based
  - **Rééquilibrage intelligent** : Seuils de drift, coûts de transaction optimisés
  - **Risk monitoring** : VaR, Expected Shortfall, corrélations, limites d'exposition

### **⚡ Execution Service**
- **Rôle** : Routage et exécution d'ordres multi-broker
- **APIs clés** : `/orders`, `/positions`, `/executions`, `/brokers/status`
- **Brokers supportés** : Alpaca (stocks/ETF), Interactive Brokers (options), Crypto.com
- **Features** : Routage intelligent, réconciliation positions, contrôles risque pré-trade

### **📡 Data Service**
- **Rôle** : Données market temps réel, cache intelligent, données alternatives
- **APIs clés** : `/market-data`, `/real-time`, `/alternative-data`, `/cache`
- **Sources** : Yahoo Finance, Alpha Vantage, Polygon, Reddit scraping, Twitter sentiment
- **Features** : Cache Redis multi-TTL, validation qualité, streaming WebSocket

### **🔔 Notification Service**
- **Rôle** : Alertes et notifications multi-canal
- **APIs clés** : `/alerts`, `/notifications`, `/channels`
- **Canaux** : Email, Telegram, Slack, SMS
- **Features** : Règles d'alerte configurables, escalade, cooldown

### **🤖 AI Agent Service**
- **Rôle** : Interface conversationnelle intelligente pour toute la plateforme
- **APIs clés** : `/chat`, `/chat/history`, `/tools`, `/ws/chat`
- **Features principales** :
  - **Interface naturelle** : Remplace complètement l'UI traditionnelle si désiré
  - **Tool calling** : Appel de tous les APIs de la plateforme via langage naturel
  - **Génération de graphiques** : Visualisation automatique des résultats
  - **Workflows complexes** : Chaînage d'opérations multiples en une conversation
  - **Confirmations sécurisées** : Validation utilisateur pour actions critiques

---

## 🌐 **Frontend Applications (React + TypeScript)**

### **🔍 Pocket Factory UI**
#### **Screening Interface** 
- **Configuration avancée** : ROIC vs sector, P/E percentiles, croissance, qualité
- **Aperçu temps réel** : Nombre d'actions, métriques moyennes, diversification
- **Résultats détaillés** : Table par période, turnover analysis, impact des critères

#### **Strategy Builder**
- **Étapes** : Univers → Indicateurs → Backtest → Validation
- **Indicateurs** : Paramètres optimisables, aperçu signaux, poids ajustables
- **Backtest** : Performance, métriques, trades, validation vs critères

### **📊 Master Portfolio UI**  
#### **Dashboard Principal**
- **KPIs** : Performance, allocation, drawdown, Sharpe ratio
- **Graphiques** : Evolution portfolio, allocation pie chart, corrélations
- **Monitoring** : Positions temps réel, ordres en cours, statut brokers

#### **Rebalancing Center**
- **Contrôles** : Déclenchement manuel/automatique, dry-run, seuils
- **Aperçu** : Ordres calculés, coûts estimés, impact market
- **Historique** : Timeline rééquilibrages, performance attribution

#### **Billing Dashboard**
- **Abonnement** : Plan actuel, usage vs quotas, factures
- **Paiements** : Méthodes, historique, upgrade/downgrade

### **🤖 AI Chat Interface**
#### **Interface Conversationnelle**
- **Mode complet** : Interface chat en remplacement total de l'UI traditionnelle
- **Mode hybride** : Chat overlay sur l'interface classique
- **Multi-modal** : Réponses texte + graphiques + tableaux + actions
- **Sécurité** : Confirmations requises pour actions critiques (trades, rééquilibrage)

#### **Exemples d'Usage**
- *"Montre-moi un backtest momentum sur les large caps US des 2 dernières années"*
- *"Rééquilibre mon portefeuille avec pondération égale"*
- *"Crée un univers avec ROIC > médiane sectorielle"*
- *"Analyse les performances de mes stratégies ce mois"*

### **🧩 Shared Components Library**
- **UI Components** : Buttons, forms, tables, modals standardisés
- **Finance Components** : Charts (performance, allocation), metric cards, risk gauges
- **Billing Components** : Subscription cards, usage bars, payment forms
- **Chat Components** : Message bubbles, chart renderers, confirmation dialogs
- **Storybook** : Documentation et tests des composants

---

## 🔗 **Infrastructure Partagée**

### **💾 Database Architecture**
- **PostgreSQL** : Base principale avec Row Level Security (RLS)
- **Multi-tenancy** : Isolation par user_id avec politiques automatiques
- **Tables principales** : users, strategies, portfolios, orders, performance_snapshots
- **Migrations** : Alembic pour évolution schema contrôlée

### **📨 Event System**
- **Architecture** : Event-driven avec Redis pub/sub
- **Events clés** : strategy.created, portfolio.rebalanced, order.filled
- **Benefits** : Découplage services, observabilité, scalabilité

### **⚡ Cache Strategy**
- **Redis** : Cache intelligent multi-TTL
- **Stratégies** : Market data (5min trading / 1h closed), backtests (1 semaine)
- **Invalidation** : Event-driven smart invalidation

### **📊 Monitoring Stack**
- **Métriques** : Prometheus + Grafana dashboards
- **Logs** : Loki + Promtail aggregation
- **Tracing** : Jaeger distributed tracing
- **Alertes** : Alertmanager → Email/Slack/PagerDuty

---

## 🚀 **Déploiement & Infrastructure**

### **🐳 Containerization**
- **Docker** : Images par service + frontend
- **Environments** : docker-compose dev, staging, production
- **Multi-stage builds** : Optimisation taille images

### **☸️ Kubernetes**
- **Services** : Deployments avec HPA (Horizontal Pod Autoscaler)
- **Databases** : StatefulSets pour PostgreSQL, Deployments pour Redis
- **Ingress** : Nginx avec TLS automatique
- **Namespaces** : Isolation dev/staging/prod

### **🏗️ Infrastructure as Code**
- **Terraform** : Modules pour VPC, EKS, RDS, ElastiCache
- **Environments** : Configuration par environnement (dev/staging/prod)
- **State management** : Backend S3 + DynamoDB locking

### **🔄 CI/CD Pipeline**
- **GitHub Actions** : Test → Build → Deploy automatisé
- **ArgoCD** : GitOps deployment avec sync automatique
- **Testing** : Unit, integration, e2e tests
- **Security** : Container scanning, secrets management

---

## 📈 **Features Avancées**

### **🎯 Dynamic Universe Screening** 🚀 **ENHANCED**
- **Multi-critères** : Fundamental, quality, momentum, value, ESG
- **Évolution temporelle** : Monthly/quarterly refresh avec turnover analysis
- **🚀 NEW: Temporal Snapshots** : Point-in-time universe compositions with full metadata preservation
- **🚀 NEW: Survivorship Bias Elimination** : Historical compositions for accurate backtesting
- **Impact analysis** : Coûts de transition, attribution performance, turnover cost estimation
- **Data sources** : Financial APIs, analyst estimates, alternative data
- **🚀 NEW: Timeline Visualization** : Frontend table showing universe evolution by date/period

### **🧠 Alternative Data Integration**
- **Social sentiment** : Reddit scraping, Twitter buzz, news analysis
- **Custom indicators** : Proprietary scoring, trend detection
- **Real-time** : Streaming sentiment updates, social momentum signals

### **⚖️ Advanced Risk Management**
- **Multi-level** : Portfolio, strategy, position-level controls
- **Real-time monitoring** : VaR breaches, correlation alerts, exposure limits
- **Pre-trade checks** : Position limits, sector concentration, liquidity

### **🔒 Enterprise Security**
- **Multi-tenancy** : Complete data isolation per user
- **Authentication** : OAuth, 2FA, session management
- **Network security** : Network policies, pod security, RBAC
- **Secrets** : HashiCorp Vault, sealed secrets, certificate management

---

## 🎯 **Business Model & Scalability**

### **💰 SaaS Monetization**
- **Free Plan** : 3 stratégies, backtest limité
- **Pro Plan** : 50 stratégies, données alternatives, support prioritaire
- **Enterprise** : Illimité, custom features, SLA

### **📊 Performance Targets**
- **Latency** : < 200ms API response (95th percentile)
- **Uptime** : 99.9% availability
- **Throughput** : 1000+ req/s sustained
- **Cache hit rate** : > 80% market data

### **🚀 Scalability Design**
- **Horizontal scaling** : Kubernetes HPA sur tous services
- **Database** : Read replicas, connection pooling
- **Cache** : Redis cluster, intelligent pre-warming
- **Event bus** : Redis streams pour high throughput

---

Cette architecture modulaire permet une **innovation continue** tout en maintenant la **robustesse** et la **scalabilité** nécessaires pour une plateforme SaaS financière professionnelle.