# XRP Arbitrage Trading System

## Overview

This is a modular XRP arbitrage trading system built with Flask that monitors price differences between XRP/USDT and XRP/USDC trading pairs to identify and execute profitable arbitrage opportunities. The system features a web-based interface with real-time monitoring, trading analytics, and comprehensive risk management. It simulates trading operations with the MEXC exchange API and implements a "sell-first" trading strategy to minimize risk exposure.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Framework
- **Flask**: Web application framework handling HTTP requests and responses
- **SQLAlchemy**: Database ORM for managing trading data, balances, and configuration
- **SQLite**: Default database for development with PostgreSQL support via environment variables

### Modular Core Components
- **Price Monitor**: Background thread monitoring XRP price feeds for both USDT and USDC pairs
- **Balance Manager**: Tracks wallet balances across XRP, USDT, and USDC currencies with locked/free amounts
- **Trade Executor**: Implements sell-first arbitrage strategy with order management
- **Risk Controller**: Validates trades against daily volume limits, balance safety margins, and volatility thresholds
- **Arbitrage Engine**: Main strategy engine coordinating price monitoring, opportunity detection, and trade execution
- **Data Logger**: Comprehensive logging system for trades, system events, and error tracking

### Business Logic Layer
- **Trading Strategy**: Advanced decision logic using multiple factors (spread size, market volatility, historical success rate)
- **Data Pipeline**: Analytics processing for trading performance metrics and opportunity analysis
- **Profit Analyzer**: Real-time and historical profit/loss calculations with success rate tracking

### Web Interface Architecture
- **Dashboard**: Main control panel showing real-time prices, spreads, balances, and trading controls
- **Monitor**: Dedicated trading activity feed with comprehensive analytics and performance charts
- **Configuration**: Settings management for trading parameters and risk controls
- **RESTful API**: JSON endpoints for real-time data updates and trading operations

### Database Schema
- **TradingConfig**: System configuration with spread thresholds, trade amounts, and risk parameters
- **Trade**: Individual trade records with execution details, P&L, and status tracking
- **Balance**: Real-time balance tracking for all currencies with locked amounts
- **PriceHistory**: Historical price data for trend analysis
- **ArbitrageOpportunity**: Detected opportunities with spread calculations and execution status

### Frontend Architecture
- **Bootstrap 5**: Dark-themed responsive UI optimized for trading terminals
- **Chart.js**: Real-time price charts and analytics visualizations
- **WebSocket-ready**: Architecture prepared for real-time data streaming
- **Modular JavaScript**: Separate modules for dashboard, monitor, and chart functionality

## External Dependencies

### Core Dependencies
- **Flask**: Web framework and request handling
- **SQLAlchemy**: Database ORM and connection management
- **Werkzeug**: WSGI utilities and development server

### Frontend Libraries
- **Bootstrap 5**: UI framework and responsive design
- **Chart.js**: Data visualization and trading charts
- **Font Awesome**: Icon library for trading interface

### Development Tools
- **Python Logging**: Comprehensive system and trade logging
- **Threading**: Background price monitoring and trade execution

### Planned Integrations
- **MEXC Exchange API**: Live market data and trade execution (currently simulated)
- **PostgreSQL**: Production database (configurable via DATABASE_URL environment variable)
- **WebSocket**: Real-time data streaming for live price updates

### Configuration Management
- **Environment Variables**: Database URLs, API keys, and deployment settings
- **Session Management**: User preferences and trading state persistence
- **Proxy Support**: Production deployment compatibility with reverse proxies

The system is designed for easy deployment on cloud platforms with environment-based configuration and supports both development (SQLite) and production (PostgreSQL) database configurations.