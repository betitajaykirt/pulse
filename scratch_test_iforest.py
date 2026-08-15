import pandas as pd
from sklearn.ensemble import IsolationForest
import numpy as np

# 1. Load and group data
df = pd.read_csv('c:/DJANGO/djangotutorial/pulse_zero_baseline_data.csv')
grouped = df.groupby(['date', 'barangay']).agg({
    'active_cases': 'sum',
    'rainfall_mm': 'mean',
    'temperature_c': 'mean',
    'humidity_pct': 'mean'
}).reset_index()

print("Grouped shape:", grouped.shape)
print("Max active cases:", grouped['active_cases'].max())

features = ['active_cases', 'rainfall_mm', 'temperature_c', 'humidity_pct']
X = grouped[features]

model = IsolationForest(
    n_estimators=200,
    contamination=0.08,
    random_state=42,
    n_jobs=-1
)
model.fit(X)

scores = model.score_samples(X)
print("Score min:", scores.min())
print("Score max:", scores.max())
print("Score mean:", scores.mean())

# Let's find scores for normal (active_cases = 0) vs surge (active_cases = max)
sample_normal = grouped[grouped['active_cases'] == 0].iloc[0:1]
sample_surge = grouped[grouped['active_cases'] >= 10].iloc[0:1]

print("Normal score:", model.score_samples(sample_normal[features])[0])
if len(sample_surge) > 0:
    print("Surge score:", model.score_samples(sample_surge[features])[0])

