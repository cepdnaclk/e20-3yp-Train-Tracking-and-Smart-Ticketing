# Save as: update_ticket_prices.py

import csv

input_csv = 'ticket_prices.csv'
output_csv = 'ticket_prices_updated.csv'
stations_txt = 'station_ids.txt'

station_ids = {}
next_id = 500

# First pass: collect unique stations from 'To' column in order
with open(input_csv, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        to_station = row['To'].strip()
        if to_station not in station_ids:
            if to_station == 'Colombo Fort':
                station_ids[to_station] = 500
                next_id = 501
            else:
                station_ids[to_station] = next_id
                next_id += 1

# Second pass: write updated CSV with IDs
with open(input_csv, newline='', encoding='utf-8') as f_in, \
     open(output_csv, 'w', newline='', encoding='utf-8') as f_out:
    reader = csv.DictReader(f_in)
    fieldnames = ['From_ID', 'To_ID', 'Distance_km', 'Class_1st_Rs', 'Class_2nd_Rs', 'Class_3rd_Rs']
    writer = csv.DictWriter(f_out, fieldnames=fieldnames)
    writer.writeheader()
    for row in reader:
        from_station = row['From'].strip()
        to_station = row['To'].strip()
        # Assign ID to 'From' if not already assigned
        if from_station not in station_ids:
            station_ids[from_station] = next_id
            next_id += 1
        writer.writerow({
            'From_ID': station_ids[from_station],
            'To_ID': station_ids[to_station],
            'Distance_km': row['Distance_km'],
            'Class_1st_Rs': row['Class_1st_Rs'],
            'Class_2nd_Rs': row['Class_2nd_Rs'],
            'Class_3rd_Rs': row['Class_3rd_Rs'],
        })

# Write station IDs to TXT
with open(stations_txt, 'w', encoding='utf-8') as f:
    for name, sid in sorted(station_ids.items(), key=lambda x: x[1]):
        f.write(f"{name},{sid}\n")