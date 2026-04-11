"use client";

import { useState, useMemo, useEffect, type ReactNode, type CSSProperties } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  AreaChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import type { Ranking, Decision } from "@/types/rankings";

const DECISION_STYLE: Record<Decision, { bg: string; color: string; textColor: string }> = {
  BUY:   { bg: "#e4f2eb", color: "#1a6e3e", textColor: "#2d7a52" },
  HOLD:  { bg: "#e4edf9", color: "#1a4a8a", textColor: "#1a5ca8" },
  WATCH: { bg: "#fef0e0", color: "#9a5c0a", textColor: "#b86e10" },
  AVOID: { bg: "#fde8e8", color: "#9a2020", textColor: "#b83030" },
};

function badgePill(decision: Decision): CSSProperties {
  const s = DECISION_STYLE[decision];
  return { background: s.bg, color: s.color, borderRadius: 100, fontSize: 11, fontWeight: 700, padding: "3px 12px", display: "inline-block" };
}

const REGIME_COLOR: Record<string, string> = {
  TRENDING: "#2d7a52",
  MIXED:    "#888888",
  RISK_OFF: "#b86e10",
};

const RISK_COLOR: Record<string, string> = {
  LOW:    "#2d7a52",
  MEDIUM: "#b86e10",
  HIGH:   "#b83030",
};

const TIME_RANGES = [
  { label: "1M",  days: 30  },
  { label: "3M",  days: 90  },
  { label: "6M",  days: 180 },
  { label: "1Y",  days: 365 },
  { label: "ALL", days: 9999 },
];

const MA_LINES = [
  { key: "ma30",  period: 30,  color: "#f59e0b", rgba: "rgba(245,158,11,0.12)",  label: "MA30"  },
  { key: "ma50",  period: 50,  color: "#3a7bd5", rgba: "rgba(58,123,213,0.12)",  label: "MA50"  },
  { key: "ma120", period: 120, color: "#8b5cf6", rgba: "rgba(139,92,246,0.12)",  label: "MA120" },
] as const;

type PriceRow = { date: string; open: number; high: number; low: number; close: number; volume: number };

function ScoreBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = Math.min(Math.abs(value) / max * 100, 100);
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: 12, color: "#444" }}>{label}</span>
        <span style={{ fontSize: 12, color: "#1a1a1a", fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>{value.toFixed(1)}</span>
      </div>
      <div style={{ height: 6, background: "rgba(0,0,0,0.07)", borderRadius: 3 }}>
        <div style={{ height: "100%", borderRadius: 3, background: color, width: `${pct}%` }} />
      </div>
    </div>
  );
}

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: { dataKey: string; value: number; color: string }[]; label?: string }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#fff", border: "1px solid rgba(0,0,0,0.09)", borderRadius: 8, padding: "8px 12px", fontSize: 12, color: "#1a1a1a", boxShadow: "0 2px 8px rgba(0,0,0,0.08)" }}>
      <p style={{ color: "#888", margin: "0 0 4px" }}>{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ fontVariantNumeric: "tabular-nums", color: p.color, margin: "2px 0" }}>
          {p.dataKey === "close" ? "" : p.dataKey.toUpperCase() + " "}${p.value?.toFixed(2) ?? "—"}
        </p>
      ))}
    </div>
  );
};

interface TickerDetails {
  name?: string;
  sic_description?: string;
  market_cap?: number;
  total_employees?: number;
  homepage_url?: string;
  description?: string;
}

function fmtCap(v: number) {
  if (v >= 1e12) return `$${(v / 1e12).toFixed(1)}T`;
  if (v >= 1e9)  return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6)  return `$${(v / 1e6).toFixed(0)}M`;
  return `$${v.toLocaleString()}`;
}

function fmtEmployees(v: number) {
  if (v >= 1000) return `${(v / 1000).toFixed(1)}K`;
  return v.toLocaleString();
}

function CompanyInfoCard({ ticker }: { ticker: string }) {
  const [info, setInfo] = useState<TickerDetails | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const polyTicker = ticker.replace("-", ".");
    const key = process.env.NEXT_PUBLIC_POLYGON_API_KEY;
    if (!key) return;
    fetch(`https://api.polygon.io/v3/reference/tickers/${polyTicker}?apiKey=${key}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d?.results) setInfo(d.results); })
      .catch(() => {});
  }, [ticker]);

  if (!info) return null;

  const fields: { label: string; value: string | ReactNode }[] = [];
  if (info.sic_description) fields.push({ label: "Industry",   value: info.sic_description });
  if (info.market_cap)      fields.push({ label: "Market Cap", value: fmtCap(info.market_cap) });
  if (info.total_employees) fields.push({ label: "Employees",  value: fmtEmployees(info.total_employees) });
  if (info.homepage_url) {
    const display = info.homepage_url.replace(/^https?:\/\//, "").replace(/\/$/, "");
    fields.push({
      label: "Website",
      value: (
        <a href={info.homepage_url} target="_blank" rel="noopener noreferrer" style={{ color: "#2d7a52", textDecoration: "none" }}>
          {display}
        </a>
      ),
    });
  }

  return (
    <div style={{ background: "#fff", border: "1px solid rgba(0,0,0,0.09)", borderRadius: 14, padding: "20px 24px", marginBottom: 24 }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
        <div style={{ minWidth: 0 }}>
          {info.name && <h2 style={{ fontSize: 15, fontWeight: 700, color: "#1a1a1a", margin: "0 0 8px" }}>{info.name}</h2>}
          {fields.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 20px" }}>
              {fields.map(({ label, value }) => (
                <div key={label} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
                  <span style={{ color: "#888" }}>{label}</span>
                  <span style={{ color: "#1a1a1a", fontWeight: 600 }}>{value}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      {info.description && (
        <div style={{ marginTop: 12 }}>
          <p className={expanded ? undefined : "line-clamp-3"} style={{ fontSize: 13, color: "#444", lineHeight: 1.6, margin: 0 }}>
            {info.description}
          </p>
          {info.description.length > 200 && (
            <button
              onClick={() => setExpanded(!expanded)}
              style={{ marginTop: 4, fontSize: 12, color: "#2d7a52", background: "none", border: "none", cursor: "pointer", padding: 0 }}
            >
              {expanded ? "Show less" : "Show more"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export function AssetDetailView({
  ranking,
  prices,
  allTickers,
}: {
  ranking: Ranking;
  prices: PriceRow[];
  allTickers: string[];
}) {
  const router = useRouter();
  const [range, setRange] = useState("3M");
  const [maVisible, setMaVisible] = useState<Record<string, boolean>>({ ma30: true, ma50: true, ma120: true });

  const filteredPrices = useMemo(() => {
    const selected = TIME_RANGES.find((r) => r.label === range)!;
    if (selected.days >= 9999) return prices;
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - selected.days);
    const cutoffStr = cutoff.toISOString().split("T")[0];
    return prices.filter((p) => p.date >= cutoffStr);
  }, [prices, range]);

  const firstClose = filteredPrices[0]?.close ?? 0;
  const lastClose  = filteredPrices[filteredPrices.length - 1]?.close ?? 0;
  const pctChange  = firstClose > 0 ? ((lastClose - firstClose) / firstClose) * 100 : 0;
  const isUp       = pctChange >= 0;
  const chartColor     = isUp ? "#2d7a52" : "#b83030";
  const chartFillColor = isUp ? "#e4f2eb"  : "#fde8e8";

  const chartData = useMemo(() => {
    const allCloses = prices.map((p) => p.close);
    const filteredStartIdx = filteredPrices.length > 0
      ? prices.findIndex((p) => p.date === filteredPrices[0].date)
      : 0;
    return filteredPrices.map((p, i) => {
      const globalIdx = filteredStartIdx + i;
      const row: Record<string, number | null | string> = {
        date:  p.date.slice(0, 10),
        close: parseFloat(p.close.toFixed(2)),
      };
      for (const { key, period } of MA_LINES) {
        if (globalIdx >= period - 1) {
          const slice = allCloses.slice(globalIdx - period + 1, globalIdx + 1);
          row[key] = parseFloat((slice.reduce((a, b) => a + b, 0) / period).toFixed(2));
        } else {
          row[key] = null;
        }
      }
      return row;
    });
  }, [prices, filteredPrices]);

  const { combinedData, lastHistDate } = useMemo(() => {
    if (!chartData.length || !lastClose) return { combinedData: chartData, lastHistDate: "" };

    const driftDaily = ranking.momentum_score / 10000;
    const dailyVol   = Math.abs(ranking.risk_penalty) / 100 / Math.sqrt(252);
    const z          = 1.645;

    const lastDate    = new Date(filteredPrices[filteredPrices.length - 1]?.date ?? Date.now());
    const lastDateStr = chartData[chartData.length - 1]?.date as string;

    const forecastPoints = [10, 20, 30, 45, 60, 75, 90].map((t) => {
      const center = lastClose * (1 + driftDaily * t);
      const spread = dailyVol * Math.sqrt(t) * z;
      const futureDate = new Date(lastDate);
      futureDate.setDate(futureDate.getDate() + t);
      return {
        date:      futureDate.toISOString().split("T")[0].slice(0, 10),
        close:     null as number | null,
        fanUpper:  parseFloat((center * (1 + spread)).toFixed(2)),
        fanLower:  parseFloat((center * (1 - spread)).toFixed(2)),
        fanCenter: parseFloat(center.toFixed(2)),
        ma30: null, ma50: null, ma120: null,
      };
    });

    const bridge = {
      ...chartData[chartData.length - 1],
      fanUpper: lastClose, fanLower: lastClose, fanCenter: lastClose,
    };
    const histWithFan = chartData.slice(0, -1).map((d) => ({
      ...d,
      fanUpper: null as number | null,
      fanLower: null as number | null,
      fanCenter: null as number | null,
    }));

    return { combinedData: [...histWithFan, bridge, ...forecastPoints], lastHistDate: lastDateStr };
  }, [chartData, lastClose, ranking, filteredPrices]);

  const fanColor = ranking.decision === "BUY" ? "#2d7a52"
    : ranking.decision === "AVOID" ? "#b83030"
    : "#b86e10";

  const decStyle = DECISION_STYLE[ranking.decision];

  return (
    <div style={{ background: "#f5f4f0", minHeight: "100vh", fontFamily: "Nunito, sans-serif" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "32px 40px" }}>

        {/* Back link */}
        <Link href="/dashboard" style={{ fontSize: 13, color: "#444", textDecoration: "none", display: "block", marginBottom: 16 }}>
          ← Market Overview
        </Link>

        {/* Asset header */}
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-start", justifyContent: "space-between", gap: 16, marginBottom: 24 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <select
              value={ranking.ticker}
              onChange={(e) => router.push(`/asset/${e.target.value}`)}
              style={{ background: "#fff", border: "1px solid rgba(0,0,0,0.12)", borderRadius: 8, color: "#1a1a1a", fontSize: 14, fontWeight: 600, padding: "8px 12px", cursor: "pointer" }}
            >
              {[...new Set(allTickers)].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <div>
              <h1 style={{ fontSize: 32, fontWeight: 700, color: "#1a1a1a", margin: 0 }}>{ranking.ticker}</h1>
              <p style={{ fontSize: 12, color: "#888", margin: "4px 0 0" }}>
                {ranking.asset_type.toUpperCase()} · Rank #{ranking.rank_overall}
              </p>
            </div>
            <span style={badgePill(ranking.decision)}>{ranking.decision}</span>
          </div>
          <div style={{ textAlign: "right" }}>
            <p style={{ fontSize: 32, fontWeight: 700, color: "#1a1a1a", margin: 0, fontVariantNumeric: "tabular-nums" }}>${lastClose.toFixed(2)}</p>
            <p style={{ fontSize: 13, fontVariantNumeric: "tabular-nums", margin: "4px 0 0", color: isUp ? "#2d7a52" : "#b83030" }}>
              {isUp ? "▲" : "▼"} {Math.abs(pctChange).toFixed(2)}% ({range})
            </p>
          </div>
        </div>

        <CompanyInfoCard ticker={ranking.ticker} />

        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 24 }}>
          {/* Left: chart + OHLCV */}
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>

            {/* Chart card */}
            <div style={{ background: "#fff", border: "1px solid rgba(0,0,0,0.09)", borderRadius: 14, padding: "20px 24px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                <h2 style={{ fontSize: 14, fontWeight: 700, color: "#1a1a1a", margin: 0 }}>Price History</h2>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  {/* MA toggles */}
                  <div style={{ display: "flex", gap: 4 }}>
                    {MA_LINES.map(({ key, label, color, rgba }) => (
                      <button
                        key={key}
                        onClick={() => setMaVisible((prev) => ({ ...prev, [key]: !prev[key] }))}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 5,
                          background: maVisible[key] ? rgba : "transparent",
                          color:      maVisible[key] ? color : "#888",
                          border:     maVisible[key] ? `1.5px solid ${color}` : "1px solid rgba(0,0,0,0.12)",
                          borderRadius: 100,
                          fontSize: 11,
                          fontWeight: 600,
                          padding: "3px 10px",
                          cursor: "pointer",
                        }}
                      >
                        <span style={{ width: 16, height: 3, borderRadius: 2, background: color, display: "inline-block", opacity: maVisible[key] ? 1 : 0.4 }} />
                        {label}
                      </button>
                    ))}
                  </div>
                  <div style={{ width: 1, height: 16, background: "rgba(0,0,0,0.1)" }} />
                  {/* Time range */}
                  <div style={{ display: "flex", gap: 2 }}>
                    {TIME_RANGES.map((r) => (
                      <button
                        key={r.label}
                        onClick={() => setRange(r.label)}
                        style={{
                          background: range === r.label ? "#1a1a1a" : "transparent",
                          color:      range === r.label ? "#fff"    : "#888",
                          borderRadius: 100,
                          fontSize: 12,
                          padding: "3px 10px",
                          border: "none",
                          cursor: "pointer",
                        }}
                      >
                        {r.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={combinedData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor={chartFillColor} stopOpacity={1} />
                      <stop offset="95%" stopColor={chartFillColor} stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="fanGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%"   stopColor={fanColor} stopOpacity={0.1} />
                      <stop offset="100%" stopColor={fanColor} stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: "#aaa", fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                    interval="preserveStartEnd"
                    tickFormatter={(v) => v.slice(5).replace("-", "/")}
                  />
                  <YAxis
                    tick={{ fill: "#aaa", fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => `$${v}`}
                    width={56}
                    domain={["auto", "auto"]}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="close"
                    stroke={chartColor}
                    strokeWidth={1.5}
                    fill="url(#chartGrad)"
                    dot={false}
                  />
                  {MA_LINES.map(({ key, color }) =>
                    maVisible[key] ? (
                      <Line
                        key={key}
                        type="monotone"
                        dataKey={key}
                        stroke={color}
                        strokeWidth={1}
                        strokeDasharray="4 3"
                        dot={false}
                        connectNulls={false}
                      />
                    ) : null
                  )}
                  <Area type="monotone" dataKey="fanUpper" stroke="none" fill="url(#fanGrad)" dot={false} connectNulls={false} />
                  <Area type="monotone" dataKey="fanLower" stroke="none" fill="#f5f4f0"       dot={false} connectNulls={false} />
                  <Line  type="monotone" dataKey="fanCenter" stroke={fanColor} strokeWidth={1} strokeDasharray="6 4" dot={false} connectNulls={false} />
                  {lastHistDate && (
                    <ReferenceLine x={lastHistDate} stroke="rgba(0,0,0,0.15)" strokeDasharray="3 3" strokeWidth={1} />
                  )}
                </AreaChart>
              </ResponsiveContainer>
              <p style={{ marginTop: 8, fontSize: 11, color: "#aaa", textAlign: "right" }}>
                Based on historical volatility. Not a price target.
              </p>
            </div>

            {/* OHLCV summary */}
            {filteredPrices.length > 0 && (() => {
              const last = filteredPrices[filteredPrices.length - 1];
              const hi   = Math.max(...filteredPrices.map(p => p.high));
              const lo   = Math.min(...filteredPrices.map(p => p.low));
              return (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
                  {[
                    { label: "Open",   val: `$${last.open.toFixed(2)}`          },
                    { label: "High",   val: `$${hi.toFixed(2)}`                 },
                    { label: "Low",    val: `$${lo.toFixed(2)}`                 },
                    { label: "Volume", val: (last.volume / 1e6).toFixed(1) + "M" },
                  ].map(({ label, val }) => (
                    <div key={label} style={{ background: "#fafaf8", border: "1px solid rgba(0,0,0,0.07)", borderRadius: 10, padding: "12px 16px" }}>
                      <p style={{ fontSize: 11, color: "#888", textTransform: "uppercase", letterSpacing: "0.5px", margin: "0 0 4px" }}>{label}</p>
                      <p style={{ fontSize: 18, fontWeight: 700, color: "#1a1a1a", margin: 0, fontVariantNumeric: "tabular-nums" }}>{val}</p>
                    </div>
                  ))}
                </div>
              );
            })()}
          </div>

          {/* Right: factor panels */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

            {/* Factor Score */}
            <div style={{ background: "#fff", border: "1px solid rgba(0,0,0,0.09)", borderRadius: 14, padding: "20px 24px" }}>
              <p style={{ fontSize: 11, color: "#888", textTransform: "uppercase", letterSpacing: "0.5px", margin: "0 0 12px" }}>Factor Score</p>
              <div style={{ display: "flex", alignItems: "flex-end", gap: 8, marginBottom: 16 }}>
                <span style={{ fontSize: 32, fontWeight: 700, color: "#1a1a1a", lineHeight: 1, fontVariantNumeric: "tabular-nums" }}>{ranking.composite_score.toFixed(1)}</span>
                <span style={{ fontSize: 16, color: "#888", marginBottom: 2 }}>/ 70</span>
              </div>
              <ScoreBar label="Trend"    value={ranking.trend_score}            max={30} color="#3a7bd5" />
              <ScoreBar label="Momentum" value={ranking.momentum_score}         max={40} color="#b86e10" />
              <ScoreBar label="Risk"     value={Math.abs(ranking.risk_penalty)} max={10} color="#b83030" />
            </div>

            {/* Signal Details */}
            <div style={{ background: "#fff", border: "1px solid rgba(0,0,0,0.09)", borderRadius: 14, padding: "20px 24px" }}>
              <p style={{ fontSize: 11, color: "#888", textTransform: "uppercase", letterSpacing: "0.5px", margin: "0 0 12px" }}>Signal Details</p>
              {[
                { label: "Confidence", val: `${ranking.confidence}%`,   color: "#1a1a1a" },
                { label: "Regime",     val: ranking.regime,              color: REGIME_COLOR[ranking.regime] ?? "#444" },
                { label: "Risk Level", val: ranking.risk_level,          color: RISK_COLOR[ranking.risk_level] ?? "#444" },
                { label: "Horizon",    val: `${ranking.horizon_days}d`,  color: "#1a1a1a" },
                { label: "Snapshot",   val: ranking.snapshot_date,       color: "#444" },
              ].map(({ label, val, color }) => (
                <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                  <span style={{ fontSize: 13, color: "#444" }}>{label}</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color }}>{val}</span>
                </div>
              ))}
              <div style={{ marginTop: 12, height: 6, background: "#e4edf9", borderRadius: 3 }}>
                <div style={{ height: "100%", borderRadius: 3, background: "#3a7bd5", width: `${ranking.confidence}%` }} />
              </div>
            </div>

            {/* Why DECISION? */}
            <div style={{ background: "#fff", border: "1px solid rgba(0,0,0,0.09)", borderRadius: 14, padding: "20px 24px" }}>
              <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", color: decStyle.textColor, margin: "0 0 12px" }}>
                Why {ranking.decision}?
              </p>
              <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {(() => {
                  const reasons: { text: string; weight: number }[] = [];
                  const rp = Math.abs(ranking.risk_penalty);
                  if (ranking.trend_score > 25)     reasons.push({ text: "Trend is strong — price is trading above key moving averages", weight: ranking.trend_score });
                  if (ranking.trend_score < 15)     reasons.push({ text: "Trend is weak — price is below key moving averages", weight: 30 - ranking.trend_score });
                  if (ranking.momentum_score > 30)  reasons.push({ text: "Momentum is accelerating across multiple timeframes", weight: ranking.momentum_score });
                  if (ranking.momentum_score < 15)  reasons.push({ text: "Momentum is fading — recent returns are underperforming", weight: 40 - ranking.momentum_score });
                  if (rp < 5)                       reasons.push({ text: "Volatility is contained — drawdown risk is low", weight: 10 - rp });
                  if (rp > 7)                       reasons.push({ text: "Elevated volatility — price has pulled back significantly from highs", weight: rp });
                  if (ranking.confidence >= 70)     reasons.push({ text: "Signal confidence is high — factors are broadly aligned", weight: ranking.confidence / 10 });
                  if (ranking.confidence < 40)      reasons.push({ text: "Mixed signals — factor alignment is weak", weight: (100 - ranking.confidence) / 10 });
                  if (ranking.regime === "TRENDING") reasons.push({ text: "Market regime is trending — conditions favor momentum", weight: 7 });
                  if (ranking.regime === "RISK_OFF") reasons.push({ text: "Market regime is risk-off — caution advised", weight: 7 });
                  return reasons
                    .sort((a, b) => b.weight - a.weight)
                    .slice(0, 3)
                    .map(({ text }) => (
                      <li key={text} style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: 13, color: "#444", lineHeight: 1.6, marginBottom: 8 }}>
                        <span style={{ color: "#ccc", marginTop: 2 }}>•</span>
                        {text}
                      </li>
                    ));
                })()}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
