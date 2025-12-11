# NEXUS: Intelligent Supply Chain Orchestration Engine

## Vision

Transform POWERGRID's supply chain from reactive logistics to a proactive, AI-driven orchestration system - a "Sentient Supply Chain" that prevents crises rather than managing them.

## Strategic Goals

1. **Financial Prudence**: Reduce procurement costs (5-10%), minimize inventory carrying costs (15-20%)
2. **Operational Efficiency**: Reduce material shortage delays by 30%, optimize warehouse operations
3. **Strategic Resilience**: Proactive risk management, long-term planning via GNN, Explainable AI

## Key Features (20 Core Pillars)

- Digital Twin simulation with engineering-standard BOM calculations
- AI Sentinel Agent for market intelligence & RoW detection
- Hybrid Prophet + modifier-based demand forecasting
- Smart inventory reconciliation (transfer-first logic)
- Multi-criteria procurement optimizer with XAI reasoning
- Unsupervised GNN for strategic grid health monitoring

## Tech Stack

- **Backend**: Python 3.9+
- **ML/AI**: Prophet, PyTorch, scikit-learn
- **Data**: pandas, numpy
- **Visualization**: matplotlib, plotly

## Setup

```bash
pip install -r requirements.txt
python src/core/data_factory.py  # Generate synthetic datasets
python main.py                    # Run simulation
```

## Project Structure

- `src/core/`: Foundational layer (Digital Twin, BOM)
- `src/intelligence/`: External awareness (Sentinel, Weather)
- `src/forecasting/`: Demand forecasting engine
- `src/solver/`: Supply chain optimization logic
- `src/graph/`: Graph database simulation
- `src/ai/`: Advanced AI (Prophet, GNN)

## Author

Built for Smart India Hackathon 2025 - POWERGRID Challenge
