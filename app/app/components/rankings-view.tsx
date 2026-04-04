"use client";

import { useState } from "react";
import Link from "next/link";
import type { Ranking, Decision } from "@/types/rankings";

const D_COLOR: Record<Decision, { badge: string; text: string; bar: string }> = {
  BUY:   { badge: "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30", text: "text-emerald-400", bar: "bg-emerald-500" },
  HOLD:  { badge: "bg-sky-500/15 text-sky-400 ring-1 ring-sky-500/30",             text: "text-sky-400",    bar: "bg-sky-500"     },
  WATCH: { badge: "bg-amber-500/15 text-amber-400 ring-1 ring-amber-500/30",       text: "text-amber-400", bar: "bg-amber-500"   },
  AVOID: { badge: "bg-red-500/15 text-red-400 ring-1 ring-red-500/30",             text: "text-red-400",   bar: "bg-red-500"     },
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

function ScoreBar({ value, max = 70 }: { value: number; max?: number }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="flex items-center gap-2">
      <span className="w-10 text-right font-mono text-xs text-slate-300">{value.toFixed(1)}</span>
      <div className="h-1.5 w-20 rounded-full bg-slate-700">
        <div className="h-full rounded-full bg-slate-400" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function RankingsView({
  rankings,
  counts,
}: {
  rankings: Ranking[];
  counts: Record<Decision, number>;
}) {
  const [filter, setFilter] = useState<Decision | "ALL">("ALL");
  const topBuys = rankings.filter((r) => r.decision === "BUY").slice(0, 5);
  const filtered = filter === "ALL" ? rankings : rankings.filter((r) => r.decision === filter);

  return (
    <div className="space-y-6">
      {/* KPI row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {(["BUY", "HOLD", "WATCH", "AVOID"] as Decision[]).map((d) => (
          <div
            key={d}
            onClick={() => setFilter(filter === d ? "ALL" : d)}
            className={`cursor-pointer rounded-xl border p-4 transition-all ${
              filter === d
                ? "border-slate-500 bg-slate-800"
                : "border-slate-800 bg-slate-900 hover:border-slate-600"
            }`}
          >
            <p className="text-xs font-medium tracking-widest text-slate-500">{d}</p>
            <p className={`mt-1 text-3xl font-bold tabular-nums ${D_COLOR[d].text}`}>
              {counts[d]}
            </p>
            <p className="mt-1 text-xs text-slate-600">
              {((counts[d] / rankings.length) * 100).toFixed(0)}% of universe
            </p>
          </div>
        ))}
      </div>

      {/* Top 5 BUY cards */}
      {filter === "ALL" && (
        <div>
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">
            Top opportunities
          </h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            {topBuys.map((r) => (
              <Link
                key={r.source_ticker}
                href={`/asset/${r.ticker}`}
                className="rounded-xl border border-slate-800 bg-slate-900 p-4 hover:border-emerald-500/40 hover:bg-slate-800 transition-all"
              >
                <div className="flex items-start justify-between">
                  <span className="text-sm font-bold text-slate-100">{r.ticker}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded font-semibold ${D_COLOR.BUY.badge}`}>
                    BUY
                  </span>
                </div>
                <p className="mt-3 text-2xl font-bold tabular-nums text-slate-100">
                  {r.composite_score.toFixed(1)}
                </p>
                <p className="text-xs text-slate-500">composite</p>
                <div className="mt-3 h-1 w-full rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-emerald-500"
                    style={{ width: `${(r.composite_score / 70) * 100}%` }}
                  />
                </div>
                <p className={`mt-2 text-xs ${REGIME_COLOR[r.regime] ?? "text-slate-400"}`}>
                  {r.regime}
                </p>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Rankings table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
          <h2 className="text-sm font-semibold text-slate-300">
            {filter === "ALL" ? `All assets · ${rankings.length}` : `${filter} · ${filtered.length}`}
          </h2>
          {filter !== "ALL" && (
            <button
              onClick={() => setFilter("ALL")}
              className="text-xs text-slate-500 hover:text-slate-300"
            >
              Clear filter ✕
            </button>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800">
                {["#","Ticker","Signal","Score","Trend","Mom","Risk","Regime","Risk Lvl","Conf"].map((h) => (
                  <th key={h} className="px-3 py-2.5 text-left text-xs font-medium text-slate-500 first:pl-4 last:pr-4">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr
                  key={r.source_ticker}
                  className="border-b border-slate-800/50 hover:bg-slate-800/50 transition-colors"
                >
                  <td className="pl-4 py-2.5 font-mono text-xs text-slate-500 w-8">{r.rank_overall}</td>
                  <td className="px-3 py-2.5">
                    <Link href={`/asset/${r.ticker}`} className="font-bold text-slate-100 hover:text-sky-400 transition-colors">
                      {r.ticker}
                    </Link>
                  </td>
                  <td className="px-3 py-2.5">
                    <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-semibold ${D_COLOR[r.decision].badge}`}>
                      {r.decision}
                    </span>
                  </td>
                  <td className="px-3 py-2.5">
                    <ScoreBar value={r.composite_score} />
                  </td>
                  <td className="px-3 py-2.5 font-mono text-xs text-slate-300">{r.trend_score.toFixed(1)}</td>
                  <td className="px-3 py-2.5 font-mono text-xs text-slate-300">{r.momentum_score.toFixed(1)}</td>
                  <td className="px-3 py-2.5 font-mono text-xs text-red-400">{r.risk_penalty.toFixed(1)}</td>
                  <td className={`px-3 py-2.5 text-xs font-medium ${REGIME_COLOR[r.regime] ?? "text-slate-400"}`}>{r.regime}</td>
                  <td className={`px-3 py-2.5 text-xs font-medium ${RISK_COLOR[r.risk_level] ?? "text-slate-400"}`}>{r.risk_level}</td>
                  <td className="pr-4 py-2.5 font-mono text-xs text-slate-300">{r.confidence}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
