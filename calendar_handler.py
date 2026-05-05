
import os
import ics
from ics import Calendar
import uuid
from datetime import timezone, timedelta, datetime
import text_engine
from zoneinfo import ZoneInfo

class RadicaleCalendar():

    file_ending = ".org.ics"
    def __init__(self, folder):
        self.folder = folder
        self.i = 0
        os.makedirs(folder, exist_ok=True)

        props_file_path = f"{folder}/.Radicale.props"
        if not os.path.exists(props_file_path):
            with open(props_file_path, 'w') as file:
                file.write('{"tag": "VCALENDAR"}')
        else:
            pass

    def keys(self):
        return [filename[0:-len(self.file_ending)] for filename in os.listdir(self.folder) if filename.endswith(self.file_ending)]

    def items(self):
        for uid in self:
            yield uid, self[uid]

    def __getitem__(self, uid):
        with open(os.path.join(self.folder, f"{uid}{self.file_ending}")) as f:
            cal = Calendar(f.read())
        return next(iter(cal.events))
    
    def __setitem__(self, uid, event):
        calendar = ics.Calendar(events=[event])
        path = os.path.join(self.folder, f"{uid}{self.file_ending}")
        with open(path, 'w', encoding='utf-8') as file:
            file.write(calendar.serialize())

    def __delitem__(self, uid):
        os.remove(os.path.join(self.folder, f"{uid}{self.file_ending}"))

    def __iter__(self):
        uids = self.keys()
        return iter(zip(uids, map(self.__getitem__, uids)))
    
    def __len__(self):
        return len(self.keys())

    def __contains__(self, uid):
        return os.path.exists(os.path.join(self.folder, f"{uid}{self.file_ending}"))
    
    def append(self, event):
        pass

    def mirror(self, events, start_date, end_date):
        for uid, event in self:
            event_begin = event.begin.to('UTC')
            if start_date < event_begin < end_date and uid not in [new_event.uid for new_event in events]:
                del self[uid]
        
        for event in events:
            self[event.uid] = event