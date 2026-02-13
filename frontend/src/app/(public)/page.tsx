import { StockSearch } from '@/components/features/stock-search'
import { TrendingUp, BarChart2, ShieldCheck, Zap } from 'lucide-react'

export default function Home() {
    return (
        <div className="flex flex-col items-center">
            {/* Hero Section */}
            <section className="w-full py-24 md:py-32 lg:py-40 flex flex-col items-center justify-center bg-radial-gradient from-accent/20 to-background text-center px-4">
                <div className="space-y-6 max-w-3xl mx-auto">
                    <div className="inline-flex items-center rounded-full border border-border bg-background px-3 py-1 text-sm text-muted-foreground shadow-sm mb-4">
                        <span className="flex h-2 w-2 rounded-full bg-primary mr-2 animate-pulse"></span>
                        Finlify Demo v1.0
                    </div>
                    <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold tracking-tight bg-gradient-to-br from-foreground to-muted-foreground bg-clip-text text-transparent">
                        Smarter Investment Decisions, <br /> Powered by Data.
                    </h1>
                    <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto">
                        Explore US stocks with AI-driven insights, explainable recommendations, and personalized risk profiles.
                    </p>

                    <div className="pt-8 w-full">
                        <StockSearch placeholder="Try searching 'AAPL' or 'NVDA'..." />
                    </div>

                    <div className="pt-8 flex items-center justify-center space-x-8 text-sm text-muted-foreground">
                        <div className="flex items-center"><TrendingUp className="mr-2 h-4 w-4" /> Real-time Data</div>
                        <div className="flex items-center"><ShieldCheck className="mr-2 h-4 w-4" /> Secure & Private</div>
                    </div>
                </div>
            </section>

            {/* Features Grid */}
            <section className="w-full py-20 bg-muted/30">
                <div className="container mx-auto px-4">
                    <h2 className="text-3xl font-bold text-center mb-16">Why Finlify?</h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        <FeatureCard
                            icon={<BarChart2 className="h-10 w-10 text-primary" />}
                            title="Advanced Analytics"
                            description="Visualize historical trends with interactive charts and technical indicators."
                        />
                        <FeatureCard
                            icon={<Zap className="h-10 w-10 text-amber-500" />}
                            title="Instant Forecasts"
                            description="Get AI-powered price predictions and rating signals in milliseconds."
                        />
                        <FeatureCard
                            icon={<ShieldCheck className="h-10 w-10 text-blue-500" />}
                            title="Risk Profiling"
                            description="Tailor recommendations based on your personal risk tolerance and horizon."
                        />
                    </div>
                </div>
            </section>
        </div>
    )
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) {
    return (
        <div className="flex flex-col items-center text-center p-6 rounded-2xl border border-border bg-card shadow-sm hover:shadow-md transition-shadow">
            <div className="mb-4 p-3 bg-accent rounded-full">{icon}</div>
            <h3 className="text-xl font-semibold mb-2">{title}</h3>
            <p className="text-muted-foreground">{description}</p>
        </div>
    )
}
