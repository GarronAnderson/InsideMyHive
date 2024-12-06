import numpy as np
import matplotlib.pyplot as plt

# === IMPORT DATA ===

dtypes = [("vals", "<f8"), ("dates", "datetime64[s]")]

scale_data = np.genfromtxt("hm-scale-trimmed.csv", delimiter=",", dtype=dtypes)
temp_data = np.genfromtxt("hm-temp-trimmed.csv", delimiter=",", dtype=dtypes)

#  print(scale_data[:3])
#  print(temp_data[:3])

# === FILTER DATAS ===


def reject_outliers(data, m=2.0):
    try:
        data_vals = data['vals']
    except:
        data_vals = data
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

tdiff = np.diff(temp_data['dates'])

tdiff_secs = tdiff / np.timedelta64(1, 's')
tdiff_mins = tdiff_secs / 60


hist = np.histogram(tdiff_mins, bins=250)

bin_vals = np.insert(hist[1][:-1], 0, 0)
bin_data = np.insert(hist[0], 0, 0)

datas = np.zeros(len(bin_data))

for i, (bin_val, data) in enumerate(zip(bin_vals, bin_data)):
    datas[i] = data * bin_val

fig, ax1 = plt.subplots()

ax1.plot(bin_vals, datas)

ax1.set_xlabel('Delta T between IO uploads [min]')

# Add y-axis label
ax1.set_ylabel('Delays Imposed [min]')
#ax.hist(np.log(tdiff_mins))

ax2 = ax1.twinx()
ax1.set_xlim(0, 60)

ax2.plot(bin_vals, bin_data, 'g')

ax2.set_ylabel('Number of Delays')

plt.xticks(range(0, int(max(bin_vals)), 30))
plt.yticks(range(0, int(max(bin_data)), 30))

ax1.set_xlim(0, 45)


plt.show()