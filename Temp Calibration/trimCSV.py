import csv
from datetime import datetime

input_time_format = "%Y-%m-%d"
time_format = "%Y-%m-%d %H:%M:%S"

start_time = "2024-12-24"
end_time = "2024-12-25"

start_time = datetime.strptime(start_time, input_time_format)
end_time = datetime.strptime(end_time, input_time_format)

def trim(start_time, end_time):
    for filename_in, filename_out in [
        ("hm-temp.csv", "hm-temp-trimmed.csv"),
        ("hm-scale.csv", "hm-scale-trimmed.csv"),
        ("hm-cpu.csv", "hm-cpu-trimmed.csv"),
        ("hm-thermo.csv", "hm-thermo-trimmed.csv"),
        ("hm-batt.csv", "hm-batt-trimmed.csv"),
    ]:
        with open(filename_in, "r") as file_in:
            with open(filename_out, "w") as file_out:
                if __name__ == '__main__':
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
                    if __name__ == '__main__':
                        if line_count % 1000 == 0:
                            print(f"Parsed {line_count} rows")
                            
if __name__ == '__main__':
    trim(start_time, end_time)
