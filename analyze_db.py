import sqlite3
import json

conn = sqlite3.connect('crypto_mas.db')
cursor = conn.cursor()

query = """
SELECT timestamp, features_json
FROM feature_snapshots
WHERE symbol='XRPUSDT' 
AND timestamp >= '2026-06-16 00:00:00' 
AND timestamp <= '2026-06-16 01:30:00'
ORDER BY timestamp ASC;
"""
cursor.execute(query)
rows = cursor.fetchall()

print("XRPUSDT Features:")
for row in rows:
    timestamp = row[0]
    features = json.loads(row[1])
    close = features.get('close', 0)
    ema20 = features.get('ema_20', 0)
    ema50 = features.get('ema_50', 0)
    adx14 = features.get('adx_14', 0)
    rsi14 = features.get('rsi_14', 0)
    print(f"{timestamp}: close={close:.4f}, ema20={ema20:.4f}, ema50={ema50:.4f}, adx={adx14:.1f}, rsi={rsi14:.1f}")

conn.close()
