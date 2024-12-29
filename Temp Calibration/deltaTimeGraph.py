import numpy as np
import matplotlib.pyplot as plt

# === IMPORT DATA ===

dtypes = [("vals", "<f8"), ("dates", "datetime64[s]")]

scale_data = np.genfromtxt(r"Data\hm-scale-trimmed.csv", delimiter=",", dtype=dtypes)
temp_data = np.genfromtxt(r"Data\hm-temp-trimmed.csv", delimiter=",", dtype=dtypes)


print(f"scale len {len(scale_data)}")
print(f"temp len  {len(temp_data)}")

# === DATAS READY ===

tdiff = np.diff(temp_data["dates"])

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
