import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CheckCircle2, AlertTriangle, TrendingDown, TrendingUp, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'

interface RecommendationProps {
    action: 'BUY' | 'SELL' | 'HOLD' | 'STRONG_BUY' | 'STRONG_SELL'
    rating: number // 1-5
    signals: string[]
}

export function RecommendationCard({ action, rating, signals }: RecommendationProps) {
    const getActionColor = (action: string) => {
        switch (action) {
            case 'STRONG_BUY': return 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20'
            case 'BUY': return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20'
            case 'SELL': return 'text-red-400 bg-red-400/10 border-red-400/20'
            case 'STRONG_SELL': return 'text-red-500 bg-red-500/10 border-red-500/20'
            default: return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20'
        }
    }

    const getIcon = (action: string) => {
        if (action.includes('BUY')) return <TrendingUp className="h-6 w-6" />
        if (action.includes('SELL')) return <TrendingDown className="h-6 w-6" />
        return <Minus className="h-6 w-6" />
    }

    return (
        <Card className="h-full">
            <CardHeader>
                <CardTitle className="text-lg font-medium">AI Recommendation</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
                <div className={cn("flex items-center justify-between p-4 rounded-lg border", getActionColor(action))}>
                    <div className="flex items-center space-x-3">
                        {getIcon(action)}
                        <span className="text-2xl font-bold tracking-tight">{action.replace('_', ' ')}</span>
                    </div>
                    <div className="flex space-x-1">
                        {[1, 2, 3, 4, 5].map((star) => (
                            <div
                                key={star}
                                className={cn(
                                    "h-2 w-6 rounded-full transition-all",
                                    star <= rating ? "bg-current" : "bg-muted/30"
                                )}
                            />
                        ))}
                    </div>
                </div>

                <div className="space-y-3">
                    <h4 className="text-sm font-semibold text-muted-foreground">Why this recommendation?</h4>
                    <ul className="space-y-2">
                        {signals.map((signal, idx) => (
                            <li key={idx} className="flex items-start text-sm">
                                <CheckCircle2 className="h-4 w-4 mr-2 text-primary shrink-0 mt-0.5" />
                                <span>{signal}</span>
                            </li>
                        ))}
                    </ul>
                </div>

                <div className="text-xs text-muted-foreground border-t pt-4">
                    <div className="flex items-center mb-1">
                        <AlertTriangle className="h-3 w-3 mr-1" />
                        <span>Disclaimer</span>
                    </div>
                    <p>AI-generated score based on technical analysis and mock data. Not financial advice.</p>
                </div>
            </CardContent>
        </Card>
    )
}
