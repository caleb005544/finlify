"use client";

import { useState, useRef, type CSSProperties } from "react";
import Link from "next/link";
import type { Ranking, Decision } from "@/types/rankings";

const D_BADGE: Record<Decision, CSSProperties> = {
  BUY:   { background: "#e4f2eb", color: "#1a6e3e", borderRadius: 100, fontSize: 11, fontWeight: 700, padding: "2px 10px", display: "inline-block" },
  HOLD:  { background: "#e4edf9", color: "#1a4a8a", borderRadius: 100, fontSize: 11, fontWeight: 700, padding: "2px 10px", display: "inline-block" },
  WATCH: { background: "#fef0e0", color: "#9a5c0a", borderRadius: 100, fontSize: 11, fontWeight: 700, padding: "2px 10px", display: "inline-block" },
  AVOID: { background: "#fde8e8", color: "#9a2020", borderRadius: 100, fontSize: 11, fontWeight: 700, padding: "2px 10px", display: "inline-block" },
};

const D_TEXT: Record<Decision, string> = {
  BUY:   "#2d7a52",
  HOLD:  "#1a5ca8",
  WATCH: "#b86e10",
  AVOID: "#b83030",
};

const REGIME_COLOR: Record<string, string> = {
  TRENDING: "#2d7a52",
  MIXED:    "#888888",
  RISK_OFF: "#b83030",
};

const RISK_COLOR: Record<string, string> = {
  LOW:    "#2d7a52",
  MEDIUM: "#b86e10",
  HIGH:   "#b83030",
};

export function RankingsView({
  rankings,
}: {
  rankings: Ranking[];
  counts: Record<Decision, number>;
}) {
  const [filter, setFilter] = useState<Decision | "ALL">("ALL");
  const [assetFilter, setAssetFilter] = useState<"ALL" | "stock" | "etf">("ALL");
  const [sectorFilter, setSectorFilter] = useState("ALL");
  const [selectedTickers, setSelectedTickers] = useState<string[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const sectors = ["ALL", ...Array.from(new Set(rankings.map((r) => r.sector).filter(Boolean))).sort()] as string[];

  const assetFiltered = rankings.filter((r) => {
    const matchesAsset = assetFilter === "ALL" || r.asset_type === assetFilter;
    const matchesSector = sectorFilter === "ALL" || r.sector === sectorFilter;
    return matchesAsset && matchesSector;
  });

  const dynamicCounts = { BUY: 0, HOLD: 0, WATCH: 0, AVOID: 0 };
  for (const r of assetFiltered) dynamicCounts[r.decision as Decision]++;

  const decisionFiltered = rankings.filter((r) => {
    const matchesDecision = filter === "ALL" || r.decision === filter;
    const matchesSector = sectorFilter === "ALL" || r.sector === sectorFilter;
    return matchesDecision && matchesSector;
  });
  const stockCount = decisionFiltered.filter((r) => r.asset_type === "stock").length;
  const etfCount = decisionFiltered.filter((r) => r.asset_type === "etf").length;

  const topBuys = assetFiltered.filter((r) => r.decision === "BUY").slice(0, 5);

  const tickerCandidates = rankings
    .map((r) => r.ticker)
    .filter((t) => !selectedTickers.includes(t) && t.toLowerCase().includes(inputValue.toLowerCase()));

  const addTicker = (ticker: string) => {
    setSelectedTickers((prev) => [...prev, ticker]);
    setInputValue("");
    setDropdownOpen(false);
    inputRef.current?.focus();
  };

  const removeTicker = (ticker: string) => {
    setSelectedTickers((prev) => prev.filter((t) => t !== ticker));
  };

  const filtered = rankings.filter((r) => {
    const matchesDecision = filter === "ALL" || r.decision === filter;
    const matchesAsset = assetFilter === "ALL" || r.asset_type === assetFilter;
    const matchesSector = sectorFilter === "ALL" || r.sector === sectorFilter;
    const matchesTicker = selectedTickers.length === 0 || selectedTickers.includes(r.ticker);
    return matchesDecision && matchesAsset && matchesSector && matchesTicker;
  });

  return (
    <div style={{ background: "#f5f4f0", minHeight: "100vh", padding: "32px 40px", fontFamily: "Nunito, sans-serif" }}>

      {/* Back link */}
      <Link href="/" style={{ fontSize: 13, color: "#444", textDecoration: "none", display: "block", marginBottom: 16 }}>
        ← Finlify
      </Link>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 32 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: "#1a1a1a", margin: 0 }}>Finlify</h1>
          <p style={{ fontSize: 13, color: "#444", margin: "4px 0 0" }}>Market Overview</p>
        </div>
        <div style={{ textAlign: "right" }}>
          <p style={{ fontSize: 13, color: "#444", margin: 0 }}>Universe</p>
          <p style={{ fontSize: 20, fontWeight: 700, color: "#1a1a1a", margin: "2px 0 0" }}>{rankings.length} assets</p>
        </div>
      </div>

      {/* KPI cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 32 }}>
        {(["BUY", "HOLD", "WATCH", "AVOID"] as Decision[]).map((d) => (
          <div
            key={d}
            onClick={() => setFilter(filter === d ? "ALL" : d)}
            style={{
              background: "#fff",
              border: filter === d ? `2px solid ${D_TEXT[d]}` : "1px solid rgba(0,0,0,0.09)",
              borderRadius: 14,
              padding: "20px 24px",
              cursor: "pointer",
              transition: "all 0.15s",
            }}
          >
            <p style={{ fontSize: 11, fontWeight: 600, color: "#888", textTransform: "uppercase", letterSpacing: "0.5px", margin: 0 }}>{d}</p>
            <p style={{ fontSize: 32, fontWeight: 700, color: D_TEXT[d], margin: "4px 0 2px", fontVariantNumeric: "tabular-nums" }}>
              {dynamicCounts[d]}
            </p>
            <p style={{ fontSize: 12, color: "#888", margin: 0 }}>
              {assetFiltered.length > 0 ? ((dynamicCounts[d] / assetFiltered.length) * 100).toFixed(0) : 0}% of {assetFilter === "ALL" ? "universe" : assetFilter}
            </p>
          </div>
        ))}
      </div>

      {/* Top 5 BUY cards */}
      {filter === "ALL" && topBuys.length > 0 && (
        <div style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 11, fontWeight: 600, color: "#888", textTransform: "uppercase", letterSpacing: "1px", margin: "0 0 12px" }}>
            Top Opportunities
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
            {topBuys.map((r) => (
              <Link
                key={r.source_ticker}
                href={`/asset/${r.ticker}`}
                style={{ textDecoration: "none", background: "#fff", border: "1px solid rgba(0,0,0,0.09)", borderRadius: 14, padding: 20, display: "block" }}
              >
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 12 }}>
                  <span style={{ fontSize: 15, fontWeight: 700, color: "#1a1a1a" }}>{r.ticker}</span>
                  <span style={{ background: "#e4f2eb", color: "#1a6e3e", fontSize: 11, fontWeight: 700, borderRadius: 100, padding: "2px 10px" }}>BUY</span>
                </div>
                <p style={{ fontSize: 26, fontWeight: 700, color: "#1a1a1a", margin: "0 0 2px", fontVariantNumeric: "tabular-nums" }}>
                  {r.composite_score.toFixed(1)}
                </p>
                <p style={{ fontSize: 11, color: "#888", margin: "0 0 10px" }}>composite</p>
                <div style={{ height: 4, background: "#e4f2eb", borderRadius: 2 }}>
                  <div style={{ height: "100%", borderRadius: 2, background: "#2d7a52", width: `${Math.min((r.composite_score / 70) * 100, 100)}%` }} />
                </div>
                <p style={{ fontSize: 11, color: REGIME_COLOR[r.regime] ?? "#888", margin: "8px 0 0" }}>{r.regime}</p>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Ticker multi-select + asset type filter */}
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 12, marginBottom: 16 }}>
        {/* Ticker search */}
        <div style={{ position: "relative" }}>
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6, minWidth: 220, maxWidth: 320, padding: "6px 10px", borderRadius: 8, border: "1px solid rgba(0,0,0,0.12)", background: "#fff" }}>
            {selectedTickers.map((t) => (
              <span key={t} style={{ display: "inline-flex", alignItems: "center", gap: 4, padding: "2px 8px", borderRadius: 100, background: "#f0efeb", fontSize: 12, fontWeight: 600, color: "#1a1a1a" }}>
                {t}
                <button onClick={() => removeTicker(t)} style={{ background: "none", border: "none", cursor: "pointer", color: "#444", fontSize: 12, lineHeight: 1, padding: 0 }}>✕</button>
              </span>
            ))}
            <input
              ref={inputRef}
              type="text"
              placeholder={selectedTickers.length === 0 ? "Filter tickers..." : ""}
              value={inputValue}
              onChange={(e) => { setInputValue(e.target.value); setDropdownOpen(true); }}
              onFocus={() => setDropdownOpen(true)}
              onBlur={() => setTimeout(() => setDropdownOpen(false), 150)}
              style={{ flex: 1, minWidth: 80, background: "transparent", border: "none", outline: "none", fontSize: 14, color: "#1a1a1a" }}
            />
          </div>
          {dropdownOpen && tickerCandidates.length > 0 && (
            <ul style={{ position: "absolute", zIndex: 10, marginTop: 4, width: "100%", maxHeight: 192, overflowY: "auto", borderRadius: 8, border: "1px solid rgba(0,0,0,0.12)", background: "#fff", boxShadow: "0 4px 12px rgba(0,0,0,0.08)", listStyle: "none", padding: 0, margin: 0 }}>
              {tickerCandidates.slice(0, 20).map((t) => (
                <li
                  key={t}
                  onMouseDown={() => addTicker(t)}
                  style={{ padding: "8px 14px", fontSize: 13, color: "#1a1a1a", cursor: "pointer" }}
                >
                  {t}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Asset type toggle */}
        <div style={{ display: "flex", gap: 6 }}>
          {([
            { key: "ALL"   as const, label: "ALL",   count: decisionFiltered.length },
            { key: "stock" as const, label: "STOCK", count: stockCount },
            { key: "etf"   as const, label: "ETF",   count: etfCount },
          ]).map(({ key, label, count }) => (
            <button
              key={key}
              onClick={() => setAssetFilter(assetFilter === key ? "ALL" : key)}
              style={{
                background: assetFilter === key ? "#1a1a1a" : "transparent",
                color: assetFilter === key ? "#fff" : "#666",
                border: assetFilter === key ? "none" : "1px solid rgba(0,0,0,0.15)",
                borderRadius: 100,
                padding: "6px 16px",
                fontSize: 13,
                fontWeight: assetFilter === key ? 600 : 400,
                cursor: "pointer",
              }}
            >
              {label} <span style={{ opacity: 0.6, fontSize: 11 }}>({count})</span>
            </button>
          ))}
        </div>

        <span style={{ fontSize: 13, color: "#888" }}>
          {filtered.length} / {rankings.length} tickers
        </span>
      </div>

      {/* Sector filter pills */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 24 }}>
        {sectors.map((sector) => (
          <button
            key={sector}
            onClick={() => setSectorFilter(sectorFilter === sector ? "ALL" : sector)}
            style={{
              background: sectorFilter === sector ? "#1a1a1a" : "#fff",
              color: sectorFilter === sector ? "#fff" : "#555",
              border: sectorFilter === sector ? "none" : "1px solid rgba(0,0,0,0.12)",
              borderRadius: 100,
              fontSize: 12,
              fontWeight: 500,
              padding: "4px 14px",
              cursor: "pointer",
            }}
          >
            {sector}
          </button>
        ))}
      </div>

      {/* Rankings table */}
      <div style={{ background: "#fff", border: "1px solid rgba(0,0,0,0.09)", borderRadius: 14, overflow: "hidden", marginBottom: 40 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 20px", borderBottom: "1px solid rgba(0,0,0,0.06)" }}>
          <h2 style={{ fontSize: 13, fontWeight: 600, color: "#1a1a1a", margin: 0 }}>
            {filter === "ALL" ? `All assets · ${rankings.length}` : `${filter} · ${filtered.length}`}
          </h2>
          {filter !== "ALL" && (
            <button
              onClick={() => setFilter("ALL")}
              style={{ fontSize: 12, color: "#888", background: "none", border: "none", cursor: "pointer" }}
            >
              Clear filter ✕
            </button>
          )}
        </div>
        <div style={{ overflowX: "auto", maxHeight: 600, overflowY: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "#fafaf8" }}>
                {["#", "Ticker", "Signal", "Score", "Trend", "Mom", "Risk", "Regime", "Risk Lvl", "Conf"].map((h) => (
                  <th key={h} style={{ padding: "10px 20px", textAlign: "left", fontSize: 11, color: "#aaa", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.4px", whiteSpace: "nowrap" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr
                  key={r.source_ticker}
                  style={{ borderBottom: "1px solid rgba(0,0,0,0.05)" }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "#fafaf8")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <td style={{ padding: "10px 20px", color: "#888", fontSize: 13, fontVariantNumeric: "tabular-nums" }}>{r.rank_overall}</td>
                  <td style={{ padding: "10px 20px" }}>
                    <Link
                      href={`/asset/${r.ticker}`}
                      style={{ fontWeight: 700, color: "#1a1a1a", textDecoration: "none", fontSize: 14 }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = "#2d7a52")}
                      onMouseLeave={(e) => (e.currentTarget.style.color = "#1a1a1a")}
                    >
                      {r.ticker}
                    </Link>
                  </td>
                  <td style={{ padding: "10px 20px" }}>
                    <span style={D_BADGE[r.decision as Decision]}>{r.decision}</span>
                  </td>
                  <td style={{ padding: "10px 20px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ width: 36, textAlign: "right", fontSize: 12, color: "#444", fontVariantNumeric: "tabular-nums" }}>{r.composite_score.toFixed(1)}</span>
                      <div style={{ height: 4, width: 60, borderRadius: 2, background: "rgba(0,0,0,0.07)" }}>
                        <div style={{ height: "100%", borderRadius: 2, background: "#2d7a52", width: `${Math.min((r.composite_score / 70) * 100, 100)}%` }} />
                      </div>
                    </div>
                  </td>
                  <td style={{ padding: "10px 20px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <span style={{ minWidth: 28, textAlign: "right", fontSize: 12, color: "#444", fontVariantNumeric: "tabular-nums" }}>{r.trend_score.toFixed(1)}</span>
                      <div style={{ height: 4, width: 40, borderRadius: 2, background: "rgba(0,0,0,0.07)" }}>
                        <div style={{ height: "100%", borderRadius: 2, background: "#3a7bd5", width: `${Math.min((r.trend_score / 30) * 100, 100)}%` }} />
                      </div>
                    </div>
                  </td>
                  <td style={{ padding: "10px 20px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <span style={{ minWidth: 28, textAlign: "right", fontSize: 12, color: "#444", fontVariantNumeric: "tabular-nums" }}>{r.momentum_score.toFixed(1)}</span>
                      <div style={{ height: 4, width: 40, borderRadius: 2, background: "rgba(0,0,0,0.07)" }}>
                        <div style={{ height: "100%", borderRadius: 2, background: "#b86e10", width: `${Math.min((r.momentum_score / 40) * 100, 100)}%` }} />
                      </div>
                    </div>
                  </td>
                  <td style={{ padding: "10px 20px", fontSize: 12, color: "#b83030", fontVariantNumeric: "tabular-nums" }}>{r.risk_penalty.toFixed(1)}</td>
                  <td style={{ padding: "10px 20px", fontSize: 12, fontWeight: 500, color: REGIME_COLOR[r.regime] ?? "#888" }}>{r.regime}</td>
                  <td style={{ padding: "10px 20px", fontSize: 12, fontWeight: 500, color: RISK_COLOR[r.risk_level] ?? "#888" }}>{r.risk_level}</td>
                  <td style={{ padding: "10px 20px", fontSize: 12, color: "#444", fontVariantNumeric: "tabular-nums" }}>{r.confidence}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* How Scores Work */}
      <div>
        <h2 style={{ fontSize: 16, fontWeight: 700, color: "#1a1a1a", margin: "0 0 16px" }}>
          How Scores Work
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          {[
            { icon: "📐", name: "Trend Score",     range: "0–30",    desc: "Measures price position relative to 20/50/200-day moving averages and 52-week range." },
            { icon: "🚀", name: "Momentum Score",  range: "0–40",    desc: "Captures return strength across 1D, 20D, 60D, 120D, 252D timeframes." },
            { icon: "⚠️", name: "Risk Penalty",    range: "0 to −10", desc: "Penalizes high volatility and extended drawdown from 52-week high." },
            { icon: "🎯", name: "Composite Score", range: "0–70",    desc: "Weighted combination of Trend, Momentum, and Risk. Higher = stronger signal." },
            { icon: "🌊", name: "Regime",          range: "Label",   desc: "Market condition (TRENDING / MIXED / RISK_OFF) derived from MA alignment and momentum." },
            { icon: "🔒", name: "Confidence",      range: "0–100",   desc: "Signal reliability score based on internal consistency of factor scores." },
          ].map(({ icon, name, range, desc }) => (
            <div key={name} style={{ background: "#fff", border: "1px solid rgba(0,0,0,0.09)", borderRadius: 14, padding: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <span style={{ fontSize: 16 }}>{icon}</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: "#1a1a1a" }}>{name}</span>
                <span style={{ marginLeft: "auto", fontSize: 11, color: "#888", fontFamily: "monospace" }}>{range}</span>
              </div>
              <p style={{ fontSize: 13, color: "#444", lineHeight: 1.6, margin: 0 }}>{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
