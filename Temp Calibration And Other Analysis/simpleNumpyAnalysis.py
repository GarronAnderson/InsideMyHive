import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

# ===== INPUT =====

WEIGHT_ON_SCALE = 50.09  #  lbs, 50 before 11/21/2024

# ===== END INPUT =====

# === IMPORT DATA ===

dtypes = [("vals", "<f8"), ("dates", "datetime64[s]")]

scale_data = np.genfromtxt(r"Data\hm-scale-trimmed.csv", delimiter=",", dtype=dtypes)
temp_data = np.genfromtxt(r"Data\hm-temp-trimmed.csv", delimiter=",", dtype=dtypes)

#  print(scale_data[:3])
#  print(temp_data[:3])

# === FILTER DATAS ===


def reject_outliers(data, m=2.0):
    data_vals = data["vals"]
    d = np.abs(data_vals - np.median(data_vals))
    mdev = np.median(d)
    s = d / mdev if mdev else np.zeros(len(d))
    return data[s < m]


scale_data = reject_outliers(scale_data)

matched_dates = np.intersect1d(scale_data["dates"], temp_data["dates"])
scale_indexes = np.searchsorted(scale_data["dates"], matched_dates)
temp_indexes = np.searchsorted(temp_data["dates"], matched_dates)

scale_data = scale_data[scale_indexes]
temp_data = temp_data[temp_indexes]

scale_vals = scale_data["vals"]

print(f"scale len {len(scale_data)}")
print(f"temp len  {len(temp_data)}")

# === DATAS READY ===


def run_temp_estimation(scale_data, temp_data, r):
    scale_temp = temp_data["vals"][0]
    state_estimates = np.zeros(len(temp_data))
    state_estimates[0] = scale_temp

    for i, air_temp in enumerate(temp_data["vals"]):
        t_diff = air_temp - scale_temp
        delta_temp = r * t_diff
        scale_temp += delta_temp
        state_estimates[i] = scale_temp

    return state_estimates


def fit_correction(temp_data, scale_vals):
    coef = np.polyfit(temp_data, scale_vals, 1)
    return coef


def check_goodness(temp_vals, scale_data):
    scale_vals = scale_data["vals"]
    coef = fit_correction(temp_vals, scale_vals)

    #  corrected scale reading
    avg_cal_val = np.mean(scale_vals)
    lbs_reading = (scale_vals * WEIGHT_ON_SCALE) / avg_cal_val

    corrected_scale = scale_vals - (temp_vals * coef[0])
    avg_cal_val = np.mean(corrected_scale)
    lbs_reading_corrected = (corrected_scale * WEIGHT_ON_SCALE) / avg_cal_val

    score = np.ptp(lbs_reading_corrected)

    return score


def plot_visualizations(
    temp_vals, scale_vals, lbs_reading, lbs_reading_corrected, coef
):
    #  scatter temp/scale
    plt.plot(
        temp_vals, scale_vals, "o", temp_vals, coef[0] * temp_vals + coef[1], "--k"
    )
    plt.show()

    plt.plot(temp_data["dates"], lbs_reading, "g", label="reading [lbs]")
    plt.plot(
        temp_data["dates"], lbs_reading_corrected, "b", label="reading corrected [lbs]"
    )
    plt.legend(loc="upper left")
    plt.show()


def estimate_r_range(scale_data, temp_data, r_min, r_max, r_step):
    r_vals = np.arange(r_min, r_max, r_step)
    estimates = [np.zeros(len(temp_data))] * len(r_vals)
    for i, r in enumerate(r_vals):
        estimates[i] = run_temp_estimation(scale_data, temp_data, r)

    return r_vals, estimates


# === PROCESS DATAS ===

# run newtons
r_vals, estimates = estimate_r_range(scale_data, temp_data, 0.005, 1.01, 0.01)

scores = np.zeros(len(r_vals))
for i, est in enumerate(estimates):
    scores[i] = check_goodness(est, scale_data)


best_r_index = np.argmin(scores)
best_r = r_vals[best_r_index]

best_estimates = run_temp_estimation(scale_data, temp_data, best_r)
coef = fit_correction(best_estimates, scale_vals)


#  corrected scale reading
avg_cal_val = np.mean(scale_vals)
lbs_reading = (scale_vals * WEIGHT_ON_SCALE) / avg_cal_val

corrected_scale = scale_vals - (best_estimates * coef[0])
avg_cal_val = np.mean(corrected_scale)
lbs_reading_corrected = (corrected_scale * WEIGHT_ON_SCALE) / avg_cal_val

mapper = interp1d(
    [min(scale_vals), max(scale_vals)], [max(temp_data["vals"]), min(temp_data["vals"])]
)
data_mapped = mapper(scale_vals)

plt.plot(temp_data["dates"], data_mapped, label="scale data [mapped]")
plt.plot(temp_data["dates"], temp_data["vals"], label="temp data [deg F]")
plt.legend(loc="upper left")
plt.show()

plt.plot(r_vals, scores, label="scores")
plt.legend(loc="upper left")
plt.show()

plt.scatter(temp_data["vals"], scale_data["vals"], label="raw temp")
plt.scatter(best_estimates, scale_data["vals"], label="est temp")
plt.legend(loc="upper left")
plt.show()

plt.plot(temp_data["dates"], lbs_reading, "g", label="reading [lbs]")
plt.plot(
    temp_data["dates"], lbs_reading_corrected, "b", label="reading corrected [lbs]"
)
plt.legend(loc="upper left")
plt.show()

plt.plot(
    temp_data["dates"], lbs_reading_corrected, "b", label="reading corrected [lbs]"
)
plt.legend(loc="upper left")
plt.show()

print(f"BEST R VALUE:  {best_r}")
print(f"MAX DEVIATION: {np.ptp(lbs_reading_corrected)} lbs")
