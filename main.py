import ics
import scraper

semesters = [
    "Wintersemester 2025 / 2026",
    "Sommersemester 2025",
    "Wintersemester 2024 / 2025"
]

university_page = scraper.UniversityPage()

# Get all events from all semesters
# events = university_page.getEvents(input("name: "), input("password: "), semesters)
events = university_page.getEvents("MGS31253", "oSgPS8D$hyUV", semesters)

# Create calendar and add all events
calendar = ics.Calendar(events=events)

print(f"Total events found: {len(events)}")

# Export to ics format
with open("calendar.ics", 'w', encoding='utf-8') as file:
    file.write(calendar.serialize())

print("Calendar successfully exported to calendar.ics")