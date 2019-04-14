import inspect
import os
import sys
from datetime import datetime
from shutil import copyfile

import yaml

import site_analyzer


def get_path():
    return os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))


if __name__ == "__main__":
    if not os.path.exists(get_path() + '/config.yml'):
        copyfile(get_path() + '/resources/config.yml', get_path() + '/config.yml')
    try:
        with open(get_path() + '/config.yml', 'r') as ymlfile:
            cfg = yaml.load(ymlfile)
    except (OSError, IOError):
        sys.exit('Ошибка чтения файла конфигурации config.yml')

    now = datetime.now()

    for sc in cfg['sites']:
        site = site_analyzer.Site(sc)
        try:
            if sc["check-ping"]:
                site.check_ping()
            if sc["check-content"]:
                site.check_content()
            if sc["check-errors"]:
                site.check_errors()
            site.check_performance()
            if sc["report"] == str(now.hour) + ":" + str(now.minute):
                site.generate_report()
        except Exception as e:
            site.anxiety("*Обнаружена прочая неисправность на сайте " + sc["address"] + "*\n\n_" + str(e) + "_")
        except:
            site.anxiety("*Обнаружена неизвестная ошибка при мониторинге!*")
