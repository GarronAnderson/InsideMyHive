"""
Auto temp cal tester.

Makes a spreadsheet (CSV) of results and writes graphs.
"""

import csv
import datetime
import numpy as np
import time

from t0NumpyAnalysis import *
from trimCSV import *

import matplotlib.dates as mdates

# === USER INPUT ===

start_time = "2024-12-10"  # YYYY-MM-DD
end_time = "2025-01-12" # ditto

out_file = r"Data\autoTestTwoDaysMoreData.csv"

DAYS_PER_SIM = 2

PACKETS_PER_DAY = 644

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
            "P2P raw",
            "P2P corrected",
            "P2P simple",
            "P2P no t0",
            "degrees per lb",
            "offset",
            "data points",
            "temp raw ptp",
            "temp corr ptp",
            "percentage correct after match",
        ]
    )

    for start_time, end_time in date_pairs:
        print(f"Running with {str(start_time)[:10]} to {str(end_time)[:10]} temp")

        trim(start_time, end_time)

        scale_data, temp_data = import_data(
            r"Data\hm-scale-trimmed.csv", r"Data\hm-temp-trimmed.csv"
        )

        if (scale_data.size > 10) and (temp_data.size > 10):
            print('filtering and matching')
            scale_data, temp_data = filter_and_match(scale_data, temp_data)
            
            num_after_match = scale_data.size
            
            avg_cal_val = np.mean(scale_data["vals"])
            scale_data['vals'] = (scale_data["vals"] * WEIGHT_ON_SCALE) / avg_cal_val
            
            print('finding best r, t0')

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
                    raw_ptp,
                    corr_ptp,
                    simple_ptp,
                    t0_0_ptp,
                    coef[0],
                    coef[1],
                    len(scale_data),
                    np.ptp(temp_data['vals']),
                    np.ptp(best_estimates),
                    (num_after_match/PACKETS_PER_DAY),
                ]
            )


            date_fmt = mdates.DateFormatter('%m/%d %H')
            hrs = mdates.HourLocator(interval=4)
    
            fig, ax = plt.subplots()
            ax.xaxis.set_major_locator(hrs)
            ax.xaxis.set_major_formatter(date_fmt)
            plt.plot(temp_data["dates"], lbs_reading, "g", label="reading [lbs]")
            plt.plot(
                temp_data["dates"],
                lbs_reading_corrected,
                "b",
                label="reading corrected [lbs]",
            )
            plt.plot(
                temp_data["dates"],
                lbs_reading_simple,
                label="reading corrected simple [lbs]",
            )
            plt.plot(
                temp_data["dates"], lbs_reading_t0_0, label="no t0 correction [lbs]"
            )
            plt.legend(loc="upper left")
            plt.savefig(f"images/{str(start_time)[:10]} to {str(end_time)[:10]} temp data correction")
            plt.clf()
            
            plt.scatter(temp_data["vals"], scale_data["vals"], label="raw temp")
            plt.scatter(best_estimates, scale_data["vals"], label="est temp")
            plt.plot(temp_data["vals"], coef[1] + coef[0] * temp_data["vals"], "k--")
            plt.xlabel('temperature [deg F]')
            plt.ylabel('reading [lbs]')
            plt.legend(loc="upper left")
            plt.savefig(f'images/{str(start_time)[:10]} to {str(end_time)[:10]} temp data correction loop')
            plt.clf()
            
    for start_time, end_time in date_pairs:
        if start_time > datetime(2024, 12, 17, 0, 0, 0):
            print(f"Running with {str(start_time)[:10]} to {str(end_time)[:10]} thermo")

            trim(start_time, end_time)

            scale_data, temp_data = import_data(
                r"Data\hm-scale-trimmed.csv", r"Data\hm-thermo-trimmed.csv"
            )

            if (scale_data.size > 10) and (temp_data.size > 10):
                print('filtering and matching')
                scale_data, temp_data = filter_and_match(scale_data, temp_data)
                
                num_after_match = scale_data.shape
                
                avg_cal_val = np.mean(scale_data["vals"])
                scale_data['vals'] = (scale_data["vals"] * WEIGHT_ON_SCALE) / avg_cal_val
                
                print('finding best r, t0')
                r_vals, t0_vals, scores, best_r, best_t0 = find_best_r_t0(
                    scale_data, temp_data, r_min, r_max, r_step, t0_min, t0_max, t0_step
                )

                lbs_reading, lbs_reading_corrected, lbs_reading_simple = (
                    correct_readings(scale_data, temp_data, best_r, best_t0)
                )
                _, lbs_reading_t0_0, _ = correct_readings(
                    scale_data, temp_data, best_r, 0
                )

                raw_ptp = np.ptp(lbs_reading)
                corr_ptp = np.ptp(lbs_reading_corrected)
                simple_ptp = np.ptp(lbs_reading_simple)
                t0_0_ptp = np.ptp(lbs_reading_t0_0)

                best_estimates = run_temp_estimation(
                    scale_data, temp_data, best_r, best_t0
                )
                coef = fit_correction(best_estimates, scale_data)
                
                
                fig, ax = plt.subplots()
                ax.xaxis.set_major_locator(hrs)
                ax.xaxis.set_major_formatter(date_fmt)
                plt.plot(temp_data["dates"], lbs_reading, "g", label="reading [lbs]")
                plt.plot(
                    temp_data["dates"],
                    lbs_reading_corrected,
                    "b",
                    label="reading corrected [lbs]",
                )
                plt.plot(
                    temp_data["dates"],
                    lbs_reading_simple,
                    label="reading corrected simple [lbs]",
                )
                plt.plot(
                    temp_data["dates"], lbs_reading_t0_0, label="no t0 correction [lbs]"
                )
                plt.legend(loc="upper left")
                plt.savefig(f"images/{str(start_time)[:10]} to {str(end_time)[:10]} thermo data correction")
                plt.clf()
                
                plt.scatter(temp_data["vals"], scale_data["vals"], label="raw temp")
                plt.scatter(best_estimates, scale_data["vals"], label="est temp")
                plt.plot(temp_data["vals"], coef[1] + coef[0] * temp_data["vals"], "k--")
                plt.xlabel('temperature [deg F]')
                plt.ylabel('reading [lbs]')
                plt.legend(loc="upper left")
                plt.savefig(f'images/{str(start_time)[:10]} to {str(end_time)[:10]} thermo data correction loop')
                plt.clf()

                writer.writerow(
                    [
                        str(start_time)[:10],
                        str(end_time)[:10],
                        "thermo",
                        best_r,
                        best_t0,
                        raw_ptp,
                        corr_ptp,
                        simple_ptp,
                        t0_0_ptp,
                        coef[0],
                        coef[1],
                        len(scale_data),
                        np.ptp(temp_data['vals']),
                        np.ptp(best_estimates),
                        (num_after_match/PACKETS_PER_DAY),
                    ]
                )


processing_end = time.time()

print('\n=== SIM DONE ===\n')
print(f'proccessing took {round((processing_end - processing_start)//60)} mins {round((processing_end - processing_start)%60)} secs')