from playwright.sync_api import sync_playwright
from lxml import etree, html

def login(page, name, password):
    page.goto("https://campus.ku.de/Evt_Pages/Login.aspx")
    page.wait_for_load_state("networkidle")
    page.fill('input[name="ctl00$WebPartManager1$gwpLogin1$Login1$LoginMask$UserName"]', name)
    page.fill('input[name="ctl00$WebPartManager1$gwpLogin1$Login1$LoginMask$Password"]', password)
    page.click('input[name="ctl00$WebPartManager1$gwpLogin1$Login1$LoginMask$LoginButton"]')
    page.wait_for_load_state("networkidle")


def getSemesterHtml(page, semester):
    # NAVIGATE TO SCHEDULE PAGE
    page.goto("https://campus.ku.de/cst_pages/meinstundenplanstudent.aspx?node=48c364b0-3f23-4a58-a027-d7544585b0c4&tabkey=webtab_cst_lektionenstudent")
    page.wait_for_load_state("networkidle")

    # SELECT YEAR
    page.select_option('select[name="ctl00$WebPartManager1$gwpMeinStundenplanStudent$MeinStundenplanStudent$ddlPeriodeList"]', label=semester)

    # SEARCH FOR SCHEDULE
    page.click('input[name="ctl00$WebPartManager1$gwpMeinStundenplanStudent$MeinStundenplanStudent$btnSearch2"]')
    page.wait_for_load_state("networkidle")

    # GO TO PRINT VIEW
    page.goto("https://campus.ku.de/cst_pages/meinstundenplanstudent.aspx?node=48c364b0-3f23-4a58-a027-d7544585b0c4&tabkey=webtab_cst_lektionenstudent&Print=true")
    page.wait_for_load_state("networkidle")

    return html.fromstring(page.content()).xpath('//table[contains(@class, "result-grid")]')[0][0]

def getScheduleHtml(name, password, semesters):

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # set True for headless
        page = browser.new_page()

        # LOGIN
        login(page, name, password)

        # GET HTML
        html_list = list(map(lambda semester: getSemesterHtml(page, semester), semesters))

        # RETURN HTML
        return html_list
        browser.close()