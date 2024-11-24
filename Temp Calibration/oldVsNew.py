import numpy as np
import matplotlib.pyplot as plt

# ===== INPUT =====

WEIGHT_ON_SCALE = 50.09  #  lbs, 50 before 11/21/2024

# ===== END INPUT =====

# === IMPORT DATA ===

dtypes = [("vals", "<f8"), ("dates", "datetime64[s]")]

old_scale_data = np.genfromtxt("hm-old-scale-trimmed.csv", delimiter=",", dtype=dtypes)
old_temp_data = np.genfromtxt("hm-old-temp-trimmed.csv", delimiter=",", dtype=dtypes)

#  print(old_scale_data[:3])
#  print(old_temp_data[:3])

# === FILTER DATAS ===


def reject_outliers(data, m=2.0):
    data_vals = data["vals"]
    d = np.abs(data_vals - np.median(data_vals))
    mdev = np.median(d)
    s = d / mdev if mdev else np.zeros(len(d))
    return data[s < m]


old_scale_data = reject_outliers(old_scale_data)

matched_dates = np.intersect1d(old_scale_data["dates"], old_temp_data["dates"])
scale_indexes = np.searchsorted(old_scale_data["dates"], matched_dates)
temp_indexes = np.searchsorted(old_temp_data["dates"], matched_dates)

old_scale_data = old_scale_data[scale_indexes]
old_temp_data = old_temp_data[temp_indexes]

old_scale_vals = old_scale_data["vals"]

print(f"old scale len {len(old_scale_data)}")
print(f"old temp len  {len(old_temp_data)}")

scale_data = np.genfromtxt("hm-scale-trimmed.csv", delimiter=",", dtype=dtypes)
temp_data = np.genfromtxt("hm-temp-trimmed.csv", delimiter=",", dtype=dtypes)

scale_data = reject_outliers(scale_data)

matched_dates = np.intersect1d(scale_data["dates"], temp_data["dates"])
scale_indexes = np.searchsorted(scale_data["dates"], matched_dates)
temp_indexes = np.searchsorted(temp_data["dates"], matched_dates)

scale_data = scale_data[scale_indexes]
temp_data = temp_data[temp_indexes]

scale_vals = scale_data["vals"]

print(f"scale len {len(scale_data)}")
print(f"temp len  {len(temp_data)}")

# cpu temp stuff

cpu_scale_data = np.genfromtxt("hm-scale-trimmed.csv", delimiter=",", dtype=dtypes)
cpu_temp_data = np.genfromtxt("hm-cpu-trimmed.csv", delimiter=",", dtype=dtypes)

cpu_scale_data = reject_outliers(cpu_scale_data)

matched_dates = np.intersect1d(cpu_scale_data["dates"], cpu_temp_data["dates"])
scale_indexes = np.searchsorted(cpu_scale_data["dates"], matched_dates)
temp_indexes = np.searchsorted(cpu_temp_data["dates"], matched_dates)

cpu_scale_data = cpu_scale_data[scale_indexes]
cpu_temp_data = cpu_temp_data[temp_indexes]

cpu_scale_vals = cpu_scale_data["vals"]

print(f"cpu scale len {len(cpu_scale_data)}")
print(f"cpu temp len  {len(cpu_temp_data)}")

# === DATAS READY ===

plt.scatter(old_temp_data["vals"], old_scale_vals, label="outside temp data")
plt.scatter(temp_data["vals"], scale_vals, label="scale temp data")
# plt.scatter(cpu_temp_data['vals'], cpu_scale_vals, label='cpu data')
plt.legend(loc="upper left")
plt.show()
