import { createClient } from "@supabase/supabase-js";
import type { Ranking } from "@/types/rankings";
import { AssetDetailView } from "./asset-detail-view";
import { notFound } from "next/navigation";

async function getAssetData(ticker: string) {
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );

  const [rankingRes, priceRes, allRankingsRes] = await Promise.all([
    supabase
      .from("rankings")
      .select("*")
      .eq("ticker", ticker)
      .single(),
    supabase
      .from("stock_prices")
      .select("date, open, high, low, close, volume")
      .eq("ticker", ticker)
      .gte("date", new Date(Date.now() - 2 * 365 * 24 * 60 * 60 * 1000).toISOString().split("T")[0])
      .order("date", { ascending: true })
      .limit(600),
    supabase
      .from("rankings")
      .select("ticker")
      .order("rank_overall", { ascending: true }),
  ]);

  if (rankingRes.error || !rankingRes.data) return null;

  return {
    ranking: rankingRes.data as Ranking,
    prices: (priceRes.data ?? []) as { date: string; open: number; high: number; low: number; close: number; volume: number }[],
    allTickers: (allRankingsRes.data ?? []).map((r: { ticker: string }) => r.ticker),
  };
}

export default async function AssetPage({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker } = await params;
  const data = await getAssetData(ticker.toUpperCase());
  if (!data) notFound();

  return <AssetDetailView {...data} />;
}
