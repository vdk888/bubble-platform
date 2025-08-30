# Sprint 3 Implementation Plan: Market Data & Technical Indicators Service with OpenBB Integration

## Current Implementation Status Analysis

Based on examination of the codebase and Sprint 3 roadmap documentation, here's the current status:

### ✅ **COMPLETED - Sprint 3 Components**
1. **Enhanced Market Data API Foundation**
   - ✅ Market Data API endpoints (`/api/v1/market-data/*`) fully implemented
   - ✅ Triple-provider architecture (OpenBB → Yahoo → Alpha Vantage) established
   - ✅ `MarketDataService` with composite provider integration
   - ✅ Professional OpenBB integration framework in place
   - ✅ Provider health monitoring and failover mechanisms
   - ✅ Bulk data optimization capabilities
   - ✅ Cost analysis and monitoring endpoints

2. **Core Infrastructure Ready**
   - ✅ Temporal universe system (Sprint 2.5) fully implemented
   - ✅ Multi-tenant isolation and security
   - ✅ Complete dataset approach architecture established
   - ✅ API routing and authentication systems

### ❌ **MISSING - Critical Sprint 3 Components**

#### 1. **Technical Indicators Engine** - **MAJOR GAP**
- ❌ No indicator service implementation found
- ❌ Missing RSI, MACD, Momentum calculation engines  
- ❌ No signal generation service (-1, 0, 1 format)
- ❌ No composite signal weighting system
- ❌ Missing temporal-aware indicator calculations

#### 2. **Enhanced Market Data Integration** - **PARTIAL**
- ⚠️ OpenBB implementation skeleton exists but advanced features not fully implemented
- ❌ Missing economic indicators integration
- ❌ Missing news sentiment analysis
- ❌ Missing analyst estimates and insider trading data
- ❌ Missing temporal-aware market data APIs

#### 3. **API Endpoints** - **MAJOR GAP**
- ❌ No indicators API endpoints (`/api/v1/indicators/*`)
- ❌ No signals API endpoints (`/api/v1/signals/*`)
- ❌ Missing temporal indicator endpoints
- ❌ Several OpenBB advanced features marked as "coming soon"

#### 4. **Frontend Integration** - **MISSING**
- ❌ No indicator configuration interface
- ❌ No signal visualization components
- ❌ No charts with technical indicator overlays

## Sprint 3 Requirements from Planning Documentation

### **Core Sprint 3 Deliverables (Week 4)**
From `planning/00_sprint_roadmap.md` lines 690-920:

1. **Enhanced Multi-Provider Market Data Foundation with Temporal Universe Integration**
2. **OpenBB Terminal integration for professional-grade financial data**
3. **Temporal-Aware Technical Indicators Engine**
4. **Frontend Indicators Interface**

### **Technical Requirements**
From `planning/2_jira.md` Epic 2 - Indicators & Signals:

**Technical Implementation:**
- RSI calculation (14-period default, verified via unit tests)
- MACD signals (12,26,9 parameters with crossover detection)  
- Momentum indicators (configurable lookback periods, ±2% thresholds)
- Signal output format: pandas Series with -1, 0, 1 values

**Performance Requirements:**
- Temporal indicator calculations: <2 seconds for 1000 assets
- Complete dataset creation: 5x faster than traditional approach
- API endpoints: <500ms (95th percentile)

**API Requirements:**
- `GET /api/v1/indicators/default`
- `POST /api/v1/indicators/calculate`
- `POST /api/v1/signals/generate`
- `POST /api/v1/indicators/temporal-batch`
- `GET /api/v1/indicators/temporal/{universe_id}/{date}`

## Detailed Implementation Plan

### **Phase 1: Technical Indicators Engine (Priority 1)**

#### **Step 1.1: Create Indicator Service Interface**
**Location**: `backend/app/services/interfaces/indicator_service.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import date
import pandas as pd

class IIndicatorService(ABC):
    @abstractmethod
    async def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate RSI with standard 14-period default"""
        pass
    
    @abstractmethod
    async def calculate_macd(self, data: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """Calculate MACD with 12,26,9 parameters"""
        pass
    
    @abstractmethod
    async def calculate_momentum(self, data: pd.DataFrame, period: int = 10) -> pd.Series:
        """Calculate momentum with configurable lookback"""
        pass
    
    @abstractmethod
    async def generate_composite_signals(self, indicators: Dict[str, pd.Series], weights: Dict[str, float]) -> pd.Series:
        """Generate weighted composite signals with -1, 0, 1 format"""
        pass
```

#### **Step 1.2: Implement Technical Indicators Service**
**Location**: `backend/app/services/technical_indicators_service.py`

**Dependencies**: `pandas`, `numpy`, `ta-lib` (optional) or pure pandas implementation

**Key Requirements**:
- RSI calculation matching industry standards
- MACD crossover signal detection
- Momentum with ±2% thresholds
- Conflict resolution hierarchy: MACD > RSI > Momentum
- Data validation (reject data >15min old)
- Complete dataset batch processing for 5x performance

#### **Step 1.3: Create Temporal-Aware Indicators Service**
**Location**: `backend/app/services/temporal_indicators_service.py`

**Key Innovation**: Integration with Sprint 2.5 temporal universe system
- Use historical universe snapshots to calculate indicators only for assets that were actually in universe at each date
- Eliminate survivorship bias in indicator calculations
- Pre-compute complete dataset for ultra-fast temporal filtering

#### **Step 1.4: Implement Signal Generation Service**
**Location**: `backend/app/services/signal_generation_service.py`

**Requirements**:
- Weighted composite signals
- Priority-based conflict resolution
- Audit logging for all signal events
- Real-time data freshness validation

### **Phase 2: API Endpoints Implementation (Priority 1)**

#### **Step 2.1: Create Indicators API Router**
**Location**: `backend/app/api/v1/indicators.py`

**Required Endpoints**:
```python
# Standard indicator endpoints
GET    /api/v1/indicators/default           # Default configurations
POST   /api/v1/indicators/calculate         # Calculate individual indicators
GET    /api/v1/indicators/rsi               # RSI calculation endpoint
GET    /api/v1/indicators/macd              # MACD calculation endpoint  
GET    /api/v1/indicators/momentum          # Momentum calculation endpoint

# Temporal-aware endpoints (Sprint 3 Innovation)
POST   /api/v1/indicators/temporal-batch    # Bulk calculate for complete dataset
GET    /api/v1/indicators/temporal/{universe_id}/{date}  # Point-in-time indicators
```

#### **Step 2.2: Create Signals API Router** 
**Location**: `backend/app/api/v1/signals.py`

**Required Endpoints**:
```python
POST   /api/v1/signals/generate             # Generate composite signals
POST   /api/v1/signals/temporal-composite   # Temporal composite signals
GET    /api/v1/signals/validate            # Signal validation endpoint
GET    /api/v1/signals/history/{universe_id} # Historical signals
```

#### **Step 2.3: Update Main Application Router**
**Location**: `backend/app/main.py` (line 126)

Add the new routers:
```python
app.include_router(indicators.router, tags=["Technical Indicators"])
app.include_router(signals.router, tags=["Signal Generation"])
```

### **Phase 3: Enhanced OpenBB Integration (Priority 2)**

#### **Step 3.1: Complete OpenBB Provider Implementation**
**Location**: `backend/app/services/implementations/openbb_data_provider.py`

Current status: Framework exists but several methods return "coming soon"

**Complete Implementation Required**:
- Economic indicators integration
- News sentiment analysis  
- Analyst estimates
- Insider trading data
- Fundamental data enhancement

#### **Step 3.2: Update Market Data API Endpoints**
**Location**: `backend/app/api/v1/market_data.py` (lines 504-592)

Change endpoints from "coming soon" status to full implementation:
- `/news-sentiment` (line 504)
- `/analyst-estimates` (line 524)
- `/insider-trading` (line 559)

### **Phase 4: Temporal Integration Enhancements (Priority 2)**

#### **Step 4.1: Create Temporal Market Data APIs**
**Location**: `backend/app/api/v1/market_data.py`

**New Endpoints Required**:
```python
GET    /api/v1/market-data/temporal/{universe_id}/{date}     # Point-in-time universe data
POST   /api/v1/market-data/complete-dataset                 # Complete universe dataset
GET    /api/v1/market-data/backtest-dataset/{universe_id}   # Optimized backtest data
```

#### **Step 4.2: Complete Dataset Service Enhancement**
**Location**: `backend/app/services/market_data_service.py`

The `build_complete_universe_dataset` method (mentioned in roadmap line 756) needs full implementation with:
- Bulk fetching all historical universe members
- Pre-computation of all indicators
- Temporal filtering optimization

### **Phase 5: Frontend Implementation (Priority 3)**

#### **Step 5.1: Create Indicator Configuration Components**
**Location**: `frontend/src/components/indicators/`

**Required Components**:
- `IndicatorConfigPanel.tsx` - RSI, MACD, Momentum parameter configuration
- `SignalWeightingPanel.tsx` - Composite signal weight configuration
- `IndicatorChart.tsx` - Price charts with indicator overlays

#### **Step 5.2: Create Signal Visualization Components**
**Location**: `frontend/src/components/signals/`

**Required Components**:
- `SignalVisualization.tsx` - Buy/sell signal markers
- `CompositeSignalChart.tsx` - Multi-indicator signal display
- `SignalHistory.tsx` - Historical signal timeline

### **Phase 6: Testing Implementation (Priority 1)**

#### **Step 6.1: Unit Tests for Indicators**
**Location**: `backend/app/tests/test_technical_indicators.py`

**Test Requirements**:
- RSI calculation accuracy against known datasets
- MACD crossover detection validation
- Momentum threshold testing
- Signal generation format validation (-1, 0, 1)

#### **Step 6.2: Integration Tests**
**Location**: `backend/app/tests/test_temporal_indicators.py`

**Test Requirements**:
- Temporal indicator calculations with universe evolution
- Complete dataset performance benchmarking
- Survivorship bias elimination validation
- API endpoint integration testing

#### **Step 6.3: Performance Tests**
**Location**: `backend/app/tests/test_indicator_performance.py`

**Test Requirements**:
- <2 second indicator calculations for 1000 assets
- 5x performance improvement validation
- API response time <500ms validation

## Implementation Dependencies and Prerequisites

### **Technical Dependencies**
1. **Python Libraries**: `pandas`, `numpy`, `scipy` (for indicators)
2. **Optional**: `TA-Lib` for optimized technical analysis calculations
3. **Database**: Temporal universe system (✅ already implemented)
4. **Redis**: For indicator result caching

### **Service Dependencies**
1. **Market Data Service**: ✅ Already implemented and functional
2. **Temporal Universe Service**: ✅ Already implemented and functional  
3. **Composite Data Provider**: ✅ Already implemented and functional

### **Architecture Prerequisites**
1. **Interface-First Design**: ✅ Pattern established in existing services
2. **Multi-tenant Isolation**: ✅ RLS policies active
3. **API Authentication**: ✅ JWT system operational

## Risk Assessment and Mitigation

### **High Risk Items**
1. **Technical Indicator Accuracy**: Implement with industry-standard libraries and validate against known datasets
2. **Performance Requirements**: Use vectorized pandas operations and bulk processing
3. **Temporal Integration Complexity**: Leverage existing temporal universe system architecture

### **Medium Risk Items** 
1. **OpenBB Integration Costs**: Implement cost monitoring and optimize free vs premium tier usage
2. **Frontend Complexity**: Start with basic implementations and iterate

### **Mitigation Strategies**
1. **Incremental Development**: Implement core indicators first (RSI, MACD, Momentum) before advanced features
2. **Performance Monitoring**: Real-time benchmarking of API response times
3. **Fallback Mechanisms**: Graceful degradation when indicator calculations fail

## Success Criteria and Validation

### **Technical Validation**
- ✅ All indicator calculations match industry standards (validated via unit tests)
- ✅ API endpoints respond within 500ms (95th percentile)
- ✅ Temporal calculations complete within 2 seconds for 1000 assets
- ✅ Complete dataset approach achieves 5x performance improvement

### **Business Validation**
- ✅ End-to-end workflow: Create universe → Configure indicators → Generate signals → View charts
- ✅ Temporal survivorship bias elimination demonstrated
- ✅ AI agent can perform indicator operations via natural language (preparation for Sprint 5)

### **Integration Validation**  
- ✅ OpenBB integration provides professional-grade data
- ✅ Triple-provider fallback system operational
- ✅ Multi-tenant security maintained across all new components

## Implementation Timeline

### **Week 1: Core Indicators Engine**
- Days 1-2: Indicator service interfaces and implementations
- Days 3-4: Temporal-aware indicator service
- Day 5: Unit testing and validation

### **Week 2: API Implementation** 
- Days 1-2: Indicators and signals API endpoints
- Days 3-4: OpenBB integration completion
- Day 5: Integration testing

### **Week 3: Frontend and Polish**
- Days 1-3: Frontend indicator components
- Days 4-5: Performance optimization and comprehensive testing

## Next Steps

1. **Immediate Priority**: Implement technical indicators service (`IIndicatorService` interface and implementation)
2. **Critical Path**: Create indicators API endpoints to enable frontend development
3. **Parallel Development**: Complete OpenBB advanced features while indicators are in development
4. **Testing Strategy**: Continuous integration testing with real market data validation

This implementation plan addresses all Sprint 3 requirements while building on the solid foundation already established in Sprints 0-2. The focus is on delivering the missing critical components (indicators engine and APIs) while maintaining the high-quality, production-ready architecture already established.