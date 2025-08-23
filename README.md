# =€ Bubble Platform

AI-Native Investment Strategy Automation Platform

## <¯ Overview

Bubble Platform is a comprehensive investment management system that combines:
- **Universe Definition**: Create and manage investment universes
- **Technical Indicators**: RSI, MACD, Momentum with signal generation  
- **Strategy Backtesting**: Historical performance validation
- **Risk Parity Portfolios**: Automated multi-strategy allocation
- **AI Agent**: Natural language platform control with tool calling
- **Broker Execution**: Automated rebalancing via multi-broker integration

## <× Architecture

- **Backend**: FastAPI + PostgreSQL + Redis
- **Frontend**: React + TypeScript + Tailwind CSS
- **AI Integration**: Anthropic Claude with tool calling
- **Deployment**: Docker + Docker Compose

## =€ Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd bubble-platform
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Start development environment**:
   ```bash
   docker-compose up -d
   ```

3. **Access the application**:
   - API: http://localhost:8000
   - Frontend: http://localhost:3000
   - API Docs: http://localhost:8000/docs

## =Ú Documentation

- [Architecture Decision Records](./docs/decisions/)
- [API Documentation](http://localhost:8000/docs) (when running)

## =à Development

Built with Interface-First Design principles for:
- Clean service boundaries
- Easy testing and mocking
- Seamless microservice migration
- AI-native architecture

## =Ý License

Private - All rights reserved