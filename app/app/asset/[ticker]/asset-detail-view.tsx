"use client";

import { useState, useMemo } from "react";
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
                <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={chartColor} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={chartColor} stopOpacity={0} />
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
                </AreaChart>
              </ResponsiveContainer>
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
          </div>
        </div>
      </div>
    </div>
  );
}
