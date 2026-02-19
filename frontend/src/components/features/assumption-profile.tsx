'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { getProfile, saveProfile, AssumptionProfileData } from '@/lib/api/profiles'
import { Loader2 } from 'lucide-react'

const RISK_OPTIONS: AssumptionProfileData['risk_level'][] = ['Low', 'Medium', 'High']
const HORIZON_OPTIONS: AssumptionProfileData['horizon'][] = ['Short', 'Medium', 'Long']

export function AssumptionProfile() {
    const [risk, setRisk] = useState<AssumptionProfileData['risk_level']>('Medium')
    const [horizon, setHorizon] = useState<AssumptionProfileData['horizon']>('Long')
    const [sector, setSector] = useState<string>('Tech')

    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [message, setMessage] = useState('')

    useEffect(() => {
        loadProfile()
    }, [])

    const loadProfile = async () => {
        try {
            setLoading(true)
            const data = await getProfile()
            if (data) {
                setRisk(data.risk_level)
                setHorizon(data.horizon)
                setSector(data.sector_preference)
            }
        } catch (e) {
            console.error("Failed to load profile", e)
        } finally {
            setLoading(false)
        }
    }

    const handleSave = async () => {
        try {
            setSaving(true)
            await saveProfile({
                risk_level: risk,
                horizon: horizon,
                sector_preference: sector
            })
            setMessage("Profile saved!")
            setTimeout(() => setMessage(''), 2000)
        } catch (e) {
            setMessage("Failed to save.")
            console.error(e)
        } finally {
            setSaving(false)
        }
    }

    if (loading) {
        return (
            <Card>
                <CardHeader><CardTitle>Investment Profile</CardTitle></CardHeader>
                <CardContent className="h-[250px] flex items-center justify-center">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </CardContent>
            </Card>
        )
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle>Investment Profile</CardTitle>
                <CardDescription>Customize AI recommendations based on your preferences.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-2">
                    <label className="text-sm font-medium">Risk Tolerance</label>
                    <div className="grid grid-cols-3 gap-2">
                        {RISK_OPTIONS.map((r) => (
                            <Button
                                key={r}
                                variant={risk === r ? 'default' : 'outline'}
                                size="sm"
                                onClick={() => setRisk(r)}
                                className="text-xs"
                            >
                                {r}
                            </Button>
                        ))}
                    </div>
                </div>

                <div className="space-y-2">
                    <label className="text-sm font-medium">Time Horizon</label>
                    <div className="grid grid-cols-3 gap-2">
                        {HORIZON_OPTIONS.map((h) => (
                            <Button
                                key={h}
                                variant={horizon === h ? 'default' : 'outline'}
                                size="sm"
                                onClick={() => setHorizon(h)}
                                className="text-xs"
                            >
                                {h}
                            </Button>
                        ))}
                    </div>
                </div>

                <div className="space-y-2">
                    <label className="text-sm font-medium">Preferred Sector</label>
                    <select
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                        value={sector}
                        onChange={(e) => setSector(e.target.value)}
                    >
                        <option value="Tech">Technology</option>
                        <option value="Finance">Finance</option>
                        <option value="Healthcare">Healthcare</option>
                        <option value="Energy">Energy</option>
                        <option value="Consumer">Consumer Goods</option>
                    </select>
                </div>
            </CardContent>
            <CardFooter>
                <Button className="w-full" onClick={handleSave} disabled={saving}>
                    {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    {message || "Update Profile"}
                </Button>
            </CardFooter>
        </Card>
    )
}
