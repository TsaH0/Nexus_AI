# Inventory Management System

## Overview

The NEXUS Inventory Management System is a comprehensive, enterprise-grade solution for managing materials, stock levels, transactions, reservations, and alerts across multiple warehouses. Built for POWERGRID's supply chain operations.

## Features

### 🏭 Core Functionality

1. **Multi-Warehouse Stock Management**
   - Real-time stock tracking across all warehouses
   - Available, reserved, and in-transit quantities
   - Automatic reorder point monitoring
   - Min/max stock level enforcement

2. **Stock Operations**
   - **Stock IN**: Receive materials from vendors (purchase orders, returns)
   - **Stock OUT**: Issue materials to projects (with project tracking)
   - **Stock Transfer**: Move inventory between warehouses
   - **Stock Adjustment**: Corrections for damage, losses, or audits

3. **Stock Reservations**
   - Reserve materials for specific projects
   - Priority-based reservation system (Low, Medium, High, Critical)
   - Partial fulfillment support
   - Automatic stock deduction on issuance

4. **Intelligent Alerts**
   - **Low Stock**: Alert when stock falls below reorder point
   - **Out of Stock**: Critical alert for zero inventory
   - **Overstock**: Warning for excess inventory
   - Auto-resolution when conditions improve

5. **Transaction History**
   - Complete audit trail of all inventory movements
   - Detailed transaction records with references
   - Cost tracking and valuation
   - User attribution for all operations

6. **Analytics & Reporting**
   - Real-time inventory summary dashboards
   - Warehouse-level inventory analytics
   - Material-level stock distribution
   - Stock movement reports
   - Cost analytics

## Database Schema

### Tables

#### `inventory_stocks`

Tracks current stock levels at each warehouse for each material.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| warehouse_id | Integer | Foreign key to warehouses |
| material_id | Integer | Foreign key to materials |
| quantity_available | Float | Available for use |
| quantity_reserved | Float | Reserved for projects |
| quantity_in_transit | Float | Coming to warehouse |
| reorder_point | Float | Trigger for reorder |
| max_stock_level | Float | Maximum allowed |
| min_stock_level | Float | Safety stock level |
| last_restocked_date | DateTime | Last stock IN |
| last_issued_date | DateTime | Last stock OUT |

#### `inventory_transactions`

Complete audit trail of all inventory movements.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| transaction_type | String | IN, OUT, TRANSFER_OUT, TRANSFER_IN, ADJUSTMENT |
| warehouse_id | Integer | Warehouse involved |
| material_id | Integer | Material involved |
| quantity | Float | Quantity moved |
| unit_cost | Float | Cost per unit |
| total_cost | Float | Total transaction cost |
| reference_type | String | PO, PROJECT, TRANSFER, etc. |
| reference_id | String | Reference document ID |
| project_id | Integer | Associated project (if any) |
| vendor_id | Integer | Associated vendor (if any) |
| remarks | Text | Additional notes |
| performed_by | String | User who performed |
| transaction_date | DateTime | When it happened |

#### `stock_reservations`

Material reservations for projects.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| warehouse_id | Integer | Warehouse to reserve from |
| material_id | Integer | Material to reserve |
| project_id | Integer | Project requiring material |
| quantity_reserved | Float | Total reserved |
| quantity_issued | Float | Already issued |
| reservation_date | DateTime | When reserved |
| required_by_date | DateTime | When needed |
| status | String | Active, Partially_Fulfilled, Fulfilled, Cancelled |
| priority | String | Low, Medium, High, Critical |

#### `stock_alerts`

Automated inventory alerts and warnings.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| alert_type | String | LOW_STOCK, OUT_OF_STOCK, EXPIRING_SOON, OVERSTOCK |
| severity | String | Low, Medium, High, Critical |
| warehouse_id | Integer | Affected warehouse |
| material_id | Integer | Affected material |
| current_quantity | Float | Current stock level |
| threshold_quantity | Float | Alert threshold |
| message | Text | Alert message |
| is_resolved | Boolean | Resolution status |
| alert_date | DateTime | When created |

## API Endpoints

### Stock Level Management

#### `GET /api/v1/inventory/stock`

Get all stock records with filtering.

**Query Parameters:**

- `warehouse_id` (optional): Filter by warehouse
- `material_id` (optional): Filter by material
- `low_stock_only` (optional): Show only low stock items
- `include_zero` (optional): Include zero stock items
- `skip`, `limit`: Pagination

**Response:** List of `InventoryStockWithDetails`

#### `GET /api/v1/inventory/stock/{warehouse_id}/{material_id}`

Get specific stock details.

**Response:** `InventoryStockWithDetails`

#### `POST /api/v1/inventory/stock`

Create new stock record.

**Body:** `InventoryStockCreate`

#### `PATCH /api/v1/inventory/stock/{warehouse_id}/{material_id}`

Update stock settings (reorder points, limits).

**Body:** `InventoryStockUpdate`

### Stock Operations

#### `POST /api/v1/inventory/operations/stock-in`

Add stock to warehouse.

**Request Body:**

```json
{
  "warehouse_id": 1,
  "material_id": 5,
  "quantity": 100.0,
  "unit_cost": 50000.0,
  "vendor_id": 2,
  "reference_type": "PO",
  "reference_id": "PO-20251208-0001",
  "remarks": "Purchase order receipt"
}
```

#### `POST /api/v1/inventory/operations/stock-out`

Remove stock from warehouse.

**Request Body:**

```json
{
  "warehouse_id": 1,
  "material_id": 5,
  "quantity": 50.0,
  "project_id": 3,
  "reference_type": "PROJECT",
  "reference_id": "PRJ-001",
  "remarks": "Issued to Project Alpha"
}
```

#### `POST /api/v1/inventory/operations/transfer`

Transfer stock between warehouses.

**Request Body:**

```json
{
  "material_id": 5,
  "source_warehouse_id": 1,
  "destination_warehouse_id": 2,
  "quantity": 25.0,
  "remarks": "Rebalancing inventory"
}
```

#### `POST /api/v1/inventory/operations/adjust`

Adjust stock level (corrections).

**Request Body:**

```json
{
  "warehouse_id": 1,
  "material_id": 5,
  "quantity_adjustment": -10.0,
  "remarks": "Damaged during inspection"
}
```

### Transaction History

#### `GET /api/v1/inventory/transactions`

Get transaction history.

**Query Parameters:**

- `warehouse_id`, `material_id`, `transaction_type`
- `start_date`, `end_date`: Date range filter
- `skip`, `limit`: Pagination

#### `GET /api/v1/inventory/transactions/{transaction_id}`

Get specific transaction details.

### Stock Reservations

#### `POST /api/v1/inventory/reservations`

Reserve stock for a project.

**Request Body:**

```json
{
  "warehouse_id": 1,
  "material_id": 5,
  "project_id": 3,
  "quantity": 30.0,
  "required_by_date": "2025-12-31T00:00:00",
  "priority": "High",
  "remarks": "Critical project requirement"
}
```

#### `GET /api/v1/inventory/reservations`

Get all reservations with filters.

#### `POST /api/v1/inventory/reservations/{reservation_id}/issue`

Issue stock against a reservation.

**Request Body:**

```json
{
  "quantity_to_issue": 15.0,
  "remarks": "Partial fulfillment"
}
```

#### `POST /api/v1/inventory/reservations/{reservation_id}/cancel`

Cancel a reservation.

**Query Parameter:** `remarks` (reason for cancellation)

### Alerts

#### `GET /api/v1/inventory/alerts`

Get stock alerts.

**Query Parameters:**

- `alert_type`: LOW_STOCK, OUT_OF_STOCK, OVERSTOCK
- `severity`: Low, Medium, High, Critical
- `warehouse_id`, `material_id`
- `is_resolved`: Boolean filter

#### `PATCH /api/v1/inventory/alerts/{alert_id}/resolve`

Manually resolve an alert.

**Query Parameter:** `resolved_by` (user name)

### Analytics

#### `GET /api/v1/inventory/analytics/summary`

Get overall inventory summary.

**Response:**

```json
{
  "total_warehouses": 5,
  "total_materials_tracked": 150,
  "total_stock_value": 25000000.00,
  "total_reserved_value": 5000000.00,
  "low_stock_items": 12,
  "out_of_stock_items": 3,
  "overstock_items": 5,
  "active_reservations": 25,
  "pending_alerts": 20
}
```

#### `GET /api/v1/inventory/analytics/warehouse/{warehouse_id}`

Get warehouse-specific inventory summary.

#### `GET /api/v1/inventory/analytics/material/{material_id}`

Get material distribution across warehouses.

## Usage Examples

### Python Example: Stock Operations

```python
import requests

BASE_URL = "http://localhost:8000/api/v1/inventory"

# Add stock to warehouse
response = requests.post(f"{BASE_URL}/operations/stock-in", json={
    "warehouse_id": 1,
    "material_id": 5,
    "quantity": 100.0,
    "unit_cost": 50000.0,
    "vendor_id": 2,
    "reference_type": "PO",
    "reference_id": "PO-123",
    "remarks": "New shipment"
})
print(response.json())

# Issue stock to project
response = requests.post(f"{BASE_URL}/operations/stock-out", json={
    "warehouse_id": 1,
    "material_id": 5,
    "quantity": 25.0,
    "project_id": 3,
    "remarks": "Project requirement"
})
print(response.json())

# Transfer between warehouses
response = requests.post(f"{BASE_URL}/operations/transfer", json={
    "material_id": 5,
    "source_warehouse_id": 1,
    "destination_warehouse_id": 2,
    "quantity": 20.0,
    "remarks": "Rebalancing"
})
print(response.json())
```

### Python Example: Reservations

```python
# Reserve stock for project
response = requests.post(f"{BASE_URL}/reservations", json={
    "warehouse_id": 1,
    "material_id": 5,
    "project_id": 3,
    "quantity": 30.0,
    "priority": "High"
})
reservation = response.json()
print(f"Reservation created: {reservation['id']}")

# Issue reserved stock
response = requests.post(
    f"{BASE_URL}/reservations/{reservation['id']}/issue",
    json={"quantity_to_issue": 15.0}
)
print(response.json())
```

### Python Example: Analytics

```python
# Get inventory summary
response = requests.get(f"{BASE_URL}/analytics/summary")
summary = response.json()
print(f"Total Stock Value: ₹{summary['total_stock_value']:,.2f}")
print(f"Low Stock Items: {summary['low_stock_items']}")
print(f"Active Reservations: {summary['active_reservations']}")

# Get warehouse analytics
response = requests.get(f"{BASE_URL}/analytics/warehouse/1")
warehouse_summary = response.json()
print(f"Warehouse: {warehouse_summary['warehouse_name']}")
print(f"Materials: {warehouse_summary['total_materials']}")
print(f"Value: ₹{warehouse_summary['total_stock_value']:,.2f}")
```

## Business Logic

### Reorder Point Calculation

Reorder points are calculated based on:

- Lead time from vendor (days)
- Average daily consumption
- Safety stock buffer (typically 30 days)

Formula: `Reorder Point = (Lead Time × Daily Consumption) + Safety Stock`

### Alert Generation

Alerts are automatically created when:

- **Out of Stock**: `quantity_available <= 0`
- **Low Stock (Critical)**: `quantity_available <= min_stock_level`
- **Low Stock (Medium)**: `quantity_available <= reorder_point`
- **Overstock**: `quantity_available > max_stock_level`

Alerts auto-resolve when conditions improve.

### Reservation System

1. When stock is reserved:
   - `quantity_reserved` increases
   - Stock remains in warehouse (not moved)
   - Available for reservation = `quantity_available - quantity_reserved`

2. When reserved stock is issued:
   - `quantity_available` decreases
   - `quantity_reserved` decreases
   - `quantity_issued` increases on reservation
   - Transaction created as OUT type

3. Reservation statuses:
   - **Active**: Created, not fulfilled
   - **Partially_Fulfilled**: Some stock issued
   - **Fulfilled**: Completely issued
   - **Cancelled**: Reservation cancelled

### Cost Tracking

Stock valuation uses weighted average cost:

- Unit cost calculated from recent IN transactions
- Average of last 5 receipts
- Fallback to material's base unit_price

## Integration Points

### With Procurement System

- Stock IN operations triggered by PO deliveries
- Vendor information linked to transactions
- Cost tracking from purchase orders

### With Project Management

- Stock OUT operations for project material issues
- Project-specific reservations
- Material requirement tracking

### With Forecasting

- Current stock levels feed into demand forecasts
- Reorder alerts trigger procurement optimization
- Stock movement patterns analyzed

## Best Practices

1. **Always use transactions**: Never directly modify stock levels
2. **Reserve before issuing**: Use reservations for planned material usage
3. **Set reorder points**: Configure appropriate reorder points for each material
4. **Monitor alerts**: Check and resolve alerts regularly
5. **Document adjustments**: Always provide clear remarks for adjustments
6. **Regular audits**: Reconcile physical stock with system records

## Performance Considerations

- Indexes on `warehouse_id` and `material_id` for fast lookups
- Transaction history can grow large - consider archiving old records
- Stock queries optimized with proper joins
- Analytics queries use aggregations for performance

## Security

- All operations logged with user attribution
- Transaction history immutable (no updates/deletes)
- Role-based access control recommended for production
- Audit trail maintained for compliance

## Testing

Start the API server:

```bash
cd /Users/chiru/Projects/Nexus
uvicorn src.api.server:app --reload --port 8000
```

Access interactive API docs at: `http://localhost:8000/docs`

## Future Enhancements

- [ ] Batch processing for bulk operations
- [ ] Stock aging analysis
- [ ] Material expiry tracking
- [ ] Barcode/RFID integration
- [ ] Mobile app for warehouse operations
- [ ] Advanced analytics and ML predictions
- [ ] Integration with IoT sensors
- [ ] Blockchain for supply chain traceability

## Support

For issues or questions, contact the development team or refer to the main NEXUS documentation.

---

**Built for POWERGRID India | Smart India Hackathon 2024**
