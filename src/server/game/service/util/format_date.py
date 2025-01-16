def format_date(day: int, month: int, year: int):
    season = "зима"
    if month >= 11 or month <= 1:
        season = "зима"
    if month >= 2 or month <= 4:
        season = "весна"
    if month >= 5 or month <= 7:
        season = "лето"
    if month >= 8 or month <= 10:
        season = "осень"

    months = ["Утренней Звезды", "Восхода Солнца", "Первого зерна", "Руки дождя", "Второго зерна",
              "середины года", "Высокого Солнца", "Последнего зерна", "Огня очага", "Начала морозов",
              "Заката Солнца", "Вечерней звезды",
              "Вечерней звезды"]
    return f"День {day} месяца {months[month]}, {season}, год {year} Третьей Эры."
