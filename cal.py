from lxml import etree
import datetime

class calendar():
    def __init__(self, events):
        self.events = events
    def add_event(self, event):
        self.events.append(event)
    def export(self):
        output = ""
        output += "BEGIN:VCALENDAR\n"
        for event in self.events:
            output += event.export()
        output += "END:VCALENDAR\n"
        return output
    def __add__(self, other):
        return calendar(self.events+other.events)
    def __iadd__(self, other):
        self.events += other.events
        return self
    
    @staticmethod
    def import_from_html(tbody):
        return calendar(list(map(lambda row: event.import_from_html(row), tbody[1:])))

class event():

    def __init__(self,
                 begin=datetime.date(1970, 1, 1),
                 end=datetime.date(1970, 1, 1),
                 summary="new event",
                 description="",
                 link="",
                 location = ""):
        self.begin = begin
        self.end = end
        self.summary = summary
        self.description = description
        self.link = link
        self.location = location

    def export(self):
        output = ""
        output += "BEGIN:VEVENT\n"
        if type(self.begin) == datetime.date:
            output += "DTSTART;VALUE=DATE:" + self.begin.strftime("%Y%m%d") + "\n"
        elif type(self.begin) == datetime.datetime:
            output += "DTSTART:" + self.begin.strftime("%Y%m%dT%H%M%S") + "\n"
        if type(self.end) == datetime.date:
            output += "DTEND;VALUE=DATE:" + self.end.strftime("%Y%m%d") + "\n"
        elif type(self.end) == datetime.datetime:
            output += "DTEND:" + self.end.strftime("%Y%m%dT%H%M%S") + "\n"
        output += "SUMMARY:" + self.summary + "\n"
        if (len(self.description) > 0):
            output += "DESCRIPTION:" + self.description + "\n"
        if (len(self.link) > 0):
            output += "URL:" + self.link + "\n"
        if (len(self.location) > 0):
            output += "LOCATION:" + self.location + "\n"
        output += "END:VEVENT\n"
        return output
    
    @staticmethod
    def import_from_html(row):

        # parsing data
        datum      = row[0][0].text.strip() if len(row) > 0 and len(row[0]) > 0 and row[0][0].text else ""
        bezeichnung = row[1][0][1].text.strip() if len(row) > 1 and len(row[1][0]) > 1 and row[1][0][1].text else ""
        raum       = row[2][0].text.strip() if len(row) > 2 and len(row[2]) > 0 and row[2][0].text else ""
        dozent     = row[3][0].text.strip() if len(row) > 3 and len(row[3]) > 0 and row[3][0].text else ""
        link = "https://campus.ku.de/cst_pages/" + "/".join(row[1][0][1].attrib["href"].split("/")[2:])

        # preparing date
        date, begin_time, _, end_time = tuple(datum.split(" "))
        year = int(date[6:10])
        month = int(date[3:5])
        day = int(date[0:2])
        begin_hour = int(begin_time[0:2])
        begin_minute = int(begin_time[3:5])
        end_hour = int(end_time[0:2])
        end_minute = int(end_time[3:5])
        begin = datetime.datetime(year, month, day, begin_hour, begin_minute, 0)
        end = datetime.datetime(year, month, day, end_hour, end_minute, 0)

        return event(begin=begin, end=end, summary=bezeichnung, description=dozent, link=link, location=raum)