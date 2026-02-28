'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { TrendingUp, AlertCircle } from 'lucide-react'

export default function AuthCodeErrorPage() {
    return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-muted/30 px-4">
            <div className="w-full max-w-sm space-y-6">
                <div className="flex flex-col items-center space-y-2 text-center">
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/15">
                        <AlertCircle className="h-6 w-6 text-destructive" />
                    </div>
                    <h1 className="text-2xl font-bold tracking-tight">Invalid verification link</h1>
                    <p className="text-sm text-muted-foreground">
                        The verification link has expired or is invalid. Please try signing up again.
                    </p>
                </div>

                <div className="grid gap-4">
                    <Link href="/signup" className="w-full">
                        <Button className="w-full">
                            Return to Sign Up
                        </Button>
                    </Link>

                    <Link href="/" className="w-full">
                        <Button variant="outline" className="w-full">
                            Go to Home
                        </Button>
                    </Link>
                </div>

                <div className="text-center text-xs text-muted-foreground">
                    <p>Already have a verified account?{" "}
                        <Link href="/login" className="underline hover:text-primary">
                            Sign in here
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    )
}
