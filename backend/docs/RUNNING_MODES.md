# NEXUS - Running Modes Guide

## Overview

NEXUS supports three main operating modes that can be launched via the main `main.py` file:

1. **Simulation Mode** - Run the supply chain orchestration simulation
2. **API Mode** - Start the REST API server for external integrations
3. **Data Generation Mode** - Generate synthetic digital twin data

---

## Quick Start

### 1. Simulation Mode (Default)

Run the complete supply chain simulation:

```bash
# Default: 7 days with balanced strategy
python main.py

# Custom parameters
python main.py --mode simulation --days 30 --strategy cost_focused
```

**Strategies available:**

- `balanced` - Balance cost and risk (default)
- `cost_focused` - Minimize procurement costs
- `rush` - Prioritize speed of delivery
- `risk_averse` - Maximize reliability

**Output:**

- Daily action plans saved to: `data/outputs/action_plans/`
- Simulation logs saved to: `data/outputs/simulation_logs/`
- Real-time console output with progress tracking

### 2. API Mode

Start the REST API server for accessing simulation data and running simulations remotely:

```bash
# Start API server on port 8000
python main.py --mode api
```

**Available at:**

- Interactive API Docs: `http://localhost:8000/docs` (Swagger UI)
- Alternative Docs: `http://localhost:8000/redoc` (ReDoc)
- API Root: `http://localhost:8000/`

**Key endpoints:**

- `GET /health` - Health check
- `POST /api/v1/simulation/run` - Run simulation via API
- `GET /api/v1/simulation/status` - Get simulation status
- `GET /api/v1/simulation/action-plans` - Retrieve action plans
- `POST /api/v1/forecasts/generate` - Generate demand forecasts
- See `docs/API_GUIDE.md` for complete API reference

### 3. Data Generation Mode

Generate fresh synthetic data for testing:

```bash
# Generate new digital twin data
python main.py --mode generate-data
```

**Generates:**

- 30 materials with specifications
- 20 vendors with locations and reliability scores
- 15 warehouses across India
- 50 projects in various states
- Historical consumption data (50 weeks)
- BOM standards
- Weather forecasts
- Market sentiment data

---

## Command Line Options

```bash
python main.py --help
```

**Full options:**

```
usage: main.py [-h] [--mode {simulation,api,generate-data}] 
               [--days DAYS] 
               [--strategy {balanced,cost_focused,rush,risk_averse}]

NEXUS - Intelligent Supply Chain Orchestration for POWERGRID

options:
  -h, --help            show this help message and exit
  --mode {simulation,api,generate-data}
                        Operation mode (default: simulation)
  --days DAYS           Number of days to simulate (default: 7)
  --strategy {balanced,cost_focused,rush,risk_averse}
                        Optimization strategy (default: balanced)
```

---

## Usage Examples

### Example 1: Quick 7-Day Simulation

```bash
python main.py
```

### Example 2: 30-Day Simulation with Cost Focus

```bash
python main.py --mode simulation --days 30 --strategy cost_focused
```

### Example 3: Start API and Access from Browser

```bash
# Terminal 1: Start API server
python main.py --mode api

# Terminal 2 or Browser:
# Open http://localhost:8000/docs
```

### Example 4: Generate Fresh Data, Then Run Simulation

```bash
# Generate data
python main.py --mode generate-data

# Run simulation with generated data
python main.py --mode simulation --days 14
```

### Example 5: API-Based Simulation

```bash
# Terminal 1: Start API
python main.py --mode api

# Terminal 2: Run simulation via API
curl -X POST http://localhost:8000/api/v1/simulation/run \
  -H "Content-Type: application/json" \
  -d '{"days": 10, "strategy": "balanced"}'
```

---

## Output Files

### Simulation Mode

- **Action Plans:** `data/outputs/action_plans/action_plan_YYYYMMDD.json`
- **Logs:** `data/outputs/simulation_logs/`
- **Raw Data:** `data/generated/`

### API Mode

- **Database:** `data/nexus.db` (SQLite)
- **Logs:** Console output with request details

---

## Monitoring

### Simulation Progress

The simulation provides real-time progress information:

```
2025-12-08 15:28:47 - nexus_orchestrator - INFO - Processing: 2025-12-08
2025-12-08 15:28:47 - nexus_orchestrator - INFO - 1. Generating demand forecast...
2025-12-08 15:28:47 - nexus_orchestrator - INFO -    ✓ Generated 42 demand forecasts
2025-12-08 15:28:47 - nexus_orchestrator - INFO - 2. Aggregating material requirements...
...
```

### API Health

```bash
curl -s http://localhost:8000/health | python -m json.tool
```

---

## Environment Configuration

### Environment Variables

```bash
# Database URL (for API mode)
export DATABASE_URL="sqlite:///./data/nexus.db"

# Python environment
conda activate nexus
```

### Configuration File

Edit `src/config.py` for:

- Number of materials, vendors, warehouses
- Simulation parameters
- Vendor evaluation weights
- Tax rates and lead times

---

## Troubleshooting

### Issue: "Cannot save file into a non-existent directory"

**Solution:** Ensure `data/` directory exists

```bash
mkdir -p data/generated
mkdir -p data/outputs/action_plans
mkdir -p data/outputs/simulation_logs
```

### Issue: API port 8000 already in use

**Solution:** Kill existing process or use different port

```bash
# Kill existing
lsof -ti:8000 | xargs kill -9

# Or use different port by editing src/api/server.py
```

### Issue: ProphetForecaster fails

**Solution:** Ensure Prophet is installed

```bash
conda activate nexus
pip install prophet
```

---

## Performance Considerations

| Mode | Typical Duration | Memory | CPU |
|------|-----------------|--------|-----|
| Simulation (7 days) | 5-10 seconds | 500MB | Low-Medium |
| Simulation (30 days) | 20-30 seconds | 800MB | Medium |
| API Server | N/A | 300MB | Low |
| Data Generation | 2-3 seconds | 400MB | Low |

---

## Architecture Integration

All modes are built on the same core components:

```
main.py (Unified Entry Point)
├── NexusOrchestrator (Core Logic)
├── src/forecasting/ (Prophet Forecasts)
├── src/solver/ (Optimization)
├── src/intelligence/ (AI Agents)
├── src/api/ (FastAPI REST)
└── src/core/data_factory (Data Generation)
```

---

## Support & Documentation

- **API Documentation:** Run API mode and visit `/docs`
- **Architecture Guide:** `docs/ARCHITECTURE.py`
- **API Guide:** `docs/API_GUIDE.md`
- **Production Roadmap:** `docs/PRODUCTION_ROADMAP.md`
- **README:** `README.md`

---

## License & Attribution

Built for Smart India Hackathon 2024 for POWERGRID
