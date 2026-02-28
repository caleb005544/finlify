'use client'

import { useRouter } from 'next/navigation'
import { Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useState } from 'react'

export function StockSearch({ placeholder = 'Search for a stock...' }: { placeholder?: string }) {
    const [query, setQuery] = useState('')
    const router = useRouter()

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault()
        if (query.trim()) {
            router.push(`/ticker/${query.trim().toUpperCase()}`)
        }
    }

    return (
        <div className="w-full max-w-lg mx-auto">
            <form onSubmit={handleSearch} className="relative flex items-center">
                <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-muted-foreground">
                    <Search className="h-5 w-5" />
                </div>
                <input
                    type="text"
                    className="flex h-12 w-full rounded-full border border-input bg-background/50 backdrop-blur-sm px-10 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 shadow-lg transition-shadow hover:shadow-xl"
                    placeholder={placeholder}
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
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
        </div>
    )
}
