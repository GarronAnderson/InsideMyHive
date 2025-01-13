"""
Auto lbs/degree calculator.

Puts results in a spreadsheet.
"""

import csv
import datetime
import numpy as np
import time

from t0NumpyAnalysis import *
from trimCSV import *

import matplotlib.dates as mdates

# === USER INPUT ===

start_time = "2024-12-17"  # YYYY-MM-DD
end_time = "2025-01-08"  # ditto

out_file = r"Data\lbsPerDegree.csv"

DAYS_PER_SIM = 1

# === END USER INPUT ===

processing_start = time.time()

start_time = datetime.strptime(start_time, input_time_format)
end_time = datetime.strptime(end_time, input_time_format)

date_range = np.arange(start_time, end_time, dtype="datetime64[D]")
date_range = np.append(date_range, np.datetime64(end_time, "D")).astype("datetime64[s]")

date_pairs = list(zip(date_range, date_range[DAYS_PER_SIM:]))

with open(out_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(
        [
            "start date",
            "end date",
            "data source",
            "R",
            "t0",
            "data points",
            "lbs per degree",
            "offset",
        ]
    )

    for start_time, end_time in date_pairs:
        print(f"Running with {str(start_time)[:10]} to {str(end_time)[:10]} temp")

        trim(start_time, end_time)

        scale_data, temp_data = import_data(
            r"Data\hm-scale-trimmed.csv", r"Data\hm-temp-trimmed.csv"
        )

        if (scale_data.size > 10) and (temp_data.size > 10):
            print("filtering and matching")
            scale_data, temp_data = filter_and_match(scale_data, temp_data)

            print("finding best r, t0")

            avg_cal_val = np.mean(scale_data["vals"])
            scale_data["vals"] = (scale_data["vals"] * WEIGHT_ON_SCALE) / avg_cal_val

            r_vals, t0_vals, scores, best_r, best_t0 = find_best_r_t0(
                scale_data, temp_data, r_min, r_max, r_step, t0_min, t0_max, t0_step
            )

            lbs_reading, lbs_reading_corrected, lbs_reading_simple = correct_readings(
                scale_data, temp_data, best_r, best_t0
            )
            _, lbs_reading_t0_0, _ = correct_readings(scale_data, temp_data, best_r, 0)

            raw_ptp = np.ptp(lbs_reading)
            corr_ptp = np.ptp(lbs_reading_corrected)
            simple_ptp = np.ptp(lbs_reading_simple)
            t0_0_ptp = np.ptp(lbs_reading_t0_0)

            best_estimates = run_temp_estimation(scale_data, temp_data, best_r, best_t0)
            coef = fit_correction(best_estimates, scale_data)

            writer.writerow(
                [
                    str(start_time)[:10],
                    str(end_time)[:10],
                    "temp",
                    best_r,
                    best_t0,
                    coef[0],
                    coef[1],
                    len(scale_data),
                ]
            )

processing_end = time.time()

print("\n=== SIM DONE ===\n")
print(
    f"proccessing took {round((processing_end - processing_start)//60)} mins {round((processing_end - processing_start)%60)} secs"
)
