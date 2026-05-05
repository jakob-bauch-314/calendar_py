from dateutil.relativedelta import relativedelta
from datetime import datetime
import argparse
from calendar_handler import RadicaleCalendar
from scraper import UniversityEventSource, WorkEventSource
from zoneinfo import ZoneInfo

def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d")

def parse_source(value):
    return {
        "uni": UniversityEventSource,
        "work": WorkEventSource
    }[value]

tz = ZoneInfo("Europe/Berlin")
today = datetime.today().replace(tzinfo=tz)

parser = argparse.ArgumentParser()
parser.add_argument("--source", help="source name", default="uni")
parser.add_argument("--username", help="username for source login", required=True)
parser.add_argument("--password", help="password for source login", required=True)
parser.add_argument("--path", help="radicale calendar path", default="./calendars/uni")
parser.add_argument("--headless", help="set browser to headless", default=True, type=bool)
parser.add_argument("--start", help="sync from this time", type=parse_date, default=today - relativedelta(weeks=1))
parser.add_argument("--end", help="sync until this time", type=parse_date, default=today + relativedelta(weeks=4))

args = parser.parse_args()

radicale_calendar = RadicaleCalendar(args.path)
cal = {
    "uni": UniversityEventSource,
    "work": WorkEventSource
}[args.source](args.username, args.password).export(args.start, args.end, False)

radicale_calendar.mirror(cal.events, args.start, args.end)