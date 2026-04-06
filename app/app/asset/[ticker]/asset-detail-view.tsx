"use client";

import { useState, useMemo, useEffect, type ReactNode } from "react";
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

const D_COLOR: Record<Decision, { badge: string; text: string }> = {
  BUY:   { badge: "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30", text: "text-emerald-400" },
  HOLD:  { badge: "bg-sky-500/15 text-sky-400 ring-1 ring-sky-500/30",             text: "text-sky-400"    },
  WATCH: { badge: "bg-amber-500/15 text-amber-400 ring-1 ring-amber-500/30",       text: "text-amber-400" },
  AVOID: { badge: "bg-red-500/15 text-red-400 ring-1 ring-red-500/30",             text: "text-red-400"   },
};

const REGIME_COLOR: Record<string, string> = {
  TRENDING: "text-emerald-400",
  MIXED:    "text-slate-400",
  RISK_OFF: "text-red-400",
};

const RISK_COLOR: Record<string, string> = {
  LOW:    "text-emerald-400",
  MEDIUM: "text-amber-400",
  HIGH:   "text-red-400",
};

const TIME_RANGES = [
  { label: "1M",  days: 30  },
  { label: "3M",  days: 90  },
  { label: "6M",  days: 180 },
  { label: "1Y",  days: 365 },
  { label: "ALL", days: 9999 },
];

const MA_LINES = [
  { key: "ma30",  period: 30,  color: "#f59e0b", label: "MA30"  },
  { key: "ma50",  period: 50,  color: "#3b82f6", label: "MA50"  },
  { key: "ma120", period: 120, color: "#a855f7", label: "MA120" },
] as const;

type PriceRow = { date: string; open: number; high: number; low: number; close: number; volume: number };

function ScoreBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = Math.min(Math.abs(value) / max * 100, 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-slate-500">{label}</span>
        <span className="font-mono text-slate-300">{value.toFixed(1)}</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-slate-800">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: { dataKey: string; value: number; color: string }[]; label?: string }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} className="font-mono" style={{ color: p.color }}>
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
  if (v >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(0)}M`;
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
  if (info.sic_description) fields.push({ label: "Industry", value: info.sic_description });
  if (info.market_cap) fields.push({ label: "Market Cap", value: fmtCap(info.market_cap) });
  if (info.total_employees) fields.push({ label: "Employees", value: fmtEmployees(info.total_employees) });
  if (info.homepage_url) {
    const display = info.homepage_url.replace(/^https?:\/\//, "").replace(/\/$/, "");
    fields.push({
      label: "Website",
      value: (
        <a href={info.homepage_url} target="_blank" rel="noopener noreferrer" className="text-sky-400 hover:text-sky-300 transition-colors">
          {display}
        </a>
      ),
    });
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 mb-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          {info.name && <h2 className="text-sm font-semibold text-slate-200 truncate">{info.name}</h2>}
          {fields.length > 0 && (
            <div className="flex flex-wrap gap-x-5 gap-y-1 mt-2">
              {fields.map(({ label, value }) => (
                <div key={label} className="flex items-center gap-1.5 text-xs">
                  <span className="text-slate-500">{label}</span>
                  <span className="text-slate-300">{value}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      {info.description && (
        <div className="mt-3">
          <p className={`text-xs leading-relaxed text-slate-400 ${expanded ? "" : "line-clamp-3"}`}>
            {info.description}
          </p>
          {info.description.length > 200 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="mt-1 text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
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
  const lastClose = filteredPrices[filteredPrices.length - 1]?.close ?? 0;
  const pctChange = firstClose > 0 ? ((lastClose - firstClose) / firstClose) * 100 : 0;
  const isUp = pctChange >= 0;
  const chartColor = isUp ? "#00c87a" : "#ff4d4d";

  const chartData = useMemo(() => {
    // Use full prices array for MA calculation, then slice to filtered range
    const allCloses = prices.map((p) => p.close);
    const filteredStartIdx = filteredPrices.length > 0
      ? prices.findIndex((p) => p.date === filteredPrices[0].date)
      : 0;

    const result = filteredPrices.map((p, i) => {
      const globalIdx = filteredStartIdx + i;
      const row: Record<string, number | null | string> = {
        date: p.date.slice(0, 10),
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
    return result;
  }, [prices, filteredPrices]);

  // Forecast fan chart
  const { combinedData, lastHistDate } = useMemo(() => {
    if (!chartData.length || !lastClose) return { combinedData: chartData, lastHistDate: "" };

    const driftDaily = ranking.momentum_score / 10000;
    const dailyVol = Math.abs(ranking.risk_penalty) / 100 / Math.sqrt(252);
    const z = 1.645; // 90% CI

    const lastDate = new Date(filteredPrices[filteredPrices.length - 1]?.date ?? Date.now());
    const lastDateStr = chartData[chartData.length - 1]?.date as string;

    // Generate forecast points at day 10, 20, 30, 45, 60, 75, 90
    const forecastDays = [10, 20, 30, 45, 60, 75, 90];
    const forecastPoints = forecastDays.map((t) => {
      const center = lastClose * (1 + driftDaily * t);
      const spread = dailyVol * Math.sqrt(t) * z;
      const futureDate = new Date(lastDate);
      futureDate.setDate(futureDate.getDate() + t);
      const dateStr = futureDate.toISOString().split("T")[0].slice(0, 10);
      return {
        date: dateStr,
        close: null as number | null,
        fanUpper: parseFloat((center * (1 + spread)).toFixed(2)),
        fanLower: parseFloat((center * (1 - spread)).toFixed(2)),
        fanCenter: parseFloat(center.toFixed(2)),
        ma30: null, ma50: null, ma120: null,
      };
    });

    // Bridge point: last historical point starts the fan
    const bridge = {
      ...chartData[chartData.length - 1],
      fanUpper: lastClose,
      fanLower: lastClose,
      fanCenter: lastClose,
    };

    // Historical points get null fan values
    const histWithFan = chartData.slice(0, -1).map((d) => ({
      ...d,
      fanUpper: null as number | null,
      fanLower: null as number | null,
      fanCenter: null as number | null,
    }));

    return {
      combinedData: [...histWithFan, bridge, ...forecastPoints],
      lastHistDate: lastDateStr,
    };
  }, [chartData, lastClose, ranking, filteredPrices]);

  const fanColor = ranking.decision === "BUY" ? "#00c87a"
    : ranking.decision === "AVOID" ? "#ff4d4d"
    : "#f59e0b";

  return (
    <div style={{ background: "#0a0e1a", minHeight: "100vh", color: "#e2e8f0" }}>
      <div className="mx-auto max-w-7xl px-4 py-8">

        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <Link href="/" className="text-slate-500 hover:text-slate-300 text-sm transition-colors">
            ← Market Overview
          </Link>
        </div>

        <div className="flex flex-wrap items-start justify-between gap-4 mb-8">
          <div className="flex items-center gap-4">
            {/* Stock selector */}
            <select
              value={ranking.ticker}
              onChange={(e) => router.push(`/asset/${e.target.value}`)}
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-slate-500"
            >
              {allTickers.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <div>
              <h1 className="text-3xl font-bold text-slate-100">{ranking.ticker}</h1>
              <p className="text-sm text-slate-500 mt-0.5">{ranking.asset_type.toUpperCase()} · Rank #{ranking.rank_overall}</p>
            </div>
            <span className={`px-3 py-1 rounded-lg text-sm font-bold ${D_COLOR[ranking.decision].badge}`}>
              {ranking.decision}
            </span>
          </div>
          <div className="text-right">
            <p className="text-3xl font-bold tabular-nums text-slate-100">${lastClose.toFixed(2)}</p>
            <p className={`text-sm font-mono mt-0.5 ${isUp ? "text-emerald-400" : "text-red-400"}`}>
              {isUp ? "▲" : "▼"} {Math.abs(pctChange).toFixed(2)}% ({range})
            </p>
          </div>
        </div>

        <CompanyInfoCard ticker={ranking.ticker} />

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Left: chart */}
          <div className="lg:col-span-2 space-y-6">

            {/* Chart card */}
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-slate-400">Price History</h2>
                <div className="flex items-center gap-3">
                  {/* MA toggles */}
                  <div className="flex gap-1">
                    {MA_LINES.map(({ key, label, color }) => (
                      <button
                        key={key}
                        onClick={() => setMaVisible((prev) => ({ ...prev, [key]: !prev[key] }))}
                        className={`px-2 py-1 rounded text-[10px] font-bold transition-all border ${
                          maVisible[key]
                            ? "border-current opacity-100"
                            : "border-slate-700 opacity-40"
                        }`}
                        style={{ color }}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <div className="w-px h-4 bg-slate-700" />
                  {/* Time range */}
                  <div className="flex gap-1">
                    {TIME_RANGES.map((r) => (
                      <button
                        key={r.label}
                        onClick={() => setRange(r.label)}
                        className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
                          range === r.label
                            ? "bg-slate-700 text-slate-100"
                            : "text-slate-500 hover:text-slate-300"
                        }`}
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
                      <stop offset="5%" stopColor={chartColor} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={chartColor} stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="fanGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={fanColor} stopOpacity={0.15} />
                      <stop offset="100%" stopColor={fanColor} stopOpacity={0.03} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: "#64748b", fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    interval="preserveStartEnd"
                    tickFormatter={(v) => v.slice(5)}
                  />
                  <YAxis
                    tick={{ fill: "#64748b", fontSize: 11 }}
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
                  {/* Forecast fan */}
                  <Area
                    type="monotone"
                    dataKey="fanUpper"
                    stroke="none"
                    fill="url(#fanGrad)"
                    dot={false}
                    connectNulls={false}
                  />
                  <Area
                    type="monotone"
                    dataKey="fanLower"
                    stroke="none"
                    fill="#0a0e1a"
                    dot={false}
                    connectNulls={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="fanCenter"
                    stroke={fanColor}
                    strokeWidth={1}
                    strokeDasharray="6 4"
                    dot={false}
                    connectNulls={false}
                  />
                  {lastHistDate && (
                    <ReferenceLine
                      x={lastHistDate}
                      stroke="#475569"
                      strokeDasharray="3 3"
                      strokeWidth={1}
                    />
                  )}
                </AreaChart>
              </ResponsiveContainer>
              <p className="mt-2 text-[10px] text-slate-600 text-right">
                Based on historical volatility. Not a price target.
              </p>
            </div>

            {/* OHLCV summary */}
            {filteredPrices.length > 0 && (() => {
              const last = filteredPrices[filteredPrices.length - 1];
              const hi = Math.max(...filteredPrices.map(p => p.high));
              const lo = Math.min(...filteredPrices.map(p => p.low));
              return (
                <div className="grid grid-cols-4 gap-3">
                  {[
                    { label: "Open",     val: `$${last.open.toFixed(2)}`  },
                    { label: "High",     val: `$${hi.toFixed(2)}`         },
                    { label: "Low",      val: `$${lo.toFixed(2)}`         },
                    { label: "Volume",   val: (last.volume / 1e6).toFixed(1) + "M" },
                  ].map(({ label, val }) => (
                    <div key={label} className="rounded-lg border border-slate-800 bg-slate-900 p-3">
                      <p className="text-xs text-slate-500">{label}</p>
                      <p className="mt-1 font-mono text-sm font-semibold text-slate-200">{val}</p>
                    </div>
                  ))}
                </div>
              );
            })()}
          </div>

          {/* Right: factor scores */}
          <div className="space-y-4">
            {/* Composite score */}
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Factor Score</p>
              <div className="flex items-end gap-3 mb-4">
                <p className="text-4xl font-bold tabular-nums text-slate-100">{ranking.composite_score.toFixed(1)}</p>
                <p className="text-slate-500 text-sm mb-1">/ 70</p>
              </div>
              <div className="space-y-3">
                <ScoreBar label="Trend"    value={ranking.trend_score}     max={30} color="bg-sky-500"     />
                <ScoreBar label="Momentum" value={ranking.momentum_score}  max={40} color="bg-violet-500"  />
                <ScoreBar label="Risk"     value={Math.abs(ranking.risk_penalty)} max={10} color="bg-red-500" />
              </div>
            </div>

            {/* Signal details */}
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 space-y-3">
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">Signal Details</p>
              {[
                { label: "Confidence",  val: `${ranking.confidence}%`,  cls: "text-slate-200" },
                { label: "Regime",      val: ranking.regime,            cls: REGIME_COLOR[ranking.regime] ?? "text-slate-400" },
                { label: "Risk Level",  val: ranking.risk_level,        cls: RISK_COLOR[ranking.risk_level] ?? "text-slate-400" },
                { label: "Horizon",     val: `${ranking.horizon_days}d`, cls: "text-slate-200" },
                { label: "Snapshot",    val: ranking.snapshot_date,     cls: "text-slate-400" },
              ].map(({ label, val, cls }) => (
                <div key={label} className="flex justify-between items-center">
                  <span className="text-xs text-slate-500">{label}</span>
                  <span className={`text-xs font-semibold ${cls}`}>{val}</span>
                </div>
              ))}
            </div>

            {/* Confidence bar */}
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Signal Confidence</p>
              <div className="flex items-center gap-3">
                <div className="flex-1 h-2 rounded-full bg-slate-800">
                  <div
                    className={`h-full rounded-full ${D_COLOR[ranking.decision].badge.includes("emerald") ? "bg-emerald-500" : D_COLOR[ranking.decision].badge.includes("sky") ? "bg-sky-500" : D_COLOR[ranking.decision].badge.includes("amber") ? "bg-amber-500" : "bg-red-500"}`}
                    style={{ width: `${ranking.confidence}%` }}
                  />
                </div>
                <span className="text-sm font-bold tabular-nums text-slate-200">{ranking.confidence}%</span>
              </div>
            </div>

            {/* Why DECISION? */}
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <p className={`text-xs font-semibold uppercase tracking-widest mb-3 ${D_COLOR[ranking.decision].text}`}>
                Why {ranking.decision}?
              </p>
              <ul className="space-y-2">
                {(() => {
                  const reasons: { text: string; weight: number }[] = [];
                  const rp = Math.abs(ranking.risk_penalty);
                  if (ranking.trend_score > 25)    reasons.push({ text: "Trend is strong — price is trading above key moving averages", weight: ranking.trend_score });
                  if (ranking.trend_score < 15)    reasons.push({ text: "Trend is weak — price is below key moving averages", weight: 30 - ranking.trend_score });
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
                      <li key={text} className="flex items-start gap-2 text-xs leading-relaxed text-slate-400">
                        <span className="mt-0.5 text-slate-600">•</span>
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
