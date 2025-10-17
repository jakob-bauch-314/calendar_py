from playwright.sync_api import sync_playwright
from lxml import etree, html
import ics
from datetime import datetime

class OnlineEventDataBase:

    def __init__(self):
        self.base_url = None
        self.login_url = None
        self.name_field = None
        self.password_field = None
        self.login_button = None

    # abstract method page operations

    def login(self, page, name, password):
        page.goto(f"{self.base_url}/{self.login_url}")
        page.wait_for_load_state(f"networkidle")
        page.fill(self.name_field, name)
        page.fill(self.password_field, password)
        page.click(self.login_button)
        page.wait_for_load_state(f"networkidle")

    def logout(self, page):
        print("abstract method 'logout' not implemented")

    def navigateToBasePage(self, page):
        print("abstract method 'navigateToBasePage' not implemented")

    def navigateToSubpage(self, page, subpage_name):
        print("abstract method 'navigateToSubPage' not implemented")

    def extractTableFromSubpage(self, page, subpage_name):
        print("abstract method 'extractTableFromSubpage' not implemented")

    # abstract others

    def getEventFromRow(self, row):
        print("abstract method 'getEventsFromRow' not implemented")
    
    # methods

    def getEventsFromTable(self, table, skip=1):
        events = []
        
        # Skip header rows and process data
        for row in table[skip:]:
            event = self.getEventFromRow(row)
            if event:
                events.append(event)

        return events

    def getSubpageEvents(self, page, subpage_name):
        table = self.extractTableFromSubpage(page, subpage_name)
        return self.getEventsFromTable(table)

    def getEvents(self, name, password, subpage_name_list):

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)  # set True for headless
            page = browser.new_page()

            # LOGIN
            self.login(page, name, password)

            # GET EVENTS FOR EACH SUBPAGE
            event_list = []
            for subpage_name in subpage_name_list:
                print(f"Fetching events for {subpage_name}...")
                subpage_event_list = self.getSubpageEvents(page, subpage_name)
                event_list.extend(subpage_event_list)
                print(f"Found {len(event_list)} events for {subpage_name}")

            browser.close()
            return event_list

class UniversityPage(OnlineEventDataBase):

    def __init__(self):
        self.schedule_url = "cst_pages/meinstundenplanstudent.aspx?node=48c364b0-3f23-4a58-a027-d7544585b0c4&tabkey=webtab_cst_lektionenstudent"
        self.field_name_prefix = "ctl00$WebPartManager1$gwp"
        self.login_name_prefix = "Login1$Login1$LoginMask"
        self.schedule_name_prefix = "MeinStundenplanStudent$MeinStundenplanStudent"

        self.base_url = "https://campus.ku.de"
        self.login_url = "Evt_Pages/Login.aspx"
        self.name_field = f'input[name="{self.field_name_prefix}{self.login_name_prefix}$UserName"]'
        self.password_field = f'input[name="{self.field_name_prefix}{self.login_name_prefix}$Password"]'
        self.login_button = f'input[name="{self.field_name_prefix}{self.login_name_prefix}$LoginButton"]'
    
    def extractTableFromSubpage(self, page, Subpage):
        # NAVIGATE TO SCHEDULE PAGE
        page.goto(f"{self.base_url}/{self.schedule_url}")
        page.wait_for_load_state(f"networkidle")

        # SELECT YEAR
        page.select_option(f'select[name="{self.field_name_prefix}{self.schedule_name_prefix}$ddlPeriodeList"]', label=Subpage)

        # SEARCH FOR SCHEDULE
        page.click(f'input[name="{self.field_name_prefix}{self.schedule_name_prefix}$btnSearch2"]')
        page.wait_for_load_state(f"networkidle")

        # GO TO PRINT VIEW
        page.goto(f"{self.base_url}/{self.schedule_url}&Print=true")
        page.wait_for_load_state(f"networkidle")

        table = html.fromstring(page.content()).xpath(f'//table[contains(@class, "result-grid")]')[0][0]
        return table

    def getEventFromRow(self, row):
        try:
            # parsing data
            datum = row[0][0].text.strip() if len(row) > 0 and len(row[0]) > 0 and row[0][0].text else ""
            bezeichnung = row[1][0][1].text.strip() if len(row) > 1 and len(row[1][0]) > 1 and row[1][0][1].text else ""
            raum = row[2][0].text.strip() if len(row) > 2 and len(row[2]) > 0 and row[2][0].text else ""
            dozent = row[3][0].text.strip() if len(row) > 3 and len(row[3]) > 0 and row[3][0].text else ""
            
            # Construct link if available
            link = ""
            if len(row) > 1 and len(row[1][0]) > 1 and row[1][0][1].get(f"href"):
                link = f"{self.base_url}/cst_pages/{"/".join(row[1][0][1].attrib["href"].split(f"/")[2:])}"

            # Skip if no date information
            if not datum:
                return None

            # preparing date
            date, begin_time, _, end_time = tuple(datum.split(f" "))
            year = int(date[6:10])
            month = int(date[3:5])
            day = int(date[0:2])
            begin_hour = int(begin_time[0:2])
            begin_minute = int(begin_time[3:5])
            end_hour = int(end_time[0:2])
            end_minute = int(end_time[3:5])
            
            begin = datetime(year, month, day, begin_hour, begin_minute, 0)
            end = datetime(year, month, day, end_hour, end_minute, 0)

            # Create ics event
            event = ics.Event(
                name=bezeichnung,
                begin=begin,
                end=end,
                description=dozent,
                url=link,
                location=raum
            )
            
            return event
            
        except Exception as e:
            print(f"Error parsing event row: {e}")
            return None