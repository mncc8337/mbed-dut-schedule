import requests
from helper import *

LOGIN_URL = "https://sv.dut.udn.vn/PageDangNhap.aspx"
HOME_URL = "https://sv.dut.udn.vn/PageCaNhan.aspx"
SCHEDULE_URL = "https://sv.dut.udn.vn/PageLichTH.aspx"

class Scraper:
    def __init__(self, user, password):
        self.user = user
        self.password = password


        # get login html to get session id and some hidden ASP fields
        resp = requests.get(LOGIN_URL)
        login_html = resp.text

        self.headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": resp.headers["Set-Cookie"]
        }

        self.__VIEWSTATE = get_hidden_field(login_html, "__VIEWSTATE")

        self.__VIEWSTATEGENERATOR = get_hidden_field(login_html, "__VIEWSTATEGENERATOR")

    def login(self):
        request_data = {
            "_ctl0:MainContent:DN_txtPass": self.password,
            "_ctl0:MainContent:DN_txtAcc": self.user,
            "_ctl0:MainContent:QLTH_btnLogin": "Đăng+nhập",
            "__VIEWSTATEGENERATOR": self.__VIEWSTATEGENERATOR,
            "__VIEWSTATE": self.__VIEWSTATE,
        }
        encoded_data = '&'.join(f"{quote_plus(k)}={quote_plus(v)}" for k, v in request_data.items())
        resp = requests.post(
            LOGIN_URL,
            data=encoded_data,
            headers=self.headers,
        )

        if resp.status_code != 200:
            raise Exception("got status code " + str(resp.status_code))

        if resp.url == LOGIN_URL:
            raise Exception("wrong username/password, got redirected to " + resp.url)

        if resp.url != HOME_URL:
            raise Exception("unknown error, got redirected to " + resp.url)

    def get_schedule(self, print_table=False):
        resp = requests.get(SCHEDULE_URL, timeout=20, headers=self.headers)
        schedule_html = resp.text

        if resp.status_code != 200 or resp.url != SCHEDULE_URL:
            raise Exception("failed to reach to schedule page, got status code " + str(resp.status_code) + "and redirected to page " + resp.url)

        table = extract_table_html(schedule_html, "TTKB_GridInfo")
        if not table:
            raise Exception("no table found on the schedule page")

        table_rows = parse_table_rows(table)
        table_headers = table_rows[1]
        table_headers.insert(0, "TT")
        # remove headers row
        table_rows.pop(0)
        table_rows.pop(0)
        # remove total row
        table_rows.pop(-1)

        schedule = []

        for row in table_rows:
            tkb = row[7].split(",")
            tiet = tkb[1].split("-")
            tiet_bat_dau = int(tiet[0])
            tiet_ket_thuc = int(tiet[1])
            tuan_hoc = []
            for dur in row[8].split(";"):
                lst = dur.split("-")
                tuan_hoc.append([int(lst[0]), int(lst[1])])

            dat = {
                "ma lop": row[1],
                "ten lop": row[2],
                "so tc": row[3],
                "giang vien": row[6],
                "ngay hoc": tkb[0],
                "tiet bat dau": tiet_bat_dau,
                "tiet ket thuc": tiet_ket_thuc,
                "phong": tkb[2],
                "tuan hoc": tuan_hoc,
            }
            schedule.append(dat)

            if print_table:
                for i in range(len(row)):
                    if row[i]:
                        print(i, table_headers[i], ":", row[i])
                print()

        return schedule
