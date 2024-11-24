import csv
from datetime import datetime

time_format = "%Y-%m-%d %H:%M:%S"

start_time = "2024-11-23 00:00:00"
start_time = datetime.strptime(start_time, time_format)

end_time = "2024-11-24 00:00:00"
end_time = datetime.strptime(end_time, time_format)

for filename_in, filename_out in [
    ("hm-temp.csv", "hm-temp-trimmed.csv"),
    ("hm-scale.csv", "hm-scale-trimmed.csv"),
    ("hm-cpu.csv", "hm-cpu-trimmed.csv"),

]:
    with open(filename_in, "r") as file_in:
        with open(filename_out, "w") as file_out:
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
                if line_count % 1000 == 0:
                    print(f"Parsed {line_count} rows")
