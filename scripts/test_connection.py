from sl_analytics.db import query

df = query("SELECT version() AS version, now() AS now")
print(df.to_string(index=False))
