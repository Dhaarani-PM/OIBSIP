def calculate_bmi(height_cm, weight_kg):
    height_cm = float(height_cm)
    weight_kg = float(weight_kg)
    if height_cm <= 0 or weight_kg <= 0:
        raise ValueError("Height and weight must be greater than zero.")
    return round(weight_kg / (height_cm / 100) ** 2, 2)


def get_bmi_category(age, bmi):
    if int(age) < 18:
        return "Growth Chart Required", "#2563EB"
    if bmi < 18.5:
        return "Underweight", "#2563EB"
    if bmi < 25:
        return "Normal Weight", "#16A34A"
    if bmi < 30:
        return "Overweight", "#F97316"
    return "Obese", "#DC2626"
