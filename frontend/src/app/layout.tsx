import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Finlify | Empower Finance Through Data",
  description: "A decision-driven stock analysis platform.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
