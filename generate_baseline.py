import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# 1. All 24 Official Barangays in Bago City
barangays_bago = [
    "Abuanan", "Alianza", "Atipuluan", "Balingasag", "Binubuhan",
    "Busay", "Calumangan", "Caridad", "Dulao", "Ilijan",
    "Lag-asan", "Ma-ao", "Mailum", "Malingin", "Napoles",
    "Pacol", "Poblacion", "Sagasa", "Sampinit", "San Antonio",
    "San Jose", "Santa Cruz", "Tabunan", "Taloc"
]

# 2. Your 7 Exact Monitored Diseases
diseases = [
    "Dengue Fever",
    "Leptospirosis",
    "Typhoid Fever",
    "Anthrax",
    "Meningococcal Disease",
    "Diarrheal Disease",
    "Hand, Foot, and Mouth Disease"
]

# 3-Year Date Range (Jan 1, 2023 - Aug 1, 2026)
start_date = datetime(2023, 1, 1)
end_date = datetime(2026, 8, 1)
date_list = [start_date + timedelta(days=x) for x in range((end_date - start_date).days)]

records = []
np.random.seed(42)

for current_date in date_list:
    month = current_date.month
    is_rainy = month in [6, 7, 8, 9, 10, 11]
    
    # Climate baselines for Bago City / Western Visayas
    avg_rainfall = np.random.uniform(12.0, 35.0) if is_rainy else np.random.uniform(0.0, 8.0)
    avg_temp = np.random.uniform(26.0, 32.0)
    humidity = np.random.uniform(75.0, 95.0) if is_rainy else np.random.uniform(60.0, 80.0)

    for barangay in barangays_bago:
        is_dense = barangay in ["Poblacion", "Ma-ao", "Calumangan", "Taloc", "Lag-asan"]
        
        # ZERO BASELINE DISTRIBUTION:
        # 88% - 94% chance of 0 cases on any given day
        # 6% - 12% chance of 1 routine background case
        zero_prob = 0.88 if is_dense else 0.94
        case_count = np.random.choice([0, 1], p=[zero_prob, 1.0 - zero_prob])
        
        disease_label = np.random.choice(diseases) if case_count > 0 else "None"

        records.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "barangay": barangay,
            "active_cases": case_count,
            "disease": disease_label,
            "rainfall_mm": round(avg_rainfall, 2),
            "temperature_c": round(avg_temp, 1),
            "humidity_pct": round(humidity, 1)
        })

# Export to CSV
df_baseline = pd.DataFrame(records)
df_baseline.to_csv("pulse_zero_baseline_data.csv", index=False)

print(f"Successfully generated {len(df_baseline):,} zero-baseline records!")
print(f"Total 0-case days: {len(df_baseline[df_baseline['active_cases'] == 0]):,}")
print(f"Total 1-case routine background days: {len(df_baseline[df_baseline['active_cases'] == 1]):,}")