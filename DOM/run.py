"""

Подготовка виртуального окружения.
Запуск клиента.

# TODO: Задокументировать код.

"""

import argparse
import os
import sys

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

parser = argparse.ArgumentParser()
parser.add_argument(
    "--env",
    default=r"{LOCALAPPDATA}\DOM",
    type=str,
    help="Путь к директории с файлами игры",
)
parser.add_argument(
    "--ll",
    default="DEBUG",
    type=str,
    choices=["TRACE", "DEBUG", "INFO"],
    help="Уровень логирования",
)
parser.add_argument(
    "--host",
    default="https://dungeon-of-masters.herokuapp.com",
    # default="http://127.0.0.1:5000",  # localhost
    type=str,
    help="Сервер",
)
parser.add_argument(
    "--clear-appdata",
    action="store_true",
)

args = parser.parse_args()

# CONFIG SETUP
# Путь к директории приложения
os.environ["APP_DIR"] = args.env.format(**{k: v for k, v in os.environ.items()})
if not os.path.exists(os.environ["APP_DIR"]):
    os.mkdir(os.environ["APP_DIR"])
# Путь к базе данных
os.environ["DB_PATH"] = os.path.join(os.environ["APP_DIR"], "database.sqlite")
# Путь к файлу отладки
os.environ["DEBUG_PATH"] = os.path.join(os.environ["APP_DIR"], "debug.log")
# Путь к файлу с данными аккаунта
os.environ["AUTH_PATH"] = os.path.join(os.environ["APP_DIR"], ".auth")
# Путь к директории с персонажами
os.environ["CHARACTERS_PATH"] = os.path.join(os.environ["APP_DIR"], "characters")
# Путь к директории с иконками пользователей
os.environ["USER_ICONS_PATH"] = os.path.join(os.environ["APP_DIR"], "user_icons")
# Путь к директории с иконками интерфейса
os.environ["UI_ICONS_PATH"] = os.path.join(os.environ["APP_DIR"], "ui_icons")
# Путь к директории с иконками предметов
os.environ["ITEMS_PATH"] = os.path.join(os.environ["APP_DIR"], "items")
# Путь к директории с рамками предметов
os.environ["ITEM_BORDERS_PATH"] = os.path.join(os.environ["APP_DIR"], "item_borders")
# Путь к директории со стендами предметов
os.environ["ITEM_STANDS_PATH"] = os.path.join(os.environ["APP_DIR"], "item_stands")
# Путь к директории с кнопками
os.environ["BUTTONS_PATH"] = os.path.join(os.environ["APP_DIR"], "buttons")
# Путь к директории с боссами
os.environ["BOSSES_PATH"] = os.path.join(os.environ["APP_DIR"], "bosses")
# Путь к директории с враждебными существами
os.environ["ENEMIES_PATH"] = os.path.join(os.environ["APP_DIR"], "enemies")
# Путь к директории с локациями
os.environ["LOCATIONS_PATH"] = os.path.join(os.environ["APP_DIR"], "locations")
# Путь к директории с гранями кости
os.environ["CUBE_PATH"] = os.path.join(os.environ["APP_DIR"], "cube")
# Шрифт
os.environ["FONT"] = os.path.join(os.environ["APP_DIR"], "font.ttf")
# Версия приложения
os.environ["VERSION"] = "1.0.0-beta.1"
# Уровень логирования
os.environ["LOGGING_LEVEL"] = args.ll
# Сервер
os.environ["HOST"] = args.host

if args.clear_appdata:
    import clear_appdata  # noqa

    sys.exit()

import pygame  # noqa

pygame.init()

info = pygame.display.Info()
# Разрешение монитора
# TODO: Сделать экран загрузки перехода из меню клиента в игровой клиент
os.environ["MAX_RESOLUTION"] = f"{info.current_w};{info.current_h}"

from logger import logger  # noqa

import database  # noqa

database.Config.init()
import main  # noqa

main.main()

pygame.quit()

logger.info("Клиент закрыт")
