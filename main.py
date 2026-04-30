import ics
import scraper
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

start_date = datetime.today() - relativedelta(years=1)
end_date = datetime.today() + relativedelta(years=1)

scraper.UniversityPage("your_username", "your_password").export(start_date, end_date, "university.ics", True)
scraper.WorkPage("your_username", "your_password", "2339300042").export(start_date, end_date, "work.ics", True)
