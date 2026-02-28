# Local Testing Guide - Phase A Complete

## 🚀 環境檢查

### ✅ 正在運行
- Frontend Dev Server: `http://localhost:3000`
- Backend Dev Server: `http://localhost:8000`
- Supabase: Connected and tables created

---

## 📝 完整測試流程

### Step 1: 驗證後端 Market APIs

在瀏覽器或 curl 中測試這些端點：

#### 1a. 搜尋股票
```bash
curl "http://localhost:8000/api/search?q=apple"
```
**預期：** 返回 AAPL 和其他蘋果相關的股票

#### 1b. 獲取股票報價
```bash
curl "http://localhost:8000/api/quotes?ticker=AAPL"
```
**預期：** 返回股票價格、變化、市值、P/E、EPS 等

#### 1c. 獲取歷史數據
```bash
curl "http://localhost:8000/api/history?ticker=AAPL&range=1m"
```
**預期：** 返回過去一個月的日線數據（日期 + 收盤價）

#### 1d. 計算評分
```bash
curl -X POST "http://localhost:8000/score" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "profile": {
      "risk_level": "Medium",
      "horizon": "Long",
      "sector_preference": "Tech"
    }
  }'
```
**預期：** 返回股票評分和詳細說明

---

### Step 2: 測試 Frontend 公開頁面

訪問 `http://localhost:3000` 並測試：

#### 2a. 首頁搜尋
- [ ] 在首頁搜尋框輸入 "AAPL"
- [ ] 點擊搜尋或選擇建議
- [ ] 應該跳轉到 `/ticker/AAPL`

#### 2b. 股票詳情頁面
- [ ] 訪問 `http://localhost:3000/ticker/AAPL`
- [ ] 應顯示：
  - 股票名稱和價格
  - 價格變化（漲跌幅）
  - 歷史圖表（過去 1 個月）
  - 評分和建議
- [ ] 無需登入即可瀏覽

#### 2c. Demo 頁面
- [ ] 訪問 `http://localhost:3000/demo`
- [ ] 應該看到產品介紹

#### 2d. About 頁面
- [ ] 訪問 `http://localhost:3000/about`
- [ ] 應該看到關於信息

---

### Step 3: 完整 Auth 流程測試

#### 3a. 註冊新帳號
1. [ ] 訪問 `http://localhost:3000/signup`
2. [ ] 填入測試郵箱（e.g., `test@example.com`）
3. [ ] 填入密碼（至少 6 字符）
4. [ ] 點擊 "Sign Up"
5. [ ] **檢查郵箱** - Supabase 應該發送驗證郵件
   - 郵件內容會包含驗證連結
   - 點擊連結會重定向到 `/auth/callback`

#### 3b. 驗證郵件後登入
1. [ ] 點擊郵件中的驗證連結
2. [ ] 應該被重定向到 Dashboard (`/dashboard`)
3. [ ] 如果連結過期，應該看到 `/auth/auth-code-error` 頁面

#### 3c. 重新登入
1. [ ] 訪問 `http://localhost:3000/login`
2. [ ] 輸入郵箱和密碼
3. [ ] 點擊 "Sign In"
4. [ ] 應該進入 Dashboard

---

### Step 4: Dashboard 功能測試

#### 4a. 看盤清單 (Watchlist)
1. [ ] 在 Dashboard 搜尋框搜尋股票（e.g., "MSFT"）
2. [ ] 股票應該出現在搜尋建議中
3. [ ] 點擊股票將其新增到 Watchlist
4. [ ] 股票應該出現在 Watchlist 卡片中
5. [ ] 點擊股票卡片上的 X 按鈕移除它
6. [ ] **重新加載頁面** - 股票應該仍在 Watchlist 中（持久化）

#### 4b. 投資檔案 (Assumption Profile)
1. [ ] 在 Dashboard 點擊右上角設置按鈕（齒輪圖標）
2. [ ] 進入 `/settings` 頁面
3. [ ] 向下滾動找到「Profile Summary」或使用修改按鈕
4. [ ] 修改投資檔案：
   - Risk Level: Low / Medium / High
   - Time Horizon: Short / Medium / Long
   - Sector Preference: Tech / Healthcare / Finance 等
5. [ ] 點擊「Save」或「Update」
6. [ ] 應該看到「Saved!」確認訊息
7. [ ] **重新加載頁面** - 檔案應該保持修改

#### 4c. 修改密碼
1. [ ] 在 Settings 頁面輸入：
   - Current Password
   - New Password
   - Confirm Password
2. [ ] 點擊「Update Password」
3. [ ] 應該被重定向到登入頁面
4. [ ] 使用新密碼登入

#### 4d. 登出
1. [ ] 在 Settings 頁面點擊「Sign Out」
2. [ ] 應該被重定向到首頁
3. [ ] 嘗試訪問 `/dashboard` - 應該被重定向到 `/login`

---

### Step 5: 資料持久化驗證

#### 5a. Watchlist 持久化
1. [ ] 確保你已登入
2. [ ] 新增 2-3 個股票到 Watchlist
3. [ ] 重新加載頁面 (`F5` 或 `Cmd+R`)
4. [ ] [ ] 股票應該仍在 Watchlist
5. [ ] 開啟瀏覽器開發者工具 → Application → Cookies
6. [ ] 應該看到 Supabase 的 session cookie

#### 5b. Profile 持久化
1. [ ] 修改投資檔案
2. [ ] 重新加載頁面
3. [ ] Dashboard 右側「Profile Summary」應該顯示更新後的值

#### 5c. Supabase 驗證
1. [ ] 登入 Supabase Dashboard
2. [ ] 進入 Table Editor
3. [ ] 檢查 `user_watchlist` 表：
   - [ ] 應該看到你的郵箱對應的 user_id
   - [ ] 應該看到新增的股票代碼
4. [ ] 檢查 `assumption_profiles` 表：
   - [ ] 應該看到你的用戶資料
   - [ ] risk_level, horizon, sector_preference 應該是你設定的值

---

## 🧪 API 測試工具

### 使用 curl 測試

#### 測試搜尋
```bash
curl -s "http://localhost:8000/api/search?q=apple" | jq .
```

#### 測試報價
```bash
curl -s "http://localhost:8000/api/quotes?ticker=AAPL" | jq .
```

#### 測試歷史
```bash
curl -s "http://localhost:8000/api/history?ticker=AAPL&range=1y" | jq .
```

#### 計算評分
```bash
curl -s -X POST "http://localhost:8000/score" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "profile": {
      "risk_level": "Medium",
      "horizon": "Long",
      "sector_preference": "Tech"
    }
  }' | jq .
```

---

## 🐛 除錯提示

### 如果市場 API 返回錯誤

#### 錯誤: 503 FINNHUB_NOT_CONFIGURED
- **原因**: 環境變數 `FINNHUB_API_KEY` 未設定
- **解決**: 檢查 `.env` 文件，確認 `FINNHUB_API_KEY` 已設置

#### 錯誤: 429 RATE_LIMITED
- **原因**: Finnhub API 配額已用完
- **解決**: 等待配額重置（每分鐘 55 次請求限制）

#### 錯誤: 504 UPSTREAM_TIMEOUT
- **原因**: Finnhub API 反應時間過長
- **解決**: 重試或等待

### 如果 Auth 流程失敗

#### 無法登入
1. [ ] 確認郵箱已驗證（檢查郵件）
2. [ ] 確認密碼正確
3. [ ] 檢查瀏覽器 console 中的錯誤信息

#### 無法接收驗證郵件
1. [ ] 檢查垃圾郵件夾
2. [ ] 在 Supabase 檢查 Auth 設定
3. [ ] 確認 Email Provider 已啟用

### 如果 Watchlist/Profile 無法保存

#### 檢查點
1. [ ] 確認已登入（檢查 Supabase session）
2. [ ] 開啟瀏覽器開發者工具 → Network
3. [ ] 查看 API 請求是否成功 (200)
4. [ ] 檢查 Console 中的錯誤
5. [ ] 驗證 Supabase RLS 策略是否正確

---

## ✅ 完成標準

測試通過時應該：
- ✅ 所有公開頁面都能訪問
- ✅ 市場 API 返回實時數據
- ✅ 可以完整進行註冊 → 驗證 → 登入
- ✅ 可以新增/移除看盤清單
- ✅ 可以修改投資檔案
- ✅ 所有資料在頁面重新加載後持久化
- ✅ Supabase 中可以看到用戶資料

---

## 預計測試時間

- 後端 API 驗證: 5-10 分鐘
- 前端公開頁面: 5 分鐘
- Auth 流程: 10-15 分鐘（包括郵件驗證等待）
- Watchlist 和 Profile: 10 分鐘
- **總計: 30-40 分鐘**

**讓我們開始測試吧！** 🚀
