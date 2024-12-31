import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from scipy.interpolate import interp1d
from scipy.signal import medfilt

# ===== INPUT =====

WEIGHT_ON_SCALE = 50.09  #  lbs, 50 before 11/21/2024

BAD_TIMING_THRESHOLD = 10  # seconds

r_min, r_max, r_step, t0_min, t0_max, t0_step = 0.0025, 0.05, 0.001, -12, 15, 0.5

# ===== END INPUT =====

# === IMPORT DATA ===


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
    filtered_data["vals"] = medfilt(scale_data["vals"], kernel_size=15)
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


def fit_correction(temp_data, scale_data):
    coef = np.polyfit(temp_data, scale_data["vals"], 1)
    return coef


def check_goodness(scale_data, temp_vals):
    scale_data["vals"] = scale_data["vals"]
    coef = fit_correction(temp_vals, scale_data)

    #  corrected scale reading
    avg_cal_val = np.mean(scale_data["vals"])
    lbs_reading = (scale_data["vals"] * WEIGHT_ON_SCALE) / avg_cal_val

    corrected_scale = scale_data["vals"] - (temp_vals * coef[0])
    avg_cal_val = np.mean(corrected_scale)
    lbs_reading_corrected = (corrected_scale * WEIGHT_ON_SCALE) / avg_cal_val

    score = np.ptp(lbs_reading_corrected)

    return score


def estimate_r_t0(scale_data, temp_data, r_min, r_max, r_step, t0_min, t0_max, t0_step):
    r_vals = np.arange(r_min, r_max, r_step)
    t0_vals = np.arange(t0_min, t0_max, t0_step)

    estimates = np.zeros((len(t0_vals), len(r_vals), len(temp_data)))
    for i, r in enumerate(r_vals):
        for j, t0 in enumerate(t0_vals):
            estimates[j][i] = run_temp_estimation(scale_data, temp_data, r, t0)

    return r_vals, t0_vals, estimates


def find_best_r_t0(
    scale_data, temp_data, r_min, r_max, r_step, t0_min, t0_max, t0_step
):
    r_vals, t0_vals, estimates = estimate_r_t0(
        scale_data, temp_data, r_min, r_max, r_step, t0_min, t0_max, t0_step
    )

    scores = np.zeros((len(r_vals), len(t0_vals)))

    for i, row in enumerate(estimates):
        for j, est in enumerate(row):
            scores[j][i] = check_goodness(scale_data, est)

    best_r_index = np.unravel_index(scores.argmin(), scores.shape)

    best_r = r_vals[best_r_index[0]]
    best_t0 = t0_vals[best_r_index[1]]

    return r_vals, t0_vals, scores, best_r, best_t0


def correct_readings(scale_data, temp_data, best_r, best_t0):
    best_estimates = run_temp_estimation(scale_data, temp_data, best_r, best_t0)
    coef = fit_correction(best_estimates, scale_data)

    avg_cal_val = np.mean(scale_data["vals"])
    lbs_reading = (scale_data["vals"] * WEIGHT_ON_SCALE) / avg_cal_val

    corrected_scale = scale_data["vals"] - (best_estimates * coef[0])
    avg_cal_val = np.mean(corrected_scale)
    lbs_reading_corrected = (corrected_scale * WEIGHT_ON_SCALE) / avg_cal_val

    simple_coef = fit_correction(temp_data["vals"], scale_data)
    simple_corrected_scale = scale_data["vals"] - (temp_data["vals"] * simple_coef[0])
    simple_avg_cal_val = np.mean(simple_corrected_scale)
    lbs_reading_simple = (simple_corrected_scale * WEIGHT_ON_SCALE) / simple_avg_cal_val

    return lbs_reading, lbs_reading_corrected, lbs_reading_simple


# USE THIS CODE WHEN NOT IMPORTING

if __name__ == "__main__":
    scale_data, temp_data = import_data(r"Data\hm-scale-trimmed.csv", r"Data\hm-thermo-trimmed.csv")

    scale_data, temp_data = filter_and_match(scale_data, temp_data)

    r_vals, t0_vals, scores, best_r, best_t0 = find_best_r_t0(
        scale_data, temp_data, r_min, r_max, r_step, t0_min, t0_max, t0_step
    )

    lbs_reading, lbs_reading_corrected, lbs_reading_simple = correct_readings(
        scale_data, temp_data, best_r, best_t0
    )
    _, lbs_reading_t0_0, _ = correct_readings(scale_data, temp_data, best_r, 0)

    best_estimates = run_temp_estimation(scale_data, temp_data, best_r, best_t0)
    coef = fit_correction(best_estimates, scale_data)

    mapper = interp1d(
        [min(scale_data["vals"]), max(scale_data["vals"])],
        [max(best_estimates), min(best_estimates)],
    )
    data_mapped = mapper(scale_data["vals"])

    print(f"BEST R VALUE:            {best_r:.03f}")
    print(f"BEST t0     :            {best_t0:.03f}")
    print(f"NO CORRECTION DEVIATION: {np.ptp(lbs_reading):.03f} lbs")
    print(f"MAX DEVIATION:           {np.ptp(lbs_reading_corrected):.03f} lbs")
    print(f"SIMPLE MAX DEVIATION:    {np.ptp(lbs_reading_simple):.03f} lbs")
    print(f"NO t0 DEVIATION:         {np.ptp(lbs_reading_t0_0):.03f} lbs")
    Y, X = np.meshgrid(t0_vals, r_vals)

    fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
    surf = ax.plot_surface(
        X, Y, scores, cmap=cm.coolwarm, linewidth=0, antialiased=False
    )
    ax.set_ylabel("Delta T0 [deg F]")
    ax.set_xlabel("R val [no dim]")
    ax.set_zlabel("P2P dev [lbs]")
    plt.show()

    plt.scatter(temp_data["vals"], scale_data["vals"], label="raw temp")
    plt.scatter(best_estimates, scale_data["vals"], label="est temp")
    plt.plot(temp_data["vals"], coef[1] + coef[0] * temp_data["vals"], "k--")
    plt.legend(loc="upper left")
    plt.show()

    plt.plot(temp_data["dates"], lbs_reading, "g", label="reading [lbs]")
    plt.plot(
        temp_data["dates"], lbs_reading_corrected, "b", label="reading corrected [lbs]"
    )
    plt.plot(
        temp_data["dates"], lbs_reading_simple, label="reading corrected simple [lbs]"
    )
    plt.plot(temp_data["dates"], lbs_reading_t0_0, label="no t0 correction [lbs]")
    plt.legend(loc="upper left")
    plt.show()
