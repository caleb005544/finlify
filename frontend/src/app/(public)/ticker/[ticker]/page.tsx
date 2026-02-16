import { fetchForecast, fetchScore, fetchStockHistory, fetchStockQuote } from '@/lib/api/backend'
import { notFound } from 'next/navigation'
import { TickerDashboard } from '@/components/features/ticker-dashboard'

const PUBLIC_PROFILE = {
  risk_level: 'Medium',
  horizon: 'Medium',
  sector_preference: 'Tech',
}

export default async function TickerPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params

  const [quote, history, score, forecast] = await Promise.all([
    fetchStockQuote(ticker).catch(() => null),
    fetchStockHistory(ticker, '1y').catch(() => []),
    fetchScore(ticker, PUBLIC_PROFILE).catch(() => null),
    fetchForecast(ticker, 30).catch(() => []),
  ])

  if (!quote) {
    notFound()
  }

  return (
    <TickerDashboard
      ticker={ticker}
      quote={quote}
      initialHistory={history}
      initialForecast={forecast}
      score={score}
      initialHistoryRange="1y"
      initialForecastPeriod="1m"
    />
  )
}
