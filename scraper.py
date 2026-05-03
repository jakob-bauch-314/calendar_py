
from playwright.sync_api import sync_playwright
from datetime import datetime, date, time, timedelta, timezone
from abc import ABC, abstractmethod
from lxml import etree, html
from text_engine import normalize

import urllib.parse
import semesters
import requests
import logging
import json
import ics
import os
import re

logging.basicConfig(level=logging.INFO)

class Event(ABC):

    def __init__(self, begin, end):
        self.begin = begin
        self.end = end

    @abstractmethod
    def export(self) -> ics.Event:
        pass

    @abstractmethod
    def category(self) -> str:
        pass

class EventScope(ABC):

    def label(self):
        return self.key()

    @abstractmethod
    def key(self):
        pass

#    @abstractmethod
#    def begin(self):
#        pass
#
#    @abstractmethod
#    def end(self):
#        pass

class UIDGenerator():

    def __init__(self):
        self.counter = dict()

    def generate(self, event, eventscope):
        if eventscope.key() not in self.counter.keys():
            self.counter[eventscope.key()] = dict()
        if event.category() not in self.counter[eventscope.key()].keys():
            self.counter[eventscope.key()][event.category()] = 0
        self.counter[eventscope.key()][event.category()] += 1

        return f"{eventscope.key()}_{event.category()}_{self.counter[eventscope.key()][event.category()]}"

class EventSource(ABC):
    base_url, login_url, name_field, password_field, login_button, logout_button = [None] * 6

    def __init__(self, name, password):
        self.name = name
        self.password = password
        self.uid_generator = UIDGenerator()

    # page operations

    def login(self, page):
        page.goto(f"{self.base_url}/{self.login_url}")
        page.wait_for_load_state(f"networkidle")
        page.fill(self.name_field, self.name)
        page.fill(self.password_field, self.password)
        page.click(self.login_button)
        page.wait_for_load_state(f"networkidle")
    
    def logout(self, page):
        page.goto(f"{self.base_url}")
        page.wait_for_load_state(f"networkidle")
        page.click(self.logout_button)
        page.wait_for_load_state(f"networkidle")
    
    # abstract methods
    
    @abstractmethod
    def fetch_raw_data(self, page, eventscope): # RETURNS ANYTHING
        pass

    @abstractmethod
    def parse_raw_data(self, raw_data) -> list:
        pass

    @abstractmethod
    def parse_event(self, raw_event, eventscope) -> ics.Event | None:
        pass

    @abstractmethod
    def eventscopes(self, page, start, end) -> list[str]:
        pass
    
    # export

    def process_scope(self, page, eventscope):

        logging.info(f"Fetching events for {eventscope.label()}...")

        try:
            raw_data = self.fetch_raw_data(page, eventscope)
        except Exception as e:
            logging.warning(f"Can't fetch data: {e}")
            return []
        try:
            data = self.parse_raw_data(raw_data)
        except Exception as e:
            logging.warning(f"Can't parse data: {e}")
            return []

        eventscope_event_list = []
        for raw_event in data:
            try:
                event = self.parse_event(raw_event, eventscope)
            except Exception as e:
                logging.warning(f"Can't parse event: {e}")
                continue
            if event: # filter out None
                ics_event = event.export()
                ics_event.uid = self.uid_generator.generate(event, eventscope)
                eventscope_event_list.append(ics_event)

        logging.info(f"Found {len(eventscope_event_list)} events for {eventscope.label()}")
        return eventscope_event_list

    def export(self, start_date, end_date, headless):

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()

            try:
                self.login(page)
            except Exception as e:
                logging.error(f"Can't log in: {e}")
                return
            
            try:
                eventscopes = self.eventscopes(page, start_date, end_date)
            except Exception as e:
                logging.error(f"Can't get eventscope name list: {e}")
                return

            event_list = []
            for eventscope in eventscopes:
                event_list.extend(self.process_scope(page, eventscope))
            
            try:
                self.logout(page)
            except Exception as e:
                logging.warning(f"Can't log out: {e}")
    
            browser.close()

            return ics.Calendar(events=event_list)

class WorkEvent(Event):
    def __init__(self, begin, end, students, room, subject):
        super().__init__(begin, end)
        self.students = students
        self.room = room
        self.subject = subject
    
    def export(self):
        return ics.Event(
            name="Nachhilfe",
            begin=self.begin,
            end=self.end,
            description=f"Fach {self.subject},\nSchüler:\n{'\n'.join(self.students)}",
            location=f"room {self.room}"
        )

    def category(self):
        return ""

class WorkDay(EventScope):
    def __init__(self, date):
        self.date = date
    
    def label(self):
        return self.date.strftime("%Y-%m-%d")
    
    def key(self):
        return self.date.strftime("%Y-%m-%d")
    
class WorkEventSource(EventSource):

    # page
    schedule_url = "teacher/course-index"
    base_url = "https://schug-russer.icas7.de/app/#"
    login_url = "login"

    # elements
    name_field = f'input[name="username"]'
    password_field = f'input[name="password"]'
    login_button = f'button[type="submit"]'
    logout_button = f'button[ng-click="$ctrl.logout()"]'

    def __init__(self, name, password, teacher_id):
        super().__init__(name, password)
        self.teacher_id = teacher_id

    def fetch_raw_data(self, page, eventscope):
        page.locator("a", has_text="Kurse").click()
        page.wait_for_timeout(1000)
        cookies = page.context.cookies()
        icas_cookie = next(c for c in cookies if c["name"] == "icas_user")
        decoded = urllib.parse.unquote(icas_cookie["value"])
        data = json.loads(decoded)
        token = data["access_token"]

        # request
        return page.context.request.get(
            "https://schug-russer.icas7.de/courselist",
            params={
                "present": eventscope.label(),
                "teacher_id": self.teacher_id
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://schug-russer.icas7.de/app/",
                "X-Requested-With": "XMLHttpRequest"
            }
        )
    
    def parse_raw_data(self, raw_data):
        return raw_data.json()["courselist"]

    def parse_event(self, raw_event, eventscope):
        if raw_event["course_members_excused"] >= raw_event["course_members_total"]:
            return None
        
        students = [m["pupil_display_name"] for m in raw_event["course_member"]]
        begin = datetime.combine(eventscope.date, time.strptime(raw_event['starts_at'], "%H:%M:%S").time())
        end = datetime.combine(eventscope.date, time.strptime(raw_event['ends_at'], "%H:%M:%S").time())
        subject = raw_event["subject_short"]
        room = raw_event["room"]

        return WorkEvent(begin, end, students, room, subject)
    
    def eventscopes(self, page, start_date, end_date):
        return [ WorkDay((start_date + timedelta(days=shift))) for shift in range((end_date - start_date).days + 1)]

class Semester(EventScope):

    wintersemester_start = datetime(70, 10, 1)
    sommersemester_start = datetime(70, 4, 1)

    def __init__(self, index):
        self.index = index
    
    def label(self):
        type = self.index % 2
        year = self.index // 2

        if type == 1:
            return f"Wintersemester {year} / {year + 1}"
        else:
            return f"Sommersemester {year}"
    
    def key(self):
        type = self.index % 2
        year = self.index // 2

        if type == 1:
            return f"ws{str(year)[2:]}"
        else:
            return f"ss{str(year)[2:]}"
    
    def category(self):
        return normalize(self.course)

    @staticmethod
    def from_date(date):
        if (date > Semester.sommersemester_start.replace(year=date.year)):
            year = date.year
            if (date < Semester.wintersemester_start.replace(year=date.year)):
                type = 0 # sommersemester
            else:
                type = 1 # wintersemester
        else:
            year = date.year - 1
            type = 1 # wintersemester
        return Semester(2 * year + type)

class UniversityEvent(Event):

    def __init__(self, begin, end, prof, room, course, link):
        super().__init__(begin, end)
        self.prof = prof
        self.room = room
        self.course = course
        self.link = link
    
    def export(self):
        return ics.Event(name=self.course, begin=self.begin, end=self.end, description=self.prof, url=self.link, location=self.room)
    
    def category(self):
        return normalize(self.course)

class UniversityEventSource(EventSource):

    # pages
    schedule_url = "cst_pages/meinstundenplanstudent.aspx?node=48c364b0-3f23-4a58-a027-d7544585b0c4&tabkey=webtab_cst_lektionenstudent"
    base_url = "https://campus.ku.de"
    login_url = "Evt_Pages/Login.aspx"
    
    # elements
    field_name_prefix = "ctl00$WebPartManager1$gwp"
    login_name_prefix = "Login1$Login1$LoginMask"
    schedule_name_prefix = "MeinStundenplanStudent$MeinStundenplanStudent"
    name_field = f'input[name="{field_name_prefix}{login_name_prefix}$UserName"]'
    password_field = f'input[name="{field_name_prefix}{login_name_prefix}$Password"]'
    login_button = f'input[name="{field_name_prefix}{login_name_prefix}$LoginButton"]'
    logout_button = 'a[id="ctl00_lnkLogInOut"]'
    
    def fetch_raw_data(self, page, eventscope):
        # NAVIGATE TO SCHEDULE PAGE
        page.goto(f"{self.base_url}/{self.schedule_url}")
        page.wait_for_load_state(f"networkidle")
        page.select_option(f'select[name="{self.field_name_prefix}{self.schedule_name_prefix}$ddlPeriodeList"]', label=eventscope.label())

        # SEARCH FOR SCHEDULE

        page.click(f'input[name="{self.field_name_prefix}{self.schedule_name_prefix}$btnSearch2"]')
        page.wait_for_load_state(f"networkidle")

        # GO TO PRINT VIEW
        page.goto(f"{self.base_url}/{self.schedule_url}&Print=true")
        page.wait_for_load_state(f"networkidle")

        return page.content()

    def parse_raw_data(self, raw_data):
        return html.fromstring(raw_data).xpath(f'//table[contains(@class, "result-grid")]')[0][0][1:]

    def parse_event(self, raw_event, eventscope):

        # parsing data
        raw_date =  raw_event[0][0].text.strip() if len(raw_event) > 0 and len(raw_event[0]) > 0 and raw_event[0][0].text else ""
        name =      raw_event[1][0][1].text.strip() if len(raw_event) > 1 and len(raw_event[1][0]) > 1 and raw_event[1][0][1].text else ""
        room =      raw_event[2][0].text.strip() if len(raw_event) > 2 and len(raw_event[2]) > 0 and raw_event[2][0].text else ""
        prof =      raw_event[3][0].text.strip() if len(raw_event) > 3 and len(raw_event[3]) > 0 and raw_event[3][0].text else ""
        
        # Construct link if available
        link = ""
        if len(raw_event) > 1 and len(raw_event[1][0]) > 1 and raw_event[1][0][1].get(f"href"):
            link = f"{self.base_url}/cst_pages/{"/".join(raw_event[1][0][1].attrib["href"].split(f"/")[2:])}"

        # Skip if no date information
        if not raw_date:
            return None

        # preparing date
        date_part, time_range = raw_date.split(" ", 1)
        start_time, end_time = time_range.split(" - ")
        begin = datetime.strptime(f"{date_part} {start_time}", "%d.%m.%Y %H:%M")
        end   = datetime.strptime(f"{date_part} {end_time}", "%d.%m.%Y %H:%M")

        # Create ics event
        return UniversityEvent(begin, end, prof, room, name, link)
        #return ics.Event(name=name, begin=begin, end=end, description=prof, url=link, location=room)

    def eventscopes(self, page, start_date, end_date):

        semesters_in_time_range = [Semester(i) for i in range(Semester.from_date(start_date).index, Semester.from_date(end_date).index+1)]
        page.goto(f"{self.base_url}/{self.schedule_url}")
        page.wait_for_load_state(f"networkidle")
        selectable_semester_names = page.locator(f'select[name="{self.field_name_prefix}{self.schedule_name_prefix}$ddlPeriodeList"] option').all_inner_texts()
        return [semester for semester in semesters_in_time_range if semester.label() in selectable_semester_names]