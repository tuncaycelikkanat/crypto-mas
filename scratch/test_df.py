import pandas as pd

df = pd.DataFrame({
    "open": [1]*50, "high": [1]*50, "low": [1]*50, "close": [1]*50, "volume": [1]*50
})
df.ta.sma(close=df["volume"], length=20, append=True, prefix="VOL")
print(df.columns)
