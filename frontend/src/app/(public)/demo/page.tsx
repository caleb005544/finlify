import Link from 'next/link'
import { ArrowRight, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { StockSearch } from '@/components/features/stock-search'

const DEMO_TICKERS = [
    { ticker: 'AAPL', note: 'Large-cap quality profile' },
    { ticker: 'NVDA', note: 'High-growth momentum profile' },
    { ticker: 'MSFT', note: 'Balanced tech profile' },
    { ticker: 'TSLA', note: 'High-volatility profile' },
]

export default function DemoPage() {
    return (
        <div className="container mx-auto px-4 py-12 space-y-10">
            <div className="space-y-4">
                <div className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs text-muted-foreground">
                    <Sparkles className="h-3.5 w-3.5 text-primary" />
                    Public Demo
                </div>
                <h1 className="text-4xl font-bold tracking-tight">Try Finlify Demo</h1>
                <p className="text-muted-foreground max-w-2xl">
                    Search a stock or start from curated tickers. You will see quote, chart,
                    recommendation, and forecast in one page.
                </p>
            </div>

            <div className="max-w-xl">
                <StockSearch placeholder="Type a ticker (e.g. AAPL, NVDA, MSFT)..." />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {DEMO_TICKERS.map((item) => (
                    <Link
                        key={item.ticker}
                        href={`/ticker/${item.ticker}`}
                        className="rounded-xl border bg-card p-5 hover:border-primary/60 transition-colors"
                    >
                        <div className="flex items-center justify-between">
                            <div>
                                <div className="text-2xl font-bold">{item.ticker}</div>
                                <p className="text-sm text-muted-foreground">{item.note}</p>
                            </div>
                            <ArrowRight className="h-5 w-5 text-muted-foreground" />
                        </div>
                    </Link>
                ))}
            </div>

            <div className="rounded-xl border p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div>
                    <h2 className="text-lg font-semibold">Need full features?</h2>
                    <p className="text-sm text-muted-foreground">
                        Sign in to save watchlists and profile-based assumptions.
                    </p>
                </div>
                <div className="flex gap-2">
                    <Link href="/login">
                        <Button variant="outline">Sign In</Button>
                    </Link>
                    <Link href="/signup">
                        <Button>Get Started</Button>
                    </Link>
                </div>
            </div>
        </div>
    )
}
