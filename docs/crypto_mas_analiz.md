# 🔬 Crypto MAS — Kapsamlı Sistem Analizi

> Analiz tarihi: 2026-07-26 | Analist: Antigravity AI

---

## 📊 Genel Puan Tablosu

| Kategori | Puan | Açıklama |
|---|---|---|
| 🏗️ Mimari & Tasarım | **8.5 / 10** | DDD ilkeleri güçlü, katman ayrımı net |
| 🧹 Kod Kalitesi | **7.5 / 10** | Tutarlı ama bazı code smell'ler mevcut |
| 📐 Tip Güvenliği | **7.0 / 10** | Kısmi typing, mypy toleranslı ayarlı |
| ⚙️ Performans | **7.0 / 10** | Numba JIT güzel, ama backtest'te darboğazlar var |
| 🧪 Test Kalitesi | **8.0 / 10** | 58 unit test, iyi kapsam ancak bazı boşluklar |
| 🔒 Güvenlik | **5.5 / 10** | API auth yok, secret yönetimi zayıf |
| 🚀 DevOps & CI/CD | **6.5 / 10** | Docker var, CI pipeline minimal |
| 🔀 Concurrency | **7.5 / 10** | AsyncIO doğru kullanılmış, race condition riski var |
| 📊 Finans Mantığı | **6.5 / 10** | Sinyaller güçlü, backtest'te ciddi eksikler |
| 📖 Dokümantasyon | **8.0 / 10** | README mükemmel, docstring zayıf |
| **🏆 TOPLAM ORTALAMA** | **7.2 / 10** | Çok güçlü bir temel, production için eksikler var |

---

## 🏗️ 1. MİMARİ & TASARIM — 8.5/10

### ✅ Güçlü Yönler

**Katmanlı DDD Mimarisi Çok Başarılı**
```
domain/        ← Pure business logic, framework bağımlılığı yok
infrastructure/ ← Dış dünya ile tek temas noktası
services/      ← Use case'ler burada
engine/        ← Karar motoru, tek sorumluluk
apps/          ← Entry pointler
brokers/       ← Exchange adaptörleri
```

Bu ayrım ciddiye alınmış. `domain/models/candle.py`, `domain/models/position.py` gibi modeller hiçbir framework kodu içermiyor; sadece SQLAlchemy ORM dekorasyonu var — ki bu da kabul edilebilir bir trade-off.

**Adapter Pattern Doğru Kullanılmış**
- `BinanceAdapter`, `MockAdapter`, `BacktestBrokerAdapter`, `PaperBrokerAdapter` → aynı arayüz, farklı implementasyonlar. Mode değişimi tek env var ile yapılabiliyor.

**Dependency Injection Mevcut**
`PortfolioEngine`, `RiskEngine`, `TradingCycleService` gibi sınıflar bağımlılıklarını constructor'dan alıyor. Bu testability'yi artırıyor.

**TimeProvider Soyutlaması**
```python
# infrastructure/time/time_provider.py
class SystemTimeProvider:
    def now() -> datetime
class MockTimeProvider:  # testlerde kullanılıyor
```
Bu detay, saat bağımlı testleri mümkün kılıyor. Küçük ama çok önemli.

### ⚠️ Zayıf Yönler

**`domain/entities/` klasörü boş!**
`src/crypto_mas/domain/entities/` altında sadece `__init__.py` var. Domain Entity kavramı (ORM model değil, business entity) gerçek anlamda implemente edilmemiş. Aggregate root mantığı eksik.

**Singleton Anti-Pattern**
`OrderExecutorQueue.get_instance()` — global singleton kullanımı. Test conftest'inde bu sıfırlanıyor:
```python
# tests/conftest.py
queue = OrderExecutorQueue.get_instance()
queue.sync_mode = False
queue._broker_factory = None
```
Singleton, concurrency testlerinde de özel önlem gerektiriyor. Bu bir tasarım riskidir.

**`SchedulerService` içinde hard-coded business logic**
```python
# scheduler_service.py:17-21
MODE_CONFIG: dict[str, tuple[str, str, int]] = {
    "scalping": ("15m", "hft_momentum", 60),
    "swing":    ("4h",  "macd_cross",   120),
    "hodl":     ("1d",  "ema_golden_cross", 3600),
}
```
Bu bir config dosyasına veya DB'ye taşınmalı. Strategy-mode-timeframe bağlantısı sert kodlanmış.

**`PortfolioEngine` içinde domain bilgisi (coin grupları)**
```python
# portfolio.py:8-16
BTC_CORRELATED = {"BTCUSDT", "ETHUSDT", "BNBUSDT", ...}
COIN_GROUPS = {
    "TOP10": {...},
    "MEMES": {...},
```
Bu sabit listeler domain modeline veya konfig'e ait. Engine sınıfında hard-code edilmiş olması bakım sorununa yol açar.

---

## 🧹 2. KOD KALİTESİ — 7.5/10

### ✅ Güçlü Yönler

**Temiz ve Okunabilir Sinyal/Regime/Scoring Motoru**
`trend.py`, `regime.py`, `scoring.py` — her biri tek sorumluluk ilkesine uyuyor. İsimlendirme tutarlı (`_calculate_strength`, `_trend_confidence`, `_collect_issues`).

**`assert` Bloklarına Not Edilmesi Gereken Pattern**
```python
# trend.py:41-47
assert close is not None
assert ema_20 is not None
...
```
`None in {close, ema_20,...}` kontrolünden sonra `assert` bloğu type narrowing için kullanılıyor. Aslında mantıklı, ama `cast()` daha Pythonic olurdu.

**RiskEngine'deki EPSILON Kullanımı**
```python
class RiskEngine:
    EPSILON = 1e-9
    if target.gross_exposure > self.limits.max_gross_exposure + self.EPSILON:
```
Float karşılaştırmalarında epsilon kullanmak doğru ve mesleki bir tercih.

**`FeatureCalculator` Vektörize Hesaplama**
pandas-ta ile tüm indikatörler toplu hesaplanıyor. Loop-based hesaplama yerine vektörize yaklaşım doğru performans kararı.

### ⚠️ Zayıf Yönler

**`BacktestEngine` içinde hard-coded TP/SL**
```python
# backtest/engine.py:116-117
TP_PCT = 0.02   # Hard coded!
SL_PCT = 0.01   # Hard coded!
```
Bu değerler constructor'dan veya config'den gelmeliydi. Parametre olarak alınmaması backtesting'in temel amacını zayıflıtıyor.

**`trades: list[Any]` — Zayıf Tip**
```python
# backtest/engine.py:36
self.trades: list[Any] = []
```
Trade için bir dataclass veya TypedDict tanımlanmalıydı.

**`auto_optimizer_service.py` içinde Import'lar Metodun İçinde**
```python
def run_optimization_job(self, ...):
    from crypto_mas.domain.repositories.candle_repository import CandleRepository
    from crypto_mas.services.backtesting.memory_cache import InMemoryCandleRepository
    ...
```
Lazy import'lar performans için bazen gereklidir, ancak burada circular import korkusu mu yoksa kasıtlı mı belli değil. Bu pattern okunabilirliği düşürür.

**`FeatureCalculator.calculate()` içindeki feature_map karmaşası**
```python
# calculator.py:67-77
"OBV": "obv", "OBV_in_1": "obv",   # İki farklı key aynı değere
"STOCHRSIk_14_14_3_3": "stoch_rsi_k", "STOCHk_14_3_3": "stoch_rsi_k",  # Duplikasyon
"ROC_14": "roc_14", "ROCP_14": "roc_14",  # Aynı
```
pandas-ta'nın farklı versiyonlarda farklı kolon adları üretmesine karşı savunma amaçlı yazılmış bu map, iyi bir fikir olsa da brittle. Birim testlerde gizlenmiş bir zaman bombası.

**`_run_async()` anti-pattern — `auto_optimizer_service.py`**
```python
def _run_async(self, coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is None:
        return asyncio.run(coro)
    else:
        import nest_asyncio  # ← Production'da kötü pratik
        nest_asyncio.apply()
        return loop.run_until_complete(coro)
```
`nest_asyncio` production kodunda ciddi bir kod kokusu. Bu sync-in-async problemi, mimarisel bir sorunu patch etmeye çalışıyor. AutoOptimizer async-first olmalı veya bir ThreadPoolExecutor ile izole edilmeliydi.

**`PortfolioEngine` içinde mutation**
```python
# portfolio.py:62-73
decision.confidence = 0.0   # ← Input objesini mutate ediyor!
decision.reason = f"[Filtered] ..."
decision.confidence = min(0.99, decision.confidence + 0.15)  # ← Yine mutate
```
Input parametrelerini mutate etmek sürpriz yan etkiler yaratır. Yeni bir karar nesnesi oluşturulmalıydı.

---

## 📐 3. TİP GÜVENLİĞİ — 7.0/10

### Bulgular

**mypy Ayarları Gevşek**
```toml
# pyproject.toml:59
disallow_untyped_defs = false  # ← Bütün fonksiyonlar typed olmak zorunda değil
ignore_missing_imports = true  # ← 3rd party lib hataları gizleniyor
```

**Pozitif: SQLAlchemy 2.0 Mapped[] Kullanımı**
```python
id: Mapped[int] = mapped_column(primary_key=True)
symbol: Mapped[str] = mapped_column(String(64), nullable=False)
stop_loss_price: Mapped[Decimal | None] = mapped_column(nullable=True)
```
SQLAlchemy 2.0'ın modern `Mapped[]` syntax'ı kullanılmış, bu type checker'ların ORM modellerini anlamasını sağlıyor.

**Negatif: `dict[str, Any]` yaygın kullanımı**
`features_json: dict[str, Any]` tüm sistem boyunca dolaşıyor. Bu "untyped bag" pattern, IDE desteğini ve compile-time güvenliği yok ediyor. Bir `FeatureSet` TypedDict tanımlanması önerilir.

---

## ⚙️ 4. PERFORMANS — 7.0/10

### ✅ İyi Kararlar

**Numba JIT Compilation**
```python
@njit(cache=True)
def jit_trend_score(close, ema_20, ema_50, direction_val) -> float:
```
Hot path'lerdeki (scoring) matematik Numba ile JIT derlenmiş. `cache=True` ile soğuk başlangıç sorunu azaltılmış.

**Vektörize Feature Hesaplama**
pandas-ta kullanımı row-by-row hesaplama yerine numpy alt yapısıyla vektörize.

**In-Memory Cache Backtest için**
`InMemoryCandleRepository`, `InMemoryFeatureSnapshotRepository` — optimizasyon döngüsünde DB hit'ini minimize etmek için.

### ⚠️ Darboğazlar

**Backtest'te O(n) Snapshot Window (list.pop(0))**
```python
# backtest/engine.py:80-81
snapshot_window.append(snapshot)
if len(snapshot_window) > 5:
    snapshot_window.pop(0)  # ← O(n) shift!
```
`collections.deque(maxlen=5)` kullanılmalı.

**`FeatureCalculator`: Her candle için yeniden DataFrame oluşturma**
Backtest döngüsünde her sembol için ayrı DataFrame oluşturuluyor. Büyük veri setlerinde bellek ve CPU yükü artar.

**DB Session'ı Scheduler'da Manuel Yönetim**
```python
# scheduler_service.py:178-206
db = SessionLocal()
try:
    ...
finally:
    db.close()
```
Her scheduler tick'inde yeni session açıp kapanıyor. Bağlantı havuzu genellikle bunu yönetir, ancak çok sayıda eşzamanlı bot için `async with` session yönetimi daha sağlam.

---

## 🧪 5. TEST KALİTESİ — 8.0/10

### ✅ Güçlü Yönler

**Hacim ve Çeşitlilik**
58 unit test dosyası, entegrasyon testleri, coverage dosyası mevcut (`.coverage`). Bu hacim gerçek bir taahhüt gösteriyor.

**Concurrency Test — Çok İyi Bir Test**
`test_concurrency_engines.py` — backtest ve live cycle'ın aynı anda çalışmasını, singleton queue'nun izolasyonunu test ediyor. Bu production'da karşılaşılabilecek gerçek bir sorunu test ediyor.

**SQLite In-Memory DB ile Entegrasyon Test**
```python
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
```
Gerçek DB bağlantısı gerektirmeden ORM seviyesinde test ediliyor.

**Optimization Framework Testleri Matematiksel Doğruluk İçeriyor**
```python
# test_optimization_framework.py:63-65
# Expected: 0.8 + 0.45 + 0.40 + 0.08 = 1.73
score = FitnessCalculator.calculate_composite_score(result, min_trades=30)
assert pytest.approx(score, 0.01) == 1.73
```

### ⚠️ Eksikler

**`conftest.py` Singleton Reset — Kötü Kokular**
Singleton sıfırlama kodu conftest'te bulunması, test isolation'ının singleton nedeniyle kırılgan olduğunu gösteriyor.

**`test_sensitivity_analyzer.py` içinde `nest_asyncio.apply()`**
Test kodunda `nest_asyncio` — production'daki aynı anti-pattern test koduna sızdı.

**Backtest Engine'in TP/SL Parametreleri Test Edilmemiş**
Hard-coded `TP_PCT=0.02`, `SL_PCT=0.01` değerleri için parametrik test yok.

**`tests/integration/` klasörü boş (neredeyse)**
Gerçek DB veya exchange bağlantısı gerektiren entegrasyon testleri eksik.

---

## 🔒 6. GÜVENLİK — 5.5/10

### 🚨 Kritik Eksikler

**API Authentication Yok**
`apps/api/main.py` içinde herhangi bir auth middleware yok. 14 router açık. Bu production'da kabul edilemez — özellikle bot başlatma/durdurma, paper trading endpointleri için.

**Secret Yönetimi Minimal**
```python
# settings.py
binance_api_key: str = ""
binance_api_secret: str = ""
```
`.env` dosyasında tutuluyorlar. `.env.example` mevcut ki bu iyi, ama AWS Secrets Manager, HashiCorp Vault gibi secret management entegrasyonu yok.

**`.env` dosyası `.gitignore`'da mı?**
Kontrol edilmeli.

**Rate Limiting Yok**
API endpointleri rate limit yok. Abuse ve DDoS'a açık.

**CORS Ayarları Görünmüyor**
`main.py`'de CORS middleware tanımlanmamış. Bu frontend'den güvenli erişimi engeller veya wildcard'a açık bırakır.

---

## 🚀 7. DEVOPS & CI/CD — 6.5/10

### ✅ İyi Yönler

**Multi-Stage Dockerfile**
```dockerfile
FROM node:20-alpine AS frontend-builder  # Stage 1: React build
FROM python:3.12-slim                    # Stage 2: Python runtime
```
`python:3.12-slim` tercih edilmiş, image boyutu makul.

**Healthcheck Tanımlı**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
```

**Auto Migration on Startup**
```dockerfile
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn ..."]
```
Container ayakta kalınca migrationları otomatik uygular. Küçük ekipler için pratik.

**`uv` Paket Yönetimi**
Modern, hızlı paket yöneticisi. `uv.lock` ile reproducible build'ler.

### ⚠️ Eksikler

**`docker-compose.yml` sadece `api` servisi içeriyor**
TimescaleDB, Redis tanımlanmamış! README'de gerekli deniyor ama compose dosyasında yok. Yeni geliştirici nasıl çalıştıracak?

**`.github/` CI pipeline içeriği bilinmiyor (subagentlar inceliyor)**
Muhtemelen basit, çünkü proje aktif geliştirme aşamasında.

**Sınırlı Ortam Ayrımı**
```python
# main.py:36
setup_logging(env="dev")  # ← Hard-coded "dev"!
```
Production'da `env` değişkeni env var'dan okunmalıydı.

**`COPY . .` — Kötü Docker Pratik**
```dockerfile
COPY . .
```
Bu `.env`, geçici dosyalar, `crypto_mas.db` gibi büyük dosyaları da kopyalayabilir. `.dockerignore` kontrol edilmeli.

---

## 📊 8. FİNANS MANTIĞI — 6.5/10

### ✅ Güçlü Yönler

**Multi-Stage Karar Hattı Teorik Olarak Sağlam**
Signal → Score → Regime → Portfolio → Risk zincirleme yapısı, profesyonel quant sistemlerin standart mantığına uyuyor.

**Regime-Based Dinamik Ayarlama**
```python
# BEAR market'ta TOP10 dışı longs filtrelenir
if regime == MarketRegime.BEAR_TREND and decision.action == DecisionAction.CONSIDER_LONG:
    if decision.symbol not in COIN_GROUPS["TOP10"]:
        decision.confidence = 0.0
```
Piyasa rejimine göre pozisyon filtresi — doğru yaklaşım.

**Correlation Group Control**
BTC-correlated group weight cap: konsantrasyon riskini azaltma girişimi doğru.

**Backfill + Feature Önbellek Stratejisi**
Optimizasyon öncesi verileri ön-ısıtmak (warmup) hesaplama verimliliğini artırıyor.

### 🚨 Önemli Eksikler

**Backtest'te Lookahead Bias Riski**
```python
# backtest/engine.py:58
feature_snapshots = self.feature_calculator.calculate(candles)
# Tüm veriler üzerinden hesaplanıyor, SONRA zaman bazlı iterasyon
```
İndikatörler *tüm veri seti üzerinden* bir kerede hesaplanıyor. Bu, future data'ya erişim anlamına gelir — gerçek backtest şartlarında her zaman adımda sadece o anki verilerle hesaplama yapılmalı.

**TP/SL Backtest'te Sabit ve Gerçekçi Değil**
```python
TP_PCT = 0.02  # Her strateji, her sembol için aynı %2 TP
SL_PCT = 0.01  # Her strateji için aynı %1 SL
```
Gerçek sistemde ATR bazlı dinamik TP/SL kullanılmalı.

**Equity Curve Drawdown Hesabı Yaklaşık**
```python
# Equity'yi sadece closed trades üzerinden hesaplıyor
# Açık pozisyonlar dahil edilmiyor
for t in closed_trades:
    current_equity += t['realized_pnl']
```

**Sharpe/Sortino Oranı Eksik**
`BacktestResult` `sortino_ratio`, `calmar_ratio` içeriyor — bunların nasıl hesaplandığı `BacktestEngineService`'e taşınmış, ancak basit backtest engine'de yok.

**Slippage Modeli Çok Basit**
```python
execution_price = current_price * (1 + self.slippage_pct)  # Sabit %
```
Market impact, likidite, order book derinliği modellenmiyor.

**SHORT Position Desteği Eksik**
Backtest engine sadece LONG pozisyonlar açıyor:
```python
elif decision.action == DecisionAction.CONSIDER_LONG:
    # Open Position
```
CONSIDER_SHORT için pozisyon açılmıyor.

---

## 🔀 9. CONCURRENCY — 7.5/10

### ✅ Güçlü Yönler

**AsyncIO + uvloop**
```python
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
```
uvloop ile %20-40 daha hızlı event loop.

**Backtest İzolasyonu Düşünülmüş**
Backtest çalışırken global queue'ya etkisi test edilmiş — iyi bir endişe, iyi bir test.

**APScheduler AsyncIO Entegrasyonu**
`AsyncIOScheduler` ile scheduler ve uygulama event loop'u aynı thread'de çalışıyor.

### ⚠️ Riskler

**EventDrivenService Thread Safety**
```python
self._event_bots = {}  # ← Plain dict, thread-safe değil
```
WebSocket callback'ler farklı thread'de çalışabilir. `threading.Lock()` veya async lock gerekebilir.

**Singleton OrderExecutorQueue**
Global state, özellikle backtest-live concurrency senaryosunda race condition riski var.

---

## 📖 10. DOKÜMANTASYON — 8.0/10

### ✅ Güçlü Yönler

**README.md Çok İyi**
ASCII banner, mimari diyagram, karar akışı, veri modeli tablosu, trading mode tablosu — profesyonel seviye.

**`reason` Alanı Her Yerde**
```python
TradingSignal(reason="Close > EMA20 > EMA50, RSI > 50, ROC > 0.")
RiskCheckIssue(message=f"{position.symbol} target weight {position.target_weight:.4f} exceeds limit")
```
Her karar açıklanıyor — explainability vaat edilmiş ve hayata geçirilmiş.

### ⚠️ Eksikler

**Docstring Neredeyse Yok**
`TrendSignalEngine.generate()`, `RegimeEngine.detect()`, `PortfolioEngine.build_target_portfolio()` — hiç docstring yok.

---

## 🔍 GENEL EKSİKLER ÖZETİ

| Eksik | Öncelik | Etki |
|---|---|---|
| API Authentication (JWT/API Key) | 🔴 Kritik | Güvenlik |
| Lookahead Bias - Backtest | 🔴 Kritik | Finans doğruluğu |
| docker-compose'da DB/Redis eksik | 🔴 Kritik | Geliştirici deneyimi |
| SHORT backtest desteği | 🟠 Yüksek | Finans eksikliği |
| `nest_asyncio` anti-pattern | 🟠 Yüksek | Teknik borç |
| Hard-coded TP/SL backtest | 🟠 Yüksek | Esneklik |
| CORS + Rate Limiting | 🟠 Yüksek | Güvenlik |
| Feature_map brittle pattern | 🟡 Orta | Bakım |
| `dict[str, Any]` features_json | 🟡 Orta | Tip güvenliği |
| `list.pop(0)` → deque | 🟡 Orta | Performans |
| Hard-coded "dev" logging | 🟡 Orta | Operasyon |
| Docstring eksikliği | 🟢 Düşük | Bakım |
| Coin grupları config'e taşınmalı | 🟢 Düşük | Esneklik |

---

## 🛠️ ÖNERİLEN ARAÇLAR & KÜTÜPHANELER

### 🔒 Güvenlik
| Araç | Amaç |
|---|---|
| **FastAPI + `python-jose`** | JWT authentication |
| **`slowapi`** | Rate limiting (FastAPI için) |
| **`starlette-csrf`** | CSRF koruması |
| **HashiCorp Vault / AWS Secrets Manager** | Secret yönetimi |
| **`bandit`** | Python güvenlik açığı tarayıcı |

### 📊 Finans & Backtest
| Araç | Amaç |
|---|---|
| **`backtesting.py`** | Profesyonel backtesting framework |
| **`vectorbt`** | Çok hızlı vektörize backtesting |
| **`quantstats`** | Portföy performans analizi (Sharpe, Sortino, Calmar raporları) |
| **`zipline-reloaded`** | Production-grade backtesting, survivorship bias önleme |
| **`PyPortfolioOpt`** | Markowitz, Black-Litterman portföy optimizasyonu |
| **`ffn`** | Financial functions (drawdown, Sharpe hesaplamaları) |

### 🧪 Test & Kalite
| Araç | Amaç |
|---|---|
| **`pytest-cov`** | Code coverage raporlama |
| **`hypothesis`** | Property-based testing (sayısal kenarlara karşı) |
| **`pytest-benchmark`** | Performans regression testi |
| **`freezegun`** | Zaman bazlı testlerde saat dondurma |

### 📐 Tip & Kalite
| Araç | Amaç |
|---|---|
| **`mypy --strict`** | Tam tip güvenliği (mevcut ayar gevşek) |
| **`pyright`** | Microsoft'un güçlü type checker'ı |
| **`pydantic v2 TypeAdapter`** | `features_json` için runtime validation |

### 🚀 Performans & Monitoring
| Araç | Amaç |
|---|---|
| **`prometheus-client` + `Grafana`** | Sistem metrikleri, bot performance |
| **`opentelemetry-api`** | Distributed tracing |
| **`Sentry`** | Hata takibi, production monitoring |
| **`locust`** | API yük testi |
| **`py-spy`** | Production profiling |

### 🏗️ Altyapı
| Araç | Amaç |
|---|---|
| **`celery` + Redis** | Ağır async task'lar (optimizer) için |
| **`asyncpg`** | PostgreSQL için tam async driver |
| **`alembic` hooks** | Migration öncesi/sonrası test |
| **`terraform`** | Altyapı-as-code |

### 📊 Veri & ML
| Araç | Amaç |
|---|---|
| **`scikit-learn`** | Regime detection için ML (SVM, HMM) |
| **`hmmlearn`** | Hidden Markov Model ile piyasa rejimi |
| **`statsmodels`** | GARCH volatilite modellemesi |
| **`ta-lib`** | Daha geniş indikatör seti (pandas-ta alternatifi) |

### 🐳 DevOps
| Araç | Amaç |
|---|---|
| **GitHub Actions** | CI/CD pipeline (test + lint + build) |
| **`pre-commit`** | Commit öncesi otomatik ruff + mypy |
| **`hadolint`** | Dockerfile lint |
| **`docker-compose` (tam)** | TimescaleDB + Redis + API birlikte |

---

## 🎯 ÖNCELİKLİ İYİLEŞTİRME PLANI

### 🔴 Hafta 1 — Kritik
1. `docker-compose.yml`'e TimescaleDB + Redis ekle
2. API'ye JWT/API Key auth middleware ekle
3. Backtest lookahead bias'ını düzelt (rolling window ile hesaplama)

### 🟠 Hafta 2 — Güvenlik & Doğruluk
4. CORS + Rate limiting ekle
5. SHORT position backtest desteği ekle
6. `nest_asyncio` → celery veya async-native çözümle değiştir
7. ATR bazlı dinamik TP/SL ekle

### 🟡 Hafta 3 — Teknik Borç
8. `dict[str, Any]` → `FeatureSet` TypedDict dönüşümü
9. `features_json` feature_map → robust key discovery
10. Hard-coded mode configs → DB/config service
11. `setup_logging(env="dev")` → env var'dan oku
12. `list.pop(0)` → `deque(maxlen=5)`

### 🟢 Hafta 4 — İyileştirme
13. Docstring ekle (Google style)
14. `mypy --strict` hedefine doğru ilerleme
15. `quantstats` entegrasyonu ile backtest raporlama
16. `prometheus-client` ile bot metrik yayını
17. `pre-commit` hook'ları ekle

---

*Bu rapor Antigravity AI tarafından kaynak kodu doğrudan incelenerek üretilmiştir.*
