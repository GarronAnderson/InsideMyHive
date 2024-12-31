import csv
from datetime import datetime

input_time_format = "%Y-%m-%d"
time_format = "%Y-%m-%d %H:%M:%S"

start_time = "2024-12-27"
end_time = "2024-12-28"

start_time = datetime.strptime(start_time, input_time_format)
end_time = datetime.strptime(end_time, input_time_format)


def trim(start_time, end_time):
    for filename_in, filename_out in [
        (r"Data\hm-temp-old-backup.csv", r"Data\hm-temp-trimmed.csv"),
        (r"Data\hm-scale-old-backup.csv", r"Data\hm-scale-trimmed.csv"),
        (r"Data\hm-cpu.csv", r"Data\hm-cpu-trimmed.csv"),
        (r"Data\hm-thermo.csv", r"Data\hm-thermo-trimmed.csv"),
        (r"Data\hm-batt.csv", r"Data\hm-batt-trimmed.csv"),
    ]:
        with open(filename_in, "r") as file_in:
            with open(filename_out, "w") as file_out:
                if __name__ == "__main__":
                    print(f"File: {filename_in}")
                csv_reader = csv.reader(file_in)
                csv_writer = csv.writer(file_out)

                line_count = 0
                for row in csv_reader:
                    if line_count == 0:
                        line_count += 1
                        continue
                    
                    val, date = row[1], row[3][:-4]

                    date_parsed = datetime.strptime(date, time_format)

                    if start_time < date_parsed < end_time:
                        csv_writer.writerow([val, date_parsed])

                    line_count += 1
                    if __name__ == "__main__":
                        if line_count % 1000 == 0:
                            print(f"Parsed {line_count} rows")


if __name__ == "__main__":
    trim(start_time, end_time)
