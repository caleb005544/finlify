'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, Line } from 'recharts'

interface StockChartProps {
  data: Array<{ date: string; value: number }>
  forecast?: Array<{ date: string; value: number }>
  showForecast?: boolean
  historyLabel?: string
  forecastLabel?: string
  ticker: string
  historyColor?: string
  forecastColor?: string
}

function formatDateLabel(dateString: string) {
  const date = new Date(dateString)
  if (Number.isNaN(date.getTime())) return dateString
  return `${date.getMonth() + 1}/${date.getDate()}`
}

export function StockChart({
  data,
  forecast = [],
  showForecast = true,
  historyLabel = '1Y',
  forecastLabel = '30D',
  ticker,
  historyColor = '#16a34a',
  forecastColor = '#f59e0b',
}: StockChartProps) {
  const mergedData: Array<{ date: string; value?: number; forecastValue?: number }> = [
    ...data.map((p) => ({ date: p.date, value: p.value })),
  ]

  if (showForecast) {
    for (const f of forecast) {
      mergedData.push({
        date: f.date,
        value: undefined,
        forecastValue: f.value,
      })
    }
  }

  return (
    <Card className="w-full h-[460px] shadow-sm">
      <CardHeader className="pb-3">
        <CardTitle className="text-xl font-semibold text-primary">
          {ticker} History ({historyLabel}) {showForecast ? `+ Forecast (${forecastLabel})` : ''}
        </CardTitle>
      </CardHeader>
      <CardContent className="h-[380px] w-full p-0">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={mergedData} role="img" aria-label={`Stock price chart for ${ticker}`} margin={{ top: 8, right: 14, left: 6, bottom: 8 }}>
            <defs>
              <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={historyColor} stopOpacity={0.22} />
                <stop offset="95%" stopColor={historyColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDateLabel}
              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              minTickGap={24}
            />
            <YAxis
              domain={['auto', 'auto']}
              orientation="right"
              tickFormatter={(val) => `$${Number(val).toFixed(0)}`}
              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
              axisLine={false}
              tickLine={false}
              width={65}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--popover))',
                borderRadius: '8px',
                border: '1px solid hsl(var(--border))',
                color: 'hsl(var(--foreground))',
              }}
              labelFormatter={(label) => formatDateLabel(String(label))}
              formatter={(value, name) => [
                typeof value === 'number' ? `$${value.toFixed(2)}` : '-',
                String(name) === 'forecastValue' ? 'Forecast' : 'Historical',
              ]}
            />
            <Area type="monotone" dataKey="value" stroke={historyColor} fillOpacity={1} fill="url(#colorValue)" strokeWidth={2} dot={false} connectNulls />
            {showForecast && (
              <Line type="monotone" dataKey="forecastValue" stroke={forecastColor} strokeWidth={2} dot={false} connectNulls />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
