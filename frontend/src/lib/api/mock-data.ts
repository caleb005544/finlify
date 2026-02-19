export interface StockData {
    ticker: string
    name: string
    price: number
    change: number
    changePercent: number
    history: Array<{ date: string; value: number }>
    forecast: Array<{ date: string; value: number; confidenceLow: number; confidenceHigh: number }>
    recommendation: {
        action: 'BUY' | 'SELL' | 'HOLD' | 'STRONG_BUY' | 'STRONG_SELL'
        rating: number // 1-5
        signals: string[]
    }
}

export function getMockStockData(ticker: string): StockData {
    // Deterministic-ish random based on ticker char codes
    const seed = ticker.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)

    const basePrice = (seed % 500) + 50
    const volatility = 0.02
    const historyDays = 365

    const history = []
    let currentPrice = basePrice * 0.8 // Start a bit lower

    const now = new Date()

    // Generate history
    for (let i = historyDays; i >= 0; i--) {
        const date = new Date(now)
        date.setDate(date.getDate() - i)

        // Random walk
        const change = (Math.random() - 0.48) * volatility * currentPrice // slight upward drift
        currentPrice += change

        history.push({
            date: date.toISOString().split('T')[0],
            value: parseFloat(currentPrice.toFixed(2))
        })
    }

    const lastPrice = history[history.length - 1].value
    const prevPrice = history[history.length - 2].value
    const change = lastPrice - prevPrice

    // Generate forecast
    const forecast = []
    let forecastPrice = lastPrice
    const forecastDays = 30

    for (let i = 1; i <= forecastDays; i++) {
        const date = new Date(now)
        date.setDate(date.getDate() + i)

        const change = (Math.random() - 0.45) * volatility * forecastPrice
        forecastPrice += change

        const uncertainty = i * (volatility * 10) // Uncertainty grows with time

        forecast.push({
            date: date.toISOString().split('T')[0],
            value: parseFloat(forecastPrice.toFixed(2)),
            confidenceLow: parseFloat((forecastPrice - uncertainty).toFixed(2)),
            confidenceHigh: parseFloat((forecastPrice + uncertainty).toFixed(2))
        })
    }

    // Determine recommendation
    let action: 'BUY' | 'SELL' | 'HOLD' | 'STRONG_BUY' | 'STRONG_SELL' = 'HOLD'
    let rating = 3

    if (forecastPrice > lastPrice * 1.15) {
        action = 'STRONG_BUY'
        rating = 5
    } else if (forecastPrice > lastPrice * 1.05) {
        action = 'BUY'
        rating = 4
    } else if (forecastPrice < lastPrice * 0.95) {
        action = 'SELL'
        rating = 2
    }

    return {
        ticker,
        name: `${ticker} Inc.`, // Simplified Mock
        price: lastPrice,
        change: parseFloat(change.toFixed(2)),
        changePercent: parseFloat(((change / prevPrice) * 100).toFixed(2)),
        history,
        forecast,
        recommendation: {
            action,
            rating,
            signals: [
                'Positive momentum in last 30 days',
                'Sector performance is strong',
                'Volatility index remains low'
            ]
        }
    }
}
