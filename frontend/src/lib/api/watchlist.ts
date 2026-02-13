import { createClient } from '@/lib/supabase/client'

export interface WatchlistItem {
    id: string
    ticker: string
    created_at: string
}

export async function getWatchlist() {
    const supabase = createClient()
    const { data, error } = await supabase
        .from('user_watchlist')
        .select('*')
        .order('created_at', { ascending: false })

    if (error) throw error
    return data as WatchlistItem[]
}

export async function addToWatchlist(ticker: string) {
    const supabase = createClient()
    // first get user
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) throw new Error("User not authenticated")

    const { data, error } = await supabase
        .from('user_watchlist')
        .insert([{ user_id: user.id, ticker: ticker.toUpperCase() }])
        .select()

    if (error) throw error
    return data[0]
}

export async function removeFromWatchlist(ticker: string) {
    const supabase = createClient()
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) throw new Error("User not authenticated")

    // Delete by ticker and user_id to be safe
    const { error } = await supabase
        .from('user_watchlist')
        .delete()
        .eq('user_id', user.id)
        .eq('ticker', ticker.toUpperCase())

    if (error) throw error
}
