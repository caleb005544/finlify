import { Header } from '@/components/layout/header'
import { Footer } from '@/components/layout/footer'
import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'

export default async function ProtectedLayout({
    children,
}: {
    children: React.ReactNode
}) {
    const supabase = await createClient()

    const {
        data: { user },
    } = await supabase.auth.getUser()

    if (!user && process.env.NEXT_PUBLIC_SUPABASE_URL) {
        // Only enforce if env vars exist, otherwise allow demo
        redirect('/login')
    }

    return (
        <div className="flex min-h-screen flex-col">
            <Header />
            <main className="flex-1 pt-16 bg-muted/10">
                {children}
            </main>
            <Footer />
        </div>
    )
}
