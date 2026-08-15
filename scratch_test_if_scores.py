import pandas as pd
from sklearn.ensemble import IsolationForest

baseline_path = 'c:/DJANGO/djangotutorial/pulse_zero_baseline_data.csv'
baseline = pd.read_csv(baseline_path)
grouped = baseline.groupby(['date', 'barangay']).agg({
    'active_cases': 'sum',
    'rainfall_mm': 'mean',
    'temperature_c': 'mean',
    'humidity_pct': 'mean'
}).reset_index()

features = grouped[['active_cases', 'rainfall_mm', 'temperature_c', 'humidity_pct']]

model = IsolationForest(
    n_estimators=200,
    contamination=0.08,
    random_state=42,
    n_jobs=-1
)
model.fit(features)

test_data = pd.DataFrame([
    {'active_cases': 0, 'rainfall_mm': 0.0, 'temperature_c': 30.0, 'humidity_pct': 70.0},
    {'active_cases': 1, 'rainfall_mm': 0.0, 'temperature_c': 30.0, 'humidity_pct': 70.0},
    {'active_cases': 3, 'rainfall_mm': 0.0, 'temperature_c': 30.0, 'humidity_pct': 70.0},
    {'active_cases': 10, 'rainfall_mm': 0.0, 'temperature_c': 30.0, 'humidity_pct': 70.0},
    {'active_cases': 16, 'rainfall_mm': 0.0, 'temperature_c': 30.0, 'humidity_pct': 70.0},
])

scores = model.score_samples(test_data[['active_cases', 'rainfall_mm', 'temperature_c', 'humidity_pct']])
print("Raw scores for 0, 1, 3, 10, 16 active cases:")
print(scores)

