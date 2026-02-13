# API Contract

Base URL: `http://localhost:8000`

## Stock Data

### `GET /api/quotes`
Returns current price and change for a ticker.

**Query Params**:
- `ticker`: string (e.g., "AAPL")

**Response**:
```json
{
  "ticker": "AAPL",
  "name": "Apple Inc.",
  "price": 150.25,
  "change": 1.2,
  "change_percent": 0.8
}
```

### `GET /api/history`
Returns historical price data.

**Query Params**:
- `ticker`: string
- `range`: "1m" | "3m" | "6m" | "1y" | "all"

**Response**:
```json
[
  {"date": "2023-01-01", "value": 140.50},
  {"date": "2023-01-02", "value": 141.20}
]
```

## Logic & Analysis

### `POST /score`
Returns a deterministic score based on user profile and stock data.

**Request**:
```json
{
  "ticker": "AAPL",
  "profile": {
    "risk_level": "Medium",
    "horizon": "Long",
    "sector_preference": "Tech"
  }
}
```

**Response**:
```json
{
  "total_score": 75,
  "rating": 4, // 1-5
  "action": "BUY",
  "reasons": [
    "Strong momentum matches your sector preference",
    "Volatility is within Medium risk tolerance"
  ],
  "breakdown": {
    "momentum": 80,
    "volatility": 70,
    "value": 60
  }
}
```

### `POST /forecast`
Returns projected price data (mocked).

**Request**:
```json
{
  "ticker": "AAPL",
  "days": 30
}
```

**Response**:
```json
[
  {
    "date": "2023-06-01",
    "value": 155.00,
    "confidence_low": 150.00,
    "confidence_high": 160.00
  }
]
```
