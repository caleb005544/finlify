'use client'

import { StockSearch } from '@/components/features/stock-search'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { SlidersHorizontal } from 'lucide-react'
import Link from 'next/link'
import { Watchlist } from '@/components/features/watchlist'
import { AssumptionProfile } from '@/components/features/assumption-profile'
import { useEffect, useState } from 'react'
import { getProfile, AssumptionProfileData } from '@/lib/api/profiles'

export default function DashboardPage() {
    const [profile, setProfile] = useState<AssumptionProfileData | null>(null)

    useEffect(() => {
        getProfile().then(setProfile)
    }, [])

    return (
        <div className="container mx-auto px-4 py-8 space-y-8">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
                    <p className="text-muted-foreground">Manage your watchlist and view personalized insights.</p>
                </div>
                <div className="flex items-center space-x-2 w-full md:w-auto">
                    <StockSearch placeholder="Add to watchlist..." />
                    <Link href="/settings">
                        <Button variant="outline" size="icon">
                            <SlidersHorizontal className="h-4 w-4" />
                        </Button>
                    </Link>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                {/* Watchlist Section */}
                <div className="md:col-span-2 space-y-6">
                    <Watchlist />

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Card className="bg-gradient-to-br from-primary/5 to-transparent border-primary/20">
                            <CardHeader>
                                <CardTitle className="text-sm">Daily Top Pick</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="flex items-center justify-between">
                                    <div>
                                        <div className="text-2xl font-bold">AMD</div>
                                        <div className="text-xs text-muted-foreground">Semiconductors</div>
                                    </div>
                                    <div className="text-right">
                                        <div className="text-emerald-500 font-bold">+3.4%</div>
                                        <div className="text-xs text-muted-foreground">Forecast</div>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle className="text-sm">Profile Summary</CardTitle>
                            </CardHeader>
                            <CardContent>
                                {profile ? (
                                    <div className="space-y-2">
                                        <div className="flex justify-between text-sm">
                                            <span>Risk</span>
                                            <span className="font-medium">{profile.risk_level}</span>
                                        </div>
                                        <div className="flex justify-between text-sm">
                                            <span>Sector</span>
                                            <span className="font-medium">{profile.sector_preference}</span>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="text-sm text-muted-foreground">Loading profile...</div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </div>

                {/* Profile / Assumptions Summary */}
                <div className="space-y-6">
                    <AssumptionProfile />
                </div>
            </div>
        </div>
    )
}
