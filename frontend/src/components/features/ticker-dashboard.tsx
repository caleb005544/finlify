'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, Minus, Plus } from 'lucide-react'

import { StockChart } from '@/components/features/stock-chart'
import { RecommendationCard } from '@/components/features/recommendation-card'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  fetchForecast,
  fetchStockHistory,
  ForecastPoint,
  HistoryPoint,
  StockQuote,
} from '@/lib/api/backend'

type ScoreData = {
  action?: 'BUY' | 'SELL' | 'HOLD' | 'STRONG_BUY' | 'STRONG_SELL'
  rating?: number
  reasons?: string[]
}

type HistoryRange = '3y' | '1y' | '12m' | '6m' | '3m' | '1m' | '1w' | '3d' | '1d'
type ForecastPeriod = '1m' | '3m' | '6m'

const HISTORY_RANGES: HistoryRange[] = ['3y', '1y', '12m', '6m', '3m', '1m', '1w', '3d', '1d']
const FORECAST_PERIODS: ForecastPeriod[] = ['1m', '3m', '6m']

const FORECAST_DAYS: Record<ForecastPeriod, number> = {
  '1m': 30,
  '3m': 90,
  '6m': 180,
}

interface TickerDashboardProps {
  ticker: string
  quote: StockQuote
  initialHistory: HistoryPoint[]
  initialForecast: ForecastPoint[]
  score: ScoreData | null
  initialHistoryRange?: HistoryRange
  initialForecastPeriod?: ForecastPeriod
}

function formatCurrency(value: number) {
  if (!Number.isFinite(value)) return '-'
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatCompact(value: number) {
  if (!Number.isFinite(value)) return '-'
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 2,
  }).format(value)
}

function formatNumber(value: number, digits: number = 2) {
  if (!Number.isFinite(value)) return '-'
  return value.toFixed(digits)
}

function periodLabel(period: ForecastPeriod) {
  if (period === '1m') return '30d/1m'
  return period
}

export function TickerDashboard({
  ticker,
  quote,
  initialHistory,
  initialForecast,
  score,
  initialHistoryRange = '1y',
  initialForecastPeriod = '1m',
}: TickerDashboardProps) {
  const [historyRange, setHistoryRange] = useState<HistoryRange>(initialHistoryRange)
  const [forecastPeriod, setForecastPeriod] = useState<ForecastPeriod>(initialForecastPeriod)
  const [showForecast, setShowForecast] = useState(true)

  const [history, setHistory] = useState<HistoryPoint[]>(initialHistory)
  const [forecast, setForecast] = useState<ForecastPoint[]>(initialForecast)

  const [historyLoading, setHistoryLoading] = useState(false)
  const [forecastLoading, setForecastLoading] = useState(false)

  const updateHistoryRange = (next: HistoryRange) => {
    setHistoryLoading(true)
    setHistoryRange(next)
  }

  const updateForecastPeriod = (next: ForecastPeriod) => {
    setForecastLoading(true)
    setForecastPeriod(next)
  }

  useEffect(() => {
    let cancelled = false
    fetchStockHistory(ticker, historyRange)
      .then((rows) => {
        if (!cancelled) setHistory(rows)
      })
      .catch(() => {
        if (!cancelled) setHistory([])
      })
      .finally(() => {
        if (!cancelled) setHistoryLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [ticker, historyRange])

  useEffect(() => {
    let cancelled = false
    fetchForecast(ticker, FORECAST_DAYS[forecastPeriod])
      .then((rows) => {
        if (!cancelled) setForecast(rows)
      })
      .catch(() => {
        if (!cancelled) setForecast([])
      })
      .finally(() => {
        if (!cancelled) setForecastLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [ticker, forecastPeriod])

  const safePrice = Number(quote.price ?? 0)
  const safeChange = Number(quote.change ?? 0)
  const safeChangePct = Number(quote.change_percent ?? 0)

  const historyIdx = HISTORY_RANGES.indexOf(historyRange)
  const forecastIdx = FORECAST_PERIODS.indexOf(forecastPeriod)

  const forecastTarget = useMemo(() => {
    if (!showForecast || forecast.length === 0) return null
    return forecast[forecast.length - 1]
  }, [forecast, showForecast])

  const action = score?.action ?? 'HOLD'
  const reasons = score?.reasons ?? []

  return (
    <div className="container mx-auto px-4 py-10 space-y-7">
      <div className="flex items-start gap-4 rounded-xl border border-border bg-card px-5 py-4 shadow-sm">
        <Link href="/demo">
          <Button variant="outline" size="icon" aria-label="Go back" className="rounded-full">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>

        <div>
          <h1 className="text-4xl font-bold tracking-tight text-primary">{quote.ticker}</h1>
          <p className="text-muted-foreground text-lg">{quote.name}</p>
          <p className="mt-1 text-xs text-muted-foreground">As of {quote.date || new Date().toISOString().slice(0, 10)}</p>
        </div>

        <div className="ml-auto text-right pt-1">
          <div className="text-5xl font-bold leading-none">{formatCurrency(safePrice)}</div>
          <div className={safeChange >= 0 ? 'text-emerald-600 font-medium' : 'text-rose-600 font-medium'}>
            {safeChange > 0 ? '+' : ''}
            {safeChange.toFixed(2)} ({safeChangePct.toFixed(2)}%)
          </div>
        </div>
      </div>

      <Card className="shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-primary">Forecast Dashboard Controls</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="flex flex-wrap gap-2 items-center">
            <span className="mr-2 rounded-full bg-secondary px-3 py-1 text-xs font-semibold uppercase tracking-wide text-primary">History</span>
            <Button
              variant="outline"
              size="icon"
              className="rounded-full"
              onClick={() => historyIdx > 0 && updateHistoryRange(HISTORY_RANGES[historyIdx - 1])}
              disabled={historyIdx <= 0}
            >
              <Minus className="h-4 w-4" />
            </Button>
            {HISTORY_RANGES.map((item) => (
              <Button
                key={item}
                variant={item === historyRange ? 'default' : 'outline'}
                size="sm"
                className="rounded-full"
                onClick={() => updateHistoryRange(item)}
              >
                {item}
              </Button>
            ))}
            <Button
              variant="outline"
              size="icon"
              className="rounded-full"
              onClick={() => historyIdx < HISTORY_RANGES.length - 1 && updateHistoryRange(HISTORY_RANGES[historyIdx + 1])}
              disabled={historyIdx >= HISTORY_RANGES.length - 1}
            >
              <Plus className="h-4 w-4" />
            </Button>
            {historyLoading && <span className="ml-2 text-xs text-muted-foreground">Loading history...</span>}
          </div>

          <div className="flex flex-wrap gap-2 items-center">
            <span className="mr-2 rounded-full bg-secondary px-3 py-1 text-xs font-semibold uppercase tracking-wide text-primary">Forecast</span>
            <Button
              variant={showForecast ? 'default' : 'outline'}
              size="sm"
              className="rounded-full"
              onClick={() => setShowForecast((v) => !v)}
            >
              {showForecast ? 'On' : 'Off'}
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="rounded-full"
              onClick={() => forecastIdx > 0 && updateForecastPeriod(FORECAST_PERIODS[forecastIdx - 1])}
              disabled={forecastIdx <= 0}
            >
              <Minus className="h-4 w-4" />
            </Button>
            {FORECAST_PERIODS.map((item) => (
              <Button
                key={item}
                variant={item === forecastPeriod ? 'default' : 'outline'}
                size="sm"
                className="rounded-full"
                onClick={() => updateForecastPeriod(item)}
              >
                {item}
              </Button>
            ))}
            <Button
              variant="outline"
              size="icon"
              className="rounded-full"
              onClick={() => forecastIdx < FORECAST_PERIODS.length - 1 && updateForecastPeriod(FORECAST_PERIODS[forecastIdx + 1])}
              disabled={forecastIdx >= FORECAST_PERIODS.length - 1}
            >
              <Plus className="h-4 w-4" />
            </Button>
            {forecastLoading && <span className="ml-2 text-xs text-muted-foreground">Loading forecast...</span>}
          </div>
        </CardContent>
      </Card>

      <StockChart
        data={history}
        forecast={forecast}
        showForecast={showForecast}
        historyLabel={historyRange}
        forecastLabel={forecastPeriod}
        ticker={quote.ticker}
        historyColor="#16a34a"
        forecastColor="#f59e0b"
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-xl border bg-card p-4 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-muted-foreground">Market Cap</div>
          <div className="text-2xl font-bold text-emerald-600">{formatCompact(quote.market_cap)}</div>
        </div>
        <div className="rounded-xl border bg-card p-4 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-muted-foreground">P/E Ratio</div>
          <div className="text-2xl font-bold text-emerald-600">{formatNumber(quote.pe_ratio, 2)}</div>
        </div>
        <div className="rounded-xl border bg-card p-4 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-muted-foreground">EPS</div>
          <div className="text-2xl font-bold text-emerald-600">{formatNumber(quote.eps, 2)}</div>
        </div>
        <div className="rounded-xl border bg-card p-4 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-muted-foreground">Trade Volume</div>
          <div className="text-2xl font-bold text-emerald-600">{formatCompact(quote.volume)}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle className="text-primary">Forecast Summary Table</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="border-b text-muted-foreground">
                      <th className="text-left py-3 pr-4 font-semibold">Ticker</th>
                      <th className="text-left py-3 pr-4 font-semibold">Company</th>
                      <th className="text-left py-3 pr-4 font-semibold">Today</th>
                      <th className="text-left py-3 pr-4 font-semibold">Close</th>
                      <th className="text-left py-3 pr-4 font-semibold">Forecasted Period</th>
                      <th className="text-left py-3 pr-4 font-semibold">Forecasted Date</th>
                      <th className="text-left py-3 pr-4 font-semibold">Forecasted Price</th>
                      <th className="text-left py-3 pr-4 font-semibold">Recommendation</th>
                      <th className="text-left py-3 pr-4 font-semibold">Why</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b last:border-0 align-top">
                      <td className="py-3 pr-4 font-semibold">{quote.ticker}</td>
                      <td className="py-3 pr-4">{quote.name}</td>
                      <td className="py-3 pr-4">{quote.date || new Date().toISOString().slice(0, 10)}</td>
                      <td className="py-3 pr-4">{formatCurrency(safePrice)}</td>
                      <td className="py-3 pr-4">{periodLabel(forecastPeriod)}</td>
                      <td className="py-3 pr-4">{forecastTarget?.date ?? '-'}</td>
                      <td className="py-3 pr-4">{forecastTarget ? formatCurrency(forecastTarget.value) : '-'}</td>
                      <td className="py-3 pr-4">
                        <span className="rounded-full bg-secondary px-2.5 py-1 text-xs font-semibold text-primary">
                          {action.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="py-3 pr-4 max-w-xl leading-6">{reasons.length > 0 ? reasons.join(' | ') : '-'}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="lg:sticky lg:top-24 h-fit">
          <RecommendationCard action={action} rating={score?.rating ?? 3} signals={reasons} />
        </div>
      </div>
    </div>
  )
}
