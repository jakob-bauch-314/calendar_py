from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from zoneinfo import ZoneInfo
from lxml import etree, html

import urllib.parse
import semesters
import requests
import logging
import json
import ics
import os

logging.basicConfig(level=logging.INFO)

class OnlineEventDataBase(ABC):
    tz, base_url, login_url, name_field, password_field, login_button, logout_button = [None] * 7

    def __init__(self, name, password):
        self.name = name
        self.password = password

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
    def fetch_raw_data(self, page, subpage_name): # RETURNS ANYTHING
        pass

    @abstractmethod
    def parse_raw_data(self, raw_data) -> list:
        pass

    @abstractmethod
    def parse_event(self, raw_event, subpage_name) -> ics.Event | None:
        pass

    @abstractmethod
    def get_subpage_name_list_from_dates(self, page, start, end) -> list[str]:
        pass
    
    # export

    def export(self, start_date, end_date, filename, headless):

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()

            try:
                self.login(page)
            except Exception as e:
                print(f"Can't log in: {e}")
                return
            
            try:
                subpage_name_list = self.get_subpage_name_list_from_dates(page, start_date, end_date)
            except Exception as e:
                print(f"Can't get subpage name list: {e}")
                return

            event_list = []            
            for subpage_name in subpage_name_list:

                logging.info(f"Fetching events for {subpage_name}...")

                try:
                    raw_data = self.fetch_raw_data(page, subpage_name)
                except Exception as e:
                    logging.warning(f"Can't fetch data: {e}")
                    continue

                try:
                    data = self.parse_raw_data(raw_data)
                except Exception as e:
                    logging.warning(f"Can't parse data: {e}")
                    continue

                subpage_event_list = []
                for raw_event in data:
                    try:
                        event = self.parse_event(raw_event, subpage_name)
                    except Exception as e:
                        logging.warning(f"Can't parse event: {e}")
                        continue
                    if event: # filter out None
                        subpage_event_list.append(event)

                logging.info(f"Found {len(subpage_event_list)} events for {subpage_name}")
                event_list.extend(subpage_event_list)
            
            try:
                self.logout(page)
            except Exception as e:
                logging.warning("Can't log out: {e}")
    
            browser.close()

            calendar = ics.Calendar(events=event_list)
            os.makedirs("calendars", exist_ok=True)
            with open(f"calendars/{filename}", 'w', encoding='utf-8') as file:
                file.write(calendar.serialize())

    
class WorkPage(OnlineEventDataBase):

    # page
    schedule_url = "teacher/course-index"
    base_url = "https://schug-russer.icas7.de/app/#"
    login_url = "login"

    # elements
    name_field = f'input[name="username"]'
    password_field = f'input[name="password"]'
    login_button = f'button[type="submit"]'
    logout_button = f'button[ng-click="$ctrl.logout()"]'

    # timezone
    tz = ZoneInfo("Europe/Berlin")

    def __init__(self, name, password, teacher_id):
        super().__init__(name, password)
        self.teacher_id = teacher_id

    def fetch_raw_data(self, page, subpage_name):
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
                "present": subpage_name,
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

    def parse_event(self, raw_event, subpage_name):
        if raw_event["course_members_excused"] >= raw_event["course_members_total"]:
            return None
        
        students = [m["pupil_display_name"] for m in raw_event["course_member"]]
        begin=datetime.strptime(f"{subpage_name} {raw_event['starts_at']}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=self.tz),
        end=datetime.strptime(f"{subpage_name} {raw_event['ends_at']}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=self.tz),

        return ics.Event(
            name="Nachhilfe",
            begin=begin,
            end=end,
            description=f"Fach {raw_event["subject_short"]},\nSchüler:\n{'\n'.join(students)}",
            location=f"room {raw_event["room"]}"
        )
    
    def get_subpage_name_list_from_dates(self, page, start_date, end_date):
        return list(map(lambda x: (start_date + timedelta(days=x)).strftime("%Y-%m-%d"),range((end_date - start_date).days + 1)))

class UniversityPage(OnlineEventDataBase):

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

    # timezone
    tz = ZoneInfo("Europe/Berlin")
    
    def fetch_raw_data(self, page, subpage_name):
        # NAVIGATE TO SCHEDULE PAGE
        page.goto(f"{self.base_url}/{self.schedule_url}")
        page.wait_for_load_state(f"networkidle")
        page.select_option(f'select[name="{self.field_name_prefix}{self.schedule_name_prefix}$ddlPeriodeList"]', label=subpage_name)

        # SEARCH FOR SCHEDULE

        page.click(f'input[name="{self.field_name_prefix}{self.schedule_name_prefix}$btnSearch2"]')
        page.wait_for_load_state(f"networkidle")

        # GO TO PRINT VIEW
        page.goto(f"{self.base_url}/{self.schedule_url}&Print=true")
        page.wait_for_load_state(f"networkidle")

        return page.content()

    def parse_raw_data(self, raw_data):
        return html.fromstring(raw_data).xpath(f'//table[contains(@class, "result-grid")]')[0][0][1:]

    def parse_event(self, raw_event, subpage_name):

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
        begin = datetime.strptime(f"{date_part} {start_time}", "%d.%m.%Y %H:%M").replace(tzinfo=self.tz)
        end   = datetime.strptime(f"{date_part} {end_time}", "%d.%m.%Y %H:%M").replace(tzinfo=self.tz)

        # Create ics event
        return ics.Event(name=name, begin=begin, end=end, description=prof, url=link, location=room)

    def get_subpage_name_list_from_dates(self, page, start_date, end_date):

        page.goto(f"{self.base_url}/{self.schedule_url}")
        page.wait_for_load_state(f"networkidle")
        all_options = page.locator(f'select[name="{self.field_name_prefix}{self.schedule_name_prefix}$ddlPeriodeList"] option').all_inner_texts()
        options_in_time_range = list(map(semesters.index_to_text, range(semesters.semester_index(start_date), semesters.semester_index(end_date)+1)))
        return list(set(all_options) & set(options_in_time_range))
