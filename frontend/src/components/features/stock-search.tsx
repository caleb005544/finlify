'use client'

import { useEffect, useRef, useState } from 'react'
import { Search, Loader2 } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { fetchStockSearch, StockSearchResult } from '@/lib/api/backend'

function useDebounce<T>(value: T, delay: number): T {
    const [debounced, setDebounced] = useState(value)
    useEffect(() => {
        const timer = setTimeout(() => setDebounced(value), delay)
        return () => clearTimeout(timer)
    }, [value, delay])
    return debounced
}

export function StockSearch({ placeholder = 'Search for a stock...' }: { placeholder?: string }) {
    const [query, setQuery] = useState('')
    const [suggestions, setSuggestions] = useState<StockSearchResult[]>([])
    const [loading, setLoading] = useState(false)
    const [open, setOpen] = useState(false)
    const containerRef = useRef<HTMLDivElement>(null)
    const router = useRouter()
    const debouncedQuery = useDebounce(query, 300)

    // Clear suggestions when query is empty
    useEffect(() => {
        if (!debouncedQuery.trim()) {
            setSuggestions([])
            setOpen(false)
        }
    }, [debouncedQuery])

    // Fetch suggestions whenever the debounced query changes
    useEffect(() => {
        if (!debouncedQuery.trim()) return

        let cancelled = false
        setLoading(true)
        fetchStockSearch(debouncedQuery)
            .then((results) => {
                if (!cancelled) {
                    setSuggestions(results)
                    setOpen(results.length > 0)
                }
            })
            .catch(() => {
                if (!cancelled) setSuggestions([])
            })
            .finally(() => {
                if (!cancelled) setLoading(false)
            })

        return () => {
            cancelled = true
        }
    }, [debouncedQuery])

    // Close dropdown on outside click
    useEffect(() => {
        function onClickOutside(e: MouseEvent) {
            if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
                setOpen(false)
            }
        }
        document.addEventListener('mousedown', onClickOutside)
        return () => document.removeEventListener('mousedown', onClickOutside)
    }, [])

    const navigate = (ticker: string) => {
        setOpen(false)
        setQuery(ticker)
        router.push(`/ticker/${ticker.toUpperCase()}`)
    }

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault()
        if (query.trim()) navigate(query.trim())
    }

    return (
        <div ref={containerRef} className="relative w-full max-w-lg mx-auto">
            <form onSubmit={handleSearch} className="relative flex items-center">
                <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-muted-foreground">
                    {loading ? (
                        <Loader2 className="h-5 w-5 animate-spin" />
                    ) : (
                        <Search className="h-5 w-5" />
                    )}
                </div>
                <input
                    type="text"
                    className="flex h-12 w-full rounded-full border border-input bg-background/50 backdrop-blur-sm px-10 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 shadow-lg transition-shadow hover:shadow-xl"
                    placeholder={placeholder}
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onFocus={() => suggestions.length > 0 && setOpen(true)}
                    autoComplete="off"
                />
                <Button
                    type="submit"
                    className="absolute right-1 top-1 rounded-full px-6 h-10"
                    disabled={!query.trim()}
                >
                    Analyze
                </Button>
            </form>

            {/* Autocomplete Suggestions */}
            {open && (
                <div className="absolute top-full mt-2 w-full rounded-md border border-border bg-background shadow-lg overflow-hidden z-10 animate-in fade-in slide-in-from-top-2">
                    {suggestions.length === 0 && !loading ? (
                        <div className="px-4 py-3 text-sm text-muted-foreground">No results found</div>
                    ) : (
                        suggestions.map((stock) => (
                            <div
                                key={stock.ticker}
                                className="flex items-center justify-between px-4 py-3 hover:bg-muted cursor-pointer transition-colors"
                                onMouseDown={(e) => {
                                    e.preventDefault() // prevent blur before click fires
                                    navigate(stock.ticker)
                                }}
                            >
                                <div className="flex items-center space-x-2">
                                    <span className="font-bold text-primary">{stock.ticker}</span>
                                    <span className="text-sm text-muted-foreground truncate">{stock.name}</span>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    )
}
