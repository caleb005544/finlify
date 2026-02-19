'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Plus, X, ArrowUpRight, ArrowDownRight } from 'lucide-react'
import Link from 'next/link'
import { getWatchlist, removeFromWatchlist, WatchlistItem } from '@/lib/api/watchlist'
import { fetchStockQuote } from '@/lib/api/backend'

interface EnrichedWatchlistItem extends WatchlistItem {
    price?: number
    change?: number
    name?: string
}

export function Watchlist() {
    const [items, setItems] = useState<EnrichedWatchlistItem[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        loadWatchlist()
    }, [])

    const loadWatchlist = async () => {
        try {
            setLoading(true)
            const list = await getWatchlist()

            // Enrich with price data in parallel
            const enriched = await Promise.all(list.map(async (item) => {
                try {
                    const quote = await fetchStockQuote(item.ticker)
                    return { ...item, ...quote }
                } catch {
                    return { ...item, price: 0, change: 0, name: 'Unknown' }
                }
            }))

            setItems(enriched)
        } catch (error) {
            console.error("Failed to load watchlist", error)
        } finally {
            setLoading(false)
        }
    }

    const handleRemove = async (ticker: string) => {
        try {
            // Optimistic update
            setItems(items.filter(i => i.ticker !== ticker))
            await removeFromWatchlist(ticker)
        } catch (e) {
            console.error("Failed to remove", e)
            loadWatchlist() // Revert on error
        }
    }

    return (
        <Card className="h-full">
            <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Your Watchlist</CardTitle>
                <Link href="/">
                    <Button size="sm" variant="ghost"><Plus className="h-4 w-4 mr-2" /> Add</Button>
                </Link>
            </CardHeader>
            <CardContent>
                {loading ? (
                    <div className="space-y-4">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="h-16 w-full rounded-lg bg-muted/50 animate-pulse" />
                        ))}
                    </div>
                ) : items.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                        No stocks in watchlist.
                    </div>
                ) : (
                    <div className="space-y-1">
                        {items.map(item => (
                            <div key={item.ticker} className="flex items-center justify-between p-3 rounded-lg hover:bg-muted transition-colors group relative">
                                <Link href={`/ticker/${item.ticker}`} className="absolute inset-0 z-0" />

                                <div className="flex items-center space-x-3 z-10 pointer-events-none">
                                    <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold text-primary">
                                        {item.ticker[0]}
                                    </div>
                                    <div>
                                        <div className="font-bold">{item.ticker}</div>
                                        <div className="text-xs text-muted-foreground truncate max-w-[100px]">{item.name || item.ticker}</div>
                                    </div>
                                </div>

                                <div className="flex items-center space-x-4 z-10">
                                    <div className="text-right pointer-events-none">
                                        <div className="font-medium">${(item.price || 0).toFixed(2)}</div>
                                        <div className={`text-xs flex items-center justify-end ${(item.change || 0) >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                                            {(item.change || 0) >= 0 ? <ArrowUpRight className="h-3 w-3 mr-0.5" /> : <ArrowDownRight className="h-3 w-3 mr-0.5" />}
                                            {Math.abs(item.change || 0)}%
                                        </div>
                                    </div>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity z-20 hover:bg-destructive/10 hover:text-destructive"
                                        onClick={(e) => {
                                            e.stopPropagation() // Prevent navigation
                                            handleRemove(item.ticker)
                                        }}
                                    >
                                        <X className="h-3 w-3" />
                                    </Button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    )
}
