# Finlify Demo 上線 Roadmap

從目前狀態到可公開展示的 Demo，共分為 **4 個 Stage**。

---

## 現狀評估

| 面向 | 狀態 | 說明 |
|------|------|------|
| Policy 評分引擎 | ✅ 完成 | 邏輯完整、有完整測試 |
| Forecast Service | ✅ 完成 | 多模型路由、Runtime 控制完整 |
| Frontend 骨架 | ✅ 完成 | App Router、公開路由、Auth 流程架好 |
| 市場資料 | ❌ Mock | `/api/quotes` 和 `/api/history` 全為假資料 |
| 部署配置 | ❌ 未設定 | 無 Vercel / Fly.io 設定、無 CI/CD |
| Demo 保護機制 | ⚠️ 部分完成 | Basic Auth 程式碼存在但無環境設定 |
| 錯誤處理 / Loading UX | ⚠️ 未知 | 需要驗證邊緣案例 |

---

## Stage 1 — 接入真實資料層
> **目標**：讓股票資料從假資料變成真實 API，這是 Demo 可信度的核心。
> **預估工時**：2–3 天

### Checklist

**後端（Backend）**
- [ ] 選定市場資料來源（建議：Finnhub 免費 tier 或 Yahoo Finance 非官方 API）
- [ ] 申請 Finnhub API Key，加入 [.env.example](file:///Users/caleb/Projects/finlify/.env.example) 和 [.env](file:///Users/caleb/Projects/finlify/.env)
- [ ] 改寫 `GET /api/quotes`：呼叫真實 API，回傳 `price`, `change`, `market_cap`, `pe_ratio`, `eps`, `volume`
- [ ] 改寫 `GET /api/history`：呼叫真實 API，支援 `1d ~ 3y` 範圍
- [ ] 加入 API 錯誤處理（Timeout / Rate Limit → 回傳清楚錯誤訊息）
- [ ] 加入簡單記憶體快取（e.g. TTL 60s）避免打爆 API 配額
- [ ] 更新後端相關測試（mock 外部 API 呼叫）

**前端（Frontend）**
- [ ] 驗證 [stock-search.tsx](file:///Users/caleb/Projects/finlify/frontend/src/components/features/stock-search.tsx) 從 Backend 搜尋股票的邏輯是否正確
- [ ] 驗證 [ticker-dashboard.tsx](file:///Users/caleb/Projects/finlify/frontend/src/components/features/ticker-dashboard.tsx) 使用真實的 quotes / history 資料
- [ ] 確認圖表在真實資料下的顯示格式正確

**Forecast Service**
- [ ] 驗證 `POST /forecast` 接受真實股票歷史資料格式
- [ ] 確認 `dummy_v0` 模型在少量資料下不會 crash

---

## Stage 2 — Auth 流程 & UX 完善
> **目標**：讓使用者可以正常完成登入、使用受保護功能，公開頁面體驗完整。
> **預估工時**：1–2 天

### Checklist

**Auth 流程**
- [ ] 確認 Supabase Project 已建立，`NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` 已填入
- [ ] 測試 Sign Up → Email 驗證 → Log In 完整流程
- [ ] 測試未登入時進入 `/dashboard` 是否正確 redirect 到 `/login`
- [ ] 測試登入後跳回原本頁面（auth redirect）
- [ ] 確認 Sign Out 功能正常

**公開頁面體驗**
- [ ] 首頁（`/`）搜尋框可正常搜尋股票並跳轉
- [ ] `/ticker/[ticker]` 在不登入情況下可正常瀏覽
- [ ] `/demo` 頁面有清楚的介紹與 CTA
- [ ] `/about` 頁面內容完整
- [ ] 所有頁面 Loading 狀態有 Skeleton 或 Spinner
- [ ] 所有頁面 Error 狀態有清楚的錯誤提示（不可留空白或壞掉的畫面）

**Watchlist（登入後）**
- [ ] 確認 Supabase `user_watchlist` 資料表已建立（參考 [docs/day2_supabase.sql](file:///Users/caleb/Projects/finlify/docs/day2_supabase.sql)）
- [ ] [watchlist.tsx](file:///Users/caleb/Projects/finlify/frontend/src/components/features/watchlist.tsx) 新增/刪除功能正常運作
- [ ] Assumption Profile 儲存和讀取正常

---

## Stage 3 — 基礎設施 & 部署配置
> **目標**：讓三個服務在雲端環境中正常跑起來。
> **預估工時**：2–3 天

### Checklist

**Frontend → Vercel**
- [ ] 建立 Vercel 專案，連接 GitHub repo
- [ ] 在 Vercel Dashboard 設定所有環境變數（`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, Demo Auth 相關）
- [ ] 確認 [next.config.ts](file:///Users/caleb/Projects/finlify/frontend/next.config.ts) 沒有阻擋 Vercel 建置的設定
- [ ] 測試 Vercel Preview Deployment 能正常 build

**Backend (Scoring) → Vercel Serverless 或 Fly.io**
- [ ] 決定部署平台（Vercel Python Runtime 或 Fly.io）
  - Vercel：確認 [backend/vercel.json](file:///Users/caleb/Projects/finlify/backend/vercel.json) 設定正確
  - Fly.io：`fly launch` 初始化，設定 `fly.toml`
- [ ] 設定環境變數（`FINLIFY_POLICY_ID`, `BACKEND_CORS_ORIGINS` 指向正式域名, Finnhub API Key）
- [ ] 確認 `docs/policies/` 在部署環境中可被讀取（如 Vercel，需確認檔案隨 build 一起打包）
- [ ] 測試 `POST /score` 在線上環境正常回應

**Forecast Service → Fly.io**
- [ ] `fly launch` 初始化 forecast service
- [ ] 設定 `FORECAST_CORS_ORIGINS` 指向線上前端域名
- [ ] 設定 `FORECAST_USAGE_LOG_DB_PATH` 對應到 persistent volume
- [ ] 測試 `POST /forecast` 在線上環境正常回應
- [ ] 測試 `GET /runtime/status` 正常

**CORS 設定**
- [ ] `BACKEND_CORS_ORIGINS` 設為 Vercel 前端 URL
- [ ] `FORECAST_CORS_ORIGINS` 設為 Vercel 前端 URL
- [ ] 前端 `NEXT_PUBLIC_API_URL` 設為線上 Backend URL
- [ ] 前端 forecast 請求 URL 設為線上 Forecast Service URL

---

## Stage 4 — Demo 強化 & 上線前 QA
> **目標**：Demo 可以安全地展示給外部使用者，不會有明顯的 bug 或安全疑慮。
> **預估工時**：1 天

### Checklist

**Demo 保護（若要封閉邀請制）**
- [ ] 線上環境設定 `DEMO_BASIC_AUTH_ENABLED=true`
- [ ] 設定 `DEMO_BASIC_AUTH_USERNAME` 和 `DEMO_BASIC_AUTH_PASSWORD`
- [ ] 測試未授權訪問會彈出 Basic Auth 對話框

**安全性**
- [ ] 確認所有服務使用 HTTPS（Vercel / Fly.io 預設提供）
- [ ] 確認 Supabase RLS (Row Level Security) 在所有表格上啟用
- [ ] 確認 API Key 沒有暴露在前端程式碼中
- [ ] `.gitignore` 確認 `.env` 不會被 commit

**最終 QA 清單**
- [ ] 端對端流程測試：搜尋股票 → 進入 Ticker 頁面 → 看歷史圖表 → 看預測
- [ ] 端對端流程測試：註冊帳號 → 登入 → 加入 Watchlist → 登出
- [ ] 在手機瀏覽器上測試 RWD 版面
- [ ] 確認所有 console error / warning 已清除
- [ ] 確認各頁面 Loading / Error 狀態正常
- [ ] 跑完整測試套件（Backend 50+ 案例、Forecast 8 個測試檔）

**CI/CD（選做，建議）**
- [ ] 設定 GitHub Actions，在 PR 時自動跑 Backend + Forecast 測試
- [ ] 設定 Vercel Preview Deployment（每次 PR 自動部署預覽）

---

## 時間軸總覽

```
Stage 1 │ 資料層接入    │ 2–3 天  │ 最高優先
Stage 2 │ Auth & UX    │ 1–2 天  │ 高優先
Stage 3 │ 部署配置      │ 2–3 天  │ 高優先 (可與 Stage 2 並行)
Stage 4 │ Demo 強化 QA │ 1 天    │ 最後執行
───────────────────────────────────────
總計     │              │ 6–9 天
```

> [!TIP]
> Stage 1（真實資料）是最高優先項目，因為 Demo 的說服力完全依賴資料的真實性。Stage 2 和 Stage 3 可以並行推進以節省時間。
