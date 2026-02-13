import { createClient } from '@/lib/supabase/client'

export interface AssumptionProfileData {
    id?: string
    risk_level: 'Low' | 'Medium' | 'High'
    horizon: 'Short' | 'Medium' | 'Long'
    sector_preference: string
}

export async function getProfile() {
    const supabase = createClient()
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return null

    const { data, error } = await supabase
        .from('assumption_profiles')
        .select('*')
        .eq('user_id', user.id)
        .maybeSingle() // Use maybeSingle to avoid error if no profile exists yet

    if (error) throw error
    return data as AssumptionProfileData | null
}

export async function saveProfile(profile: AssumptionProfileData) {
    const supabase = createClient()
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) throw new Error("User not authenticated")

    // Check if profile exists
    const existing = await getProfile()

    let result
    if (existing) {
        result = await supabase
            .from('assumption_profiles')
            .update({
                risk_level: profile.risk_level,
                horizon: profile.horizon,
                sector_preference: profile.sector_preference,
                updated_at: new Date().toISOString()
            })
            .eq('id', existing.id)
            .select()
    } else {
        result = await supabase
            .from('assumption_profiles')
            .insert([{
                user_id: user.id,
                risk_level: profile.risk_level,
                horizon: profile.horizon,
                sector_preference: profile.sector_preference
            }])
            .select()
    }

    if (result.error) throw result.error
    return result.data[0]
}
