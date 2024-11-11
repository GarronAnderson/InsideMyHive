import numpy as np
import matplotlib.pyplot as plt

# from scipy.interpolate import interp1d

scale_data = np.genfromtxt("hm-scale-trimmed.csv", delimiter=",")

temp_data = np.genfromtxt("hm-temp-trimmed.csv", delimiter=",")

print(temp_data)

scale_data = np.delete(scale_data, 1, 1)
temp_data = np.delete(temp_data, 1, 1)

print(temp_data)

if len(scale_data) > len(temp_data):
    scale_data = scale_data[: len(temp_data)]
else:
    temp_data = temp_data[: len(scale_data)]

# mapper = interp1d([min(scale_data), max(scale_data)], [min(temp_data), max(temp_data)])

# scale_mapped = mapper(scale_data)


# plt.plot(temp_data)
# plt.plot(scale_mapped)
# plt.show()

plt.scatter(scale_data, temp_data)

plt.show()
