const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchStockQuote(ticker: string) {
    const res = await fetch(`${API_URL}/api/quotes?ticker=${ticker}`);
    if (!res.ok) throw new Error('Failed to fetch quote');
    return res.json();
}

export async function fetchStockHistory(ticker: string, range: string = '1y') {
    const res = await fetch(`${API_URL}/api/history?ticker=${ticker}&range=${range}`);
    if (!res.ok) throw new Error('Failed to fetch history');
    return res.json();
}

export async function fetchScore(ticker: string, profile: any) {
    const res = await fetch(`${API_URL}/score`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker, profile }),
    });
    if (!res.ok) throw new Error('Failed to fetch score');
    return res.json();
}

export async function fetchForecast(ticker: string, days: number = 30) {
    const res = await fetch(`${API_URL}/forecast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker, days }),
    });
    if (!res.ok) throw new Error('Failed to fetch forecast');
    return res.json();
}
