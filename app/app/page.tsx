import Link from "next/link";

export const metadata = {
  title: "Finlify — Invest with Clarity",
  description: "Factor-scored rankings for stocks and ETFs — updated daily, easy to understand.",
};

const MOCK_ROWS = [
  { rank: 1, ticker: "NVDA", composite: 92, trend: 88, momentum: 94, decision: "BUY" },
  { rank: 2, ticker: "MSFT", composite: 89, trend: 85, momentum: 90, decision: "BUY" },
  { rank: 3, ticker: "PLTR", composite: 85, trend: 79, momentum: 87, decision: "BUY" },
  { rank: 4, ticker: "QQQ",  composite: 76, trend: 72, momentum: 78, decision: "WATCH" },
  { rank: 5, ticker: "AAPL", composite: 72, trend: 68, momentum: 74, decision: "WATCH" },
] as const;

function ScoreCell({ value, color }: { value: number; color: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 4, borderRadius: 2, background: "rgba(0,0,0,0.07)", minWidth: 48 }}>
        <div style={{ height: "100%", borderRadius: 2, background: color, width: `${value}%` }} />
      </div>
      <span style={{ fontSize: 13, color: "#333", fontVariantNumeric: "tabular-nums", minWidth: 24, textAlign: "right" }}>{value}</span>
    </div>
  );
}

function DecisionPill({ decision }: { decision: string }) {
  const isBuy = decision === "BUY";
  return (
    <span style={{
      display: "inline-block",
      padding: "2px 10px",
      borderRadius: 100,
      fontSize: 12,
      fontWeight: 600,
      background: isBuy ? "#e4f2eb" : "#fef0e0",
      color: isBuy ? "#1a6e3e" : "#9a5c0a",
    }}>
      {decision}
    </span>
  );
}

export default function LandingPage() {
  return (
    <div style={{ background: "#f5f4f0", minHeight: "100vh", color: "#1a1a1a" }}>

      {/* A) NAVBAR */}
      <nav style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        background: "#f5f4f0",
        borderBottom: "0.5px solid rgba(0,0,0,0.08)",
        padding: "18px 40px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}>
        <span style={{ fontWeight: 700, fontSize: 20, color: "#1a1a1a" }}>Finlify</span>
        <div style={{ display: "flex", gap: 28, alignItems: "center" }}>
          <a href="#how-it-works" style={{ fontSize: 14, color: "#666", fontWeight: 500, textDecoration: "none" }}>
            How it works
          </a>
          <Link href="/dashboard" style={{ fontSize: 14, color: "#666", fontWeight: 500, textDecoration: "none" }}>
            Universe
          </Link>
        </div>
        <Link href="/dashboard" style={{
          background: "#ffffff",
          color: "#1a1a1a",
          border: "1.5px solid rgba(0,0,0,0.25)",
          borderRadius: 100,
          fontSize: 14,
          fontWeight: 600,
          padding: "8px 20px",
          textDecoration: "none",
          whiteSpace: "nowrap",
        }}>
          Open Dashboard →
        </Link>
      </nav>

      {/* B) HERO */}
      <section style={{ maxWidth: 700, margin: "0 auto", padding: "88px 40px 56px", textAlign: "center" }}>
        {/* Badge */}
        <div style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 8,
          background: "#ffffff",
          border: "0.5px solid rgba(0,0,0,0.12)",
          borderRadius: 100,
          padding: "5px 14px",
          fontSize: 12,
          color: "#555",
          marginBottom: 28,
        }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#2d7a52", display: "inline-block", flexShrink: 0 }} />
          Updated every trading day
        </div>

        {/* H1 */}
        <h1 style={{
          fontSize: "clamp(38px, 6vw, 60px)",
          fontWeight: 700,
          letterSpacing: "-1px",
          lineHeight: 1.1,
          margin: "0 0 8px 0",
        }}>
          Make Investment <span style={{ color: "#2d7a52" }}>Simple</span>
        </h1>

        {/* Subheading */}
        <p style={{
          fontSize: "clamp(34px, 5vw, 52px)",
          fontWeight: 300,
          fontStyle: "italic",
          color: "#555",
          margin: "0 0 24px",
          lineHeight: 1.15,
        }}>
          and Data-Driven.
        </p>

        {/* Description */}
        <p style={{
          fontSize: 16,
          color: "#666",
          lineHeight: 1.75,
          marginBottom: 36,
        }}>
          Finlify empowers you with factor-scored rankings for stocks and ETFs — updated daily, easy to understand.
        </p>

        {/* CTA Buttons */}
        <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
          <Link href="/dashboard" style={{
            background: "#1a1a1a",
            color: "#ffffff",
            borderRadius: 100,
            padding: "13px 30px",
            fontSize: 15,
            fontWeight: 600,
            textDecoration: "none",
            display: "inline-block",
          }}>
            Open Dashboard →
          </Link>
          <a href="#how-it-works" style={{
            background: "transparent",
            color: "#1a1a1a",
            border: "1.5px solid rgba(0,0,0,0.2)",
            borderRadius: 100,
            padding: "13px 30px",
            fontSize: 15,
            fontWeight: 500,
            textDecoration: "none",
            display: "inline-block",
          }}>
            How scores work
          </a>
        </div>
      </section>

      {/* C) DASHBOARD PREVIEW */}
      <section style={{ maxWidth: 960, margin: "0 auto", padding: "32px 40px 0" }}>
        <p style={{
          textAlign: "center",
          fontSize: 11,
          color: "#aaa",
          textTransform: "uppercase",
          letterSpacing: "1.2px",
          marginBottom: 16,
        }}>
          Live Dashboard
        </p>

        {/* Browser chrome */}
        <div style={{
          background: "#ffffff",
          border: "0.5px solid rgba(0,0,0,0.09)",
          borderRadius: "14px 14px 0 0",
          overflow: "hidden",
        }}>
          {/* Top bar */}
          <div style={{
            background: "#f9f9f8",
            borderBottom: "0.5px solid rgba(0,0,0,0.08)",
            padding: "11px 18px",
            display: "flex",
            alignItems: "center",
          }}>
            <div style={{ display: "flex", gap: 6, marginRight: 16 }}>
              <span style={{ width: 9, height: 9, borderRadius: "50%", background: "#ff5f57", display: "inline-block" }} />
              <span style={{ width: 9, height: 9, borderRadius: "50%", background: "#ffbd2e", display: "inline-block" }} />
              <span style={{ width: 9, height: 9, borderRadius: "50%", background: "#28c840", display: "inline-block" }} />
            </div>
            <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
              <span style={{
                background: "rgba(0,0,0,0.05)",
                borderRadius: 6,
                padding: "3px 16px",
                fontSize: 12,
                color: "#888",
              }}>
                finlify.vercel.app
              </span>
            </div>
          </div>

          {/* Content */}
          <div style={{ padding: 20 }}>
            {/* Header row */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <span style={{ fontWeight: 700, fontSize: 15, color: "#1a1a1a" }}>Market Overview</span>
              <span style={{ fontSize: 12, color: "#999" }}>Updated Apr 10, 2026</span>
            </div>

            {/* KPI cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 20 }}>
              {[
                { label: "BUY",      count: 18,  color: "#2d7a52" },
                { label: "WATCH",    count: 34,  color: "#b86e10" },
                { label: "AVOID",    count: 58,  color: "#b83030" },
                { label: "Universe", count: 110, color: "#333" },
              ].map(({ label, count, color }) => (
                <div key={label} style={{
                  background: "#f9f9f8",
                  border: "0.5px solid rgba(0,0,0,0.07)",
                  borderRadius: 10,
                  padding: "12px 14px",
                }}>
                  <p style={{ fontSize: 11, color: "#999", margin: 0, fontWeight: 500 }}>{label}</p>
                  <p style={{ fontSize: 24, fontWeight: 700, color, margin: "4px 0 0", fontVariantNumeric: "tabular-nums" }}>{count}</p>
                </div>
              ))}
            </div>

            {/* Rankings table */}
            <div style={{ border: "0.5px solid rgba(0,0,0,0.08)", borderRadius: 10, overflow: "hidden" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#f9f9f8", borderBottom: "0.5px solid rgba(0,0,0,0.07)" }}>
                    {["#", "Ticker", "Composite Score", "Trend", "Momentum", "Decision"].map((h) => (
                      <th key={h} style={{
                        padding: "8px 12px",
                        textAlign: "left",
                        fontSize: 11,
                        fontWeight: 600,
                        color: "#999",
                        whiteSpace: "nowrap",
                      }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {MOCK_ROWS.map((row, i) => (
                    <tr key={row.ticker} style={{
                      borderBottom: i < MOCK_ROWS.length - 1 ? "0.5px solid rgba(0,0,0,0.05)" : undefined,
                    }}>
                      <td style={{ padding: "10px 12px", color: "#bbb", fontSize: 12, fontVariantNumeric: "tabular-nums" }}>{row.rank}</td>
                      <td style={{ padding: "10px 12px", fontWeight: 700, color: "#1a1a1a" }}>{row.ticker}</td>
                      <td style={{ padding: "10px 12px", minWidth: 140 }}>
                        <ScoreCell value={row.composite} color="#2d7a52" />
                      </td>
                      <td style={{ padding: "10px 12px", minWidth: 120 }}>
                        <ScoreCell value={row.trend} color="#3a7bd5" />
                      </td>
                      <td style={{ padding: "10px 12px", minWidth: 120 }}>
                        <ScoreCell value={row.momentum} color="#b86e10" />
                      </td>
                      <td style={{ padding: "10px 12px" }}>
                        <DecisionPill decision={row.decision} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      {/* D) FEATURES SECTION */}
      <section id="how-it-works" style={{ maxWidth: 960, margin: "0 auto", padding: "72px 40px" }}>
        <p style={{
          textAlign: "center",
          fontSize: 11,
          color: "#aaa",
          textTransform: "uppercase",
          letterSpacing: "1.2px",
          marginBottom: 12,
        }}>
          How It Works
        </p>
        <h2 style={{
          fontSize: "clamp(26px, 3.5vw, 36px)",
          fontWeight: 700,
          textAlign: "center",
          marginBottom: 48,
          letterSpacing: "-0.5px",
        }}>
          Quantitative scoring, built for real decisions.
        </h2>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
          {[
            {
              icon: (
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M3 14l4-4 3 3 4-5 3 3" stroke="#2d7a52" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              ),
              title: "Daily factor scoring",
              desc: "Every trading day, assets are scored on trend strength, price momentum, and risk-adjusted returns using a consistent quantitative model.",
            },
            {
              icon: (
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M10 3v14M3 10h14" stroke="#3a7bd5" strokeWidth="1.8" strokeLinecap="round"/>
                  <circle cx="10" cy="10" r="7" stroke="#3a7bd5" strokeWidth="1.5"/>
                </svg>
              ),
              title: "Honest uncertainty",
              desc: "Statistical forecast bands show 30, 60, and 90-day ranges based on historical volatility. Wider over time — never false precision.",
            },
            {
              icon: (
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M4 16V8l6-5 6 5v8" stroke="#b86e10" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M8 16v-4h4v4" stroke="#b86e10" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              ),
              title: "Automated pipeline",
              desc: "Prices are ingested from Polygon.io every weekday after market close. Rankings update automatically — no manual refresh needed.",
            },
          ].map(({ icon, title, desc }) => (
            <div key={title} style={{
              background: "#ffffff",
              border: "0.5px solid rgba(0,0,0,0.09)",
              borderRadius: 14,
              padding: 24,
            }}>
              <div style={{ marginBottom: 12 }}>{icon}</div>
              <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 8, color: "#1a1a1a" }}>{title}</h3>
              <p style={{ fontSize: 14, color: "#666", lineHeight: 1.65, margin: 0 }}>{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* E) CTA SECTION */}
      <section style={{ maxWidth: 880, margin: "0 auto 80px", padding: "64px 40px", background: "#eeecea", border: "0.5px solid rgba(0,0,0,0.08)", borderRadius: 16, textAlign: "center" }}>
        <h2 style={{
          fontSize: "clamp(28px, 3.5vw, 44px)",
          fontWeight: 700,
          letterSpacing: "-0.8px",
          marginBottom: 28,
        }}>
          Invest with{" "}
          <em style={{ fontStyle: "italic", color: "#2d7a52", fontWeight: 600 }}>Clarity.</em>
        </h2>
        <Link href="/dashboard" style={{
          display: "inline-block",
          background: "#ffffff",
          color: "#1a1a1a",
          border: "1.5px solid rgba(0,0,0,0.25)",
          borderRadius: 100,
          padding: "14px 36px",
          fontSize: 15,
          fontWeight: 600,
          textDecoration: "none",
        }}>
          Open Dashboard →
        </Link>
      </section>

      {/* F) FOOTER */}
      <footer style={{ maxWidth: 960, margin: "0 auto", padding: "24px 40px 32px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
        <span style={{ fontSize: 12, color: "#bbb" }}>© 2026 Finlify</span>
        <span style={{ fontSize: 12, color: "#bbb" }}>Data sourced from Polygon.io · Not financial advice</span>
      </footer>

    </div>
  );
}
