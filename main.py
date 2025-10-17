import cal
import scraper

semesters = [
    "Wintersemester 2025 / 2026",
    "Sommersemester 2025",
    "Wintersemester 2024 / 2025"
]

html_list = scraper.getScheduleHtml(input("name: "), input("password: "), semesters)
output = sum(map(cal.calendar.import_from_html, html_list), start=cal.calendar([])).export()

with open("calendar.ics", 'w') as file:
    file.seek(0)
    file.truncate()
    file.write(output)