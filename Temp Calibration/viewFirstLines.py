import csv

for filename in [r"Data\hm-temp-trimmed.csv", r"Data\hm-scale-trimmed.csv"]:
    with open(filename, "r") as file:
        csv_reader = csv.reader(file)
        line_count = 0
        for row in csv_reader:
            if line_count < 10:
                print(row)
                line_count += 1
            else:
                break
