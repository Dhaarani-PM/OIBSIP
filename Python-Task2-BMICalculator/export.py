import csv

from database import fetch_bmi_records


def export_bmi_history(csv_file_path):
    records = fetch_bmi_records()
    with open(csv_file_path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow([
            "Date", "Name", "Age", "Gender", "Height (cm)",
            "Weight (kg)", "BMI", "Category",
        ])
        writer.writerows(record[1:] for record in records)
    return len(records)
