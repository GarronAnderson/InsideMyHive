import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from scipy.interpolate import interp1d

# ===== INPUT =====

WEIGHT_ON_SCALE = 50.09  #  lbs, 50 before 11/21/2024

# ===== END INPUT =====

# === IMPORT DATA ===

dtypes = [("vals", "<f8"), ("dates", "datetime64[s]")]

scale_data = np.genfromtxt("hm-scale-trimmed.csv", delimiter=",", dtype=dtypes)
#temp_data = np.genfromtxt("hm-temp-trimmed.csv", delimiter=",", dtype=dtypes)
temp_data = np.genfromtxt("hm-thermo-trimmed.csv", delimiter=",", dtype=dtypes)


#  print(scale_data[:3])
#  print(temp_data[:3])

# === FILTER DATAS ===

print(f'start {len(scale_data)}')


def reject_outliers(data, m=2.75):
    data_vals = data["vals"]
    d = np.abs(data_vals - np.median(data_vals))
    mdev = np.median(d)
    s = d / mdev if mdev else np.zeros(len(d))
    return data[s < m]

plt.plot(scale_data['dates'], scale_data['vals'])
scale_data = reject_outliers(scale_data)
plt.plot(scale_data['dates'], scale_data['vals'])
plt.show()

plt.plot(np.diff(scale_data['vals']))
plt.show()
#print(f'outlier rejection scale {len(scale_data)}')
#print(f'outlier rejection temp {len(temp_data)}')

#matched_dates = np.intersect1d(scale_data["dates"], temp_data["dates"])
#scale_indexes = np.searchsorted(scale_data["dates"], matched_dates)
#temp_indexes = np.searchsorted(temp_data["dates"], matched_dates)

#scale_data = scale_data[scale_indexes]
#temp_data = temp_data[temp_indexes]

scale_vals = scale_data["vals"]

print(f"scale len {len(scale_data)}")
print(f"temp len  {len(temp_data)}")

# === DATAS READY ===


def run_temp_estimation(scale_data, temp_data, r, t0):
    scale_temp = temp_data["vals"][0] + t0
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


def check_goodness(temp_vals):
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


def estimate_r_t0(scale_data, temp_data, r_min, r_max, r_step, t0_min, t0_max, t0_step):
    r_vals = np.arange(r_min, r_max, r_step)
    t0_vals = np.arange(t0_min, t0_max, t0_step)

    estimates = np.zeros((len(t0_vals), len(r_vals), len(temp_data)))
    for i, r in enumerate(r_vals):
        for j, t0 in enumerate(t0_vals):
            estimates[j][i] = run_temp_estimation(scale_data, temp_data, r, t0)

    return r_vals, t0_vals, estimates


# === PROCESS DATAS ===

# run newtons
r_vals, t0_vals, estimates = estimate_r_t0(
    scale_data, temp_data, 0.05, 0.2, 0.01, -5, 15, 0.5
)

scores = np.zeros((len(r_vals), len(t0_vals)))

for i, row in enumerate(estimates):
    for j, est in enumerate(row):
        scores[j][i] = check_goodness(est)


best_r_index = np.unravel_index(scores.argmin(), scores.shape)

best_r = r_vals[best_r_index[0]]
best_t0 = t0_vals[best_r_index[1]]

best_estimates = run_temp_estimation(scale_data, temp_data, best_r, best_t0)
coef = fit_correction(best_estimates, scale_vals)


#  corrected scale reading
avg_cal_val = np.mean(scale_vals)
lbs_reading = (scale_vals * WEIGHT_ON_SCALE) / avg_cal_val

corrected_scale = scale_vals - (best_estimates * coef[0])
avg_cal_val = np.mean(corrected_scale)
lbs_reading_corrected = (corrected_scale * WEIGHT_ON_SCALE) / avg_cal_val

simple_coef = fit_correction(temp_data['vals'], scale_vals)
simple_corrected_scale = scale_vals - (temp_data['vals'] * simple_coef[0])
simple_avg_cal_val = np.mean(simple_corrected_scale)
lbs_reading_simple = (simple_corrected_scale * WEIGHT_ON_SCALE) / simple_avg_cal_val

mapper = interp1d(
    [min(scale_vals), max(scale_vals)], [max(best_estimates), min(best_estimates)]
)
data_mapped = mapper(scale_vals)

print(f"BEST R VALUE:         {best_r:.03f}")
print(f"BEST t0     :         {best_t0:.03f}")
print(f"MAX DEVIATION:        {np.ptp(lbs_reading_corrected):.03f} lbs")
print(f"SIMPLE MAX DEVIATION: {np.ptp(lbs_reading_simple):.03f} lbs")

# plt.plot(temp_data["dates"], temp_data["vals"], label="temp data [deg F]")
# plt.plot(temp_data["dates"], best_estimates, label="est temps [deg F]")
# plt.plot(temp_data["dates"], data_mapped, label="scale data [mapped]")
# plt.legend(loc="upper left")
# plt.show()

Y, X = np.meshgrid(t0_vals, r_vals)
print(X.shape, Y.shape)

fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
surf = ax.plot_surface(X, Y, scores, cmap=cm.coolwarm, linewidth=0, antialiased=False)
ax.set_ylabel("Delta T0 [deg F]")
ax.set_xlabel("R val [no dim]")
ax.set_zlabel("P2P dev [lbs]")
plt.show()

fig, (ax1, ax2) = plt.subplots(1, 2)
ax1.scatter(temp_data["vals"], scale_data["vals"], label="raw temp")
ax1.scatter(best_estimates, scale_data["vals"], label="est temp")
ax1.plot(temp_data["vals"], coef[1] + coef[0] * temp_data["vals"], "k--")
ax1.legend(loc="upper left")

ax2.plot(temp_data["dates"], lbs_reading, "g", label="reading [lbs]")
ax2.plot(
    temp_data["dates"], lbs_reading_corrected, "b", label="reading corrected [lbs]"
)
ax2.plot(
    temp_data["dates"], lbs_reading_simple, label="reading corrected simple [lbs]"
)
ax2.legend(loc="upper left")

fig.set_figwidth(12)
fig.show()