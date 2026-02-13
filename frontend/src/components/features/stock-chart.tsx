'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'

interface StockChartProps {
    data: Array<{ date: string; value: number }>
    ticker: string
    color?: string
}

export function StockChart({ data, ticker, color = "#10b981" }: StockChartProps) {
    return (
        <Card className="w-full h-[400px]">
            <CardHeader>
                <CardTitle className="text-lg font-medium">Price History (1Y)</CardTitle>
            </CardHeader>
            <CardContent className="h-[320px] w-full p-0">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data} role="img" aria-label={`Stock price chart for ${ticker}`}>
                        <defs>
                            <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                                <stop offset="95%" stopColor={color} stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                        <XAxis
                            dataKey="date"
                            hide={true} // Simplify for demo
                        />
                        <YAxis
                            domain={['auto', 'auto']}
                            orientation="right"
                            tickFormatter={(val) => `$${val}`}
                            tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                            axisLine={false}
                            tickLine={false}
                        />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: 'hsl(var(--popover))',
                                borderRadius: '8px',
                                border: '1px solid hsl(var(--border))',
                                color: 'hsl(var(--foreground))'
                            }}
                            formatter={(value: number | undefined) => [value !== undefined ? `$${value}` : '', 'Price']}
                        />
                        <Area
                            type="monotone"
                            dataKey="value"
                            stroke={color}
                            fillOpacity={1}
                            fill="url(#colorValue)"
                            strokeWidth={2}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    )
}
