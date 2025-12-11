# NEXUS API Guide

## Quick Start

### 1. Run the API Server

```bash
# Method 1: Using main.py (recommended)
python main.py --mode api

# Method 2: Using uvicorn directly
uvicorn src.api.server:app --reload --port 8000
```

### 2. Access API Documentation

Once the server is running, open your browser to:

- **Swagger UI**: <http://localhost:8000/docs>
- **ReDoc**: <http://localhost:8000/redoc>

---

## Available Modes

### Simulation Mode (Default)

Run the supply chain simulation:

```bash
python main.py --mode simulation --days 7 --strategy balanced
```

### API Mode

Start the REST API server:

```bash
python main.py --mode api
```

### Data Generation Mode

Generate synthetic data:

```bash
python main.py --mode generate-data
```

---

## API Endpoints Overview

### Core Resources

#### Locations

- `GET /api/v1/locations/` - List all locations
- `POST /api/v1/locations/` - Create location
- `GET /api/v1/locations/{id}` - Get specific location
- `PUT /api/v1/locations/{id}` - Update location
- `DELETE /api/v1/locations/{id}` - Delete location

#### Projects

- `GET /api/v1/projects/` - List all projects
- `POST /api/v1/projects/` - Create project
- `GET /api/v1/projects/{id}` - Get specific project
- `GET /api/v1/projects/{id}/requirements` - Get project's material requirements

#### Materials

- `GET /api/v1/materials/` - List all materials
- `POST /api/v1/materials/` - Create material
- `GET /api/v1/materials/{id}` - Get specific material
- `GET /api/v1/materials/code/{code}` - Get material by code (e.g., MAT-001)
- `GET /api/v1/materials/category/{category}` - Filter by category

#### Material Requirements

- `GET /api/v1/material-requirements/` - List all requirements
- `POST /api/v1/material-requirements/` - Create requirement
- `GET /api/v1/material-requirements/status/{status}` - Filter by status
- `GET /api/v1/material-requirements/priority/{priority}` - Filter by priority

#### Tower Types & Substation Types

- `GET /api/v1/tower-types/` - List tower types
- `GET /api/v1/substation-types/` - List substation types
- Similar CRUD operations available

#### Budgets & Taxes

- `GET /api/v1/budgets/` - List budgets
- `GET /api/v1/budgets/fiscal-year/{year}` - Filter by fiscal year
- `GET /api/v1/budgets/summary/{year}` - Get budget summary
- `GET /api/v1/taxes/` - List taxes
- `POST /api/v1/taxes/calculate` - Calculate tax for amount

---

### Advanced Features

#### Forecasting

```bash
# Generate forecasts using Prophet
POST /api/v1/forecasts/generate
{
  "weeks": 12,
  "material_ids": [1, 2, 3],
  "location_ids": [1, 2]
}

# Get forecast summary
GET /api/v1/forecasts/summary

# Get procurement schedule
GET /api/v1/forecasts/procurement-schedule

# Get forecasts by material
GET /api/v1/forecasts/material/{material_id}
```

#### Simulation

```bash
# Run simulation via API
POST /api/v1/simulation/run
{
  "days": 7,
  "strategy": "balanced",
  "start_date": "2025-12-08T00:00:00"
}

# Get simulation status
GET /api/v1/simulation/status

# Get recent action plans
GET /api/v1/simulation/action-plans

# Get action plan for specific date
GET /api/v1/simulation/action-plans/20251208

# Get dashboard data
GET /api/v1/simulation/dashboard

# Generate synthetic data via API
POST /api/v1/simulation/generate-data
```

---

## Example Requests

### Create a Location

```bash
curl -X POST http://localhost:8000/api/v1/locations/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mumbai Central",
    "state": "Maharashtra",
    "region": "Western",
    "latitude": 19.0760,
    "longitude": 72.8777
  }'
```

### Create a Project

```bash
curl -X POST http://localhost:8000/api/v1/projects/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "765kV Transmission Line - Phase 2",
    "description": "High-voltage transmission line project",
    "location_id": 1,
    "project_type": "Transmission",
    "voltage_level": "765kV",
    "priority": "High",
    "budget": 50000000000,
    "status": "Planning"
  }'
```

### Create a Material

```bash
curl -X POST http://localhost:8000/api/v1/materials/ \
  -H "Content-Type: application/json" \
  -d '{
    "material_code": "MAT-001",
    "name": "Conductor_ACSR_Bersimis",
    "category": "Conductor",
    "unit": "meter",
    "unit_price": 850.50,
    "lead_time_days": 21,
    "min_order_quantity": 1000,
    "safety_stock_days": 30
  }'
```

### Generate Forecasts

```bash
curl -X POST http://localhost:8000/api/v1/forecasts/generate \
  -H "Content-Type: application/json" \
  -d '{
    "weeks": 8
  }'
```

### Run Simulation

```bash
curl -X POST http://localhost:8000/api/v1/simulation/run \
  -H "Content-Type: application/json" \
  -d '{
    "days": 7,
    "strategy": "balanced"
  }'
```

---

## Database

The API uses SQLite by default with the database stored at:

```
data/nexus.db
```

To use PostgreSQL instead, set the `DATABASE_URL` environment variable:

```bash
export DATABASE_URL="postgresql://user:password@localhost/nexus"
```

---

## Architecture

```
NEXUS API
├── src/api/
│   ├── server.py           # FastAPI application
│   ├── database.py         # Database configuration
│   ├── db_models.py        # SQLAlchemy ORM models
│   ├── schemas.py          # Pydantic request/response schemas
│   └── routes/             # API route modules
│       ├── locations.py
│       ├── projects.py
│       ├── materials.py
│       ├── material_requirements.py
│       ├── tower_types.py
│       ├── substation_types.py
│       ├── budgets.py
│       ├── taxes.py
│       ├── forecasts.py
│       └── simulation.py
```

---

## Integration with Core NEXUS

The API integrates seamlessly with the core NEXUS simulation engine:

1. **Forecasting**: Uses the ProphetForecaster from `src/forecasting/`
2. **Simulation**: Runs the NexusOrchestrator from `main.py`
3. **Data Generation**: Uses DataFactory from `src/core/`

---

## Development

### Install Dependencies

```bash
conda activate nexus
pip install fastapi uvicorn sqlalchemy pydantic
```

### Run in Development Mode

```bash
python main.py --mode api
```

### Run Tests (Coming Soon)

```bash
pytest tests/api/
```

---

## Support

For issues or questions:

- Check the interactive docs: <http://localhost:8000/docs>
- Review the simulation logs in `data/outputs/simulation_logs/`
- Check action plans in `data/outputs/action_plans/`
