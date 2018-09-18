import os
import sys
from datetime import date, timedelta
import time
from pprint import pprint

import requests
import telegram as telegram
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

import Main


def get_service(api_name, api_version, scopes, key_file_location):
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        key_file_location, scopes=scopes)

    # Build the service object.
    service = build(api_name, api_version, credentials=credentials)

    return service


class Site:

    def __init__(self, config):
        self.cfg = config
        self.content = ""
        if not os.path.isfile(Main.get_path() + '/client_secrets.json'):
            sys.exit('Не найден необходимый файл client_secrets.json')
        self.service = get_service(
            api_name='analytics',
            api_version='v3',
            scopes=['https://www.googleapis.com/auth/analytics.readonly'],
            key_file_location=Main.get_path() + '/client_secrets.json'
        )
        self.bot = telegram.Bot(token=config["telegram"]["token"])
        self.response = requests.get(self.cfg["address"])
        self.prohibited_words = ("Warning", "PHP", "MYSQL")

    def check_ping(self):
        if self.response.status_code != 200:
            self.anxiety(
                "*Обнаружена неисправность*\n\n_Сайт не отвечает. Код HTTP ошибки:_ " +
                str(self.response.status_code))

    def check_content(self):
        if len(self.response.content) < 40000:
            self.anxiety("*Обнаружена неисправность*\n\n_Подозрительный вывод на сайте_")

    def check_errors(self):
        content = self.response.content.decode('UTF-8')
        for word in self.prohibited_words:
            if content.find(word) != -1:
                self.anxiety("*Обнаружена неисправность*\n\n_Ошибки в алгоритме_" + word)

    def anxiety(self, message):
        if os.path.isfile("last-report.txt"):
            with open("last-report.txt", "r") as file:
                last = file.read()
                if last.isdigit():
                    last = int(last)
                else:
                    last = 0
                if (time.time() - last < 3600 * 2):
                    file.close()
                    sys.exit()
        with open("last-report.txt", "w") as f:
            f.write(str(round(time.time())))
            f.close()
        self.telegram_send(message)
        self.telegram_report()
        sys.exit()

    def telegram_report(self):
        document = open("report.txt", "wb")
        if len(self.response.content) > 0:
            document.write(self.response.content)
            document.close()
            document = open("report.txt", "rb")
            self.bot.send_document(chat_id=self.cfg["telegram"]["group"],
                                   document=document,
                                   filename="Crash_" + self.cfg["address"] + "_" + date.today().strftime('%y%m%d') + ".txt")
            document.close()
            os.remove("report.txt")

    def telegram_send(self, message):
        print(message)
        self.bot.send_message(chat_id=self.cfg["telegram"]["group"], text=message, parse_mode="Markdown")

    def generate_report(self):
        yesterday = (date.today() - timedelta(1)).strftime('%y%m%d')
        visitors = self.service.data().ga().get(
            ids=self.cfg["google-analytics"]["table-id"],
            start_date=self.cfg['google-analytics']['from'],
            end_date=self.cfg['google-analytics']['to'],
            dimensions='ga:date',
            metrics='ga:visitors'
        ).execute()
        maxv = visitors['rows'][-1]
        minv = visitors['rows'][-1]
        for day in visitors['rows']:
            if day[1] > maxv[1]:
                maxv = day
            if day[1] < minv[1]:
                minv = day
        if maxv[0] == yesterday:
            self.telegram_send("Вчера было зафиксировано самое высокое количество посетителей за 2 недели: " + maxv[1])
        if minv[0] == yesterday:
            self.telegram_send("Вчера было зафиксировано самое низкое количество посетителей за 2 недели: " + maxv[1])

        visits = self.service.data().ga().get(
            ids=self.cfg["google-analytics"]["table-id"],
            start_date=self.cfg['google-analytics']['from'],
            end_date=self.cfg['google-analytics']['to'],
            dimensions='ga:date',
            metrics='ga:visits'
        ).execute()
        maxv = visits['rows'][-1]
        minv = visits['rows'][-1]
        for day in visits['rows']:
            if day[1] > maxv[1]:
                maxv = day
            if day[1] < minv[1]:
                minv = day
        if maxv[0] == yesterday:
            self.telegram_send(
                "Вчера было зафиксировано самое высокое количество просмотров за 2 недели: *"
                + maxv[1] + "*")
        if minv[0] == yesterday:
            self.telegram_send(
                "Вчера было зафиксировано самое низкое количество просмотров за 2 недели: *"
                + maxv[1] + "*")

        self.telegram_send("Посетители: *" + visitors['rows'][-1][1] + "*\nПросмотры: *" + visits['rows'][-1][1] + "*")
