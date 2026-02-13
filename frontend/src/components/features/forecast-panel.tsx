import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface ForecastProps {
    data: Array<{ date: string; value: number; confidenceLow: number; confidenceHigh: number }>
}

export function ForecastPanel({ data }: ForecastProps) {
    const getForecastFor = (days: number) => {
        // Ensure we don't go out of bounds
        const index = Math.min(days, data.length - 1)
        if (index < 0) return null
        return data[index]
    }

    const day30 = getForecastFor(30)
    if (!day30) return null

    // Calculate percentage change from start (mock logic)
    // Assuming the first item in 'data' is tomorrow's forecast
    const startValue = data[0]?.value || day30.value
    const change = ((day30.value - startValue) / startValue) * 100

    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">30-Day Price Target</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="text-2xl font-bold">${day30.value.toFixed(2)}</div>
                <p className="text-xs text-muted-foreground mt-1">
                    Range: ${day30.confidenceLow.toFixed(2)} - ${day30.confidenceHigh.toFixed(2)}
                </p>

                <div className="mt-4 pt-4 border-t grid grid-cols-2 gap-4 text-center">
                    <div className="space-y-1">
                        <span className="block text-xs text-muted-foreground uppercase tracking-wider">Trend</span>
                        <p className={cn("font-medium", change >= 0 ? "text-emerald-500" : "text-rose-500")}>
                            {change >= 0 ? '+' : ''}{change.toFixed(2)}%
                        </p>
                    </div>
                    <div className="space-y-1">
                        <span className="block text-xs text-muted-foreground uppercase tracking-wider">Confidence</span>
                        <p className="font-medium text-blue-500">High</p>
                    </div>
                </div>
            </CardContent>
        </Card >
    )
}
