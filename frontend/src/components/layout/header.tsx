import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { TrendingUp } from 'lucide-react'

export function Header() {
    return (
        <header className="fixed top-0 w-full z-50 bg-background/80 backdrop-blur-md border-b border-border/40">
            <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                <Link href="/" className="flex items-center space-x-2">
                    <TrendingUp className="h-6 w-6 text-primary" />
                    <span className="text-xl font-bold bg-gradient-to-r from-primary to-emerald-400 bg-clip-text text-transparent">
                        Finlify
                    </span>
                </Link>

                <nav className="hidden md:flex items-center space-x-6 text-sm font-medium text-muted-foreground">
                    <Link href="/#demo" className="hover:text-primary transition-colors">
                        Demo
                    </Link>
                    <Link href="/about" className="hover:text-primary transition-colors">
                        About
                    </Link>
                </nav>

                <div className="flex items-center space-x-4">
                    <Link href="/login">
                        <Button variant="ghost" size="sm">
                            Sign In
                        </Button>
                    </Link>
                    <Link href="/signup">
                        <Button size="sm" className="bg-primary text-primary-foreground hover:bg-primary/90">
                            Get Started
                        </Button>
                    </Link>
                </div>
            </div>
        </header>
    )
}
