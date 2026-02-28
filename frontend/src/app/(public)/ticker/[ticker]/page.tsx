import { fetchForecast, fetchScore, fetchStockHistory, fetchStockQuote } from '@/lib/api/backend'
import { notFound } from 'next/navigation'
import { TickerDashboard } from '@/components/features/ticker-dashboard'
import Link from 'next/link'

const PUBLIC_PROFILE = {
  risk_level: 'Medium',
  horizon: 'Medium',
  sector_preference: 'Tech',
}

const TICKER_PATTERN = /^[A-Za-z][A-Za-z0-9.-]{0,9}$/

function TickerDataUnavailable({ ticker }: { ticker: string }) {
  return (
    <div className="container mx-auto px-4 py-16">
      <div className="mx-auto max-w-2xl rounded-xl border bg-card p-8 text-center shadow-sm">
        <h1 className="text-2xl font-bold tracking-tight">Unable to load {ticker}</h1>
        <p className="mt-3 text-sm text-muted-foreground">
          The ticker route exists, but quote data is currently unavailable. This usually means the backend API is not
          running or market-data credentials are missing/invalid.
        </p>
        <div className="mt-6 flex items-center justify-center gap-3">
          <Link href="/demo" className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent">
            Back to Demo
          </Link>
          <Link href="/" className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent">
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  )
}

export default async function TickerPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params
  const normalizedTicker = ticker.trim().toUpperCase()

  if (!TICKER_PATTERN.test(normalizedTicker)) {
    notFound()
  }

  const quote = await fetchStockQuote(normalizedTicker).catch(() => null)

  if (!quote) {
    return <TickerDataUnavailable ticker={normalizedTicker} />
  }

  const [history, score, forecast] = await Promise.all([
    fetchStockHistory(normalizedTicker, '1y').catch(() => []),
    fetchScore(normalizedTicker, PUBLIC_PROFILE).catch(() => null),
    fetchForecast(normalizedTicker, 30).catch(() => []),
  ])

  return (
    <TickerDashboard
      ticker={normalizedTicker}
      quote={quote}
      initialHistory={history}
      initialForecast={forecast}
      score={score}
      initialHistoryRange="1y"
      initialForecastPeriod="1m"
    />
  )
}
