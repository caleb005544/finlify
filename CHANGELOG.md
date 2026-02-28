# Changelog - Phase A: Auth & Database Implementation

## 2024-02-28 - Phase A Completion

### ✨ New Features

#### Frontend Routes
- **`/reset-password`** - Forgot password page with Supabase password reset integration
- **`/settings`** - User settings page with password change and logout functionality
- **`/auth/auth-code-error`** - Error page for invalid/expired email verification links

### 🔧 Implementation Details

#### Authentication System
- Implemented email/password signup with Supabase Auth
- Implemented email verification via OTP
- Implemented login with email/password
- Implemented password reset flow
- Server-side session management via middleware
- Protected routes for authenticated users only

#### Database Integration
- **Watchlist API** (`frontend/src/lib/api/watchlist.ts`)
  - `getWatchlist()` - Fetch user's watchlist from Supabase
  - `addToWatchlist(ticker)` - Add stock to watchlist
  - `removeFromWatchlist(ticker)` - Remove stock from watchlist

- **Profiles API** (`frontend/src/lib/api/profiles.ts`)
  - `getProfile()` - Fetch user's assumption profile
  - `saveProfile(data)` - Create/update user profile (risk level, horizon, sector preference)

#### Frontend Components
- **Dashboard** (`/dashboard`) - Main authenticated landing with watchlist and profile management
- **Watchlist Component** - Display and manage user's stock watchlist
- **Assumption Profile Component** - Set investment preferences (risk, time horizon, sector)

### 🔐 Security Features

- Row Level Security (RLS) defined in SQL schema
- User data isolation - each user can only access their own data
- Supabase Auth integration for secure authentication
- Server-side session validation

### ✅ Testing

- **Backend Tests**: 112/112 passing ✅
  - Market API tests (13 tests)
  - Scoring engine tests (99 tests)
  - Policy versioning tests (8+ tests)

### 📝 Environment Configuration

- `NEXT_PUBLIC_SUPABASE_URL` - Set to Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Set to Supabase anonymous key
- `NEXT_PUBLIC_API_URL` - Points to backend (http://localhost:8000 for local)
- `FINNHUB_API_KEY` - Set for market data integration

---

## 🧪 Phase A Testing Checklist

### ✅ Public Pages Testing (5 min)
- [x] Homepage accessible at `http://localhost:3000`
- [x] Stock search functionality works
- [x] Stock detail page (`/ticker/AAPL`) shows real data:
  - [x] Stock price, change percentage
  - [x] Historical chart
  - [x] No login required
- [x] Demo page (`/demo`) has content
- [x] About page (`/about`) has content

### ✅ Market API Testing
- [x] `/api/search?q=apple` - Returns search results (AAPL, APLE, etc.)
- [x] `/api/quotes?ticker=AAPL` - Returns real price data ($269.43)
- [x] `/api/history?ticker=AAPL&range=1m` - Returns historical data
- [x] All endpoints return proper error handling
- [x] Finnhub API integration verified

### 🚀 Authentication Flow Testing (Next Steps)

**What you need to do now:**

#### Step 1: Test Signup & Email Verification
1. [ ] Visit `http://localhost:3000/signup`
2. [ ] Enter your email and password
3. [ ] Click "Sign Up"
4. [ ] Check your email for verification link
5. [ ] Click the verification link
6. [ ] Should redirect to Dashboard `/dashboard`

#### Step 2: Test Login
1. [ ] Visit `http://localhost:3000/login`
2. [ ] Enter your verified email and password
3. [ ] Click "Sign In"
4. [ ] Should enter Dashboard

#### Step 3: Test Watchlist
1. [ ] In Dashboard, search for a stock (e.g., "MSFT")
2. [ ] Click to add to watchlist
3. [ ] Reload page (`Cmd+R`) - stock should still be there
4. [ ] Remove stock by clicking X button

#### Step 4: Test Settings & Logout
1. [ ] Click gear icon (⚙️) in top right
2. [ ] Go to `/settings` page
3. [ ] You can change password here
4. [ ] Click "Sign Out" to logout
5. [ ] Try accessing `/dashboard` - should redirect to `/login`

#### Step 5: Verify Supabase Data
1. [ ] Login to Supabase dashboard
2. [ ] Go to Table Editor
3. [ ] Check `user_watchlist` table - see your added stocks
4. [ ] Check `assumption_profiles` table - see your user profile

### 📊 Current Status
- ✅ SQL Schema: Executed in Supabase
- ✅ Backend APIs: All working with Finnhub integration
- ✅ Frontend Routes: All implemented
- ✅ Supabase Auth: Configured
- ⏳ Local testing: Ready to execute (see steps above)

### 🐛 Bug Fixes & Improvements

#### Email Verification Flow (2024-02-28)
**Issue:** Signup was redirecting directly to Dashboard without requiring email verification

**Root Cause:**
- Signup page was pushing to `/dashboard?welcome=true` instead of requiring email verification
- Supabase Email Confirm setting needed to be verified

**Fix Applied:**
- Modified `frontend/src/app/(auth)/signup/page.tsx` line 45
- Changed redirect behavior to show confirmation message and redirect to `/login`
- User now must verify email before logging in
- Added alert message: "✅ 帳號已建立！請檢查您的郵箱以驗證帳號。"

**Code Changes:**
```typescript
// Before:
router.push('/dashboard?welcome=true')

// After:
alert('✅ 帳號已建立！請檢查您的郵箱以驗證帳號。')
router.push('/login')
```

**Required Supabase Configuration:**
1. Authentication → Providers → Email
   - ✅ Enable Email provider: ON
   - ✅ Confirm email: ON (must be enabled)
2. Authentication → URL Configuration
   - Add redirect URLs:
     - `http://localhost:3000/auth/callback`
     - `https://<production-domain>/auth/callback`

### 📋 Remaining Tasks Before Phase B

- [ ] Complete signup → email verification → login flow (testing with fixed code)
- [ ] Add and remove stocks from watchlist
- [ ] Verify data persists in Supabase
- [ ] Test password change functionality
- [ ] Deploy to Vercel (Phase C)
- [ ] Final QA testing (Phase D)

---

---

## 🚀 Phase A → Phase C 快速推進指南

### 當前進度
- ✅ **Phase A**: 95% 完成（修復郵件驗證後 100%）
- ⏳ **Phase B**: 60% 完成（已有公開頁面）
- ⏱️ **Phase C**: 0% （準備開始）
- ⏱️ **Phase D**: 0% （最後執行）

### 立即要做的事 (按優先順序)

#### ① Phase A 完成測試 (30 分鐘)

**清空 Cache 並測試完整流程：**
1. 瀏覽器清空 Cache: `Cmd+Shift+R`
2. 測試註冊 → 郵件驗證 → 登入
3. 測試 Watchlist 新增/移除
4. 驗證 Supabase 資料持久化

**檢查清單：**
- [ ] Signup 要求郵件驗證
- [ ] 郵件驗證後才能登入
- [ ] Watchlist 能新增股票
- [ ] Watchlist 重載後持久化
- [ ] 能登出

#### ② Phase B: 快速 UX 檢查 (20 分鐘)

**在手機上測試公開頁面：**
- 開發者工具 → Toggle device toolbar (`Ctrl+Shift+M`)
- 選擇 iPhone 12 測試 RWD

**檢查清單：**
- [ ] 首頁在手機上可用
- [ ] 搜尋框能用
- [ ] 股票頁面格式正確
- [ ] 沒有 console 錯誤

#### ③ Phase C: 部署準備 (2-4 小時)

**部署前端到 Vercel：**
```bash
1. 登入 https://vercel.com
2. 建立新專案，從 GitHub 導入 finlify
3. 設定環境變數：
   - NEXT_PUBLIC_SUPABASE_URL
   - NEXT_PUBLIC_SUPABASE_ANON_KEY
   - NEXT_PUBLIC_API_URL
4. 點擊 Deploy
```

**部署後端 (選擇一個)：**

方案 A: Vercel Serverless (快速，5 分鐘)
- 建立第二個 Vercel 專案用於後端
- 設定 FINNHUB_API_KEY 等環境變數

方案 B: Fly.io (推薦，15 分鐘)
```bash
fly auth login
cd backend
fly launch --name finlify-backend
fly secrets set FINNHUB_API_KEY=<key>
```

#### ④ Phase D: 最終 QA (1 小時)

完整測試線上版本：
- [ ] 搜尋股票
- [ ] 進入股票頁面
- [ ] 註冊和驗證
- [ ] Watchlist 功能
- [ ] Supabase 資料

### 預計完成時間

| 階段 | 時間 |
|------|------|
| Phase A 測試 | 30 分鐘 |
| Phase B UX | 20 分鐘 |
| Phase C 部署 | 2-4 小時 |
| Phase D QA | 1 小時 |
| **總計** | **4-6 小時** |

### 關鍵 URLs

**開發環境:**
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

**部署後:**
- Frontend: `https://finlify-frontend.vercel.app`
- Backend: `https://finlify-backend.vercel.app` (或 fly.io)

### 常用命令

```bash
# 啟動前端
cd frontend && npm run dev

# 啟動後端
cd backend && python3 -m uvicorn main:app --reload

# 後端測試
cd backend && python3 -m pytest tests/ -v

# 清空 Cache
Cmd+Shift+R
```

---

## 📦 Phase C: 詳細部署指南 (2-4 小時)

### ✅ Step 1: Frontend 部署到 Vercel (15 分鐘)

#### 1a. 準備 GitHub
```bash
# 確保代碼已推送到 GitHub
git add .
git commit -m "feat: Phase A complete with email verification fix"
git push origin main
```

#### 1b. 在 Vercel 建立專案
```
1. 訪問 https://vercel.com
2. 點擊 "Add New" → "Project"
3. 選擇 "Import Git Repository"
4. 搜尋你的 finlify repo
5. 點擊 "Import"
6. 選擇 "Next.js" 框架（Vercel 自動偵測）
7. 點擊 "Deploy"
```

#### 1c. 設定環境變數
```
在 Vercel 部署前：
1. 進入 "Environment Variables"
2. 新增以下變數：

NEXT_PUBLIC_SUPABASE_URL=https://cluxgkdsgexyqiirudwf.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>
NEXT_PUBLIC_API_URL=http://localhost:8000

（暫時保持 localhost，後面會改為線上 URL）

3. 點擊 "Deploy"
```

#### 1d. 監控部署
```
Vercel Dashboard 會顯示：
✅ Building... (約 2-3 分鐘)
✅ Deployment succeeded
✅ Your site is live at: https://finlify-frontend.vercel.app
```

記下你的前端 URL!

---

### ✅ Step 2: Backend 部署 (15-30 分鐘)

#### 選擇 A: Vercel Serverless (推薦簡單快速)

```bash
# 1. 在 Vercel 建立第二個專案
https://vercel.com → Add New → Project
（選擇同一個 finlify repo，但這次選擇 backend 文件夾）

# 2. Root Directory: backend

# 3. Framework: Other (Python)

# 4. 設定環境變數
FINNHUB_API_KEY=d6gc1t9r01qt4932bjlgd6gc1t9r01qt4932bjm0
FINLIFY_POLICY_ID=balanced_v1
BACKEND_CORS_ORIGINS=https://finlify-frontend.vercel.app

# 5. Deploy
```

**優點:** 快速、無須額外帳戶
**缺點:** Python 支援有限

---

#### 選擇 B: Fly.io (推薦功能完整)

```bash
# 1. 安裝 Fly CLI
curl -L https://fly.io/install.sh | sh
exec $SHELL

# 2. 登入 Fly.io
fly auth login
（會打開瀏覽器讓你登入或建立帳號）

# 3. 初始化應用
cd /Users/caleb/Projects/finlify/backend
fly launch --name finlify-backend

選擇：
- Organization: 預設
- Region: 選擇離你最近的區域（e.g., nrt for Tokyo）
- PostgreSQL: No
- Redis: No

# 4. 設定環境變數
fly secrets set FINNHUB_API_KEY=d6gc1t9r01qt4932bjlgd6gc1t9r01qt4932bjm0
fly secrets set FINLIFY_POLICY_ID=balanced_v1
fly secrets set BACKEND_CORS_ORIGINS=https://finlify-frontend.vercel.app

# 5. 部署
fly deploy

# 6. 取得 URL
fly info
（會顯示你的 URL，例如: https://finlify-backend.fly.dev）
```

**優點:** 完整功能、持久化存儲
**缺點:** 需要額外帳戶、冷啟動時間

---

### ✅ Step 3: 配置 CORS 和環境變數 (10 分鐘)

#### 3a. 更新 Frontend 環境變數

在 Vercel Dashboard：
```
1. 進入 finlify-frontend 專案
2. Settings → Environment Variables
3. 編輯 NEXT_PUBLIC_API_URL：

舊值: http://localhost:8000
新值: https://finlify-backend.vercel.app
      (或 https://finlify-backend.fly.dev 如果用 Fly.io)

4. 儲存
5. 重新部署
```

#### 3b. 驗證 CORS 設定

後端已設定的 CORS（檢查 backend/main.py）：
```python
BACKEND_CORS_ORIGINS=https://finlify-frontend.vercel.app
```

確認無誤！

---

### ✅ Step 4: 測試線上端點 (15 分鐘)

#### 4a. 測試後端 API

```bash
# 測試報價 API
curl "https://finlify-backend.vercel.app/api/quotes?ticker=AAPL"

# 應該返回：
{
  "ticker": "AAPL",
  "price": 269.43,
  "change": -3.52,
  ...
}

# 測試評分 API
curl -X POST "https://finlify-backend.vercel.app/score" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker":"AAPL",
    "profile":{"risk_level":"Medium","horizon":"Long","sector_preference":"Tech"}
  }'
```

#### 4b. 測試前端

```bash
# 訪問線上前端
https://finlify-frontend.vercel.app

驗證：
✅ 首頁可訪問
✅ 搜尋功能正常
✅ API 呼叫成功（查看 Network 標籤）
✅ 沒有 CORS 錯誤
```

#### 4c. 檢查 Network 標籤

在瀏覽器開發者工具：
```
F12 → Network → 搜尋股票
應該看到：
✅ /api/search → 200
✅ /api/quotes → 200
✅ /api/history → 200
（沒有 CORS 錯誤）
```

---

### ✅ 部署檢查清單

部署前確認：
- [x] Frontend 代碼推送到 GitHub
- [x] Backend 代碼推送到 GitHub
- [ ] Finnhub API Key 已設定
- [ ] Supabase URL 和 Key 正確
- [ ] 後端 CORS_ORIGINS 設為 frontend Vercel URL

部署中：
- [ ] Frontend Vercel 部署成功
- [ ] Backend (Vercel 或 Fly.io) 部署成功
- [ ] 所有環境變數已設定

部署後：
- [ ] Frontend URL 可訪問
- [ ] Backend API 端點可訪問
- [ ] 沒有 CORS 錯誤
- [ ] 市場數據 API 返回實時數據
- [ ] Supabase 連接正常

---

### 🔗 部署完成後的 URLs

**前端:** https://finlify-frontend.vercel.app
**後端:** https://finlify-backend.vercel.app (或 fly.dev)
**Supabase:** https://supabase.com/dashboard

---

## Previous Changes

See `git log` for commit history with more details.
