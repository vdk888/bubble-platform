# Demo Data Guide - Temporal Universe System

## Overview
A comprehensive test dataset has been created to showcase the temporal universe features in the Bubble Platform. This includes a realistic tech portfolio with 6 months of historical evolution data, complete with turnover analysis and performance metrics.

## Login Credentials
**Use these exact credentials to access the demo data:**

- **Email:** `demo@bubble.ai`
- **Password:** `Demo123!`
- **Subscription:** Pro (full feature access)

## What Was Created

### 1. Demo User Account
- Pre-configured user with Pro subscription
- Full access to all temporal universe features
- No setup required - ready to test immediately

### 2. Tech Leaders Portfolio Universe
**Universe Name:** "Tech Leaders Portfolio"

**Description:** Major technology companies portfolio showcasing temporal universe features with realistic turnover patterns

**Assets Created:**
- **Core Holdings:** AAPL, GOOGL, MSFT, AMZN, TSLA, META
- **Variable Holdings:** NVDA, NFLX, ORCL, CRM, ADBE, PYPL
- **Total Assets:** 12 major tech stocks with realistic market caps and sector classifications

### 3. Historical Timeline Data (6 Months)
**Timeline Span:** March 2025 - July 2025 (6 months of data)

**Monthly Evolution Pattern:**
- **Month 1 (Mar):** Initial composition - AAPL, GOOGL, MSFT, AMZN, TSLA, META
- **Month 2 (Apr):** Added NVDA (semiconductor growth theme)
- **Month 3 (May):** Removed AMZN, added NFLX (streaming focus)
- **Month 4 (Jun):** Added ORCL, removed TSLA (enterprise software shift)
- **Month 5 (Jul):** Re-added TSLA and AMZN, removed NFLX (rebalancing)
- **Month 6 (Aug):** Final composition with CRM (CRM platform growth)

**Turnover Statistics:**
- **Average Monthly Turnover:** 24.0%
- **Realistic turnover patterns** showing portfolio evolution
- **Asset addition/removal tracking** with reasons for each change

### 4. Performance Metrics
Each historical snapshot includes realistic performance metrics:
- **Expected Return:** 8-15% annually
- **Volatility:** 15-25% range
- **Sharpe Ratio:** Calculated dynamically
- **Sector Allocation:** Technology vs Consumer Discretionary breakdown

## Features to Test

### 1. Timeline Visualization
- **What to test:** Interactive timeline showing 6 months of universe evolution
- **Expected outcome:** Visual representation of how the portfolio changed over time
- **Key insights:** Clear view of when assets were added/removed

### 2. Universe Evolution Charts
- **What to test:** Charts showing composition changes between periods
- **Expected outcome:** Before/after comparisons for each rebalancing period
- **Key insights:** Understanding of portfolio drift and rebalancing decisions

### 3. Turnover Analysis
- **What to test:** Detailed turnover metrics and calculations
- **Expected outcome:** Monthly turnover rates, cumulative changes, asset flows
- **Key insights:** Quantitative analysis of portfolio stability vs. evolution

### 4. Historical Composition Tracking
- **What to test:** Point-in-time universe composition queries
- **Expected outcome:** Ability to see exact portfolio at any historical date
- **Key insights:** Elimination of survivorship bias for backtesting

### 5. Performance Metrics Evolution
- **What to test:** How risk/return characteristics changed over time
- **Expected outcome:** Performance metrics aligned with composition changes
- **Key insights:** Impact of asset changes on portfolio characteristics

## API Endpoints to Test

### Authentication
```bash
POST /api/v1/auth/login
{
  "email": "demo@bubble.ai",
  "password": "Demo123!"
}
```

### Universe Data
```bash
GET /api/v1/universes/
# Should return "Tech Leaders Portfolio" universe

GET /api/v1/universes/{universe_id}/
# Get detailed universe info including temporal data

GET /api/v1/universes/{universe_id}/timeline
# Get historical evolution timeline

GET /api/v1/universes/{universe_id}/snapshots
# Get all historical snapshots

GET /api/v1/universes/{universe_id}/turnover-analysis
# Get turnover statistics and analysis
```

### Temporal Queries
```bash
GET /api/v1/universes/{universe_id}/composition?date=2025-05-15
# Get composition at specific historical date

GET /api/v1/universes/{universe_id}/evolution?start_date=2025-03-01&end_date=2025-07-29
# Get evolution over date range
```

## Technical Implementation Details

### Database Schema
- **Users Table:** Demo user with pro subscription
- **Assets Table:** 12 tech stocks with full metadata
- **Universes Table:** 1 universe with screening criteria
- **UniverseAssets Table:** Current universe composition
- **UniverseSnapshots Table:** 6 historical snapshots with full temporal data

### Data Quality Features
- **Realistic Market Data:** Proper market caps, sectors, and company names
- **Consistent Evolution:** Logical portfolio changes with documented reasons
- **Performance Alignment:** Metrics that reflect composition changes
- **Temporal Integrity:** Proper date sequencing and snapshot consistency

## Frontend Testing Scenarios

### Scenario 1: Portfolio Manager Review
1. Login with demo credentials
2. Navigate to "Tech Leaders Portfolio"
3. Review current composition and performance
4. Access timeline view to see 6-month evolution
5. Analyze turnover patterns and rebalancing decisions

### Scenario 2: Backtest Preparation
1. Select historical date range (March-July 2025)
2. Verify universe composition at each rebalancing point
3. Confirm elimination of survivorship bias
4. Prepare backtest with evolving universe data

### Scenario 3: Risk Analysis
1. Compare sector allocation changes over time
2. Analyze turnover impact on transaction costs
3. Review performance metric evolution
4. Assess portfolio stability vs. adaptation

## Data Validation

### Quality Checks Performed
- All assets have proper validation status
- Snapshot dates are sequential and consistent
- Turnover calculations are mathematically accurate
- Performance metrics are within realistic ranges
- Relationships between entities are properly maintained

### Business Logic Validation
- Portfolio changes reflect realistic investment decisions
- Asset selection aligns with tech sector screening criteria
- Turnover rates are consistent with active portfolio management
- Performance evolution matches composition changes

## Next Steps for Development

### Immediate Testing Priorities
1. **UI Components:** Test timeline visualization components
2. **API Integration:** Verify all temporal endpoints work correctly
3. **Performance:** Ensure fast queries across 6 months of data
4. **User Experience:** Validate intuitive navigation of temporal features

### Enhancement Opportunities
1. **Additional Universes:** Create demo data for different sectors/strategies
2. **Longer History:** Extend timeline to 12+ months for better testing
3. **More Complexity:** Add sub-universe tracking and multi-level hierarchies
4. **Real-Time Updates:** Integrate with live market data for current snapshots

## Technical Notes

### Database Optimization
- All temporal queries use proper indexes
- JSON fields store flexible metadata
- Foreign key relationships maintain data integrity
- Soft deletes preserve historical data

### API Performance
- Snapshot queries optimized for date range filtering
- Asset composition cached for faster retrieval
- Turnover calculations performed efficiently
- Pagination support for large datasets

### Security Implementation
- Multi-tenant isolation enforced via user ownership
- All queries filtered by user permissions
- Audit trail maintained for all universe changes
- Input validation prevents data corruption

---

## Quick Start Checklist

1. **Login:** Use `demo@bubble.ai` / `Demo123!`
2. **Navigate:** Find "Tech Leaders Portfolio" universe
3. **Explore Timeline:** Access 6-month evolution view
4. **Analyze Turnover:** Review monthly changes and statistics
5. **Test APIs:** Use provided endpoints for integration testing

This demo dataset provides comprehensive coverage of temporal universe features, enabling thorough testing of the frontend visualization components and API integration points.