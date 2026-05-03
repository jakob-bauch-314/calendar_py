from dateutil.relativedelta import relativedelta
from datetime import datetime
import argparse
from calendar_handler import RadicaleCalendar
from scraper import UniversityEventSource, WorkEventSource

parser = argparse.ArgumentParser()
parser.add_argument("--site", help="site name", default="uni")
parser.add_argument("--username", help="username for site login", default="your_username")
parser.add_argument("--password", help="password for site login", default="your_password")
parser.add_argument("--path", help="radicale calendar path", default="./calendars/uni")
args = parser.parse_args()

start_date = datetime.today() - relativedelta(weeks=1)
end_date = datetime.today() + relativedelta(weeks=1)
radicale_calendar = RadicaleCalendar(args.path)
cal = {
    "uni": UniversityEventSource,
    "work": WorkEventSource
}[args.site](args.username, args.password).export(start_date, end_date, False)

radicale_calendar.mirror(cal.events, start_date, end_date)