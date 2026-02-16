export default function AboutPage() {
    return (
        <div className="container mx-auto px-4 py-12 space-y-6">
            <h1 className="text-4xl font-bold tracking-tight">About Finlify</h1>
            <p className="text-muted-foreground max-w-3xl">
                Finlify is a policy-driven investment scoring and forecasting platform.
                It combines explainable scoring logic with forecast services to help users
                evaluate market opportunities quickly and transparently.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="rounded-xl border p-5">
                    <h2 className="font-semibold mb-2">Scoring Engine</h2>
                    <p className="text-sm text-muted-foreground">
                        Deterministic strategy policies with transparent weighted explanations.
                    </p>
                </div>
                <div className="rounded-xl border p-5">
                    <h2 className="font-semibold mb-2">Forecast Service</h2>
                    <p className="text-sm text-muted-foreground">
                        Multi-model forecasting with routing, cache, and runtime observability.
                    </p>
                </div>
                <div className="rounded-xl border p-5">
                    <h2 className="font-semibold mb-2">User Experience</h2>
                    <p className="text-sm text-muted-foreground">
                        Public demo flow plus authenticated watchlist and assumption profile features.
                    </p>
                </div>
            </div>
        </div>
    )
}
