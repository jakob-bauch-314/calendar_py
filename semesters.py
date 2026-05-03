from datetime import datetime, timedelta, timezone

wintersemester_start = datetime(70, 10, 1)
sommersemester_start = datetime(70, 4, 1)

start_date = datetime(2026, 5, 26)
end_date = datetime(2026, 4, 26)

def semester_index(date):
    if (date > sommersemester_start.replace(year=date.year)):
        year = date.year
        if (date < wintersemester_start.replace(year=date.year)):
            type = 0 # sommersemester
        else:
            type = 1 # wintersemester
    else:
        year = date.year - 1
        type = 1 # wintersemester
    return 2 * year + type

def index_to_text(semester_index):
    type = semester_index % 2
    year = semester_index // 2

    if type == 1:
        return f"Wintersemester {year} / {year + 1}"
    else:
        return f"Sommersemester {year}"

class Semester():

    def __init__(self, index):
        self.index = index
    
    def long_name(self):
        type = self.index % 2
        year = self.index // 2

        if type == 1:
            return f"Wintersemester {year} / {year + 1}"
        else:
            return f"Sommersemester {year}"
    
    def short_name(self):
        type = self.index % 2
        year = self.index // 2

        if type == 1:
            return f"WS{str(year)[2:]}"
        else:
            return f"SS{str(year)[2:]}"