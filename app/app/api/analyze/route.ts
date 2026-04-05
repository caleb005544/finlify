import { NextRequest, NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const {
      ticker,
      composite_score,
      trend_score,
      momentum_score,
      risk_penalty,
      decision,
      regime,
      risk_level,
    } = body;

    const prompt = `You are a senior financial analyst. Analyze the stock/ETF "${ticker}" using real-time web data.

Current Finlify factor scores:
- Composite Score: ${composite_score}/70
- Trend Score: ${trend_score}/30
- Momentum Score: ${momentum_score}/40
- Risk Penalty: ${risk_penalty}/10
- Signal: ${decision}
- Regime: ${regime}
- Risk Level: ${risk_level}

Search the web for the latest news, price action, and fundamentals for ${ticker}.

Return your analysis as a JSON object with exactly these 5 fields (each field should be 2-3 sentences):
{
  "technical": "Analysis of price trends, moving averages, support/resistance levels based on current data",
  "fundamental": "Key financial metrics, earnings, revenue, valuation based on latest available data",
  "market": "Recent news, sector trends, analyst sentiment affecting this asset",
  "macro": "Macro environment impact - interest rates, inflation, geopolitical factors relevant to this asset",
  "summary": "Overall assessment combining all factors with the Finlify signal context"
}

Return ONLY the JSON object, no markdown formatting, no code blocks.`;

    const response = await client.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 1024,
      tools: [
        {
          type: "web_search_20250305" as const,
          name: "web_search",
          max_uses: 3,
        },
      ],
      messages: [{ role: "user", content: prompt }],
    });

    // Extract text from response
    let text = "";
    for (const block of response.content) {
      if (block.type === "text") {
        text += block.text;
      }
    }

    // Parse the JSON from response
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      return NextResponse.json(
        { error: "Failed to parse analysis response" },
        { status: 500 }
      );
    }

    const analysis = JSON.parse(jsonMatch[0]);
    return NextResponse.json(analysis);
  } catch (error) {
    console.error("Analysis error:", error);
    return NextResponse.json(
      { error: "Failed to generate analysis" },
      { status: 500 }
    );
  }
}
