import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from scipy.interpolate import interp1d
from scipy.signal import medfilt

# === IMPORT DATA ===

window_size = 20

dtypes = [("vals", "<f8"), ("dates", "datetime64[s]")]

batt_data = np.genfromtxt("hm-batt-trimmed.csv", delimiter=",", dtype=dtypes)

diffs = (
    np.diff(batt_data["vals"]) / np.diff(batt_data["dates"]).astype(np.float64) * 3600
)

weights = np.ones(window_size) / window_size
sma = np.convolve(diffs, weights, mode="valid")

# sma_filt = medfilt(sma, kernel_size=41)

plt.plot(batt_data["dates"][:-window_size][sma<0], sma[sma<0])
# plt.plot(batt_data['dates'][:-window_size], sma_filt)

plt.axhline(y=0, color="k", linestyle="-")
plt.show()

plt.plot(batt_data["dates"][:-window_size], sma, ".")
plt.show()
