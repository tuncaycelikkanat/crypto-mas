# 📘 Crypto MAS (Multi-Agent System) — Kapsamlı Algoritma, Matematik ve Mekanizma Raporu

Bu doküman, **Crypto MAS** projesinde yer alan tüm algoritmaları, matematiksel modelleri, filtreleri, risk kalkanlarını, puanlama mekanizmalarını ve strateji taktiklerini formülleri ve kod referanslarıyla birlikte eksiksiz olarak açıklamaktadır.

---

## 📑 İçindekiler
1. [Sistem Mimarisi ve Döngü Akışı](#1-sistem-mimarisi-ve-döngü-akışı)
2. [Piyasa Verisi Tarama ve Filtreleme Algoritmaları](#2-piyasa-verisi-tarama-ve-filtreleme-algoritmaları)
3. [Teknik ve İstatistiksel Öznitelik Pipeline'ı (Feature Pipeline & Math)](#3-teknik-ve-istatistiksel-öznitelik-pipelineı-feature-pipeline--math)
4. [Piyasa Rejim Tespit Motoru (Regime Detection Engine)](#4-piyasa-rejim-tespit-motoru-regime-detection-engine)
5. [Varlık Puanlama Motoru (Asset Scoring Engine)](#5-varlık-puanlama-motoru-asset-scoring-engine)
6. [Pozisyon Boyutlandırma ve Portföy Motoru (Bet Sizing & Portfolio)](#6-pozisyon-boyutlandırma-ve-portföy-motoru-bet-sizing--portfolio)
7. [Risk Yönetimi ve Güvenlik Kalkanları (Risk Shields)](#7-risk-yönetimi-ve-güvenlik-kalkanları-risk-shields)
8. [Strateji ve Taktik Kataloğu (Strategy Catalog)](#8-strateji-ve-taktik-kataloğu-strategy-catalog)
9. [Event-Driven HFT ve WebSocket Akış Motoru](#9-event-driven-hft-ve-websocket-akış-motoru)
10. [Multi-Armed Bandit (MAB) Taktik Tahsisatçısı](#10-multi-armed-bandit-mab-taktik-tahsisatçısı)
11. [Yapay Zeka Komitesi (LLM Committee / Multi-Agent Council)](#11-yapay-zeka-komitesi-llm-committee--multi-agent-council)
12. [İşlem İcrası ve Paper Broker Simülasyonu](#12-işlem-icrası-ve-paper-broker-simülasyonu)
13. [Walk-Forward Optimizasyon ve Fitness Skoru](#13-walk-forward-optimizasyon-ve-fitness-skoru)

---

## 1. Sistem Mimarisi ve Döngü Akışı

Crypto MAS, her 30-60 saniyede bir otonom olarak çalışan bir **Trading Cycle Pipeline** mimarisine sahiptir:

```
[1. Market Data Sync] ──> [2. Pre-Strategy M2M / SL] ──> [3. Regime & Scoring]
                                                                  │
[6. Execution Queue]  <── [5. Risk Engine & Shields] <── [4. Portfolio Sizing]
```

* **Market Data Orchestrator:** REST ve WebSocket üzerinden taze mumları çeker, Neon PostgreSQL'e kaydeder.
* **Mark-to-Market:** Mevcut açık pozisyonların kâr/zarar ve stop-loss durumunu stratejiden *önce* günceller.
* **Strategy & Regime:** Rejim tespiti yapar, taktikleri çalıştırır ve varlıkları puanlar.
* **Portfolio Engine:** Fractional Kelly ve Volatilite hedeflemesi ile hedef ağırlıkları dağıtır.
* **Risk Engine:** BTC Çöküş Kalkanı, Üst Zaman Dilimi (HTF) Kalkanı, Cooldown ve Likidite kontrollerini uygular.
* **Execution Queue:** Asenkron FIFO kuyruğu üzerinden emirleri slippage/komisyon simülasyonu ile icra eder.

---

## 2. Piyasa Verisi Tarama ve Filtreleme Algoritmaları

### A. Auto-Gainers & Pumpwatch Algoritması (`gainers_service.py`)
Binance'in 24 saatlik ticker verisi üzerinden en yüksek ivmeli pariteleri dinamik olarak seçer.

#### 1. 24h Zirveden Düşüş (Dump / Exhaustion) Filtresi:
Dün yükselmiş ancak bugün kar satışı yiyerek düşen pariteleri eler:
$$\text{drop\_from\_high\_pct} = \frac{\text{High}_{24h} - \text{Price}_{last}}{\text{High}_{24h}} \times 100$$
$$\text{Kural: } \text{drop\_from\_high\_pct} \le 12.0\%$$

#### 2. 24h Aralık Konumu (Range Proximity):
Fiyatın gün içindeki en düşük ve en yüksek seviyeler arasındaki bağıl konumu:
$$\text{range\_pos} = \frac{\text{Price}_{last} - \text{Low}_{24h}}{\text{High}_{24h} - \text{Low}_{24h} + 10^{-8}}, \quad \text{range\_pos} \in [0.0, 1.0]$$

#### 3. Pump Skoru Formülü:
Zirveye yakın seyreden, yüksek hacimli ve pozitif ivmeli coinleri ödüllendirir:
$$\text{Pump Score} = |\Delta P_{24h}\%| \times \left(\frac{\text{Volume}_{USDT}}{1,000,000}\right)^{0.3} \times \max(0.2, \text{range\_pos})^{1.2}$$

---

### B. Hidden Gems Tarayıcısı (`fetch_hidden_gems`)
Fiyatı henüz patlamamış (yatayda sıkışan) ancak hacmi anormal derecede artan "uyuyan dev" pariteleri tespit eder.

$$\text{Kriter: } -3.0\% \le \Delta P_{24h} \le +3.0\%$$
$$\text{Gem Score} = \frac{\text{Volume}_{USDT} / 1,000}{|\Delta P_{24h}\%| + 0.1}$$

---

## 3. Teknik ve İstatistiksel Öznitelik Pipeline'ı (Feature Pipeline & Math)

Tüm göstergeler **Numba JIT** ile C hızında derlenerek hesaplanır (`jit_calculators.py`).

### A. JIT Trend Skoru (`jit_trend_score`)
Fiyatın $EMA(20)$ ve $EMA(50)$ ile olan mesafesini ve EMA aralığını normalize eder:
$$\text{ema\_spread} = \max\left(\frac{EMA_{20} - EMA_{50}}{\text{Close}}, 0.0\right)$$
$$\text{price\_dist} = \max\left(\frac{\text{Close} - EMA_{20}}{\text{Close}}, 0.0\right)$$
$$\text{Trend Score} = \min\left(\max\left(0.0, (\text{ema\_spread} \times 20.0) + (\text{price\_dist} \times 10.0)\right), 1.0\right)$$

### B. JIT Momentum Skoru (`jit_momentum_score`)
RSI, Fiyat Değişim Hızı (ROC) ve MACD Histogramını birleştirir:
$$\text{rsi\_norm} = \max\left(\frac{RSI_{14} - 50.0}{50.0}, 0.0\right)$$
$$\text{roc\_norm} = \max\left(\frac{ROC_{14}}{10.0}, 0.0\right)$$
$$\text{macd\_norm} = \max\left(\tanh\left(\frac{\text{MACD} - \text{Signal}}{\max(ATR_{14} \times 0.1, 10^{-9})}\right), 0.0\right)$$
$$\text{Momentum Score} = (\text{rsi\_norm} \times 0.30) + (\text{roc\_norm} \times 0.30) + (\text{macd\_norm} \times 0.40)$$

### C. JIT Volatilite Cezası (`jit_volatility_penalty`)
Aşırı volatil ve tehlikeli hareketleri cezalandırır:
$$\text{ATR Ratio} = \frac{ATR_{14}}{\text{Close}}$$
$$\text{Volatility Penalty} = \min\left(\max\left(0.0, \text{ATR Ratio} \times 2.0\right), 0.35\right)$$

---

## 4. Piyasa Rejim Tespit Motoru (Regime Detection Engine)

Piyasa 4 temel rejim durumuna ayrılır (`RegimeEngine`):

1. **HIGH_VOLATILITY (Yüksek Volatilite):**
   $$\frac{ATR_{14}}{\text{Close}} > 0.08 \quad \text{veya} \quad \frac{\text{BB}_{upper} - \text{BB}_{lower}}{\text{BB}_{middle}} > 0.25$$
   *Risk Çarpanı:* $0.50$ (Pozisyon büyüklükleri yarıya indirilir).

2. **BULL_TREND (Boğa Trendi):**
   $$\text{Close} > EMA_{20} > EMA_{50} \quad \text{ve} \quad ROC_{14} > 0$$
   *Güven Formülü:*
   $$\text{Confidence} = 0.4 \times \min\left(\frac{\text{Close}-EMA_{20}}{EMA_{20} \times 0.02}, 1.0\right) + 0.3 \times \min\left(\frac{EMA_{20}-EMA_{50}}{EMA_{50} \times 0.03}, 1.0\right) + 0.3 \times \min\left(\frac{ROC_{14}}{5.0}, 1.0\right)$$

3. **BEAR_TREND (Ayı Trendi):**
   $$\text{Close} < EMA_{20} < EMA_{50} \quad \text{ve} \quad ROC_{14} < 0$$
   *Risk Çarpanı:* $0.30$ (Long pozisyonlar kısıtlanır, Short'a ağırlık verilir).

4. **SIDEWAYS (Yatay Piyasa):**
   * Yukarıdaki şartlar sağlanmadığında piyasa yatay kabul edilir. Mean-reversion taktikleri devreye girer.

---

## 5. Varlık Puanlama Motoru (Asset Scoring Engine)

Her varlık için bileşik sinyal skoru (`AssetScore`) hesaplanır:

$$\text{Raw Score} = (\text{Trend Score} \times 0.55) + (\text{Momentum Score} \times 0.45) - \text{Volatility Penalty}$$

* **RSI Slope Düzeltmesi:** Son 3 mumdaki RSI yönü yukarı ise $+0.05$ ivme primi eklenir, aşağı ise $-0.05$ ceza kesilir.
* **Final Skor:** $\text{Final Score} = \max(0.0, \min(\text{Raw Score} + \text{RSI Slope Bonus}, 1.0))$.

---

## 6. Pozisyon Boyutlandırma ve Portföy Motoru (Bet Sizing & Portfolio)

### A. Fractional Kelly Kriteri (`BetSizer.calculate_fractional_kelly`)
Maksimum sermaye büyümesi ve iflas riskini sıfırlamak için Çeyrek Kelly (Quarter-Kelly) standardı kullanılır:

$$f^* = \lambda \times \left(p - \frac{1 - p}{b}\right)$$

* $p$: Stratejinin kazanma oranı (Win Rate, örn: $0.55$).
* $b$: Kazanç/Kayıp oranı (Reward/Risk Ratio, örn: $2.0$).
* $\lambda$: Kelly çarpanı (Kurumsal standart $\lambda = 0.25$).
* $f^*$: Tahsis edilecek sermaye oranı (Üst sınır: $\%35$, Alt taban: $\%2$).

### B. Volatilite Hedefleme (Volatility Targeting)
Portföyün yıllıklandırılmış oynaklığını $\%20$ seviyesinde sabitlemek için varlığın oynaklığına ters orantılı pay ayrılır:

$$\text{Asset Volatility} = \frac{ATR_{14}}{\text{Price}} \times \sqrt{1460}$$
$$\text{Weight}_{vol} = \frac{\text{Target Volatility (0.20)}}{\text{Asset Volatility}}$$

$$\text{Final Asset Weight} = \min(f^*, \text{Weight}_{vol}, \text{Max Single Cap})$$

---

## 7. Risk Yönetimi ve Güvenlik Kalkanları (Risk Shields)

Sistem 6 katmanlı savunma kalkanı uygular:

```
[1. BTC Crash Shield] ──> [2. HTF Trend Shield] ──> [3. Regime Conflict Shield]
                                                             │
[6. 120m SL Cooldown] <── [5. Overbought & Trend] <── [4. Liquidity & Spread]
```

1. **BTC Crash Shield (`btc_crash_model.py`):**
   * BTC $15\text{m } ROC_{14} < -5.0\%$ olduğunda acil durum alarmı verilir. Tüm yeni Long alımları anında reddedilir.
2. **HTF Shield (`htf_portfolio_model.py`):**
   * Üst zaman diliminde (4h / 1D) düşüş trendi olan bir coinde alt zaman diliminde (15m) Long açılamaz.
3. **Regime Conflict Shield (`regime_model.py`):**
   * Ayı rejiminde açılmak istenen Long pozisyonların güven skoru $\%50$ oranında kırpılır.
4. **Thin Liquidity & Spread Guard (`risk_calculator.py`):**
   * Bid-Ask spread oranı $\%0.35$'ten büyük veya $15\text{m}$ hacmi $\$20,000$'dan küçük olan tahtalara emir iletilmez.
5. **120 Dakikalık Stop-Loss Cooldown & Whipsaw Kalkanı:**
   * Stop-Loss ile kapanan bir pariteye **120 dakika (2 saat)** boyunca yeni pozisyon açılması kesin olarak kilitlenir.
   * Aynı parite 2 kez üst üste stop olursa **48 saatlik Whipsaw Kilidi** uygulanır.
6. **Aşırı Alım ve Derin Düşüş Kalkanı (`strategy_orchestrator.py`):**
   * $15\text{m } RSI_{14} > 75.0$ olan tepedeki pariteler reddedilir (`REJECTED: Overbought`).
   * Fiyat $15\text{m } EMA(20)$'nin $\%3.5$ altına çökmüşse düşen bıçak alımları engellenir.

---

## 8. Strateji ve Taktik Kataloğu (Strategy Catalog)

### A. Rejim-Adaptif Strateji (`RegimeAdaptiveStrategy`)
Piyasa rejimine göre 3 taktik arasında geçiş yapar:

1. **Bull Tactic (`BullTactic`):**
   * $EMA(20) > EMA(50)$ ve $ADX > 25$.
   * $EMA(20)$'ye geri çekilmelerde (Pullback) veya $RSI \in [40, 60]$ bölgesinde kırılımları Longlar.
2. **Bear Tactic (`BearTactic`):**
   * Fiyat $EMA(50)$'nin altındayken $EMA(20)$'ye yükseliş tepkilerinde Short arar; Long açmaz.
3. **Sideways Tactic (`SidewaysTactic`):**
   * Bollinger Alt Bandına ($BB_{lower}$) değen ve $RSI < 30$ olan aşırı satım noktalarında Range Trade yapar.

---

## 9. Event-Driven HFT ve WebSocket Akış Motoru

Canlı WebSocket veri akışını mikrosaniyeler içinde işler (`EventEngine`):

* **60 Saniyelik Kayan Pencere (Sliding Window):** Son 60 saniyedeki her trade'i deque üzerinde tutar.
* **CVD (Cumulative Volume Delta):** Piyasa alıcılarının ve satıcılarının kümülatif delta farkını takip eder:
  $$CVD = \sum \text{Volume}_{buy} - \sum \text{Volume}_{sell}$$
* **Order Book Depth Imbalance:** En iyi 10 kademedeki alış/satış derinlik oranı:
  $$\text{Imbalance} = \frac{\sum \text{Bid Depth}}{\sum \text{Bid Depth} + \sum \text{Ask Depth}}$$

---

## 10. Multi-Armed Bandit (MAB) Taktik Tahsisatçısı

Taktiklerin sermaye paylarını canlı kâr/zarar performansına göre dinamik olarak günceller (`MultiArmedBanditAllocator`).

### UCB1 (Upper Confidence Bound) Formülü:
$$UCB_i = \hat{\mu}_i + c \times \sqrt{\frac{2 \ln N}{n_i}}$$

* $\hat{\mu}_i$: $i$. taktiğin normalize edilmiş ortalama getirisi.
* $N$: Toplam işlem turu sayısı.
* $n_i$: $i$. taktiğin çalıştırılma sayısı.
* $c$: Keşif/Kullanım (Exploration/Exploitation) dengesi ($c = 1.0$).

---

## 11. Yapay Zeka Komitesi (LLM Committee / Multi-Agent Council)

Güçlü sinyaller üretildiğinde Google Gemini LLM Komitesi (Shadow Mode / Canlı Mod) devreye girer:

```
[Signal Generator] ──> [Macro Analyst Agent] ──┐
                  ──> [Risk Sentinel Agent]  ──┼──> [Chair Agent: Consensus Decision]
                  ──> [Technical Agent]      ──┘
```

* **Macro Analyst:** Genel piyasa yapısını ve trend gücünü değerlendirir.
* **Risk Sentinel:** Likidite tuzaklarını ve sahte hacimleri (wash trading) denetler.
* **Chair Agent:** Ajanların oylarını ağırlıklandırarak $0.0 - 1.0$ arasında nihai Güven Skoru üretir.

---

## 12. İşlem İcrası ve Paper Broker Simülasyonu

Gerçek borsa şartlarını birebir simüle eden motor (`PaperBrokerService`):

* **Kayma (Slippage) Modeli:** Emrin büyüklüğüne ve oynaklığa göre dinamik fiyat kayması uygular:
  $$\text{Execution Price} = \text{Price} \times (1 \pm \text{Slippage}), \quad \text{Slippage} \in [0.03\%, 0.15\%]$$
* **Borsa Komisyonu (Fee):** Spot işlem komisyonu ($\%0.10$ Maker / Taker) her işlemde nakit bakiyeden düşülür.
* **Dinamik Trailing Stop-Loss:** Pozisyon kâra geçtikçe en yüksek fiyattan $1.5 \times ATR_{14}$ mesafede stop seviyesini yukarı taşır.

---

## 13. Walk-Forward Optimizasyon ve Fitness Skoru

Geçmiş testleri aşırı uyumdan (overfitting) korumak için Walk-Forward ve Composite Fitness Skoru kullanılır (`FitnessCalculator`):

$$\text{Fitness} = 0.35 \times \text{Sharpe} + 0.25 \times \text{Sortino} + 0.20 \times \text{WinRate} + 0.20 \times (1.0 - \text{MaxDD})$$

* 5 Kademeli Walk-Forward dilimleme ile eğitim (In-Sample) ve test (Out-of-Sample) verileri ayrılarak katsayıların sağlamlığı doğrulanır.
