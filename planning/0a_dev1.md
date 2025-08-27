
## 🛡️ **Cybersécurité : Security by Design**

### **🎯 Principe Fondamental**

La sécurité n'est **PAS** un add-on - elle est intégrée dans **chaque décision** dès les fondations.

### **📅 Timeline Sécurité par Phase**

### **📅 Phase 0 : Fondations (Jour 1-5)**

**Architecture Security-First**

```python
# backend/app/core/[security.py](http://security.py) - DÈS LE DÉBUT
from passlib.context import CryptContext
from jose import jwt
import secrets

class SecurityConfig:
    # Secrets management
    SECRET_KEY = secrets.token_urlsafe(32)  # Généré automatiquement
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
    # Password hashing
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # Security headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
    }
```

**Configuration Sécurisée Immédiate**

```yaml
# docker-compose.yml - SÉCURISÉ DÈS LE DÉBUT
version: '3.8'
services:
  backend:
    environment:
      # JAMAIS de secrets en dur
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}  # Depuis .env
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}  # Depuis .env
    networks:
      - bubble_secure_network  # Réseau isolé

  db:
    environment:
      - POSTGRES_PASSWORD=${DB_PASSWORD}  # Jamais "password123"
    volumes:
      - db_data:/var/lib/postgresql/data:Z  # SELinux labels
    networks:
      - bubble_secure_network

networks:
  bubble_secure_network:
    driver: bridge
    internal: false  # Contrôlé
```

### **📅 Phase 1 : MVP Core (Semaine 1-4)**

**Authentication & Authorization ROBUSTE**

```python
# backend/app/core/[auth.py](http://auth.py) - SEMAINE 1
from datetime import datetime, timedelta
import bcrypt
from jose import jwt, JWTError

class AuthService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def hash_password(self, password: str) -> str:
        """Hash password with salt - SÉCURITÉ IMMÉDIATE"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password - protection contre timing attacks"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, data: dict, expires_delta: timedelta = None):
        """JWT avec expiration COURTE"""
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

# Validation stricte dès le début
class PasswordValidator:
    @staticmethod
    def validate_password(password: str) -> bool:
        """Validation FORTE dès MVP"""
        if len(password) < 12:
            raise ValueError("Password must be at least 12 characters")
        if not [re.search](http://re.search)(r'[A-Z]', password):
            raise ValueError("Password must contain uppercase letter")
        if not [re.search](http://re.search)(r'[a-z]', password):
            raise ValueError("Password must contain lowercase letter")
        if not [re.search](http://re.search)(r'\d', password):
            raise ValueError("Password must contain number")
        if not [re.search](http://re.search)(r'[!@#$%^&*]', password):
            raise ValueError("Password must contain special character")
        return True
```

**Input Validation PARTOUT**

```python
# backend/app/core/[validators.py](http://validators.py) - SEMAINE 1
from pydantic import BaseModel, validator, Field
import re

class UserCreateRequest(BaseModel):
    email: str = Field(..., regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    password: str = Field(..., min_length=12)
    
    @validator('email')
    def validate_email(cls, v):
        # Protection contre injection
        if '<' in v or '>' in v or '"' in v:
            raise ValueError('Invalid email format')
        return v.lower().strip()
    
    @validator('password')
    def validate_password_strength(cls, v):
        return PasswordValidator.validate_password(v)

class PortfolioCreateRequest(BaseModel):
    name: str = Field(..., max_length=100, regex=r'^[a-zA-Z0-9\s\-_]+$')
    allocation: Dict[str, float] = Field(...)
    
    @validator('allocation')
    def validate_allocation_weights(cls, v):
        # Validation financière ET sécurité
        total = sum(v.values())
        if not (0.99 <= total <= 1.01):
            raise ValueError("Allocation weights must sum to 1.0")
        
        for symbol, weight in v.items():
            # Protection injection
            if not re.match(r'^[A-Z]{1,5}$', symbol):
                raise ValueError(f"Invalid symbol: {symbol}")
            if not 0 <= weight <= 1:
                raise ValueError(f"Invalid weight: {weight}")
        return v
```

### **📅 Phase 2 : Production Hardening (Semaine 5-8)**

**Database Security RENFORCÉE**

```python
# backend/app/core/[database.py](http://database.py) - SEMAINE 5
from sqlalchemy import create_engine, text

class SecureDatabase:
    def __init__(self):
        # Connection sécurisée
        self.engine = create_engine(
            settings.database_url,
            # Sécurité connexion
            pool_pre_ping=True,
            pool_recycle=3600,
            # Protection injection SQL
            echo=False,  # Jamais de logs SQL en prod
            # Connection security
            connect_args={
                "sslmode": "require",
                "application_name": "bubble_app"
            }
        )
    
    async def execute_query(self, query: str, params: dict = None):
        """Exécution sécurisée avec paramètres ONLY"""
        if params is None:
            params = {}
        
        # JAMAIS de string formatting dans les queries
        # TOUJOURS des paramètres bindés
        async with self.get_session() as session:
            result = await session.execute(text(query), params)
            return result.fetchall()

# Row Level Security OBLIGATOIRE
RLS_POLICIES = """
-- Isolation multi-tenant STRICTE
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;
CREATE POLICY portfolio_isolation ON portfolios
    FOR ALL TO bubble_app_role
    USING (user_id = current_setting('app.current_user_id'));

-- Audit trail protégé
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY audit_read_only ON audit_logs
    FOR SELECT TO bubble_app_role
    USING (user_id = current_setting('app.current_user_id'));
"""
```

**API Security COMPLÈTE**

```python
# backend/app/middleware/[security.py](http://security.py) - SEMAINE 6
from starlette.middleware.base import BaseHTTPMiddleware
import time

class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rate_limit: int = 100):
        super().__init__(app)
        self.rate_limit = rate_limit
        self.request_counts = {}  # En production: Redis
    
    async def dispatch(self, request: Request, call_next):
        # Rate limiting par IP
        client_ip = [request.client.host](http://request.client.host)
        current_time = time.time()
        
        if client_ip in self.request_counts:
            if current_time - self.request_counts[client_ip]['time'] < 60:
                if self.request_counts[client_ip]['count'] >= self.rate_limit:
                    return Response(status_code=429, content="Rate limit exceeded")
                self.request_counts[client_ip]['count'] += 1
            else:
                self.request_counts[client_ip] = {'time': current_time, 'count': 1}
        else:
            self.request_counts[client_ip] = {'time': current_time, 'count': 1}
        
        # Security headers
        response = await call_next(request)
        for header, value in [SecurityConfig.SECURITY](http://SecurityConfig.SECURITY)_HEADERS.items():
            response.headers[header] = value
        
        return response
```

### **🏢 Infrastructure Security (Hébergement)**

### **🔐 Choix d'Hébergement Sécurisé**

```yaml
# Recommandation: AWS/Azure/GCP avec ces services
# infrastructure/terraform/[security.tf](http://security.tf)

# WAF (Web Application Firewall)
resource "aws_wafv2_web_acl" "bubble_waf" {
  name  = "bubble-protection"
  scope = "CLOUDFRONT"
  
  default_action {
    allow {}
  }
  
  rule {
    name     = "RateLimitRule"
    priority = 1
    
    action {
      block {}
    }
    
    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }
  }
}

# Database avec chiffrement
resource "aws_rds_instance" "bubble_db" {
  engine         = "postgres"
  engine_version = "15.3"
  
  # SÉCURITÉ OBLIGATOIRE
  storage_encrypted   = true
  kms_key_id         = aws_kms_key.bubble_key.arn
  
  # Backup sécurisé
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  
  # Network isolation
  db_subnet_group_name   = aws_db_subnet_[group.private.name](http://group.private.name)
  vpc_security_group_ids = [aws_security_[group.database.id](http://group.database.id)]
}
```

### **🚨 Monitoring & Alerting Sécurité**

```python
# backend/app/core/security_[monitoring.py](http://monitoring.py)
import logging
from datetime import datetime

class SecurityMonitor:
    def __init__(self):
        [self.security](http://self.security)_logger = logging.getLogger("[bubble.security](http://bubble.security)")
    
    async def log_security_event(self, event_type: str, user_id: str = None, 
                                 details: dict = None):
        """Log TOUS les événements sécurité"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "details": details or {},
            "severity": self._get_severity(event_type)
        }
        
        [self.security](http://self.security)_[logger.info](http://logger.info)(json.dumps(event))
        
        # Alertes automatiques pour événements critiques
        if event["severity"] == "CRITICAL":
            await self.send_security_alert(event)

# Audit trail IMMUTABLE
class AuditLogger:
    async def log_financial_action(self, user_id: str, action: str, 
                                   amount: float, details: dict):
        """OBLIGATOIRE pour actions financières"""
        audit_entry = {
            "user_id": user_id,
            "action": action,
            "amount": amount,
            "details": details,
            "timestamp": datetime.utcnow(),
            "ip_address": get_client_ip(),
            "user_agent": get_user_agent(),
            "checksum": generate_checksum(...)  # Intégrité
        }
        
        # JAMAIS modifiable
        await self.insert_audit_log(audit_entry)
```

### **📅 Timeline Implémentation Sécurité**

### **🎯 Jour 1-5 (Phase 0)**

- [ ]  **Secrets management** (variables environnement)
- [ ]  **Password hashing** (bcrypt)
- [ ]  **Input validation** (Pydantic)
- [ ]  **Security headers** (middleware)

### **🎯 Semaine 1-2 (MVP Phase 1)**

- [ ]  **JWT Authentication** robust
- [ ]  **Rate limiting** basic
- [ ]  **HTTPS only** configuration
- [ ]  **Database encryption** at rest

### **🎯 Semaine 3-4 (MVP Phase 2)**

- [ ]  **Row Level Security** (RLS)
- [ ]  **Audit logging** financier
- [ ]  **CSRF protection**
- [ ]  **SQL injection** prevention

### **🎯 Semaine 5-8 (Production)**

- [ ]  **WAF deployment**
- [ ]  **Penetration testing**
- [ ]  **Security monitoring**
- [ ]  **Incident response** plan

### **🎯 Sécurité vs Budget**

### **💰 Gratuit/Low-Cost (MVP)**

- HTTPS via Let's Encrypt
- PostgreSQL encryption native
- FastAPI security middleware
- Basic monitoring

### **💳 Investissement Raisonnable (Production)**

- WAF (Cloudflare ~20€/mois)
- Secrets Manager (AWS ~10€/mois)
- Security monitoring (DataDog ~50€/mois)
- Penetration testing (1-2k€ une fois)

### **🏆 Enterprise Level (Scale)**

- SOC 2 compliance (~10k€)
- Advanced threat detection
- Security audits réguliers

### **⚡ Action Immédiate**

**Dès demain, intégrez CETTE sécurité de base :**

```python
# backend/app/core/[config.py](http://config.py)
class Settings(BaseSettings):
    # JAMAIS en dur
    secret_key: str = Field(..., env="SECRET_KEY")
    database_url: str = Field(..., env="DATABASE_URL")
    
    # Security defaults
    access_token_expire_minutes: int = 30
    password_min_length: int = 12
    max_login_attempts: int = 5
    
    class Config:
        env_file = ".env"

# .env.example
SECRET_KEY=your_secret_key_here_minimum_32_chars
DATABASE_URL=postgresql://user:[password@localhost](mailto:password@localhost)/bubble_dev
CLAUDE_API_KEY=your_claude_key_here
```

### **🔥 Qu'est-ce qu'un Smoke Test ?**

**Définition Simple :** Un **smoke test** = Test de base pour vérifier que l'application **fonctionne minimalement** après un déploiement.

**Analogie :** Comme allumer un appareil électronique : on vérifie qu'il s'allume et qu'il n'y a pas de fumée (d'où le nom) avant de tester toutes les fonctionnalités.

**Exemples Concrets pour Bubble :**

```python
# Smoke Tests après déploiement
async def smoke_tests():
    """Tests minimaux pour vérifier que l'app marche"""
    
    # 1. L'app démarre-t-elle ?
    response = await http_client.get("/health")
    assert response.status_code == 200
    
    # 2. Base de données accessible ?
    response = await http_client.get("/health/db")
    assert response.json()["database"] == "connected"
    
    # 3. API principale répond-elle ?
    response = await http_client.get("/api/v1/")
    assert response.status_code == 200
    
    # 4. Authentification fonctionne-t-elle ?
    response = await http_[client.post](http://client.post)("/auth/login", {
        "email": "[test@example.com](mailto:test@example.com)",
        "password": "test123"
    })
    assert response.status_code == 200
    
    # 5. Une feature critique marche-t-elle ?
    response = await http_client.get("/api/v1/portfolios")
    assert response.status_code == 200
    
    print("✅ Smoke tests passed - App is basically working!")
```

**Smoke vs Autres Tests :**

| Test Type | Scope | Durée | Objectif |
| --- | --- | --- | --- |
| **Smoke** | 5-10 tests critiques | 1-2 min | App fonctionne basiquement |
| **Integration** | Workflow complets | 5-15 min | Features marchent ensemble |
| **E2E** | User journeys complets | 15-60 min | Experience utilisateur |
| **Load** | Performance sous charge | 30+ min | Scalabilité |

*La sécurité en fintech n'est PAS négociable - elle doit être intégrée dès le premier commit !* 🛡️

---


### **🔍 Framework d'Audit Systématique**

### **1. Cohérence Architecturale**

```python
def audit_architecture_consistency():
    """Audit systématique de cohérence"""
    
    # ✅ Services Dependencies
    check_service_dependencies_graph()
    # Est-ce que AuthService est bien utilisé partout ?
    # DataService appelé avant StrategyService ?
    
    # ✅ API Contracts
    validate_api_contracts_alignment()
    # Interfaces Plan Detailed = Jira acceptance criteria ?
    
    # ✅ Data Flow
    trace_data_flow_end_to_end()
    # User → Universe → Strategy → Portfolio → Orders
    
    # ✅ Error Propagation  
    validate_error_handling_patterns()
    # Erreurs gérées à chaque niveau ?
    
    return audit_report
```

### **2. Business-Technical Alignment**

**🎯 Business-Tech Audit Matrix :**

| User Story | Technical Component | API Endpoint | Database Schema | Tests Defined |
| --- | --- | --- | --- | --- |
| Universe Creation | UniverseService | POST /universes | universe table | ✅ |
| Portfolio Backtest | BacktestEngine | POST /backtests | backtest_results | ✅ |
| Risk Monitoring | RiskService | GET /portfolios/{id}/risk | risk_metrics | ✅ |

**🔍 Questions d'Audit :**

- Chaque user story a-t-elle son composant technique ?
- Chaque API a-t-elle son schéma DB correspondant ?
- Chaque fonctionnalité a-t-elle ses tests définis ?

### **3. Scalability & Performance Audit**

```python
def audit_scalability_bottlenecks():
    """Identifier les goulots d'étranglement futurs"""
    
    bottlenecks = []
    
    # 🔍 Database Bottlenecks
    if not has_database_indexing_strategy():
        bottlenecks.append("DB indexing not planned")
    
    if not has_read_replicas_plan():
        bottlenecks.append("Read scaling not addressed")
    
    # 🔍 API Bottlenecks  
    if not has_rate_limiting_strategy():
        bottlenecks.append("API rate limiting missing")
    
    if not has_caching_layers():
        bottlenecks.append("Caching strategy incomplete")
    
    # 🔍 Business Logic Bottlenecks
    if not has_async_processing():
        bottlenecks.append("Heavy operations not async")
    
    return bottlenecks
```

### **4. Security & Compliance Audit**

**🛡️ Security Audit Checklist :**

**Data Protection**

- [ ]  PII data encrypted at rest
- [ ]  Financial data audit trail
- [ ]  GDPR compliance for EU users
- [ ]  Data retention policies defined

**Access Control**

- [ ]  Multi-tenant isolation (RLS)
- [ ]  API authentication on all endpoints
- [ ]  Role-based permissions
- [ ]  Session management secure

**Financial Compliance**

- [ ]  Trade execution logging
- [ ]  Anti-fraud measures
- [ ]  Market data usage compliance
- [ ]  Broker API security

### **5. Development Workflow Audit**

```python
def audit_development_workflow():
    """Audit du processus de développement"""
    
    # ✅ Git Strategy
    has_branching_strategy = check_git_workflow()
    
    # ✅ Testing Strategy
    has_comprehensive_tests = validate_test_pyramid()
    
    # ✅ CI/CD Pipeline
    has_deployment_automation = check_cicd_pipeline()
    
    # ✅ Code Quality
    has_code_quality_gates = check_linting_standards()
    
    # ✅ Documentation
    has_living_documentation = check_docs_sync()
    
    return workflow_health_score
```

### **🎯 Méthodes Systématiques Anti-Erreurs**

### **🔄 Red Team Review Process**

**🕵️ Red Team Questions (Jouez l'Avocat du Diable) :**

**Architecture Challenges**

- "Que se passe-t-il si l'API Claude tombe ?"
- "Comment gère-t-on 1000x plus d'utilisateurs ?"
- "Que faire si PostgreSQL devient le bottleneck ?"

**Business Logic Challenges**

- "Que faire si les données market sont incorrectes ?"
- "Comment éviter les trades accidentels ?"
- "Que se passe-t-il si un utilisateur hack son portfolio ?"

**Integration Challenges**

- "Que faire si Alpaca change son API ?"
- "Comment migrer vers un nouveau broker ?"
- "Comment gérer les downtimes de maintenance ?"

### **📈 Dependency Risk Analysis**

```python
def analyze_critical_dependencies():
    """Analyse des risques de dépendances"""
    
    external_deps = {
        "claude_api": {
            "criticality": "HIGH",
            "fallback": "Degraded mode without AI",
            "vendor_lock": "Medium"
        },
        "alpaca_api": {
            "criticality": "CRITICAL", 
            "fallback": "Paper trading only",
            "vendor_lock": "High"
        },
        "market_data": {
            "criticality": "CRITICAL",
            "fallback": "Yahoo Finance backup",
            "vendor_lock": "Low"
        }
    }
    
    for dep, risk in external_deps.items():
        if risk["criticality"] == "CRITICAL" and risk["vendor_lock"] == "High":
            print(f"⚠️ RISK: {dep} creates vendor lock-in")
```

### **🎯 Load Testing Mental Model**

```python
def stress_test_architecture():
    """Test mental de charge"""
    
    scenarios = [
        {
            "users": 1000,
            "concurrent_backtests": 100,
            "expected_bottleneck": "Database CPU"
        },
        {
            "users": 10000, 
            "market_data_requests": 50000/min,
            "expected_bottleneck": "API rate limits"
        },
        {
            "users": 100000,
            "portfolio_calculations": 1M/day,
            "expected_bottleneck": "Risk calculation engine"
        }
    ]
    
    # Chaque scénario a-t-il une solution architecturale ?
```

### **🚨 Signaux d'Alarme à Surveiller**

### **🔴 Red Flags Critiques**

**⚠️ Arrêtez Tout Si Vous Voyez Ça :**

**Architecture Red Flags**

- [ ]  Circular dependencies entre services
- [ ]  Single point of failure critique
- [ ]  Pas de stratégie de rollback
- [ ]  Secrets en dur dans le code

**Business Logic Red Flags**

- [ ]  Calculs financiers sans validation
- [ ]  Pas d'audit trail pour trades
- [ ]  Logique métier dans les controllers
- [ ]  Pas de gestion d'erreurs financières

**Development Red Flags**

- [ ]  Pas de tests pour logique critique
- [ ]  Pas de code review process
- [ ]  Pas de monitoring en production
- [ ]  Documentation obsolète

### **🟡 Yellow Flags à Investiguer**

**🤔 À Creuser Plus Profondément :**

**Performance Concerns**

- APIs sans timeout configuré
- Requêtes DB sans pagination
- Cache sans TTL approprié
- Pas de monitoring APM

**Security Concerns**

- Validation input incomplète
- Logs contenant des données sensibles
- Pas de rate limiting par utilisateur
- Sessions sans expiration

**Maintainability Concerns**

- Code dupliqué entre services
- Conventions de nommage inconsistantes
- Configuration spread sur plusieurs endroits
- Pas de migration strategy DB

### **🎯 Plan d'Action pour l'Audit Final**

### **📋 Audit Sprint (3 jours)**

**Jour 1 : Cross-Reference Audit**

```bash
# Créer une matrice de cohérence
echo "Audit des références croisées"
check_jira_to_technical_mapping()
validate_api_contracts_consistency() 
trace_user_journeys_end_to_end()
```

**Jour 2 : Risk & Dependency Audit**

```bash
echo "Audit des risques"
identify_critical_paths()
analyze_vendor_dependencies()
stress_test_mental_models()
```

**Jour 3 : Security & Compliance Audit**

```bash
echo "Audit sécurité"
review_financial_data_flows()
validate_multi_tenant_isolation()
check_regulatory_compliance_basics()
```

### **🏆 Micro-Améliorations Recommandées**

### **🎯 Ajouts Stratégiques (2-3 heures)**

1. **Risk Register** → Document des risques identifiés + mitigation
2. **Rollback Scenarios** → Plan B pour chaque phase critique
3. **Performance Budget** → SLA définis (latence, throughput)
4. **Monitoring Strategy** → Métriques clés à tracker

### **📋 Risk Register Template**

```markdown
## 🚨 Risk Register

| Risk | Probability | Impact | Mitigation | Owner |
|------|-------------|--------|------------|-------|
| Claude API Rate Limit | Medium | High | Implement fallback + caching | Backend Team |
| Database Scaling | High | Medium | Read replicas + connection pooling | DevOps |
| Market Data Outage | Low | Critical | Multiple data sources + circuit breakers | Data Team |
| Security Breach | Low | Critical | Penetration testing + monitoring | Security |
```

### **🔄 Rollback Scenarios**

```markdown
## 🔙 Rollback Strategy

### Database Migrations
- **Forward**: Automated via Alembic
- **Rollback**: Tested rollback scripts for each migration
- **Data**: Backup before each major migration

### Service Deployments
- **Blue-Green**: Zero-downtime deployments
- **Feature Flags**: Instant feature disable
- **Container Rollback**: Previous image available

### Critical Features
- **AI Agent**: Fallback to traditional UI
- **Live Trading**: Automatic paper mode
- **Market Data**: Switch to backup provider
```

### **📈 Performance Budget**

```markdown
## ⏱️ Performance SLA

### API Response Times (95th percentile)
- **Authentication**: < 200ms
- **Portfolio Data**: < 500ms
- **Backtest Results**: < 2s
- **Market Data**: < 100ms

### System Availability
- **Uptime**: 99.9% (8.76 hours downtime/year)
- **Database**: 99.95%
- **Critical APIs**: 99.9%

### Throughput Targets
- **Concurrent Users**: 1,000
- **API Requests**: 10,000/minute
- **Background Jobs**: 100/second
```

## 🧪 **Guide Complet des Tests Frontend**

### **🎭 Pourquoi le Frontend est Différent**

### **🔄 Backend vs Frontend Testing**

```python
# BACKEND: Logique pure, déterministe
def calculate_portfolio_value(positions):
    return sum(pos.quantity * pos.price for pos in positions)

# Test simple et prévisible
def test_portfolio_calculation():
    positions = [Position(quantity=10, price=100)]
    assert calculate_portfolio_value(positions) == 1000
```

```tsx
// FRONTEND: UI, interactions, états asynchrones
const PortfolioChart = ({ data, onSelection }) => {
  const [loading, setLoading] = useState(false);
  const [selectedPeriod, setSelectedPeriod] = useState('1M');
  
  useEffect(() => {
    // Async data loading
    // User interactions
    // Browser APIs
    // Third-party libraries
  }, [selectedPeriod]);
  
  // Comment tester ça ? 🤔
};
```

### **🏗️ Architecture de Tests Frontend**

### **📊 Pyramide de Tests Frontend**

```
    E2E Tests
 5-10% - Cypress/Playwright
 User journeys complets

  Integration Tests
20-30% - Testing Library
Components + API + State

   Unit Tests
 60-70% - Jest + Testing Library
 Fonctions pures + logique isolée

  Component Tests
 Static + Visual - Storybook
 UI consistency + accessibility
```

### **🧪 Types de Tests Frontend Détaillés**

### **1. Unit Tests : Fonctions Pures**

```tsx
// src/utils/portfolio.ts
export const calculateAllocationPercentage = (
  amount: number, 
  total: number
): number => {
  if (total === 0) return 0;
  return Math.round((amount / total) * 100 * 100) / 100; // 2 decimales
};

export const validateScreeningCriteria = (criteria: ScreeningCriteria): string[] => {
  const errors: string[] = [];
  
  if (criteria.minMarketCap && criteria.minMarketCap < 0) {
    errors.push('Market cap must be positive');
  }
  
  if (criteria.maxPeRatio && criteria.maxPeRatio < 0) {
    errors.push('P/E ratio must be positive');
  }
  
  return errors;
};
```

```tsx
// src/utils/__tests__/portfolio.test.ts
import { calculateAllocationPercentage, validateScreeningCriteria } from '../portfolio';

describe('Portfolio Utils', () => {
  describe('calculateAllocationPercentage', () => {
    it('calculates percentage correctly', () => {
      expect(calculateAllocationPercentage(25, 100)).toBe(25);
      expect(calculateAllocationPercentage(33.333, 100)).toBe(33.33);
    });
    
    it('handles zero total', () => {
      expect(calculateAllocationPercentage(50, 0)).toBe(0);
    });
    
    it('handles edge cases', () => {
      expect(calculateAllocationPercentage(0, 100)).toBe(0);
      expect(calculateAllocationPercentage(100, 100)).toBe(100);
    });
  });

  describe('validateScreeningCriteria', () => {
    it('validates criteria correctly', () => {
      const validCriteria = { minMarketCap: 1000000, maxPeRatio: 25 };
      expect(validateScreeningCriteria(validCriteria)).toEqual([]);
    });
    
    it('catches negative values', () => {
      const invalidCriteria = { minMarketCap: -1000, maxPeRatio: -5 };
      const errors = validateScreeningCriteria(invalidCriteria);
      
      expect(errors).toContain('Market cap must be positive');
      expect(errors).toContain('P/E ratio must be positive');
    });
  });
});
```

### **2. Component Tests : UI Logic**

```tsx
// src/components/PortfolioSummary.tsx
interface PortfolioSummaryProps {
  portfolio: Portfolio;
  loading?: boolean;
  onRebalance?: () => void;
}

export const PortfolioSummary: React.FC<PortfolioSummaryProps> = ({ 
  portfolio, 
  loading = false,
  onRebalance 
}) => {
  const totalValue = portfolio.positions.reduce((sum, pos) => sum + pos.value, 0);
  const dayChange = portfolio.dayChange;
  const dayChangePercent = (dayChange / totalValue) * 100;

  return (
    <div data-testid="portfolio-summary">
      <h2>Portfolio Summary</h2>
      
      {loading ? (
        <div data-testid="loading-spinner">Loading...</div>
      ) : (
        <>
          <div data-testid="total-value">
            ${totalValue.toLocaleString()}
          </div>
          
          <div 
            data-testid="day-change"
            className={dayChange >= 0 ? 'positive' : 'negative'}
          >
            {dayChange >= 0 ? '+' : ''}${dayChange.toFixed(2)} 
            ({dayChangePercent.toFixed(2)}%)
          </div>
          
          {onRebalance && (
            <button 
              data-testid="rebalance-button"
              onClick={onRebalance}
              disabled={loading}
            >
              Rebalance Portfolio
            </button>
          )}
        </>
      )}
    </div>
  );
};
```

```tsx
// src/components/__tests__/PortfolioSummary.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { PortfolioSummary } from '../PortfolioSummary';

const mockPortfolio = {
  positions: [
    { symbol: 'AAPL', value: 1000 },
    { symbol: 'GOOGL', value: 1500 }
  ],
  dayChange: 125.50
};

describe('PortfolioSummary', () => {
  it('displays total portfolio value', () => {
    render(<PortfolioSummary portfolio={mockPortfolio} />);
    
    expect(screen.getByTestId('total-value')).toHaveTextContent('$2,500');
  });
  
  it('shows positive day change in green', () => {
    render(<PortfolioSummary portfolio={mockPortfolio} />);
    
    const dayChange = screen.getByTestId('day-change');
    expect(dayChange).toHaveTextContent('+$125.50 (5.02%)');
    expect(dayChange).toHaveClass('positive');
  });
  
  it('shows negative day change in red', () => {
    const lossPortfolio = { ...mockPortfolio, dayChange: -75.25 };
    render(<PortfolioSummary portfolio={lossPortfolio} />);
    
    const dayChange = screen.getByTestId('day-change');
    expect(dayChange).toHaveTextContent('-$75.25 (-3.01%)');
    expect(dayChange).toHaveClass('negative');
  });
  
  it('shows loading state', () => {
    render(<PortfolioSummary portfolio={mockPortfolio} loading={true} />);
    
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    expect(screen.queryByTestId('total-value')).not.toBeInTheDocument();
  });
  
  it('calls onRebalance when button clicked', () => {
    const handleRebalance = jest.fn();
    render(
      <PortfolioSummary 
        portfolio={mockPortfolio} 
        onRebalance={handleRebalance} 
      />
    );
    
    [fireEvent.click](http://fireEvent.click)(screen.getByTestId('rebalance-button'));
    expect(handleRebalance).toHaveBeenCalledTimes(1);
  });
});
```

### **3. Integration Tests : API + UI**

```tsx
// src/hooks/useScreener.ts
export const useScreener = () => {
  const [results, setResults] = useState<ScreeningResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runScreener = async (criteria: ScreeningCriteria) => {
    setLoading(true);
    setError(null);
    
    try {
      const screeningResults = await screenerService.runScreener(criteria);
      setResults(screeningResults);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Screening failed');
    } finally {
      setLoading(false);
    }
  };

  return { results, loading, error, runScreener };
};
```

```tsx
// src/hooks/__tests__/useScreener.test.tsx
import { renderHook, act } from '@testing-library/react';
import { useScreener } from '../useScreener';
import { screenerService } from '../services/screener';

// Mock the service
jest.mock('../services/screener');
const mockScreenerService = screenerService as jest.Mocked<typeof screenerService>;

describe('useScreener', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('starts with empty state', () => {
    const { result } = renderHook(() => useScreener());
    
    expect(result.current.results).toEqual([]);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('handles successful screening', async () => {
    const mockResults = [
      { symbol: 'AAPL', name: 'Apple Inc.', score: 8.5 }
    ];
    mockScreenerService.runScreener.mockResolvedValueOnce(mockResults);

    const { result } = renderHook(() => useScreener());

    await act(async () => {
      await result.current.runScreener({ minMarketCap: 1000000000 });
    });

    expect(result.current.results).toEqual(mockResults);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(mockScreenerService.runScreener).toHaveBeenCalledWith({
      minMarketCap: 1000000000
    });
  });

  it('handles API errors', async () => {
    mockScreenerService.runScreener.mockRejectedValueOnce(
      new Error('API Error')
    );

    const { result } = renderHook(() => useScreener());

    await act(async () => {
      await result.current.runScreener({ minMarketCap: 1000000000 });
    });

    expect(result.current.results).toEqual([]);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe('API Error');
  });
});
```

### **4. Component Integration Tests**

```tsx
// src/pages/__tests__/ScreenerPage.integration.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ScreenerPage } from '../ScreenerPage';
import { screenerService } from '../../services/screener';

// Mock the entire service module
jest.mock('../../services/screener');
const mockScreenerService = screenerService as jest.Mocked<typeof screenerService>;

// Mock Chart library to avoid canvas issues in tests
jest.mock('../../components/Chart', () => ({
  Chart: ({ data }: { data: any }) => (
    <div data-testid="mock-chart">Chart with {data?.length || 0} points</div>
  )
}));

describe('ScreenerPage Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('complete screening workflow', async () => {
    const user = userEvent.setup();
    
    // Setup mock response
    const mockResults = [
      {
        symbol: 'AAPL',
        name: 'Apple Inc.',
        marketCap: 3000000000000,
        peRatio: 25.4,
        roic: 0.31,
        sector: 'Technology',
        score: 8.5
      },
      {
        symbol: 'GOOGL',
        name: 'Alphabet Inc.',
        marketCap: 1800000000000,
        peRatio: 22.1,
        roic: 0.28,
        sector: 'Technology',
        score: 7.8
      }
    ];
    mockScreenerService.runScreener.mockResolvedValueOnce(mockResults);

    render(<ScreenerPage />);

    // 1. Fill out screening criteria
    await user.type(
      screen.getByLabelText(/min market cap/i), 
      '1000000000'
    );
    await user.type(
      screen.getByLabelText(/max p\/e ratio/i), 
      '30'
    );
    await user.selectOptions(
      screen.getByLabelText(/sectors/i),
      ['Technology', 'Healthcare']
    );

    // 2. Submit screening
    const submitButton = screen.getByRole('button', { name: /run screener/i });
    await [user.click](http://user.click)(submitButton);

    // 3. Verify loading state
    expect(screen.getByText(/screening\.\.\./i)).toBeInTheDocument();

    // 4. Wait for results
    await waitFor(() => {
      expect(screen.queryByText(/screening\.\.\./i)).not.toBeInTheDocument();
    });

    // 5. Verify results display
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
    expect(screen.getByText('GOOGL')).toBeInTheDocument();
    expect(screen.getByText('Alphabet Inc.')).toBeInTheDocument();

    // 6. Verify API was called with correct parameters
    expect(mockScreenerService.runScreener).toHaveBeenCalledWith({
      minMarketCap: 1000000000,
      maxPeRatio: 30,
      sectors: ['Technology', 'Healthcare']
    });

    // 7. Test result interaction - click on a stock
    const appleRow = screen.getByText('AAPL').closest('tr');
    await [user.click](http://user.click)(appleRow!);

    // Should show stock details
    expect(screen.getByTestId('stock-details')).toBeInTheDocument();
    expect(screen.getByText(/score: 8\.5/i)).toBeInTheDocument();
  });

  it('handles API errors gracefully', async () => {
    const user = userEvent.setup();
    
    mockScreenerService.runScreener.mockRejectedValueOnce(
      new Error('Rate limit exceeded')
    );

    render(<ScreenerPage />);

    await user.type(screen.getByLabelText(/min market cap/i), '1000000000');
    await [user.click](http://user.click)(screen.getByRole('button', { name: /run screener/i }));

    await waitFor(() => {
      expect(screen.getByText(/rate limit exceeded/i)).toBeInTheDocument();
    });

    // Should show retry button
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });
});
```

### **5. E2E Tests : User Journeys**

```tsx
// cypress/e2e/[screener-workflow.cy](http://screener-workflow.cy).ts
describe('Stock Screener Workflow', () => {
  beforeEach(() => {
    // Login user
    cy.login('[test@example.com](mailto:test@example.com)', 'password123');
    cy.visit('/screener');
  });

  it('complete screening and universe creation', () => {
    // 1. Run screening
    cy.get('[data-cy="min-market-cap"]').type('1000000000');
    cy.get('[data-cy="max-pe-ratio"]').type('25');
    cy.get('[data-cy="sector-select"]').select(['Technology', 'Healthcare']);
    
    cy.get('[data-cy="run-screener"]').click();

    // 2. Wait for results
    cy.get('[data-cy="screener-results"]').should('be.visible');
    cy.get('[data-cy="result-row"]').should('have.length.greaterThan', 0);

    // 3. Select stocks for universe
    cy.get('[data-cy="result-row"]').first().find('[data-cy="select-checkbox"]').check();
    cy.get('[data-cy="result-row"]').eq(2).find('[data-cy="select-checkbox"]').check();

    // 4. Create universe from selection
    cy.get('[data-cy="create-universe"]').click();
    cy.get('[data-cy="universe-name"]').type('Tech Growth Stocks');
    cy.get('[data-cy="universe-description"]').type('High-quality technology stocks with growth potential');
    
    cy.get('[data-cy="save-universe"]').click();

    // 5. Verify navigation to universe page
    cy.url().should('include', '/universes/');
    cy.contains('Tech Growth Stocks').should('be.visible');

    // 6. Verify universe contents
    cy.get('[data-cy="universe-stocks"]').should('contain', 'AAPL');
    cy.get('[data-cy="stock-count"]').should('contain', '2 stocks');
  });

  it('handles real-time data updates', () => {
    // Mock WebSocket connection for real-time updates
    cy.intercept('ws://[localhost:8000/ws/screener](http://localhost:8000/ws/screener)', { fixture: 'screener-updates.json' });

    cy.get('[data-cy="min-market-cap"]').type('500000000');
    cy.get('[data-cy="run-screener"]').click();

    // Verify initial results
    cy.get('[data-cy="result-row"]').should('have.length', 10);

    // Simulate real-time price update
    cy.window().its('websocket').invoke('send', JSON.stringify({
      type: 'price_update',
      symbol: 'AAPL',
      price: 185.50
    }));

    // Verify UI updates
    cy.get('[data-cy="result-row"]').contains('AAPL')
      .parent()
      .find('[data-cy="current-price"]')
      .should('contain', '$185.50');
  });
});
```

### **🛠️ Configuration de Tests Frontend**

### **📦 Package.json Setup**

```json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "test:e2e": "cypress run",
    "test:e2e:open": "cypress open",
    "test:all": "npm run test && npm run test:e2e"
  },
  "devDependencies": {
    "@testing-library/react": "^13.4.0",
    "@testing-library/jest-dom": "^5.16.5",
    "@testing-library/user-event": "^14.4.3",
    "jest": "^29.3.1",
    "jest-environment-jsdom": "^29.3.1",
    "cypress": "^12.3.0",
    "@types/jest": "^29.2.4"
  }
}
```

### **⚙️ Jest Configuration**

```jsx
// jest.config.js
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|eot|otf|webp|svg|ttf|woff|woff2|mp4|webm|wav|mp3|m4a|aac|oga)$': 'jest-transform-stub'
  },
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/index.tsx',
    '!src/reportWebVitals.ts'
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  }
};
```

```tsx
// src/setupTests.ts
import '@testing-library/jest-dom';

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
};

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor(cb: any) {}
  observe() {}
  unobserve() {}
  disconnect() {}
};
```

### **🎯 Stratégies Spécifiques pour Bubble**

### **📊 Testing Financial Charts**

```tsx
// src/components/__tests__/PerformanceChart.test.tsx
import { render } from '@testing-library/react';
import { PerformanceChart } from '../PerformanceChart';

// Mock Chart.js to avoid canvas rendering issues
jest.mock('react-chartjs-2', () => ({
  Line: ({ data, options }: any) => (
    <div data-testid="chart-mock">
      <span data-testid="chart-data-points">{data.datasets[0].data.length}</span>
      <span data-testid="chart-title">{options.plugins.title.text}</span>
    </div>
  )
}));

describe('PerformanceChart', () => {
  const mockPerformanceData = [
    { date: '2023-01-01', value: 10000 },
    { date: '2023-01-02', value: 10150 },
    { date: '2023-01-03', value: 9980 }
  ];

  it('renders performance chart with correct data points', () => {
    render(<PerformanceChart data={mockPerformanceData} />);
    
    expect(screen.getByTestId('chart-data-points')).toHaveTextContent('3');
    expect(screen.getByTestId('chart-title')).toHaveTextContent('Portfolio Performance');
  });
});
```

### **🔄 Testing WebSocket Connections**

```tsx
// src/hooks/__tests__/useRealtimeData.test.tsx
import { renderHook, act } from '@testing-library/react';
import { useRealtimeData } from '../useRealtimeData';

// Mock WebSocket
class MockWebSocket {
  constructor(public url: string) {}
  
  send = jest.fn();
  close = jest.fn();
  
  // Simulate WebSocket events
  simulateMessage(data: any) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) } as MessageEvent);
    }
  }
  
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
}

global.WebSocket = MockWebSocket as any;

describe('useRealtimeData', () => {
  it('receives real-time price updates', () => {
    const { result } = renderHook(() => 
      useRealtimeData(['AAPL', 'GOOGL'])
    );

    // Get the WebSocket instance
    const ws = [result.current.ws](http://result.current.ws) as MockWebSocket;

    act(() => {
      ws.simulateMessage({
        type: 'price_update',
        symbol: 'AAPL',
        price: 175.50,
        change: 2.30
      });
    });

    expect(result.current.prices['AAPL']).toEqual({
      price: 175.50,
      change: 2.30
    });
  });
});
```

### **🎨 Visual Regression Testing**

```tsx
// .storybook/main.js
module.exports = {
  stories: ['../src/**/*.stories.@(js|jsx|ts|tsx)'],
  addons: [
    '@storybook/addon-essentials',
    '@storybook/addon-interactions',
    'chromatic'
  ]
};

// src/components/PortfolioCard.stories.tsx
import type { Meta, StoryObj } from '@storybook/react';
import { PortfolioCard } from './PortfolioCard';

const meta: Meta<typeof PortfolioCard> = {
  title: 'Components/PortfolioCard',
  component: PortfolioCard,
  parameters: {
    layout: 'centered',
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    portfolio: {
      name: 'Growth Portfolio',
      value: 125000,
      dayChange: 1250,
      performance: { ytd: 0.08 }
    }
  }
};

export const Negative: Story = {
  args: {
    portfolio: {
      name: 'Value Portfolio',
      value: 87500,
      dayChange: -850,
      performance: { ytd: -0.02 }
    }
  }
};
```

---

## 🏆 **Best Practices High Standard**

### **🎯 Mapping avec Standards Enterprise**

Cette approche de tests frontend correspond **parfaitement** aux **best practices high standard** et dépasse le niveau "Senior+".

### **✅ Niveau "Maîtrise Intermédiaire" - Couvert**

- **Tests unitaires** → Fonctions pures + utils ✅
- **Tests d'intégration** → Components + hooks ✅
- **Coverage tools** → Jest + coverage reports ✅

### **✅ Niveau "Senior" - Couvert**

- **TDD approche** → Tests before implementation ✅
- **Mocking strategies** → Services, WebSocket, Chart libraries ✅
- **E2E testing** → Cypress user journeys ✅

### **✅ Niveau "Senior+" - Couvert**

- **Visual regression testing** → Storybook + Chromatic ✅
- **Performance testing** → Real-time data, async operations ✅
- **Advanced testing patterns** → Testing Library best practices ✅

### **🔥 Éléments Enterprise-Level**

### **🧪 Testing Architecture (Senior+)**

```tsx
// Test utilities pour consistency
// src/test-utils/index.ts
export const createMockPortfolio = (overrides = {}) => ({
  id: 'test-portfolio-1',
  name: 'Test Portfolio',
  positions: [
    { symbol: 'AAPL', value: 1000, quantity: 5 },
    { symbol: 'GOOGL', value: 1500, quantity: 3 }
  ],
  dayChange: 0,
  performance: { ytd: 0.05, sharpe: 1.2 },
  ...overrides
});

export const renderWithProviders = (ui: ReactElement, options = {}) => {
  const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
    return (
      <AuthProvider>
        <ThemeProvider>
          <QueryClient client={testQueryClient}>
            {children}
          </QueryClient>
        </ThemeProvider>
      </AuthProvider>
    );
  };
  
  return render(ui, { wrapper: AllTheProviders, ...options });
};

// Custom matchers pour domain-specific assertions
expect.extend({
  toBeValidPortfolio(received) {
    const pass = received && 
                 typeof [received.id](http://received.id) === 'string' &&
                 Array.isArray(received.positions) &&
                 typeof received.dayChange === 'number';
    
    return {
      message: () => `expected ${received} to be a valid portfolio`,
      pass
    };
  }
});
```

### **📊 Performance Testing (Senior+)**

```tsx
// Performance benchmarks dans les tests
import { performance } from 'perf_hooks';

describe('PerformanceChart Performance', () => {
  it('renders large datasets efficiently', async () => {
    const largeDataset = generateMockData(10000); // 10k points
    
    const startTime = [performance.now](http://performance.now)();
    render(<PerformanceChart data={largeDataset} />);
    const renderTime = [performance.now](http://performance.now)() - startTime;
    
    // Should render in under 100ms
    expect(renderTime).toBeLessThan(100);
  });
  
  it('handles real-time updates without memory leaks', async () => {
    const { unmount } = render(<RealtimeChart />);
    
    // Simulate heavy updates
    for (let i = 0; i < 1000; i++) {
      act(() => {
        mockWebSocket.simulateMessage({ price: Math.random() * 100 });
      });
    }
    
    const memoryBefore = (performance as any).memory?.usedJSHeapSize || 0;
    unmount();
    
    // Force garbage collection in test environment
    if (global.gc) global.gc();
    
    const memoryAfter = (performance as any).memory?.usedJSHeapSize || 0;
    expect(memoryAfter).toBeLessThanOrEqual(memoryBefore);
  });
});
```

### **🔄 Advanced Testing Patterns (Senior+)**

```tsx
// Property-based testing pour financial calculations
import fc from 'fast-check';

describe('Portfolio calculations', () => {
  it('allocation percentages always sum to 100%', () => {
    fc.assert([fc.property](http://fc.property)(
      fc.array(fc.float({ min: 0, max: 1000000 }), { minLength: 1 }),
      (amounts) => {
        const percentages = calculateAllocationPercentages(amounts);
        const sum = percentages.reduce((a, b) => a + b, 0);
        
        // Should be very close to 100% (accounting for rounding)
        expect(Math.abs(sum - 100)).toBeLessThan(0.01);
      }
    ));
  });
});

// Snapshot testing pour complex UI components
describe('PortfolioAnalytics', () => {
  it('matches snapshot for standard portfolio', () => {
    const portfolio = createMockPortfolio();
    const tree = renderer
      .create(<PortfolioAnalytics portfolio={portfolio} />)
      .toJSON();
    
    expect(tree).toMatchSnapshot();
  });
});

// Accessibility testing
import { axe, toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);

describe('Accessibility', () => {
  it('ScreenerForm has no accessibility violations', async () => {
    const { container } = render(<ScreenerForm />);
    const results = await axe(container);
    
    expect(results).toHaveNoViolations();
  });
});
```

### **🚀 Niveau "Best-in-Class" Enterprise**

### **📋 Contract Testing avec API**

```tsx
// Contract testing avec API
import { pactWith } from 'jest-pact';

pactWith({ consumer: 'BubbleFrontend', provider: 'BubbleAPI' }, (provider) => {
  describe('Screener API Contract', () => {
    beforeEach(() => {
      provider.addInteraction({
        state: 'user has access to screener',
        uponReceiving: 'a request for screening results',
        withRequest: {
          method: 'POST',
          path: '/api/v1/screener/run',
          headers: { 'Content-Type': 'application/json' },
          body: { minMarketCap: 1000000000 }
        },
        willRespondWith: {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: [{ symbol: 'AAPL', score: 8.5 }]
        }
      });
    });

    it('returns screening results', async () => {
      const results = await screenerApi.runScreener({ minMarketCap: 1000000000 });
      expect(results[0]).toMatchObject({ symbol: 'AAPL', score: 8.5 });
    });
  });
});
```

### **🔄 CI/CD Pipeline pour Tests**

```yaml
# .github/workflows/frontend-tests.yml
name: Frontend Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      # Unit & Integration Tests
      - name: Run Jest Tests
        run: |
          npm ci
          npm run test:coverage
          
      # Upload coverage
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        
      # Visual Regression Tests
      - name: Chromatic
        uses: chromaui/action@v1
        with:
          token: ${{ secrets.CHROMATIC_PROJECT_TOKEN }}
          
      # E2E Tests
      - name: Cypress Tests
        uses: cypress-io/github-action@v4
        with:
          start: npm start
          wait-on: '[http://localhost:3000](http://localhost:3000)'
```