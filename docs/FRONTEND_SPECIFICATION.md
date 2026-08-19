# 🛡️ Crypto MAS - Frontend Specification & Element Inventory

Bu doküman, **Crypto MAS (Multi-Agent System)** projesinin frontend mimarisini, sayfalarını, bileşenlerini ve sayfalar üzerinde **kesinlikle bulunması ve korunması gereken** tüm fonksiyonel elementleri tanımlar. Gelecekteki tüm UI güncellemeleri, refactor ve tasarım iyileştirmeleri bu teknik envanteri temel standart olarak kabul etmelidir.

---

## 1. 🏗️ Mimari ve Teknoloji Yığını (Tech Stack)

* **Çatı:** React 19 + TypeScript (`.tsx`) + Vite 8
* **Yönlendirme:** React Router v7 (`react-router-dom`)
* **Veri Görselleştirme:** Recharts (`AreaChart`, `LineChart`, `ResponsiveContainer`)
* **Animasyon & Geçişler:** Framer Motion (`motion.div`, `AnimatePresence`)
* **İkon Kütüphanesi:** Lucide React
* **Veri İletişimi:** Axios + WebSocket (`ws`/`wss` canlı risk & rejim akışı)
* **Tasarım / Tema Motoru:**
  * Koyu Tema: OLED Midnight (`#020617`), Cam efekti (`Glassmorphism` / `backdrop-filter: blur(20px)`), Neon Mavi (`#38bdf8`) & Neon Yeşil vurgular.
  * Açık Tema: Slate/Blue hafif gradyanlı arka plan.
  * Tema tokenları `frontend/src/index.css` dosyasında CSS Custom Properties olarak tanımlıdır.

---

## 2. 🧭 Ana İskelet & Navigasyon (`Layout.tsx`)

Her sayfayı çevreleyen ortak düzen bileşenidir.

### Bulunması Gereken Elementler:
1. **Sol Sabit Sidebar (`<aside className="glass-panel">`):**
   * **Logo & Marka:** Crypto MAS logosu (Aktivite ikonu + Multi-Agent System alt başlığı).
   * **Navigasyon Menüsü:**
     * `Overview` (`/` - `LayoutDashboard` ikonu)
     * `Market Radar` (`/radar` - `TrendingUp` ikonu)
     * `Paper Trading` (`/paper` - `Bot` ikonu)
     * `Backtesting` (`/backtesting` - `FlaskConical` ikonu)
     * `Auto-Optimizer` (`/optimization` - `Zap` ikonu)
     * `System Logs` (`/logs` - `Terminal` ikonu)
   * **Aktif Sayfa Göstergesi:** `framer-motion` ile `layoutId="nav-active"` animasyonlu vurgu.
   * **Sistem Canlılık Göstergesi:** `/health` endpoint'ini 15 saniyede bir sorgulayan yeşil (Online) / kırmızı (Offline) sinyal lambası.
   * **Tema Butonu:** Açık / Koyu tema geçiş anahtarı (`Sun` / `Moon`).
2. **Üst Bar (`<header>`):**
   * API bağlantı durumu (`Wifi` / `WifiOff` ikonu).
   * Türkçe yerelleştirilmiş anlık tarih bilgisi.
3. **Sayfa Gövdesi (`<Outlet />`):** Sayfa içeriklerinin dinamik render alanı.

---

## 3. 📄 Sayfa Envanteri ve Olmazsa Olmaz Elementler

---

### 📌 1. Overview / Dashboard (`/` - `Dashboard.tsx`)
Sistemin genel sağlığı ve kümülatif finansal performansının merkezidir.

#### Zorunlu Elementler:
1. **Üst Durum Çubuğu (Status Header):**
   * `API Status Pill` (Canlı/Hata)
   * `Database Health Pill` (Bağlı/Hata)
   * `Active Bots Pill` (Çalışan bot adedi)
   * `Reset Data Butonu` (Kırmızı onay pencereli işlem geçmişi sıfırlama butonu)
2. **Canlı Risk & Rejim Kalkanı (`RiskRegimeShield`):** (Bkz. Ortak Bileşenler)
3. **4'lü Ana Metrik Kartları:**
   * **Total PnL:** Gerçekleşen net kâr/zarar ($) ve toplam kapanan işlem sayısı (Pozitifte yeşil, negatifte kırmızı).
   * **Win Rate:** Yüzdelik karlı işlem oranı (%).
   * **Open Positions:** Anlık açık pozisyon sayısı.
   * **Account Equity:** Toplam kasa değeri ($) ve güncel nakit bakiye alt etiketi.
4. **Equity Curve (Kasa Gelişim Grafiği):**
   * Recharts `AreaChart` ile zaman eksenli kümülatif bakiye eğrisi.
   * Özel Tooltip (`ChartTooltip` - Tarih ve para formatı).
   * Veri noktası sayısı göstergesi.
5. **Recent Trades (Son İşlemler Tablosu):**
   * Sütunlar: Zaman (`HH:MM:SS`), Sembol, Yön (`BUY`/`SELL` rozeti), Fiyat, Hacim (Notional $), Realized PnL ($).
   * Boş durum (Empty state) uyarısı.

---

### 📌 2. Market Radar (`/radar` - `MarketRadar.tsx`)
Piyasadaki aktif paritelerin teknik durumlarını ve fiyat hareketlerini analiz eden sayfa.

#### Zorunlu Elementler:
1. **Sol Kripto Para Seçim Paneli:**
   * API'den dinamik çekilen aktif coin butonları (`BTCUSDT`, `ETHUSDT` vb.).
   * Seçili butonun `btn-primary` ile parlaması.
2. **Üst Kalkan:** `RiskRegimeShield` bileşeni.
3. **Fiyat Hareketi Grafiği (Price Action Area Chart):**
   * Seçilen paritenin sembolü, zaman dilimi (`15m` vb.) ve borsa bilgisi (`BINANCE` / `MEXC`).
   * Recharts `AreaChart` üzerinde yeşil parlayan glow filtresi.
   * X ekseni (Zaman) ve Y ekseni (Fiyat $ - dinamik ondalık hassasiyeti).
4. **Teknik Özellik & İndikatör Grid Kartları:**
   * Seçili coinin API'den dönen teknik göstergeleri (RSI, ADX, Volatilite, Trend vb.) otomatik grid kartları.
5. **Seçili Parite Konsolu (`LiveConsole`):**
   * Yalnızca seçili coine ait logları filtreleyip gösteren terminal.

---

### 📌 3. Paper Trading (`/paper` - `PaperTrading.tsx`)
Canlı simülasyon botlarının konfigüre edildiği, çalıştırıldığı ve izlendiği sayfa.

#### Zorunlu Elementler:
1. **Üst Aksiyon Butonları:**
   * `Force Cycle` butonu: Anlık manuel analiz ve al-sat turu tetikler.
   * `Start Trading` butonu: Bot yapılandırma modalını açar.
2. **Çoklu Hesap / Slot Sekmeleri (Account Tabs):**
   * `Main Account`, `Slot 2`, `Slot 3` vb. hesaplar arası geçiş sekmeleri.
3. **Hesap Bakiye Kartları:** Equity ($), Nakit Bakiye ($), Aktif Pozisyon Adedi.
4. **Son Döngü Durum Kartı (Action Log Card):**
   * Son döngü durumu (`EXECUTED` / `REJECTED`), taranan sembol, verilen karar ve açılan işlem adedi.
5. **Aktif Bot Yönetim Paneli:**
   * Bot aktif değilse "No Active Bots" uyarısı.
   * Bot aktifse:
     * Bot ID & Canlılık yeşil yanıp sönen lamba.
     * Çalışma Modu & Borsa rozeti (`SCALPING · BINANCE`).
     * `Stop Bot` (Kırmızı durdurma butonu).
     * **Canlı Risk Kaydırıcısı (Slider 0-100):** Güvenli / Dengeli / Agresif dinamik risk güncelleme.
     * **Parite Düzenleme Alanı:** Manuel parite listesi düzenleme & `Update` butonu veya `Auto-Scanner Active` kartı.
6. **Açık Pozisyonlar Tablosu (Open Positions):**
   * Sembol, Yön (`LONG`/`SHORT`), Adet, Giriş Fiyatı, Anlık Kâr/Zarar (`Unrealized PnL`).
7. **Kapalı Pozisyonlar Tablosu (Closed Positions):**
   * Sembol, Yön, Giriş Fiyatı, Çıkış Fiyatı, Gerçekleşen Kâr/Zarar (`Realized PnL`), Kapanış Sebebi (Take Profit, Trailing SL vb.).
8. **Canlı Konsol (`LiveConsole`):** Tüm işlem emirlerini basan alt terminal.
9. **Bot Başlatma Modalı (`showConfigModal`):**
   * **Borsa Seçimi:** `BINANCE`, `MEXC` (Çoklu seçim).
   * **Trading Modu:** `Scalping (15m)`, `Swing (4h)`, `HODL (1d)`.
   * **Risk Seviyesi:** 0-100 slider.
   * **Sembol Kaynağı:** `Manuel Liste` veya `🤖 Auto-Scanner`.
   * **Hızlı Coin Seçimi:** Favori coin etiketleri ve yeni favori ekleme inputu.
   * **Analiz Aralığı:** Saniye cinsinden sorgu periyodu (Scalping harici).
   * **Emniyet Kalkanları (Safety Shields):**
     * `BTC Crash Shield` (Ani BTC çöküş koruması).
     * `HTF Trend Shield` (Üst zaman dilimi trend uyumu).
     * `Market Regime Shield` (Yüksek volatilite blokajı).

---

### 📌 4. Backtesting Engine (`/backtesting` - `Backtesting.tsx`)
Stratejilerin geçmiş veriler üzerinde simüle edildiği analiz motoru.

#### Zorunlu Elementler:
1. **3'lü Üst Navigasyon Sekmesi:**
   * `Rule-Based Run`: Kural tabanlı hızlı simülasyon.
   * `LLM Shadow Run`: Çoklu yapay zeka ajanlı simülasyon (Maliyet uyarılı).
   * `History`: Geçmiş test arşivi.
2. **Tümünü Temizle Butonu (`Clear All`):** Çalışan testleri iptal eder.
3. **Simülasyon Başlatma Formu:**
   * Borsa seçimi (`BINANCE`, `MEXC`).
   * Strateji Modu (`Regime Adaptive`, `Scalping`, `Swing`, `HODL`).
   * Mum Periyodu (`1m`, `5m`, `15m`, `1h`, `4h`, `1d`).
   * Coin Kaynağı (Manuel veya Auto-Scanner - Look-ahead bias uyarısı ile).
   * Başlangıç & Bitiş Tarihi Seçicileri.
   * Başlangıç Bakiyesi ($).
   * Risk Seviyesi (0-200 slider: Güvenli / Degen / Max Risk).
   * Risk Filtreleri (BTC Shield, HTF Shield, Regime Shield checkbox'ları).
   * Gelişmiş Taktik Konfigürasyonu (`Regime Adaptive` seçildiğinde JSON editörü).
4. **Aktif / Son Testler Listesi:** Sol altta çalışan/tamamlanan test kartları.
5. **Test Sonuçları & Canlı Motor Çıktısı (Backtest Details & Logs):**
   * Durum (`RUNNING`, `COMPLETED`, `FAILED`) ve İptal butonu.
   * Metrikler: `Final Equity`, `Cycle PnL`, `Win Rate`, `Max Drawdown`, `Total Trades`.
   * **Canlı Motor Logları:** `[Saat]`, `[Aşama]` (`INIT`, `STRATEGY`, `RISK`, `EXECUTION`, `PAPER_BROKER`, `TRAILING_SL`), `[Seviye]`, `[Mesaj]`.
   * `Auto-Scroll` checkbox'ı.
6. **Geçmiş & Karşılaştırma Ekranı (`BacktestHistory.tsx`):**
   * Test Geçmiş Tablosu: Seçim kutusu, Tarih, Strateji, Risk, PnL, Win Rate, İşlem adedi, Satır Detay Açıcı (`Gross PnL`, `Komisyonlar`, `Net PnL`, `Drawdown`), Silme butonu.
   * **Test Karşılaştırma Görünümü (`Compare Selected`):** Seçilen 2 testin tüm metriklerini ve kasa eğrisi grafiklerini yan yana kıyaslama.

---

### 📌 5. Auto-Optimizer (`/optimization` - `AutoOptimizer.tsx`)
Botun kendi kendine hiperparametre bulma (Optuna) geçmişini ve manuel tetikleyicisini barındırır.

#### Zorunlu Elementler:
1. **"⚡ Force Optimize" Butonu:** Anlık 3-5 dakikalık Optuna optimizasyonunu tetikler.
2. **Bilgilendirme Paneli:** Sistemin en iyi parametreleri nasıl bulduğunu anlatan rehber kartı.
3. **Optimizasyon Geçmiş Tablosu:**
   * Koşu ID, Tarih, Tetikleyici kaynak (`SCHEDULED` / `MANUAL`), Geçmiş süre (Ay), Durum rozeti (`COMPLETED`, `RUNNING`, `FAILED`), Bulunan En İyi Ayarlar rozetleri (`Take Profit`, `Stop Loss` vb. etiketler), Hata mesajı sütunu.

---

### 📌 6. Live Logs (`/logs` - `LiveLogs.tsx`)
Sistem genelindeki tüm operasyonel kayıtların incelendiği konsol.

#### Zorunlu Elementler:
1. **Sekmeler:** `System Logs` ve `Debug Log` (Asistana göndermek üzere ham JSON kopyalama).
2. **Üst Kontrol Barı:** Son güncelleme saati, toplam log sayısı, `Auto-scroll`, `Yenile`, `Temizle` butonları.
3. **Gelişmiş Filtreleme Çubuğu:**
   * Aşama filtre butonları (`INIT`, `STRATEGY`, `PORTFOLIO`, `RISK`, `PAPER_BROKER`, `TRAILING_SL`, `COMPLETED`, `FAILED`).
   * Seviye filtre butonları (`INFO`, `SUCCESS`, `WARN`, `ERROR`).
   * Sembol arama kutusu.
4. **Çift Bölmeli (Split View) Arayüz:**
   * **Sol Panel (Log Listesi):** Saat, Aşama rozeti, Mesaj, Payload varlık noktası.
   * **Sağ Panel (Detay Paneli):** Seçilen kaydın tüm derin parametrelerini katlanabilir ağaç yapısında (`JsonNode`) gösteren ve tek tıkla panoya kopyalayan (`Copy JSON`) alan.

---

### 📌 7. Strategy Decisions (`/decisions` - `Decisions.tsx`)
Ajanların alım-satım gerekçelerini ve bloklama sebeplerini detaylandıran strateji karar tablosu.
* Zaman, Sembol, Aksiyon rozeti (`CONSIDER_LONG`, `AVOID`), Güven Skoru (%), Karar Açıklaması / Gerekçe Logu.

---

## 4. 🛡️ Ortak Bileşen Envanteri (Reusable Components)

1. **`RiskRegimeShield.tsx`:**
   * WebSocket (`/api/v1/ws/risk-regime`) üzerinden anlık veri alır; bağlantı koparsa REST polling'e döner.
   * BTC Rejimi (`BULL`, `BEAR`, `SIDEWAYS` renk kodlu), Güven skoru, ATR Stop Risk Çarpanı, Drawdown Kalkanı ve Korelasyon adedini gösterir.
2. **`LiveConsole.tsx`:**
   * macOS terminal başlığına sahip, renkli seviye etiketleri (`[INFO]`, `[SUCCESS]`, `[WARN]`, `[ERROR]`) içeren, duraklatılabilir (`Pause/Resume`) canlı log konsolu.
3. **`CoinDetails.tsx`:**
   * Seçilen kripto paraya ait AreaChart grafiği ve teknik indikatör kartlarını gösteren modüler bileşen.

---

## 5. ⚠️ Gelecekteki UI Güncellemeleri İçin Altın Kurallar

1. **Hiçbir Fonksiyonel Element Silinmeyecek:** Yeni tasarımlara geçilirken yukarıda listelenen hiçbir metrik, filtre, modal seçeneği veya kontrol butonu kaldırılmayacak; yalnızca görsel olarak modernize edilecektir.
2. **Canlı Veri & Rejim Kalkanı Korunacak:** Risk & Rejim Kalkanı (`RiskRegimeShield`) ana sayfa ve radarda her zaman görünür kalmalıdır.
3. **Tip Güvenliği (`types/api.ts`):** Backend ile haberleşen tüm interface'ler ve veri modelleri eksiksiz korunacaktır.
4. **Kullanıcı Geri Bildirimleri (Error/Success/Loading):** Tüm asenkron butonlarda yüklenme animasyonları (`animate-spin`) ve hata durumları korunacaktır.
