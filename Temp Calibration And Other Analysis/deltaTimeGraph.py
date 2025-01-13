import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import medfilt

BAD_TIMING_THRESHOLD = 10  # seconds


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


scale_data, temp_data = import_data(
    r"Data\hm-scale-trimmed.csv", r"Data\hm-temp-trimmed.csv"
)

scale_data, temp_data = filter_and_match(scale_data, temp_data)


print(f"scale len {len(scale_data)}")
print(f"temp len  {len(temp_data)}")

# === DATAS READY ===

tdiff = np.diff(scale_data["dates"])

tdiff_secs = tdiff / np.timedelta64(1, "s")
tdiff_mins = tdiff_secs / 60


hist = np.histogram(tdiff_mins, bins=250)

bin_vals = np.insert(hist[1][:-1], 0, 0)
bin_data = np.insert(hist[0], 0, 0)

datas = np.zeros(len(bin_data))

for i, (bin_val, data) in enumerate(zip(bin_vals, bin_data)):
    datas[i] = data * bin_val

fig, ax1 = plt.subplots()

ax1.plot(bin_vals, datas)

ax1.set_xlabel("Delta T between IO uploads [min]")

# Add y-axis label
ax1.set_ylabel("Delays Imposed [min]")
# ax.hist(np.log(tdiff_mins))

ax2 = ax1.twinx()

ax2.plot(bin_vals, bin_data, "g")

ax2.set_ylabel("Number of Delays")

plt.show()
