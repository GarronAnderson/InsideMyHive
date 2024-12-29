import csv

import numpy as np

with open("autoTest.csv") as f:
    reader = csv.DictReader(f)
    data_list = list(reader)
