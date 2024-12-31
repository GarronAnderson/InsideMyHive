import datetime

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import medfilt

from trimCSV import *

# ===== INPUT =====

BAD_TIMING_THRESHOLD = 10  # seconds

start_time = "2024-11-22"  # YYYY-MM-DD
end_time = "2024-12-30"

out_file = r"Data\timingAnalysis.csv"

# ===== END INPUT =====


def import_data(scale_file, temp_file):

    dtypes = [("vals", "<f8"), ("dates", "datetime64[s]")]

    scale_data = np.genfromtxt(scale_file, delimiter=",", dtype=dtypes)
    temp_data = np.genfromtxt(temp_file, delimiter=",", dtype=dtypes)

    return scale_data, temp_data


def filter_and_match(scale_data, temp_data):
    """
    Remove outliers with a median filter.
    Matches timestamps to the accuracy above.
    """
    filtered_data = np.empty_like(scale_data)
    filtered_data["vals"] = medfilt(scale_data["vals"], kernel_size=7)
    filtered_data["dates"] = scale_data["dates"]

    scale_data = filtered_data

    match_indexes = np.zeros(len(scale_data))
    match_scores = np.zeros(len(scale_data))

    for scale_ind in range(len(scale_data)):
        scores = np.zeros(len(temp_data))
        for temp_ind in range(len(temp_data)):
            scores[temp_ind] = np.abs(
                (scale_data["dates"][scale_ind] - temp_data["dates"][temp_ind])
                / np.timedelta64(1, "s")
            )

        match_indexes[scale_ind] = np.argmin(scores)
        match_scores[scale_ind] = np.min(scores)

    match_indexes = match_indexes[match_scores < BAD_TIMING_THRESHOLD]

    match_indexes = match_indexes[match_indexes < min(len(temp_data), len(scale_data))]

    scale_data = scale_data[match_indexes.astype(np.int64)]
    temp_data = temp_data[match_indexes.astype(np.int64)]

    return scale_data, temp_data

# RUN ANALYSIS

start_time = datetime.strptime(start_time, input_time_format)
end_time = datetime.strptime(end_time, input_time_format)

date_range = np.arange(start_time, end_time, dtype="datetime64[D]")
date_range = np.append(date_range, np.datetime64(end_time, "D")).astype("datetime64[s]")

date_pairs = list(zip(date_range, date_range[1:]))

with open(out_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(
        [
            "start date",
            "end date",
            "num scale points",
            "num temp points",
            "percentage correct before match",
            "num after match",
            "percentage correct after match",
        ]
    )

    for start_time, end_time in date_pairs:
        print(f"Running with {str(start_time)[:10]} to {str(end_time)[:10]} temp")

        trim(start_time, end_time)

        scale_data, temp_data = import_data(
            r"Data\hm-scale-trimmed.csv", r"Data\hm-temp-trimmed.csv"
        )
        
        num_scale = scale_data.size
        num_temp = temp_data.size
        
        if (scale_data.size > 10) and (temp_data.size > 10):
            scale_data, temp_data = filter_and_match(scale_data, temp_data)
            num_after_match = scale_data.size
        else:
            num_after_match = 0

        writer.writerow(
                [
                    str(start_time)[:10],
                    str(end_time)[:10],
                    num_scale,
                    num_temp,
                    (num_scale/644),
                    num_after_match,
                    (num_after_match/644),
                ]
            )