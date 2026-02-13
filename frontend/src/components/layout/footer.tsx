export function Footer() {
    return (
        <footer className="border-t border-border/40 bg-background/50 py-12 px-4 backdrop-blur-sm">
            <div className="container mx-auto grid grid-cols-1 md:grid-cols-4 gap-8">
                <div className="space-y-4">
                    <h3 className="text-lg font-bold">Finlify</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                        Empowering your financial decisions with explainable AI and data-driven insights.
                    </p>
                </div>

                <div className="md:col-span-2"></div>

                <div className="space-y-4">
                    <h4 className="text-sm font-semibold">Legal</h4>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                        This platform is for informational purposes only and does not constitute investment advice.
                        Past performance is not indicative of future results.
                    </p>
                    <p className="text-xs text-muted-foreground">
                        &copy; {new Date().getFullYear()} Finlify. All rights reserved.
                    </p>
                </div>
            </div>
        </footer>
    )
}
