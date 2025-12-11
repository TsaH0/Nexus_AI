"""
NEXUS Architecture Visualization
Shows the complete system flow
"""

ARCHITECTURE = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                         NEXUS ARCHITECTURE - PHASE 1                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────────┐
│                          📊 DATA FOUNDATION (COMPLETE)                       │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                       ┌───────────────┼───────────────┐
                       │               │               │
                   [Materials]     [Vendors]      [Warehouses]
                   • 30 types      • 20 firms     • 15 locations
                   • Prices        • Reliability  • Geo-coords
                   • Shelf life    • Regional     • Capacity
                                   
                                   [Projects]
                                   • 50 active
                                   • Multi-stage
                                   • RoW tracking

┌──────────────────────────────────────────────────────────────────────────────┐
│                       🧮 CALCULATION ENGINE (COMPLETE)                       │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                       ┌───────────────┼───────────────┐
                       │               │               │
                  [BOM Calculator]  [Geo Utils]   [XAI Explainer]
                  • Stage-based     • Haversine   • Reasoning
                  • Terrain adj.    • Transport   • Transparency
                  • Cost estimate   • Delivery    • Summaries

┌──────────────────────────────────────────────────────────────────────────────┐
│                    🔮 INTELLIGENCE LAYER (PHASE 2 - TODO)                    │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                       ┌───────────────┼───────────────┐
                       │               │               │
                 [Sentinel Agent]  [Weather Service]  [Prophet]
                 • RoW detection   • Impact calc     • OpEx forecast
                 • Market intel    • Seasonal       • Seasonality
                 • Risk alerts     • Construction   • Regressors

┌──────────────────────────────────────────────────────────────────────────────┐
│                     🧠 FORECASTING ENGINE (PHASE 2 - TODO)                   │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                       ┌───────────────┼───────────────┐
                       │               │               │
                  [Demand Engine]   [Safety Stock]  [Risk Adj]
                  • CapEx + OpEx    • Dynamic       • Multipliers
                  • BOM + Prophet   • Regional      • Buffering
                  • Total forecast  • Seasonal      

┌──────────────────────────────────────────────────────────────────────────────┐
│                      ⚙️  OPTIMIZATION SOLVER (PHASE 3 - TODO)                │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                       ┌───────────────┼───────────────┐
                       │               │               │
               [Inventory Recon]  [Procurement]   [Batcher]
               • Transfer-first   • Multi-criteria • Aggregation
               • Net demand       • Landed cost    • Bulk discount
               • Capacity check   • Risk-adj ETA   • Min orders

┌──────────────────────────────────────────────────────────────────────────────┐
│                       📋 ACTION PLAN OUTPUT (PHASE 4 - TODO)                 │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                  [main.py]
                                       │
                       ┌───────────────┼───────────────┐
                       │               │               │
                  [Purchase Orders] [Transfers]   [Holds]
                  • Vendor          • Warehouse   • RoW issues
                  • Quantity        • Distance    • Reasoning
                  • Cost            • Cost        • Alerts
                       │               │               │
                       └───────────────┼───────────────┘
                                       ▼
                              [JSON Action Plans]
                              data/outputs/action_plans/
                              action_plan_2025_01_15.json

╔══════════════════════════════════════════════════════════════════════════════╗
║                              KEY STATISTICS                                  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Phase 1 Complete:      11/20 features (55%)                                ║
║  Lines of Code:         ~2,500                                              ║
║  Data Points:           50 projects, 30 materials, 20 vendors, 15 warehouses║
║  Geographic Coverage:   5 regions, 15 cities across India                   ║
║  Time Horizon:          365 days simulation, 2 years historical             ║
║  Cost Optimization:     Transfer-first, multi-criteria, bulk batching       ║
║  XAI Integration:       Every decision explained                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

SAMPLE_WORKFLOW = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    SAMPLE WORKFLOW: DAY 15 SIMULATION                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

Day 15: 2025-01-15
Region: Northern

1️⃣  INTELLIGENCE GATHERING
   ├─ Market Sentiment: Labor Strike detected in Punjab (Severity: High)
   ├─ Weather: Heavy Rain in Himachal Pradesh
   └─ Action: Add 15-day lead time buffer, halt mountain projects

2️⃣  DEMAND FORECASTING
   ├─ CapEx Demand (Projects):
   │  ├─ PRJ-003 (400kV Line): Needs 500 MT Steel (Construction stage)
   │  └─ PRJ-018 (Substation): Needs 2x Transformers (Foundation stage)
   │
   ├─ OpEx Demand (Prophet):
   │  └─ Transformer Oil: 850 KL predicted (monsoon + temperature)
   │
   └─ Total: Steel=500 MT, Transformers=2, Oil=850 KL

3️⃣  INVENTORY RECONCILIATION
   ├─ Steel (500 MT needed):
   │  ├─ WH-001 (Delhi): 300 MT available
   │  ├─ WH-003 (Chandigarh): 250 MT available (150km away)
   │  └─ Decision: Transfer 200 MT from WH-003 → WH-001 (Cost: ₹3.75L)
   │           Procure remaining 300 MT
   │
   └─ Transformers (2 needed):
       ├─ No inventory available
       └─ Decision: Procure 2 units

4️⃣  VENDOR OPTIMIZATION
   ├─ Steel (300 MT):
   │  ├─ Candidate: Tata Steel (Price: ₹55K/MT, ETA: 32 days, Rel: 97%)
   │  ├─ Candidate: JSW Steel (Price: ₹53K/MT, ETA: 38 days, Rel: 94%)
   │  └─ SELECTED: Tata Steel (Balanced strategy: better reliability)
   │     Landed Cost: ₹1.95 crore (incl. GST + transport)
   │
   └─ Transformers (2 units):
       ├─ Candidate: Siemens (Price: ₹85L/unit, ETA: 120 days, Rel: 98%)
       ├─ Candidate: ABB (Price: ₹88L/unit, ETA: 110 days, Rel: 96%)
       └─ SELECTED: Siemens (Better reliability, acceptable timeline)
          Landed Cost: ₹2.01 crore

5️⃣  ACTION PLAN GENERATED
   ├─ Purchase Orders:
   │  ├─ PO-00015: 300 MT Steel from Tata → WH-001 (₹1.95Cr)
   │  └─ PO-00016: 2x Transformers from Siemens → WH-001 (₹2.01Cr)
   │
   ├─ Transfer Orders:
   │  └─ TR-00008: 200 MT Steel | WH-003 → WH-001 (₹3.75L)
   │
   ├─ Projects On Hold:
   │  └─ PRJ-045 (Himachal Pradesh line) - Heavy rain forecast
   │
   └─ Alerts:
       └─ Labor strike may delay Punjab deliveries by 15 days

6️⃣  COST SUMMARY
   ├─ Total Procurement: ₹3.96 crore
   ├─ Total Transfers:   ₹3.75 lakh
   ├─ Savings (vs individual orders): ₹42 lakh (by transfer-first)
   └─ XAI Reasoning: Attached to each decision

Output: data/outputs/action_plans/action_plan_2025_01_15.json

╔══════════════════════════════════════════════════════════════════════════════╗
║                       🎯 STRATEGIC IMPACT ACHIEVED                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ✅ Financial:     ₹42L saved by transfer optimization                      ║
║  ✅ Operational:   No material shortages, proactive hold                    ║
║  ✅ Risk:          Labor strike buffer applied, weather-aware               ║
║  ✅ Transparency:  Every decision fully explained                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

if __name__ == "__main__":
    print(ARCHITECTURE)
    print("\n\n")
    print(SAMPLE_WORKFLOW)
