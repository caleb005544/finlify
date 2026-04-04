import { createClient } from "@supabase/supabase-js";
import type { Ranking, Decision } from "@/types/rankings";
import { RankingsView } from "./components/rankings-view";

export const metadata = {
  title: "Finlify — Market Overview",
  description: "Daily asset rankings powered by quantitative factor analysis",
};

async function getRankings(): Promise<Ranking[]> {
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
  const { data, error } = await supabase
    .from("rankings")
    .select("*")
    .order("rank_overall", { ascending: true });
  if (error) throw new Error(error.message);
  return (data ?? []) as Ranking[];
}

export default async function Home() {
  const rankings = await getRankings();
  const counts = { BUY: 0, HOLD: 0, WATCH: 0, AVOID: 0 };
  for (const r of rankings) counts[r.decision as Decision]++;

  const now = new Date();
  const dateStr = now.toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" });

  return (
    <div style={{ background: "#0a0e1a", minHeight: "100vh", color: "#e2e8f0" }}>
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">
              Finlify
            </h1>
            <p className="text-sm text-slate-500 mt-0.5">Market Overview · {dateStr}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-slate-600">Universe</p>
            <p className="text-lg font-bold tabular-nums text-slate-300">{rankings.length} assets</p>
          </div>
        </div>
        <RankingsView rankings={rankings} counts={counts} />
      </div>
    </div>
  );
}
