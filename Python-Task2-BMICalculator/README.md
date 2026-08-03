# Smart BMI Tracker

A desktop-based Body Mass Index (BMI) calculator built with Python and Tkinter. The application lets users calculate BMI, save records, view history, export data, and explore analytics through charts.

## Features

- Calculate BMI using height and weight
- Supports age, name, and gender input
- BMI category classification:
  - Underweight
  - Normal Weight
  - Overweight
  - Obese
- BMI gauge and personalised health tips
- Save BMI records in an SQLite database
- Search, refresh, and delete BMI history records
- Export BMI history to a CSV file
- Analytics dashboard with:
  - Total records and average BMI
  - BMI category summary cards
  - BMI trend chart
  - BMI category distribution pie chart
- Scrollable Analytics and About BMI tabs
- Detailed About BMI page with formula, categories, health tips, and disclaimer

## Input Limits

For valid BMI calculations, the application accepts:

| Input | Allowed Range |
|---|---|
| Age | 1 to 120 years |
| Height | 50 to 300 cm |
| Weight | 2 to 500 kg |

If a value is outside these limits, the application displays a validation message instead of saving a BMI record.

## Technologies Used

- Python
- Tkinter
- SQLite
- Matplotlib

## Project Structure

```text
Python-Task2-BMICalculator/
├── main.py              # Main Tkinter application
├── bmi.py               # BMI calculation and category logic
├── charts.py            # Gauge and analytics chart logic
├── database.py          # SQLite database operations
├── export.py            # CSV export feature
├── requirements.txt     # Project dependency
├── .gitignore
└── README.md
```

## Installation

1. Clone the repository:

```bash
git clone https://github.com/YOUR-USERNAME/OIBSIP.git
```

2. Move into the project folder:

```bash
cd OIBSIP/Python-Task2-BMICalculator
```

3. Install the required package:

```bash
python -m pip install -r requirements.txt
```

## Run the Application

```bash
python main.py
```

## BMI Formula

```text
BMI = Weight (kg) / Height² (m²)
```

Example:

```text
Weight = 60 kg
Height = 1.70 m

BMI = 60 / (1.70 × 1.70)
BMI = 20.76
```

## BMI Categories

| Category | BMI Range |
|---|---|
| Underweight | Below 18.5 |
| Normal Weight | 18.5 – 24.9 |
| Overweight | 25.0 – 29.9 |
| Obese | 30 and above |

## Disclaimer

This application is intended for educational purposes only. BMI is only a screening tool and should not replace professional medical advice.

## Author

Dhaarani P M