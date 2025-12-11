# NEXUS - Power Grid Inventory & Demand Forecasting System

A comprehensive inventory management and demand forecasting platform for POWERGRID Corporation of India, featuring real-time stock monitoring, understock/overstock trigger alerts, and intelligent procurement recommendations.

## 🚀 Features

### Inventory Management
- **Real-time Stock Monitoring** - Track stock levels across 22+ warehouses
- **Trigger Engine** - Instant UTR (Understock Trigger Ratio) and OTR (Overstock Trigger Ratio) calculations
- **Smart Alerts** - Automated email and WhatsApp notifications when thresholds are breached
- **PDF Reports** - Auto-generated inventory status reports

### Analytics & Forecasting
- **Demand Forecasting** - ML-powered predictions for material consumption
- **Cost Optimization** - Track savings from reduced rush orders and optimal inventory
- **Procurement Recommendations** - Intelligent suggestions based on lead times and demand

### Visualization
- **Interactive Maps** - Substation locations with stock status indicators
- **Real-time Dashboards** - Live metrics and KPIs
- **Stock Distribution Charts** - Visual breakdown by warehouse and material

## 🛠️ Tech Stack

### Backend
- **FastAPI** - High-performance Python web framework
- **SQLAlchemy** - ORM for database operations
- **PostgreSQL/SQLite** - Database
- **Pydantic** - Data validation

### Frontend
- **React 18** - UI library
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool
- **Framer Motion** - Animations
- **Leaflet** - Interactive maps

## 📦 Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- npm or yarn

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m src.api.server
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
DATABASE_URL=sqlite:///./nexus.db
WHATSAPP_TOKEN=your_whatsapp_token
WHATSAPP_PHONE_ID=your_phone_id
EMAIL_HOST=smtp.gmail.com
EMAIL_USER=your_email
EMAIL_PASSWORD=your_app_password
```

## 📊 API Endpoints

### Inventory
- `GET /api/v1/inventory/stock` - Get all stock items
- `GET /api/v1/inventory/analytics/summary` - Inventory summary
- `POST /api/v1/inventory/update-and-alert` - Update stock with alert triggers
- `GET /api/v1/inventory/triggers` - Get trigger status for all items

### Substations
- `GET /api/v1/substations/map/data` - Substation map data

### Forecasting
- `GET /api/v1/demand-forecast/predictions` - Get demand predictions

## 🎯 Trigger Engine

The trigger engine calculates stock health using these metrics:

| Metric | Formula | Description |
|--------|---------|-------------|
| **UTR** | `(ROP - Stock) / ROP` | Understock Trigger Ratio (0-1) |
| **OTR** | `(Stock - MaxStock) / MaxStock` | Overstock Trigger Ratio |
| **PAR** | `Stock / (ROP + 7-day buffer)` | Procurement Adequacy Ratio |

### Severity Levels
- 🔴 **RED** - Critical understock, immediate action required
- 🟡 **AMBER** - Warning level, plan procurement soon
- 🟢 **GREEN** - Optimal stock levels

## 📱 Screenshots

<img width="2444" height="1814" alt="image" src="https://github.com/user-attachments/assets/303c35b0-b411-4857-848a-e77f614eaee2" />

The application features a modern dark-themed UI with:
- Glassmorphism effects
- Smooth animations
- Real-time data updates
- Responsive design

## 👥 Team

Built for POWERGRID Corporation of India

## 📄 License

This project is proprietary software developed for POWERGRID Corporation of India.
