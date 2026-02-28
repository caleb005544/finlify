const CLIENT_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const SERVER_API_URL = process.env.INTERNAL_API_URL || CLIENT_API_URL;

function resolveApiUrl() {
    return typeof window === 'undefined' ? SERVER_API_URL : CLIENT_API_URL;
}

export interface StockQuote {
    ticker: string
    name: string
    price: number
    change: number
    change_percent: number
    market_cap: number
    pe_ratio: number
    eps: number
    volume: number
    date: string
}

export interface HistoryPoint {
    date: string
    value: number
}

export interface ForecastPoint {
    date: string
    value: number
    confidenceLow: number
    confidenceHigh: number
}

interface ApiHistoryPoint {
    date?: string
    value?: number | string
}

interface ApiForecastPoint {
    date?: string
    value?: number | string
    confidenceLow?: number | string
    confidenceHigh?: number | string
    confidence_low?: number | string
    confidence_high?: number | string
}

interface ScoreProfile {
    risk_level?: string
    horizon?: string
    sector_preference?: string
}

export async function fetchStockQuote(ticker: string) {
    const res = await fetch(`${resolveApiUrl()}/api/quotes?ticker=${ticker}`);
    if (!res.ok) throw new Error('Failed to fetch quote');
    const data = await res.json();
    return {
        ...data,
        price: Number(data.price ?? 0),
        change: Number(data.change ?? 0),
        change_percent: Number(data.change_percent ?? 0),
        market_cap: Number(data.market_cap ?? 0),
        pe_ratio: Number(data.pe_ratio ?? 0),
        eps: Number(data.eps ?? 0),
        volume: Number(data.volume ?? 0),
    } as StockQuote;
}

export async function fetchStockHistory(ticker: string, range: string = '1y') {
    const res = await fetch(`${resolveApiUrl()}/api/history?ticker=${ticker}&range=${range}`);
    if (!res.ok) throw new Error('Failed to fetch history');
    const raw = await res.json();
    if (!Array.isArray(raw)) return [];
    return raw.map((point: ApiHistoryPoint) => ({
        date: point.date ?? '',
        value: Number(point.value ?? 0),
    })) as HistoryPoint[];
}

export async function fetchScore(ticker: string, profile: ScoreProfile) {
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
    const raw = await res.json();
    if (!Array.isArray(raw)) return [];
    return raw.map((point: ApiForecastPoint) => ({
        date: point.date ?? '',
        value: Number(point.value ?? 0),
        confidenceLow: Number(point.confidenceLow ?? point.confidence_low ?? point.value ?? 0),
        confidenceHigh: Number(point.confidenceHigh ?? point.confidence_high ?? point.value ?? 0),
    })) as ForecastPoint[];
}

export interface StockSearchResult {
    ticker: string
    name: string
}

export async function fetchStockSearch(query: string): Promise<StockSearchResult[]> {
    if (!query.trim()) return [];
    const res = await fetch(`${resolveApiUrl()}/api/search?q=${encodeURIComponent(query)}`);
    if (!res.ok) return []; // silently degrade on search failure
    const data = await res.json();
    if (!Array.isArray(data)) return [];
    return data as StockSearchResult[];
}
