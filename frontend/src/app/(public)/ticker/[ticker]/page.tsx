import { StockChart } from '@/components/features/stock-chart'
import { RecommendationCard } from '@/components/features/recommendation-card'
import { ForecastPanel } from '@/components/features/forecast-panel'
import { fetchStockQuote, fetchStockHistory, fetchScore, fetchForecast } from '@/lib/api/backend'
import { notFound } from 'next/navigation'
import { ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'

// Default profile for public view
const PUBLIC_PROFILE = {
    risk_level: "Medium",
    horizon: "Medium",
    sector_preference: "Tech"
}

interface StatCardProps {
    label: string
    value: string
}

function StatCard({ label, value }: StatCardProps) {
    return (
        <div className="p-4 rounded-lg bg-muted/50">
            <div className="text-sm text-muted-foreground">{label}</div>
            <div className="text-lg font-bold">{value}</div>
        </div>
    )
}

export default async function TickerPage({ params }: { params: Promise<{ ticker: string }> }) {
    const { ticker } = await params

    // Parallel fetch to Backend Logic
    const [quote, history, score, forecast] = await Promise.all([
        fetchStockQuote(ticker).catch(() => null),
        fetchStockHistory(ticker).catch(() => []),
        fetchScore(ticker, PUBLIC_PROFILE).catch(() => null),
        fetchForecast(ticker).catch(() => [])
    ])

    if (!quote) {
        notFound()
    }

    return (
        <div className="container mx-auto px-4 py-8 space-y-8">
            {/* Header / Back */}
            <div className="flex items-center space-x-4">
                <Link href="/">
                    <Button variant="ghost" size="icon">
                        <ArrowLeft className="h-4 w-4" />
                    </Button>
                </Link>
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">{quote.ticker}</h1>
                    <p className="text-muted-foreground text-lg">{quote.name}</p>
                </div>
                <div className="ml-auto text-right">
                    <div className="text-3xl font-bold">${quote.price.toFixed(2)}</div>
                    <div className={`text-sm font-medium ${quote.change >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                        {quote.change > 0 ? '+' : ''}{quote.change} ({quote.change_percent}%)
                    </div>
                </div>
            </div>

            {/* Main Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left: Chart & Stats */}
                <div className="lg:col-span-2 space-y-8">
                    <StockChart data={history} ticker={quote.ticker} />

                    {/* Key Stats Grid (Mocked for v1 as per proxy) */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <StatCard label="Market Cap" value="-" />
                        <StatCard label="P/E Ratio" value="-" />
                        <StatCard label="Volume" value="-" />
                        <StatCard label="Yield" value="-" />
                    </div>
                </div>

                {/* Right: Recommendation & Forecast */}
                <div className="space-y-8">
                    {score && (
                        <RecommendationCard
                            action={score.action}
                            rating={score.rating}
                            signals={score.reasons}
                        />
                    )}
                    <ForecastPanel data={forecast} />
                </div>
            </div>
        </div>
    )
}
