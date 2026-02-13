'use client'

import { useState } from 'react'
import { Search } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'

const MOCK_STOCKS = [
    { ticker: 'AAPL', name: 'Apple Inc.' },
    { ticker: 'MSFT', name: 'Microsoft Corp.' },
    { ticker: 'NVDA', name: 'NVIDIA Corp.' },
    { ticker: 'TSLA', name: 'Tesla Inc.' },
    { ticker: 'GOOGL', name: 'Alphabet Inc.' },
]

export function StockSearch({ placeholder = "Search for a stock..." }: { placeholder?: string }) {
    const [query, setQuery] = useState('')
    const router = useRouter()
    const [suggestions, setSuggestions] = useState<typeof MOCK_STOCKS>([])

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault()
        if (query.trim()) {
            router.push(`/ticker/${query.toUpperCase()}`)
        }
    }

    const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value
        setQuery(val)
        if (val.length > 0) {
            setSuggestions(MOCK_STOCKS.filter(s =>
                s.ticker.includes(val.toUpperCase()) ||
                s.name.toLowerCase().includes(val.toLowerCase())
            ))
        } else {
            setSuggestions([])
        }
    }

    return (
        <div className="relative w-full max-w-lg mx-auto">
            <form onSubmit={handleSearch} className="relative flex items-center">
                <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-muted-foreground">
                    <Search className="h-5 w-5" />
                </div>
                <input
                    type="text"
                    className="flex h-12 w-full rounded-full border border-input bg-background/50 backdrop-blur-sm px-10 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 shadow-lg transition-shadow hover:shadow-xl"
                    placeholder={placeholder}
                    value={query}
                    onChange={handleInput}
                />
                <Button
                    type="submit"
                    className="absolute right-1 top-1 rounded-full px-6 h-10"
                    disabled={!query}
                >
                    Analyze
                </Button>
            </form>

            {/* Autocomplete Suggestions */}
            {suggestions.length > 0 && (
                <div className="absolute top-full mt-2 w-full rounded-md border border-border bg-background shadow-lg overflow-hidden z-10 animate-in fade-in slide-in-from-top-2">
                    {suggestions.map((stock) => (
                        <div
                            key={stock.ticker}
                            className="flex items-center justify-between px-4 py-3 hover:bg-muted cursor-pointer transition-colors"
                            onClick={() => {
                                setQuery(stock.ticker)
                                setSuggestions([])
                                router.push(`/ticker/${stock.ticker}`)
                            }}
                        >
                            <div className="flex items-center space-x-2">
                                <span className="font-bold text-primary">{stock.ticker}</span>
                                <span className="text-sm text-muted-foreground truncate">{stock.name}</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
