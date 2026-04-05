import type { Metadata } from "next";
import { Inter, DM_Sans } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Finlify — Market Overview",
  description: "Daily asset rankings powered by quantitative factor analysis",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className={`${inter.variable} ${dmSans.variable} antialiased min-h-full flex flex-col`}>
        {children}
        <footer className="border-t border-border/40 mt-16 py-6 px-6">
          <p className="text-xs text-muted-foreground text-center leading-relaxed max-w-3xl mx-auto">
            <span className="font-medium text-muted-foreground/80">Disclaimer:</span>{' '}
            The information provided on Finlify is for informational purposes only and does not
            constitute investment advice, financial advice, trading advice, or any other type of
            advice. Finlify does not recommend buying, selling, or holding any asset. All data is
            sourced from third-party providers and may be delayed or inaccurate. Past performance
            is not indicative of future results. Always conduct your own research and consult a
            qualified financial advisor before making any investment decisions.
          </p>
        </footer>
      </body>
    </html>
  );
}
