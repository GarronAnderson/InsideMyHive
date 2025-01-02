import csv

import numpy as np

with open(r"Data\autoTest.csv") as f:
    reader = csv.DictReader(f)
    data_list = list(reader)
