const CLIENT_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const SERVER_API_URL = process.env.INTERNAL_API_URL || CLIENT_API_URL;

function resolveApiUrl() {
    return typeof window === 'undefined' ? SERVER_API_URL : CLIENT_API_URL;
}

export async function fetchStockQuote(ticker: string) {
    const res = await fetch(`${resolveApiUrl()}/api/quotes?ticker=${ticker}`);
    if (!res.ok) throw new Error('Failed to fetch quote');
    return res.json();
}

export async function fetchStockHistory(ticker: string, range: string = '1y') {
    const res = await fetch(`${resolveApiUrl()}/api/history?ticker=${ticker}&range=${range}`);
    if (!res.ok) throw new Error('Failed to fetch history');
    return res.json();
}

export async function fetchScore(ticker: string, profile: any) {
    const res = await fetch(`${resolveApiUrl()}/score`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker, profile }),
    });
    if (!res.ok) throw new Error('Failed to fetch score');
    return res.json();
}

export async function fetchForecast(ticker: string, days: number = 30) {
    const res = await fetch(`${resolveApiUrl()}/forecast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker, days }),
    });
    if (!res.ok) throw new Error('Failed to fetch forecast');
    return res.json();
}
