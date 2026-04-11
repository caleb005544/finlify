import { createClient } from "@supabase/supabase-js";
import type { Ranking, Decision } from "@/types/rankings";
import { RankingsView } from "../components/rankings-view";

export const metadata = {
  title: "Finlify — Market Overview",
  description: "Daily asset rankings powered by quantitative factor analysis",
};

async function getRankings(): Promise<Ranking[]> {
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
  const { data: latestSnapshot } = await supabase
    .from("rankings")
    .select("snapshot_date")
    .order("snapshot_date", { ascending: false })
    .limit(1)
    .single();
  const { data, error } = await supabase
    .from("rankings")
    .select("*")
    .eq("snapshot_date", latestSnapshot?.snapshot_date)
    .order("rank_overall", { ascending: true });
  if (error) throw new Error(error.message);
  return (data ?? []) as Ranking[];
}

export default async function Home() {
  const rankings = await getRankings();
  const counts = { BUY: 0, HOLD: 0, WATCH: 0, AVOID: 0 };
  for (const r of rankings) counts[r.decision as Decision]++;

  return <RankingsView rankings={rankings} counts={counts} />;
}
