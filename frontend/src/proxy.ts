import { type NextRequest } from 'next/server'
import { NextResponse } from 'next/server'
import { updateSession } from '@/lib/supabase/middleware'

function isDemoAuthEnabled() {
    return process.env.DEMO_BASIC_AUTH_ENABLED === 'true'
}

function unauthorizedResponse() {
    return new NextResponse('Authentication required', {
        status: 401,
        headers: {
            'WWW-Authenticate': 'Basic realm="Finlify Demo"',
        },
    })
}

function isAuthorized(request: NextRequest) {
    const expectedUser = process.env.DEMO_BASIC_AUTH_USERNAME
    const expectedPass = process.env.DEMO_BASIC_AUTH_PASSWORD
    if (!expectedUser || !expectedPass) return false

    const authHeader = request.headers.get('authorization')
    if (!authHeader?.startsWith('Basic ')) return false

    try {
        const encoded = authHeader.slice('Basic '.length)
        const decoded = atob(encoded)
        const separatorIndex = decoded.indexOf(':')
        if (separatorIndex < 0) return false
        const username = decoded.slice(0, separatorIndex)
        const password = decoded.slice(separatorIndex + 1)
        return username === expectedUser && password === expectedPass
    } catch {
        return false
    }
}

export async function proxy(request: NextRequest) {
    if (isDemoAuthEnabled() && !isAuthorized(request)) {
        return unauthorizedResponse()
    }
    return await updateSession(request)
}

export const config = {
    matcher: [
        /*
         * Match all request paths except for the ones starting with:
         * - _next/static (static files)
         * - _next/image (image optimization files)
         * - favicon.ico (favicon file)
         * Feel free to modify this pattern to include more paths.
         */
        '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
    ],
}
