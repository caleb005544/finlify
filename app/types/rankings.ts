export type Decision = 'BUY' | 'HOLD' | 'WATCH' | 'AVOID'
export type Regime = 'TRENDING' | 'MIXED' | 'RISK_OFF'
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH'

export interface Ranking {
  id: number
  source_ticker: string
  ticker: string
  asset_type: string
  snapshot_date: string
  composite_score: number
  trend_score: number
  momentum_score: number
  risk_penalty: number
  decision: Decision
  rank_overall: number
  confidence: number
  regime: Regime
  risk_level: RiskLevel
  horizon_days: number
}
