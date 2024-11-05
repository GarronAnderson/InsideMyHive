import csv

for filename in ['hm-temp.csv', 'hm-scale.csv']:
    with open(filename, 'r') as file:
        csv_reader = csv.reader(file)
        line_count = 0
        for row in csv_reader:
            if line_count < 20:
                print(row)
                line_count += 1
            else:
                break
