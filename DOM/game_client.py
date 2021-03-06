"""

Игровой клиента.

"""

from __future__ import annotations

import math
import os
import time
import typing as ty
from dataclasses import dataclass

import pygame as pg

from base import WidgetsGroup, Group, Label, Alert, Button, Anchor, Line, Text, Thread
from base.events import ButtonClickEvent
from base.widget import BaseWidget
from database.field_types import Resolution
from dice import Dice, DiceMovingStop
from game.tools import get_ways
from settings_alert import Settings
from utils import load_image, FinishStatus, InfoAlert, DropMenu, LoadingScreen

if ty.TYPE_CHECKING:
    from game.tools import Cords, Cord
    from network import NetworkClient
    from game.player import Player
    from game.item import Item
    from game.enemy import Enemy
    from game.boss import Boss
    from base.types import CordFunction


# ==== MENUS ====


class MyQueueAlert(DropMenu):
    def __init__(self, parent: WidgetsGroup):
        resolution = Resolution.converter(os.environ["resolution"])
        font_size = int(os.environ["font_size"])
        font = os.environ.get("font")

        super(MyQueueAlert, self).__init__(
            parent,
            "MyQueueAlert",
            width=round(resolution.width * 0.4),
            padding=20,
            background=pg.Color("#152622"),
            border_color=pg.Color("#f0ce69"),
            border_width=3,
        )

        self.msg = Label(
            self,
            f"{self.name}-Label",
            x=lambda obj: round(
                (self.rect.width - self.padding * 2 - self.border_width * 2) / 2
                - obj.rect.width / 2
            ),
            y=0,
            text="Ваш ход",
            font=pg.font.Font(font, font_size),
        )

        self.pos = (
            round(resolution.width / 2 - self.rect.width / 2),
            round(resolution.height / 2 - self.rect.height / 2),
        )

    def alert(self) -> None:
        self.open(self.pos)

    def handle_event(self, event: pg.event.Event) -> None:
        """
        Модифицируем базовый метод.
        Отключаем открытие меню по нажатию на виджет.
        :param event: ...
        """
        if not self.hidden:
            WidgetsGroup.handle_event(self, event)
        if event.type == pg.MOUSEBUTTONDOWN:
            # Скрываем виджет
            if event.button == pg.BUTTON_RIGHT:
                if self._widget.get_global_rect().collidepoint(event.pos):
                    return
            if hasattr(event, "pos"):
                if not self.hidden:
                    if not self.rect.collidepoint(event.pos):
                        self.hide()


class GameOverStatistic(WidgetsGroup):
    eng_rus = {
        "damage_received": "Получено урона",
        "damage_done": "Нанесено урона",
        "damage_blocked": "Заблокировано урона",
        "stolen_life": "Похищено жизни",
        "enemies_killed": "Убито врагов",
        "bosses_killed": "Убито боссов",
        "coins_earned": "Получено монет",
        "coins_spent": "Потрачено монет",
        "purchased_items": "Куплено предметов",
        "deaths": "Смертей",
    }

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        width: int,
        username: str,
        statistics: dict[str, int],
    ):
        font_size = int(os.environ["font_size"])
        font = os.environ.get("font")

        super(GameOverStatistic, self).__init__(
            None, name, x=x, y=y, width=width, border_width=2, padding=5
        )

        self.username_label = Text(
            self,
            f"{self.name}-UsernameLabel",
            x=0,
            y=0,
            width=self.rect.width - self.padding * 2,
            text=username,
            font=pg.font.Font(font, font_size),
            anchor=Anchor.center,
        )

        self.stats: list[Text] = []

        y = self.username_label.rect.bottom + 10
        for key, value in statistics.items():
            self.stats.append(
                Text(
                    None,
                    f"{self.name}-{key}-Stat",
                    x=0,
                    y=y,
                    width=self.rect.width - self.padding * 2,
                    text=f"{self.eng_rus[key]}:  {value}",
                    font=pg.font.Font(font, round(font_size * 0.8)),
                    anchor=Anchor.center,
                )
            )
            y = self.stats[-1].rect.bottom + 5

        self.add(*self.stats)


class GameOverAlert(Alert):
    def __init__(self, parent: GameClientScreen):
        """
        Меню окончания игры.
        :param parent: ...
        """
        resolution = Resolution.converter(os.environ["resolution"])
        font_size = int(os.environ["font_size"])
        font = os.environ.get("font")

        super(GameOverAlert, self).__init__(
            parent,
            "Menu",
            parent_size=resolution,
            width=int(resolution.width * 0.7),
            padding=20,
            background=pg.Color("#122321"),
            border_color=pg.Color("#b9a66d"),
            border_width=3,
            fogging=100,
        )

        self.title = Label(
            self,
            f"{self.name}-TitleLabel",
            x=0,
            y=0,
            width=self.rect.width - self.padding * 2,
            text="Игра окончена",
            font=pg.font.Font(font, font_size),
            anchor=Anchor.center,
        )

        self.statistics: list[GameOverStatistic] = []

        self.exit_button = Button(
            self,
            f"{self.name}-ExitButton",
            x=lambda obj: (self.rect.width - self.padding * 2) / 2 - obj.rect.width / 2,
            y=lambda obj: (
                (
                    self.title.rect.bottom
                    if not len(self.statistics)
                    else max(stat.rect.bottom for stat in self.statistics)
                )
                + 10
            ),
            width=int(self.rect.width * 0.8),
            text="Выйти",
            padding=5,
            active_background=pg.Color("gray"),
            font=pg.font.Font(font, font_size),
            anchor=Anchor.center,
            border_width=2,
            callback=lambda event: (
                parent.__setattr__("finish_status", FinishStatus.exit_game),
                parent.terminate(),
            ),
        )

    def init(self, data: dict[str, dict[str, int]]) -> None:
        width = round((self.rect.width - self.padding * 2) / len(data))
        y = self.title.rect.bottom + 10
        self.statistics = []
        for i, (username, statistics) in enumerate(data.items()):
            self.statistics.append(
                GameOverStatistic(
                    f"{self.name}-{username}-Statistics",
                    width * i,
                    y,
                    width,
                    username,
                    statistics,
                )
            )
        self.add(*self.statistics)
        self.update()


class EscMenu(Alert):
    def __init__(self, parent: GameClientScreen):
        """
        Меню игрового клиента.
        Открывается по нажатию клавиши Escape.
        :param parent: ...
        """
        resolution = Resolution.converter(os.environ["resolution"])
        font_size = int(os.environ["font_size"])
        font = os.environ.get("font")

        super(EscMenu, self).__init__(
            parent,
            "Menu",
            parent_size=resolution,
            width=int(resolution.width * 0.5),
            padding=20,
            background=pg.Color("#122321"),
            border_color=pg.Color("#b9a66d"),
            border_width=3,
            fogging=100,
        )

        self.title = Label(
            self,
            f"{self.name}-TitleLabel",
            x=0,
            y=0,
            width=self.rect.width,
            text="Меню",
            font=pg.font.Font(font, font_size),
            anchor=Anchor.center,
        )

        self.continue_button = Button(
            self,
            f"{self.name}-ContinueButton",
            x=lambda obj: self.rect.width / 2 - obj.rect.width / 2,
            y=self.title.rect.bottom + 10,
            width=int(self.rect.width * 0.8),
            text="Продолжить",
            padding=5,
            active_background=pg.Color("gray"),
            font=pg.font.Font(font, font_size),
            anchor=Anchor.center,
            border_width=2,
            callback=lambda event: self.hide(),
        )

        self.settings_button = Button(
            self,
            f"{self.name}-SettingsButton",
            x=lambda obj: self.rect.width / 2 - obj.rect.width / 2,
            y=self.continue_button.rect.bottom + 10,
            width=int(self.rect.width * 0.8),
            text="Настройки",
            padding=5,
            active_background=pg.Color("gray"),
            font=pg.font.Font(font, font_size),
            anchor=Anchor.center,
            border_width=2,
            callback=lambda event: self.settings.show(),
        )

        self.exit_button = Button(
            self,
            f"{self.name}-ExitButton",
            x=lambda obj: self.rect.width / 2 - obj.rect.width / 2,
            y=self.settings_button.rect.bottom + 10,
            width=int(self.rect.width * 0.8),
            text="Выйти",
            padding=5,
            active_background=pg.Color("gray"),
            font=pg.font.Font(font, font_size),
            anchor=Anchor.center,
            border_width=2,
            callback=lambda event: (
                parent.network_client.leave_lobby(),
                parent.__setattr__("finish_status", FinishStatus.exit_game),
                parent.terminate(),
            ),
        )

        self.settings = Settings(parent)  # Подключаем виджет настроек


class ItemDropMenu(DropMenu):
    def __init__(self, parent: PlayerWidget, can_remove: True | False):
        """
        Выпадающее меню для предметов.
        :param parent: ...
        :param can_remove: Может ли пользователь продать предметы.
        """
        font_size = int(os.environ["font_size"])
        font = os.environ.get("font")

        super(ItemDropMenu, self).__init__(
            parent,
            f"{parent.name}-DropMenu",
            padding=10,
            background=pg.Color("#122321"),
            border_color=pg.Color("#b9a66d"),
            border_width=2,
        )

        self.item: Item = ...
        self.item_index: int = ...

        self.item_desc: ItemDescription = ...
        if can_remove:
            self.remove_button = Button(
                self,
                name=f"{self.name}-RemoveButton",
                x=0,
                y=lambda obj: (self.item_desc.rect.bottom + 10)
                if self.item_desc is not ...
                else 0,
                width=lambda obj: self.rect.width
                - self.padding * 2
                - self.border_width * 2,
                text="Продать",
                padding=5,
                active_background=pg.Color("gray"),
                font=pg.font.Font(font, font_size),
                anchor=Anchor.center,
                border_width=2,
                callback=lambda event: (
                    self.hide(),
                    parent.network_client.remove_item(self.item_index),
                ),
            )

    def init(self, item: Item, item_index: int) -> None:
        """
        Инициализация предмета.
        :param item: Предмет.
        :param item_index: Индекс предмета в инвентаре.
        """
        self.item = item
        self.item_index = item_index
        if self.item_desc is not ...:  # Удаляем старое описание
            self.remove(self.item_desc)
        self.item_desc = ItemDescription(
            self, f"{self.name}-ItemDesc", x=0, y=0, item=item, item_index=item_index
        )

    def handle_event(self, event: pg.event.Event) -> None:
        """
        Модифицируем базовый метод.
        Отключаем открытие меню по нажатию на виджет.
        :param event: ...
        """
        if not self.hidden:
            WidgetsGroup.handle_event(self, event)
        if event.type == pg.MOUSEBUTTONDOWN:
            # Скрываем виджет
            if event.button == pg.BUTTON_RIGHT:
                if self._widget.get_global_rect().collidepoint(event.pos):
                    return
            if hasattr(event, "pos"):
                if not self.hidden:
                    if not self.rect.collidepoint(event.pos):
                        self.hide()


# ==== FIELD ====


@dataclass
class Ping:
    # TODO: Пинги перестают исчезать.
    #  Возможно это связано с тем, что при изменении разрешения создается новый
    #  Thread Filed._manage_pings
    rect: pg.Rect
    spawn_time: int


@dataclass
class EntityWidget:
    icon: pg.Surface
    rect: pg.Rect
    data: ...
    indicator: pg.Surface | None

    def blit(self, surface: pg.Surface) -> None:
        surface.blit(self.icon, self.rect)
        if self.indicator is not None:
            rect = self.rect.copy()
            rect.x = round(rect.x + rect.w / 2 - self.indicator.get_width() / 2)
            rect.y = rect.top - self.indicator.get_height() - 3
            surface.blit(self.indicator, rect)


@dataclass
class EnemyWidget(EntityWidget):
    data: Enemy
    indicator: pg.Surface | None = None


@dataclass
class BossWidget(EntityWidget):
    data: Boss
    indicator: pg.Surface | None = None


@dataclass
class CharacterWidget(EntityWidget):
    data: Player
    indicator: pg.Surface | None = None


class Field(WidgetsGroup):
    def __init__(self, parent: GameClientScreen):
        """
        Виджет поля.
        :param parent: ...
        """
        font = os.environ["FONT"]
        resolution = Resolution.converter(os.environ["resolution"])

        height = width = min(resolution)  # Размеры поля

        self.network_client = parent.network_client

        self._field_image = pg.Surface((width, height))

        super(Field, self).__init__(
            parent,
            f"Field",
            x=lambda obj: resolution.width / 2 - obj.rect.width / 2,
            y=lambda obj: resolution.height / 2 - obj.rect.height / 2,
            width=width,
            height=height,
        )

        self._generate_location_map()

        self._label = Label(
            self,
            f"{self.name}-Label",
            x=0,
            y=0,
            width=width,
            height=height,
            sprite=self._field_image,
        )

        self._boss_image = load_image(
            self.network_client.room.boss.icon,
            namespace=os.environ["BOSSES_PATH"],
            size=(None, round(self.block_height * 2)),
            save_ratio=True,
        )
        if self._boss_image.get_width() == 1:
            # TODO: remove this
            self._boss_image = load_image(
                "diablo.png",
                namespace=os.environ["BOSSES_PATH"],
                size=(None, round(self.block_height * 2)),
                save_ratio=True,
            )

        self.boss: BossWidget = ...
        self.enemies: dict[Cord, EnemyWidget] = {}
        self.characters: dict[Cord, CharacterWidget] = {}
        self.ways: dict[Cord, pg.Rect] = {}
        self._way_image = load_image(
            "indicator.png",
            namespace=os.environ["UI_ICONS_PATH"],
            size=(round(self.block_width), round(self.block_height)),
        )
        self.hit: dict[Cord, pg.Rect] = {}
        self._hit_image = load_image(
            "damage.png",
            namespace=os.environ["UI_ICONS_PATH"],
            size=(round(self.block_width), round(self.block_height)),
        )
        self._finish_image = load_image(
            "indicator.png",
            namespace=os.environ["UI_ICONS_PATH"],
            size=(round(self.block_width), round(self.block_height)),
        )
        self.finish: pg.Rect = ...

        self.lvl_label = Label(
            None,
            f"{self.name}-LvlLabel",
            x=round(self.block_width),
            y=round(self.block_height - self.block_height * 0.3),
            height=round(self.block_height),
            text=f" {self.network_client.room.lvl} уровень ",
            background=pg.Color("#122321"),
            border_color=pg.Color("#b9a66d"),
            border_width=3,
            padding=3,
            font=pg.font.Font(font, round(self.block_height - 12)),
        )

        self._ping_image = load_image(
            "ping.png",
            namespace=os.environ["UI_ICONS_PATH"],
            size=(round(self.block_width), round(self.block_height)),
        )
        self.pings: dict[Cord, Ping] = {}

        self.update_field()

        Thread(self._manage_pings, repetitive=True).run()

    def init_ways(self, ways: list[Cords]) -> None:
        self.ways.clear()
        for way in ways:
            for cord in way:
                cord = tuple(cord)
                if cord not in self.ways:
                    self.ways[cord] = pg.Rect(
                        self.block_width * cord[1],
                        self.block_height * cord[0],
                        self.block_width,
                        self.block_height,
                    )
        self.update_field()

    def init_hit(self, cords: list[Cord]) -> None:
        for cord in cords:
            cord = tuple(cord)
            if cord not in self.hit:
                self.hit[cord] = pg.Rect(
                    self.block_width * cord[1],
                    self.block_height * cord[0],
                    self.block_width,
                    self.block_height,
                )
        self.update_field()
        Thread(self._delete_hit).run()

    def _delete_hit(self) -> None:
        time.sleep(2)
        self.hit.clear()
        self.update_field()

    def _generate_location_map(self) -> None:
        """
        Создает картинку поля.
        """
        self.floors: list[tuple[pg.Surface, pg.Rect]] = []  # Элементы пола
        self.walls: list[list[tuple[pg.Surface, pg.Rect] | None]] = []  # Элементы стен

        self.block_width, self.block_height = (
            self.width / len(self.network_client.room.field[0]),
            self.height / len(self.network_client.room.field),
        )  # Размеры одного блока

        for i, (board_line, location_line) in enumerate(
            zip(self.network_client.room.field, self.network_client.room.location)
        ):
            walls_line: list[tuple[pg.Surface, pg.Rect] | None] = []
            y = self.block_height * i
            for j, (board_block, location_block) in enumerate(
                zip(board_line, location_line)
            ):
                x = self.block_width * j
                if board_block is True:  # Если блок - элемента пола
                    rect = pg.Rect(x, y, self.block_width, self.block_height)
                    self.floors.append(
                        (
                            load_image(
                                f"floor{location_block}.png",
                                namespace=os.path.join(
                                    os.environ["LOCATIONS_PATH"],
                                    self.network_client.room.location_name,
                                    "floors",
                                ),
                                size=(
                                    round(self.block_width) + 1,
                                    round(self.block_height * 1.3),
                                ),
                            ),
                            rect,
                        )
                    )
                    walls_line.append(None)
                else:  # Если блок - элемент стены
                    rect = pg.Rect(
                        x,
                        y - self.block_height * 0.3,
                        self.block_width,
                        self.block_height * 1.3,
                    )
                    walls_line.append(
                        (
                            load_image(
                                f"wall{location_block}.png",
                                namespace=os.path.join(
                                    os.environ["LOCATIONS_PATH"],
                                    self.network_client.room.location_name,
                                    "walls",
                                ),
                                size=(
                                    round(self.block_width) + 1,
                                    round(self.block_height * 1.3),
                                ),
                            ),
                            rect,
                        )
                    )
            self.walls.append(walls_line)

    def update_field(self) -> None:
        """
        Отображение игры.
        """
        if self.network_client.room is ...:
            return

        image = pg.Surface(self._field_image.get_size())
        for floor_image, floor_rect in self.floors:
            image.blit(floor_image, floor_rect)

        rect = pg.Rect(
            self.block_width * self.network_client.room.boss.pos[1]
            - self.block_width * 0.5,
            self.block_height * self.network_client.room.boss.pos[0] - self.block_width,
            self._boss_image.get_width(),
            self._boss_image.get_height(),
        )
        if self.boss is ...:
            self.boss = BossWidget(
                self._boss_image, rect=rect, data=self.network_client.room.boss
            )
        else:
            self.boss.rect = rect
            self.boss.data = self.network_client.room.boss

        enemies = {enemy.data.eid: enemy for enemy in self.enemies.values()}
        self.enemies.clear()
        for enemy in self.network_client.room.enemies:
            enemy_image = load_image(
                enemy.icon,
                namespace=os.environ["ENEMIES_PATH"],
                size=(None, round(self.block_height * 1.25)),
                save_ratio=True,
            )
            if enemy_image.get_width() == 1:
                enemy_image = load_image(
                    "mogus.png",
                    namespace=os.environ["ENEMIES_PATH"],
                    size=(None, round(self.block_height * 1.25)),
                    save_ratio=True,
                )
            rect = pg.Rect(
                self.block_width * enemy.pos[1]
                - ((enemy_image.get_width() - self.block_width) / 2),
                self.block_height * enemy.pos[0] - self.block_width * 0.25,
                enemy_image.get_width(),
                enemy_image.get_height(),
            )
            if enemy.eid not in enemies:
                enemy_widget = EnemyWidget(enemy_image, rect=rect, data=enemy)
            else:
                enemy_widget = enemies[enemy.eid]
                enemy_widget.rect = rect
                enemy_widget.data = enemy

            self.enemies[tuple(enemy.pos)] = enemy_widget

        characters = {
            character.data.uid: character for character in self.characters.values()
        }
        self.characters.clear()
        for player in self.network_client.room.players:
            player_image = load_image(
                player.character.icon,
                namespace=os.environ["CHARACTERS_PATH"],
                size=(None, round(self.block_height * 1.5)),
                save_ratio=True,
            )
            rect = pg.Rect(
                self.block_width * player.character.pos[1]
                - ((player_image.get_width() - self.block_width) / 2),
                self.block_height * player.character.pos[0] - self.block_width * 0.5,
                player_image.get_width(),
                player_image.get_height(),
            )
            if player.uid not in characters:
                character = CharacterWidget(player_image, rect=rect, data=player)
            else:
                character = characters[player.uid]
                character.rect = rect
                character.data = player

            self.characters[tuple(player.character.pos)] = character

        for i, walls_line in enumerate(self.walls):
            for j, wall in enumerate(walls_line):
                if wall:
                    image.blit(*wall)
                j -= 1
                if way := self.ways.get((i, j)):
                    image.blit(self._way_image, way)
                if enemy := self.enemies.get((i, j)):
                    enemy.blit(image)
                if character := self.characters.get((i, j)):
                    character.blit(image)
                if hit := self.hit.get((i, j)):
                    image.blit(self._hit_image, hit)
                if tuple(self.boss.data.pos) == (i, j):
                    if self.boss.data.hp > 0:
                        self.boss.blit(image)
                if ping := self.pings.get((i, j)):
                    image.blit(self._ping_image, ping)

        if self.network_client.room.boss.hp == 0:
            self.finish = pg.Rect(
                self.block_width * self.network_client.room.field[-1].index(True),
                self.block_height * (len(self.network_client.room.field) - 1),
                self._finish_image.get_width(),
                self._finish_image.get_height(),
            )
            image.blit(self._finish_image, self.finish)

        image.blit(self.lvl_label.image, self.lvl_label.rect)

        self.field_image = image

    def _manage_pings(self) -> ty.NoReturn:
        while True:
            upd = False
            for pos, ping in self.pings.copy().items():
                if time.time() - ping.spawn_time > 3:
                    del self.pings[pos]
                    upd = True
            if upd:
                self.update_field()

    def spawn_ping(self, y: int, x: int) -> None:
        pos = (y, x)
        if pos in self.pings:
            self.pings[pos].spawn_time = int(time.time())
        else:
            rect = pg.Rect(
                self.block_width * x,
                self.block_height * y,
                round(self.block_width),
                round(self.block_height),
            )
            self.pings[pos] = Ping(rect, int(time.time()))
            self.update_field()

    @property
    def field_image(self) -> pg.Surface:
        return self._field_image

    @field_image.setter
    def field_image(self, value: pg.Surface):
        self._field_image = value
        if hasattr(self, "_label"):
            self._label.sprite = self._field_image

    def get_global_rect_of(self, rect: pg.Rect) -> pg.Rect:
        rect = rect.copy()

        self_rect: pg.Rect = self.get_global_rect()
        rect.x += self_rect.x + self.padding + self.border_width
        rect.y += self_rect.y + self.padding + self.border_width

        return rect


# ==== STATS ====


class StatWidget(WidgetsGroup):
    def __init__(self, name: str, x: int, y: int | CordFunction, icon: str, value: str):
        """
        Виджет характеристики.
        Иконка + значение.
        :param name: Название элемента.
        :param x: Координата x.
        :param y: Координата y.
        :param icon: Название файла с иконкой.
        :param value: Значение характеристики.
        """
        icon_size = int(int(os.environ["icon_size"]) * 0.5)
        font = os.environ.get("font")

        super(StatWidget, self).__init__(None, name, x=x, y=y, padding=5)

        self.icon = Label(
            self,
            f"{self.name}-IconLabel",
            x=0,
            y=0,
            width=icon_size,
            height=icon_size,
            sprite=load_image(
                icon,
                namespace=os.environ["UI_ICONS_PATH"],
                size=(icon_size, icon_size),
            ),
        )

        self.value = Label(
            self,
            f"{self.name}-ValueLabel",
            x=self.icon.rect.right + 5,
            y=lambda obj: self.icon.height / 2 - obj.rect.height / 2,
            text=value,
            font=pg.font.Font(font, icon_size),
        )


class StatsWidget(WidgetsGroup):
    def __init__(self, parent: PlayerWidget):
        """
        Виджет характеристик персонажа.
        :param parent: ...
        """
        super(StatsWidget, self).__init__(
            parent,
            f"{parent.name}-StatsWidget",
            x=int(parent.width / 2),
            y=parent.line.rect.bottom + 5,
            width=int(parent.width / 2),
        )

        self.stats: list[StatWidget] = []  # Характеристики персонажа

        self.hp = self.add_stat("hp.png", parent.player.character.hp)
        self.damage = self.add_stat("damage.png", parent.player.character.damage)
        self.attack_range = self.add_stat(
            "attack_range.png", parent.player.character.attack_range
        )
        self.armor = self.add_stat("armor.png", parent.player.character.armor)
        self.move_speed = self.add_stat(
            "move_speed.png", parent.player.character.move_speed
        )
        self.life_abduction = self.add_stat(
            "life_abduction.png", parent.player.character.life_abduction
        )
        self.coins = self.add_stat("coins.png", parent.player.character.coins)

        self.add(*self.stats)

    def add_stat(self, icon: str, value: int) -> StatWidget:
        """
        Добавление характеристики.
        Автоматически смещает характеристику на новую линию,
        если нехватает места для ее отображения.
        :param icon: Название файла с иконкой.
        :param value: Значение характеристики.
        :return: Виджет характеристики.
        """
        if not len(self.stats):  # Если это первая характеристика
            x = y = 0
        else:
            y = self.stats[-1].rect.y
            x = self.stats[-1].rect.right
            # Если не хватает места
            if x + self.stats[-1].rect.width > self.rect.width:
                x = 0
                y += self.stats[-1].rect.height

        widget = StatWidget(f"{self.name}-{icon}-StatWidget", x, y, icon, str(value))
        self.stats.append(widget)  # Добавляем в список
        return widget

    def update_stats(self, player: Player) -> None:
        """
        Обновляет характеристики.
        :param player: Экземпляр игрока.
        """
        # Перебор всех характеристик
        for stat in {
            "hp",
            "damage",
            "attack_range",
            "armor",
            "move_speed",
            "life_abduction",
            "coins",
        }:
            widget: StatWidget = self.__getattribute__(stat)
            # Если значение изменилось
            if widget.value.text != (
                value := str(player.character.__getattribute__(stat))
            ):
                widget.value.text = value


# ==== ITEMS ====


class ItemWidget(WidgetsGroup):
    def __init__(self, name: str, x: int, y: int, item: Item | None):
        """
        Виджет предмета в инвентаре.
        :param name: Название виджета.
        :param x: Координата x.
        :param y: Координата y.
        :param item: Предмет.
        """
        icon_size = int(int(os.environ["icon_size"]) * 0.9)

        self.item: Item | None = ...

        super(ItemWidget, self).__init__(None, name, x=x, y=y)

        self.item_icon = Label(
            self,
            f"{name}-ItemIconLabel",
            x=2,
            y=2,
            width=icon_size - 4,
            height=icon_size - 4,
            text="",
        )

        self.border_icon = Label(
            self,
            f"{name}-ItemIconLabel",
            x=0,
            y=0,
            width=icon_size,
            height=icon_size,
            text="",
        )

        self.init(item)

    def init(self, item: Item | None) -> None:
        """
        Инициализирует предмет.
        :param item: Предмет.
        """
        icon_size = int(int(os.environ["icon_size"]) * 0.9)

        self.item = item

        self.item_icon.sprite = load_image(
            # Если слот пустой, ставим соответствующую иконку
            item.icon if item else "default.png",
            namespace=os.environ["ITEMS_PATH"],
            size=(icon_size - 4, None),
            save_ratio=True,
        )
        self.border_icon.sprite = load_image(
            # Если слот пустой, ставим рамку первого уровня
            f"lvl{item.lvl if item else 1}.png",
            namespace=os.environ["ITEM_BORDERS_PATH"],
            size=(icon_size, None),
            save_ratio=True,
        )


class ItemsWidget(WidgetsGroup):
    def __init__(self, parent: PlayerWidget):
        """
        Виджет инвентаря персонажа.
        :param parent: ...
        """
        super(ItemsWidget, self).__init__(
            parent,
            "ItemsWidget",
            x=0,
            y=parent.line.rect.bottom + 5,
            width=int(parent.width / 2),
        )

        self.items: list[ItemWidget] = []  # Слоты
        for item in parent.player.character.items:
            self.add_item(item)

        self.add(*self.items)

    def add_item(self, item: Item | None) -> ItemWidget:
        """
        Добавляет предмет в инвентарь.
        Автоматически смещает слот на новую линию,
        если нехватает места для его отображения.
        :param item: Предмет.
        :return: Виджет предмета.
        """
        if not len(self.items):  # Если это первый слот
            x = y = 0
        else:
            y = self.items[-1].rect.y
            x = self.items[-1].rect.right + 2
            if x + self.items[-1].rect.width > self.rect.width:
                x = 0
                y += self.items[-1].rect.height + 2

        widget = ItemWidget(f"{self.name}-{len(self.items) + 1}-ItemWidget", x, y, item)
        self.items.append(widget)
        return widget

    def update_items(self, player: Player) -> None:
        """
        Обновляет предметы.
        :param player: Экземпляр игрока.
        """
        for item_index, (item, item_widget) in enumerate(
            zip(player.character.items, self.items)
        ):
            # Если предмет изменился
            if (item.name if item else None) != (
                item_widget.item.name if item_widget.item else None
            ):
                item_widget.init(item)


class ItemStand(WidgetsGroup):
    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        width: int,
        icon_width: int,
        item: Item,
    ):
        """
        Стенд с предметом.
        :param name: Название виджета.
        :param x: Координата x.
        :param y: Координата y.
        :param width: Ширина виджета.
        :param item: Предмет.
        """

        self.item = item

        super(ItemStand, self).__init__(None, "name", x=x, y=y, width=width)

        self.stand = Label(
            self,
            f"{name}-StandLabel",
            x=lambda obj: round(self.rect.width / 2 - obj.rect.width / 2),
            y=round(icon_width / 3),
            width=lambda obj: obj.sprite.get_width(),
            height=lambda obj: obj.sprite.get_height(),
            sprite=load_image(
                f"stand{item.lvl if item else 1}.png",
                namespace=os.environ["ITEM_STANDS_PATH"],
                size=(icon_width * 2, None),
                save_ratio=True,
            ),
        )

        self.item_icon = Label(
            self,
            f"{name}-ItemIconLabel",
            x=lambda obj: round(self.rect.width / 2 - obj.rect.width / 2),
            y=0,
            width=lambda obj: (obj.sprite.get_width() if obj.sprite else icon_width),
            height=lambda obj: (obj.sprite.get_height() if obj.sprite else icon_width),
            sprite=(
                load_image(
                    item.icon,
                    namespace=os.environ["ITEMS_PATH"],
                    size=(icon_width, icon_width),
                )
                if item
                else None
            ),
            text="",
        )

    def sales(self) -> None:
        """
        Помечает предмет как проданный.
        """
        self.item_icon.sprite = None
        self.item = None


class ItemDescription(WidgetsGroup):
    def __init__(
        self,
        parent: WidgetsGroup,
        name: str,
        x: int | CordFunction,
        y: int | CordFunction,
        item: Item,
        item_index: int,
    ):
        """
        Описание предмета.
        Иконка, название, цена, характеристики.
        :param parent: ...
        :param name: Название виджета.
        :param x: Координата x.
        :param y: Координата y.
        :param item: Предмет.
        :param item_index: Индекс предмета в инвентаре или магазине.
        """
        font_size = int(os.environ["font_size"])
        icon_size = int(os.environ["icon_size"])
        font = os.environ.get("font")

        self.item = item
        self.item_index = item_index

        super(ItemDescription, self).__init__(parent, name, x=x, y=y)

        self.icon = Label(
            self,
            f"{self.name}-IconLabel",
            x=0,
            y=0,
            width=icon_size,
            height=icon_size,
            sprite=load_image(
                item.icon,
                namespace=os.environ["ITEMS_PATH"],
                size=(icon_size, icon_size),
            ),
        )

        # Если parent имеет ограниченную ширину, то используем Text
        self.name = (Text if parent.width else Label)(
            self,
            f"{self.name}-NameLabel",
            x=self.icon.rect.right + 5,
            y=lambda obj: self.icon.rect.height / 2 - obj.rect.height / 2,
            width=(
                (parent.rect.width - parent.padding * 2 - icon_size - 5)
                if parent.width
                else None
            ),
            text=item.name,
            font=pg.font.Font(font, font_size),
            **dict(soft_split=True) if parent.width else {},
        )

        self.price_label = Label(
            self,
            f"{self.name}-PriceLabel",
            x=0,
            y=self.icon.rect.bottom + 5,
            text=f"Цена: {item.price}",
            font=pg.font.Font(font, font_size),
        )
        self.price_icon_label = Label(
            self,
            f"{self.name}-CoinsIconLabel",
            x=self.price_label.rect.right,
            y=self.price_label.rect.top,
            width=lambda obj: obj.sprite.get_width(),
            height=lambda obj: obj.sprite.get_height(),
            sprite=load_image(
                "coins.png",
                namespace=os.environ["UI_ICONS_PATH"],
                size=(None, self.price_label.rect.height),
                save_ratio=True,
            ),
        )

        self.stats: list[StatWidget] = []  # Характеристики предмета

        for stat_name, stat_value in self.item.desc.items():
            if stat_name == "max_hp":
                stat_name = "hp"
            self.add_stat(f"{stat_name}.png", stat_value)

        self.add(*self.stats)

    def add_stat(self, icon: str, value: str) -> StatWidget:
        """
        Добавляет характеристику к предмету.
        Автоматически смещает характеристику на новую линию,
        если нехватает места для ее отображения.
        :param icon: Название файла с иконкой характеристики.
        :param value: Значение характеристики.
        :return: Виджет характеристики.
        """
        if not len(self.stats):  # Если это первая характеристика
            x = 0
            y = self.price_label.rect.bottom + 5
        else:
            y = self.stats[-1].rect.y
            x = self.stats[-1].rect.right
            if x + self.stats[-1].rect.width > self.rect.width:
                x = 0
                y += self.stats[-1].rect.height

        widget = StatWidget(f"{self.name}-{icon}-StatWidget", x, y, icon, value)
        self.stats.append(widget)
        return widget


# ==== PLAYERS ====


class ShortPlayerWidget(WidgetsGroup):
    def __init__(self, parent: PlayersMenu, player: Player, y: int):
        """
        Виджет игрока.
        Объединяет информацию об игроке, его предметы и характеристики.
        :param parent: ...
        :param player: Экземпляр игрока.
        :param y: ...
        """
        font_size = int(os.environ["font_size"])
        icon_size = int(os.environ["icon_size"])
        font = os.environ.get("font")

        self.player = player
        self.network_client = parent.network_client

        # Определяем положение виджета
        super(ShortPlayerWidget, self).__init__(
            None,
            f"{player.username}-Widget",
            x=0,
            y=y,
            width=parent.rect.width - parent.padding * 2,
        )

        self.icon = Label(
            self,
            f"{self.name}-IconLabel",
            x=0,
            y=0,
            width=icon_size,
            height=icon_size,
            sprite=load_image(
                player.character.icon,
                namespace=os.environ["CHARACTERS_PATH"],
                size=(None, icon_size),
                save_ratio=True,
            ),
        )
        self.username = Label(
            self,
            f"{self.name}-UsernameLabel",
            x=self.icon.rect.right + 5,
            y=lambda obj: self.icon.rect.height / 2 - obj.rect.height / 2,
            text=player.username,
            color=(
                pg.Color("#b9a66d")
                if f"p{player.uid}" == parent.network_client.room.queue
                else pg.Color("white")
            ),
            font=pg.font.Font(font, font_size),
        )


class PlayerWidget(WidgetsGroup):
    def __init__(
        self,
        parent: Group,
        network_client: NetworkClient,
        width: int,
        x: int | CordFunction,
        y: int | CordFunction,
        player: Player | None = None,
        can_remove_items: True | False = False,
    ):
        """
        Виджет игрока.
        Объединяет информацию об игроке, его предметы и характеристики.
        :param parent: ...
        :param network_client: ...
        :param width: Ширина виджета.
        :param y: Координата Y.
        :param player: Экземпляр игрока.
        """
        font_size = int(os.environ["font_size"])
        icon_size = int(os.environ["icon_size"])
        font = os.environ.get("font")

        self.lock = False
        self.player = player
        self.network_client = network_client

        # Определяем положение виджета
        super(PlayerWidget, self).__init__(
            parent, f"Player-Widget", x=x, y=y, width=width
        )

        self.icon = Label(
            self,
            f"{self.name}-IconLabel",
            x=0,
            y=0,
            width=icon_size,
            height=icon_size,
            text="",
        )

        self.username = Label(
            self,
            f"{self.name}-UsernameLabel",
            x=lambda obj: self.icon.rect.right + 5,
            y=lambda obj: self.icon.rect.height / 2 - obj.rect.height / 2,
            text="",
            font=pg.font.Font(font, font_size),
        )

        self.line = Line(
            self,
            x=0,
            y=lambda obj: self.icon.rect.bottom + 5,
            width=self.rect.width - self.padding * 2,
            height=2,
        )  # Линия - разделитель

        self.items: ItemsWidget = ...
        self.stats: StatsWidget = ...
        self.drop_menu: ItemDropMenu = ItemDropMenu(self, can_remove=can_remove_items)

        if player:
            self.update_data(player)

    def update_data(self, player: Player) -> None:
        """
        Обновляет данные об игроке.
        :param player: Новый экземпляр игрока.
        """

        def wait_unlock():
            while self.lock:
                time.sleep(0.1)
            self.update_data(player)

        if self.lock:
            return Thread(wait_unlock).run()

        self.lock = True

        icon_size = int(os.environ["icon_size"])

        self.player = player
        self.name = f"{player.username}-Widget"
        self.icon.sprite = load_image(
            player.character.icon,
            namespace=os.environ["CHARACTERS_PATH"],
            size=(None, icon_size),
            save_ratio=True,
        )
        self.username.text = player.username
        if self.username.color == pg.Color("red"):
            color = pg.Color("red")
        elif f"p{player.uid}" == self.network_client.room.queue:
            color = pg.Color("#b9a66d")
        else:
            color = pg.Color("white")
        self.username.color = color

        if self.items is ...:
            self.items = ItemsWidget(self)
        else:
            self.items.update_items(self.player)

        if self.stats is not ...:
            self.remove(self.stats)
        self.stats = StatsWidget(self)

        self.lock = False

    def handle_event(self, event: pg.event.Event) -> None:
        super(PlayerWidget, self).handle_event(event)
        if self.enabled:
            if event.type == pg.MOUSEBUTTONDOWN:
                if event.button == pg.BUTTON_RIGHT:
                    if self.items is not ...:
                        # Открытие выпадающего меню предмета
                        if (
                            self.items.get_global_rect().collidepoint(event.pos)
                            and self.drop_menu is not ...
                        ):
                            for i, item_widget in enumerate(self.items.items):
                                if item_widget.item:
                                    # Открытие при нажатии на предмет
                                    if item_widget.get_global_rect().collidepoint(
                                        event.pos
                                    ):
                                        self.drop_menu.init(item_widget.item, i)
                                        self.drop_menu.open(event.pos)
                                        self.drop_menu.update()
                                        break


class PlayersMenu(WidgetsGroup):
    def __init__(self, parent: GameClientScreen):
        """
        Виджет игроков.
        :param parent: ...
        """
        resolution = Resolution.converter(os.environ["resolution"])

        self.network_client = parent.network_client

        super(PlayersMenu, self).__init__(
            parent,
            "PlayersMenu",
            x=lambda obj: parent.field.rect.left / 70 * 5,
            y=lambda obj: parent.field.rect.left / 70 * 4,
            width=parent.field.rect.left - parent.field.rect.left / 70 * 5,
            height=resolution.height,
            padding=5,
        )

        self.client_player = PlayerWidget(
            self,
            parent.network_client,
            width=self.width - self.padding * 2,
            x=0,
            y=0,
            player=self.network_client.room.get_by_uid(self.network_client.user.uid),
            can_remove_items=True,
        )
        self.players: list[ShortPlayerWidget] = []  # Список игроков

        self.update_players()

    def update_players(self) -> None:
        """
        Обновляет список игроков.
        """
        # Удаление старых виджетов
        self.remove(*self.players)

        self.players.clear()

        # Создание новых виджетов
        for i, player in enumerate(self.network_client.room.players):
            if player.uid != self.client_player.player.uid:
                self.players.append(
                    ShortPlayerWidget(
                        self,
                        player,
                        y=(
                            self.players[-1].rect.bottom
                            if len(self.players)
                            else self.client_player.rect.bottom
                        )
                        + 5,
                    )
                )
        self.add(*self.players)


# ==== CLIENT ====


class EnemyMenu(WidgetsGroup):
    def __init__(self, parent: GameClientScreen):
        font_size = int(os.environ["font_size"])
        font = os.environ.get("font")

        self.enemy: EnemyWidget | None = None

        super(EnemyMenu, self).__init__(
            parent,
            "EnemyMenu",
            x=lambda obj: parent.field.rect.left / 70 * 5,
            y=lambda obj: round(
                parent.dices_widget.rect.top
                - obj.rect.height
                - parent.field.rect.left / 70 * 2
            ),
            width=parent.field.rect.left - parent.field.rect.left / 70 * 5,
            padding=10,
            hidden=True,
        )
        self.disable()

        self.icon = Label(
            self,
            f"{self.name}-IconLabel",
            x=0,
            y=0,
            width=lambda obj: (obj.sprite.get_width() if obj.sprite else 1),
            height=lambda obj: (obj.sprite.get_height() if obj.sprite else 1),
            text="",
        )

        self.name = Label(
            self,
            f"{self.name}-NameLabel",
            x=lambda obj: self.icon.rect.right + 5,
            y=lambda obj: round(self.icon.rect.height / 2 - obj.rect.height / 2),
            text="...",
            font=pg.font.Font(font, font_size),
        )

        self.stats_widget = WidgetsGroup(
            self,
            f"{self.name}-StatsWidget",
            x=0,
            y=lambda obj: self.icon.rect.bottom + 5,
            width=self.rect.width - self.padding * 2,
        )
        self.stats: list[StatWidget] = []

    def init(self, enemy: EnemyWidget) -> None:
        self.enemy = enemy
        self.stats_widget.remove(*self.stats)
        self.stats.clear()

        self.icon.sprite = enemy.icon
        self.name.text = enemy.data.name

        self.add_stat("hp.png", enemy.data.hp)
        self.add_stat("damage.png", enemy.data.damage)
        self.add_stat("attack_range.png", enemy.data.attack_range)
        self.add_stat("coins.png", enemy.data.reward)

        self.stats_widget.add(*self.stats)

        self.enable()
        self.show()

    def update_data(self, enemy: Enemy) -> None:
        self.enemy.data.__dict__.update(enemy.__dict__)
        self.init(self.enemy)

    def add_stat(self, icon: str, value: int) -> StatWidget:
        """
        Добавление характеристики.
        Автоматически смещает характеристику на новую линию,
        если нехватает места для ее отображения.
        :param icon: Название файла с иконкой.
        :param value: Значение характеристики.
        :return: Виджет характеристики.
        """
        if not len(self.stats):  # Если это первая характеристика
            x = y = 0
        else:
            y = self.stats[-1].rect.y
            x = self.stats[-1].rect.right
            # Если не хватает места
            if x + self.stats[-1].rect.width > self.stats_widget.rect.width:
                x = 0
                y += self.stats[-1].rect.height

        widget = StatWidget(f"{self.name}-{icon}-StatWidget", x, y, icon, str(value))
        self.stats.append(widget)  # Добавляем в список
        return widget


class BossSkill(WidgetsGroup):
    def __init__(self, name: str, y: int, width: int, skill: dict, index: int):
        font_size = int(os.environ["font_size"])
        font = os.environ.get("font")

        super(BossSkill, self).__init__(None, name, x=0, y=y, width=width)

        self.desc = Text(
            self,
            f"{name}-DescLabel",
            x=0,
            y=0,
            width=round(width * 0.8),
            text=f"{index}. " + (skill.get("desc") or ""),
            font=pg.font.Font(font, font_size),
            soft_split=True,
        )

        self.stats: list[StatWidget] = []

        if damage := skill.get("damage"):
            self.add_stat("damage.png", damage)
        if heal := skill.get("heal"):
            self.add_stat("hp.png", heal)
        if life_abduction := skill.get("life_abduction"):
            self.add_stat("life_abduction.png", life_abduction)

        self.add(*self.stats)

    def add_stat(self, icon: str, value: str) -> StatWidget:
        """
        Добавление характеристики.
        Автоматически смещает характеристику на новую линию,
        если нехватает места для ее отображения.
        :param icon: Название файла с иконкой.
        :param value: Значение характеристики.
        :return: Виджет характеристики.
        """
        if not len(self.stats):  # Если это первая характеристика
            y = 0
            x = self.desc._rendered_text.get_width() + 5  # noqa
        else:
            y = self.stats[-1].rect.y
            x = self.stats[-1].rect.right
            # Если не хватает места
            if x + self.stats[-1].rect.width > self.rect.width:
                x = 0
                y += self.stats[-1].rect.height
                if y <= self.desc.rect.bottom:
                    y = self.desc.rect.bottom + 5

        widget = StatWidget(f"{self.name}-{icon}-StatWidget", x, y, icon, str(value))
        self.stats.append(widget)  # Добавляем в список
        return widget


class BossMenu(WidgetsGroup):
    def __init__(self, parent: GameClientScreen):
        icon_size = int(os.environ["icon_size"])
        font_size = int(os.environ["font_size"])
        font = os.environ.get("font")

        super(BossMenu, self).__init__(
            parent,
            "BossMenu",
            x=lambda obj: parent.field.rect.left / 70 * 5,
            y=lambda obj: round(
                parent.dices_widget.rect.top
                - obj.rect.height
                - parent.field.rect.left / 70 * 2
            ),
            width=parent.field.rect.left - parent.field.rect.left / 70 * 5,
            hidden=True,
        )
        self.disable()

        self.icon = Label(
            self,
            f"{self.name}-IconLabel",
            x=0,
            y=0,
            width=lambda obj: (obj.sprite.get_width() if obj.sprite else 1),
            height=lambda obj: (obj.sprite.get_height() if obj.sprite else 1),
            text="",
        )

        self.name = Text(
            self,
            f"{self.name}-NameLabel",
            x=lambda obj: self.icon.rect.right + 5,
            y=lambda obj: round(self.icon.rect.height / 2 - obj.rect.height / 2),
            width=round(self.rect.width - icon_size * 1.5),
            text="...",
            font=pg.font.Font(font, font_size),
        )

        self.hp = StatWidget(
            f"{self.name}-HpStat",
            x=0,
            y=lambda obj: self.icon.rect.bottom + 5,
            icon="hp.png",
            value=str(),
        )
        self.add(self.hp)

        self.skills_widget = WidgetsGroup(
            self,
            f"{self.name}-SkillsWidget",
            x=0,
            y=lambda obj: self.hp.rect.bottom + 5,
            width=self.rect.width - self.padding * 2,
        )
        self.skills: list[BossSkill] = []

    def init(self, boss: BossWidget) -> None:
        self.hp.value.text = str(boss.data.hp)

        self.skills_widget.remove(*self.skills)
        self.skills.clear()

        self.icon.sprite = boss.icon
        self.name.text = boss.data.name

        for skill in boss.data.desc:
            self.add_skill(skill)

        self.skills_widget.add(*self.skills)

        self.enable()
        self.show()

    def add_skill(self, skill: dict) -> BossSkill:
        """
        Добавление характеристики.
        Автоматически смещает характеристику на новую линию,
        если нехватает места для ее отображения.
        :param skill: Описание умения.
        :return: Виджет характеристики.
        """
        if not len(self.skills):  # Если это первое умение
            y = 0
        else:
            y = self.skills[-1].rect.bottom + 5

        widget = BossSkill(
            f"{self.name}-{len(self.skills)}-SkillWidget",
            y,
            self.skills_widget.rect.width,
            skill,
            len(self.skills) + 1,
        )
        self.skills.append(widget)  # Добавляем в список
        return widget


class ShopMenu(WidgetsGroup):
    def __init__(self, parent: GameClientScreen):
        """
        Магазин.
        :param parent: ...
        """
        font_size = int(os.environ["font_size"])
        font = os.environ.get("font")
        resolution = Resolution.converter(os.environ["resolution"])

        self.network_client = parent.network_client

        super(ShopMenu, self).__init__(
            parent,
            "ShopMenu",
            x=parent.field.rect.right,
            y=0,
            width=resolution.width
            - parent.field.rect.right
            - parent.field.rect.left / 70 * 4,
            height=resolution.height,
        )

        self.items: list[ItemStand] = []  # Предметы
        for item in self.network_client.room.shop:
            self.add_item(item)

        self.add(*self.items)

        self.buy_button = Button(
            self,
            name=f"{self.name}-BuyButton",
            x=parent.field.rect.left / 70,
            y=lambda obj: (
                resolution.height
                - parent.field.rect.left / 70 * 3
                - obj.rect.height
                - parent.field.rect.left / 70 * 3 / 3
            ),
            width=parent.field.rect.left - parent.field.rect.left / 70 * 5,
            text="Купить",
            padding=5,
            active_background=pg.Color(222, 222, 222, 100),
            font=pg.font.Font(font, font_size),
            anchor=Anchor.center,
        )
        self.buy_button.disable()

        # Меню покупки предмета
        self.item_preview = WidgetsGroup(
            self,
            f"{self.name}-ItemPreview",
            x=parent.field.rect.left / 70,
            y=lambda obj: round(
                self.buy_button.rect.top
                - parent.field.rect.left / 70 * 2
                - obj.rect.height
            ),
            width=parent.field.rect.left - parent.field.rect.left / 70 * 5,
            padding=10,
            hidden=True,
        )
        self.item_preview.disable()

        self.item_desc: ItemDescription = ...  # Описание выбранного предмета

    def add_item(self, item: Item | None) -> ItemStand:
        """
        Добавляет предмет в магазин.
        Автоматически смещает предмет на новую линию,
        если нехватает места для его отображения.
        :param item:
        :return:
        """
        icon_size = int(int(os.environ["icon_size"]))

        # Кол-во предметов в строке
        max_height = (icon_size * 2 + round(icon_size / 3)) * 4
        height = float("inf")
        width = icon_width = 0
        in_line_count = (
            len(self.network_client.room.players)
            if len(self.network_client.room.players) <= 3
            else 4
        ) - 1

        while height > max_height:
            in_line_count += 1
            lines = math.ceil(len(self.network_client.room.shop) / in_line_count)
            width = int((self.rect.width - self.padding * 2) / in_line_count)
            icon_width = icon_size if width > icon_size * 2 else round((width - 6) / 2)
            height = (icon_width * 2 + round(icon_width / 3)) * lines

        if not len(self.items):  # Если это первый предмет
            x = 0
            y = round(self.height / 9 * 3.5 / 70 * 5)
        else:
            y = self.items[-1].rect.y
            x = self.items[-1].rect.right
            if x + self.items[-1].rect.width > self.rect.width:
                x = 0
                y += self.items[-1].rect.height + icon_size / 3

        widget = ItemStand(
            f"{self.name}-{len(self.items) + 1}-ItemWidget",
            x,
            y,
            width,
            icon_width,
            item,
        )
        self.items.append(widget)
        return widget

    def handle_event(self, event: pg.event.Event) -> None:
        super(ShopMenu, self).handle_event(event)
        if self.enabled:
            if event.type == pg.MOUSEBUTTONDOWN:
                if event.button == pg.BUTTON_LEFT:
                    if self.get_global_rect().collidepoint(event.pos):
                        for i, item in enumerate(self.items):
                            # Выбор предмета
                            if item.get_global_rect().collidepoint(event.pos):
                                if item.item:  # Если предмет еще не продан
                                    # Удаляем старое описание предмета
                                    if self.item_desc is not ...:
                                        self.item_preview.remove(self.item_desc)
                                    # Создаем новое описание предмета
                                    self.item_desc = ItemDescription(
                                        self.item_preview,
                                        f"{self.item_preview.name}-{i}-ItemDescription",
                                        x=0,
                                        y=0,
                                        item=item.item,
                                        item_index=i,
                                    )
                                    self.item_preview.enable()
                                    self.item_preview.show()
                                    self.buy_button.enable()
                                else:
                                    self.item_preview.disable()
                                    self.item_preview.hide()
                                    self.buy_button.disable()
                                self.item_preview.update()
                                break


class DicesWidget(WidgetsGroup):
    def __init__(self, parent: GameClientScreen):

        super(DicesWidget, self).__init__(
            parent,
            f"{parent.name}-DicesWidget",
            x=0,
            y=lambda obj: parent.pass_move_button.rect.top
            - obj.rect.height
            - parent.field.rect.left / 70 * 3,
            width=parent.field.rect.left,
        )

        self.dice = Dice(
            self,
            f"{self.name}-DefaultDice",
            # Оборот на 180 градусов за пол секунды
            speed=lambda obj: obj.rect.width / parent.clock.get_fps() * 6,
            x=lambda obj: round(
                self.rect.w / 70 * 3
                + (self.rect.width - self.rect.w / 70 * 3) / 2
                - obj.rect.width
                - 15
            ),
            y=0,
            width=round(parent.field.rect.left / 3),
            files_namespace=os.path.join(os.environ["CUBE_PATH"], "default"),
        )

        self.dice2 = Dice(
            self,
            f"{self.name}-AttackDice",
            speed=lambda obj: obj.rect.width / parent.clock.get_fps() * 6,
            x=lambda obj: self.dice.rect.right + 30,
            y=0,
            width=round(parent.field.rect.left / 3),
            files_namespace=os.path.join(os.environ["CUBE_PATH"], "fight"),
        )

    def update(self, *args, **kwargs) -> None:
        if hasattr(self, "_objects"):
            upd = False
            for widget in self.objects:
                upd = widget.update(*args, **kwargs) or upd
            if upd:
                BaseWidget.update(self, *args, **kwargs)


class GameClientScreen(Group):
    def __init__(self, network_client: NetworkClient = None):
        resolution = Resolution.converter(os.environ["resolution"])
        font_size = int(os.environ["font_size"])
        font = os.environ.get("font")

        self.clock = pg.time.Clock()
        self.running = True
        self.finish_status = FinishStatus.close

        super(GameClientScreen, self).__init__(name="GameClientScreen")
        self.network_client = (
            self.network_client if hasattr(self, "network_client") else network_client
        )

        # Если выставлено максимально возможное разрешение, открываем окно в полный экран
        if not hasattr(self, "screen") or resolution != pg.display.get_window_size():
            if resolution >= Resolution.converter(os.environ["MAX_RESOLUTION"]):
                self.screen = pg.display.set_mode(resolution, pg.FULLSCREEN)
            else:
                self.screen = pg.display.set_mode(resolution)

        self.loading_screen = LoadingScreen(
            self, f"{self.name}-LoadingScreen", parent_size=resolution
        )
        self.loading_screen.show_message("Загрузка окружения...")

        self.field = Field(self)
        self.players_menu = PlayersMenu(self)
        self.shop = ShopMenu(self)

        self.pass_move_button = Button(
            self,
            f"{self.name}-PassMoveButton",
            x=self.field.rect.left / 70 * 3,
            y=lambda obj: (
                resolution.height
                - self.field.rect.left / 70 * 3
                - obj.rect.height
                - self.field.rect.left / 70 * 3 / 3
            ),
            width=self.field.rect.left - 20,
            text="Пропустить ход",
            padding=5,
            active_background=pg.Color(222, 222, 222, 100),
            font=pg.font.Font(font, font_size),
            anchor=Anchor.center,
            callback=lambda ev: self.network_client.pass_move(
                self.info_alert.show_message
            ),
        )
        if self.network_client.room.queue != f"p{self.network_client.user.uid}":
            self.pass_move_button.hide()
            self.pass_move_button.disable()

        self.dices_widget = DicesWidget(self)

        self.player_nemu = PlayerWidget(
            self,
            self.network_client,
            width=self.players_menu.width - self.players_menu.padding * 2,
            x=lambda obj: self.field.rect.left / 70 * 5,
            y=lambda obj: round(
                self.dices_widget.rect.top
                - obj.rect.height
                - self.field.rect.left / 70 * 2
            ),
        )
        self.enemy_menu = EnemyMenu(self)
        self.boss_menu = BossMenu(self)

        self.esc_menu = EscMenu(self)
        self.info_alert = InfoAlert(
            self,
            f"{self.name}-InfoAlert",
            parent_size=resolution,
            width=int(resolution.width * 0.7),
        )
        self.my_queue_alert = MyQueueAlert(self.field)
        self.game_over_alert = GameOverAlert(self)

        self.network_client.on_leaving_the_lobby(
            callback=lambda msg: (
                self.info_alert.show_message(msg),
                self.players_menu.update_players(),
                self.field.update_field(),
            )
        )
        self.network_client.on_loading_game(
            callback=lambda: self.loading_screen.show_message(
                "Переход на новый уровень"
            )
        )
        self.network_client.on_start_game(callback=self.on_start_game)
        self.network_client.on_game_over(
            callback=lambda data: (
                self.game_over_alert.init(data),
                self.game_over_alert.show(),
            )
        )
        self.network_client.on_ping(callback=self.field.spawn_ping)

        # ITEMS
        self.network_client.on_buying_an_item(
            callback=lambda item_index, player: (
                self.shop.items[item_index].sales(),
                self.update_player(player),
                (
                    (self.shop.item_preview.hide(), self.shop.item_preview.disable())
                    if self.shop.item_desc is not ...
                    and self.shop.item_desc.item_index == item_index
                    else ...
                ),
            )
        )
        self.network_client.on_removing_an_item(callback=self.update_player)

        # MOVING
        self.network_client.on_player_moving(
            callback=lambda: (
                self.field.ways.clear(),
                self.field.update_field(),
                self.network_client.next(),
            )
        )
        self.network_client.on_enemy_moving(callback=self.field.update_field)
        self.network_client.on_boss_moving(callback=self.field.update_field)

        # UPDATES
        self.network_client.on_update_players(
            callback=lambda: list(
                self.update_player(player)
                for player in self.network_client.room.players
            )
        )
        self.network_client.on_update_enemies(callback=self.field.update_field)
        self.network_client.on_boss_heal(callback=self.on_boss_heal)
        self.network_client.on_set_queue(callback=self.on_set_queue)

        # FIGHT
        self.network_client.on_fight(callback=self.on_fight)

        # HITS
        self.network_client.on_hit_player(callback=self.update_player)
        self.network_client.on_kill_player(callback=self.on_kill_player)
        self.network_client.on_hit_enemy(
            callback=lambda enemy: (
                self.field.update_field(),
                (
                    self.enemy_menu.update_data(enemy)
                    if not self.enemy_menu.hidden
                    and self.enemy_menu.enemy is not None
                    and self.enemy_menu.enemy.data.eid == enemy.eid
                    else ...
                ),
            )
        )
        self.network_client.on_kill_enemy(
            callback=lambda eid: (
                self.field.update_field(),
                (
                    (self.enemy_menu.disable(), self.enemy_menu.hide())
                    if not self.enemy_menu.hidden
                    and self.enemy_menu.enemy is not None
                    and self.enemy_menu.enemy.data.eid == eid
                    else ...
                ),
            )
        )
        self.network_client.on_hit_boss(
            callback=lambda boss: (
                self.boss_menu.hp.value.__setattr__("text", str(boss.hp))
                if not self.boss_menu.hidden
                else ...
            )
        )
        self.network_client.on_kill_boss(callback=self.field.update_field)
        self.network_client.on_hit(callback=self.on_hit)

        # CHOICE ENEMY
        self.network_client.on_need_choice_enemy(self.on_need_choice_enemy)

        # ROLLING DICES
        self.network_client.on_rolling_the_dice(callback=self.rolling_the_dice)
        self.network_client.on_rolling_the_fight_dice(
            callback=self.rolling_the_fight_dice
        )
        self.network_client.on_boss_rolling_the_dice(
            callback=self.rolling_the_fight_dice
        )

        if self.__dict__.get("eids"):
            del self.__dict__["eids"]

        self.loading_screen.hide()

        self._left_menu_image = load_image(
            "left_menu.png", size=(None, resolution.height), save_ratio=True
        )
        self._left_menu_rect = pg.Rect(0, 0, *self._left_menu_image.get_size())
        self._right_menu_image = load_image(
            "right_menu.png", size=(None, resolution.height), save_ratio=True
        )
        self._right_menu_rect = pg.Rect(
            resolution.width - self._right_menu_image.get_width(),
            0,
            *self._right_menu_image.get_size(),
        )

    def on_start_game(self) -> None:
        self.__init__()

    def update_player(self, player: Player) -> None:
        if player.uid == self.players_menu.client_player.player.uid:
            self.players_menu.client_player.update_data(player)
        else:
            for pos, character_widget in self.field.characters.items():
                if character_widget.data.uid == player.uid:
                    self.field.characters[pos].data = player
            if self.player_nemu.player is not None and not self.player_nemu.hidden:
                if self.player_nemu.player.uid == player.uid:
                    self.player_nemu.update_data(player)

    def on_set_queue(self, queue: str) -> None:
        if len(self.field.ways):
            self.field.ways.clear()
            self.field.update_field()
        if eids := self.__dict__.get("eids"):
            for enemy in self.field.enemies.values():
                if enemy.data.eid in eids:
                    enemy.indicator = None
            self.field.update_field()

        if queue.startswith("p"):
            uid = int(queue[1:])
            if uid == self.players_menu.client_player.player.uid:
                if len(self.network_client.room.players) > 1:
                    self.my_queue_alert.alert()
                    self.my_queue_alert.update()
                self.pass_move_button.show()
                self.pass_move_button.enable()
            else:
                self.pass_move_button.hide()
                self.pass_move_button.disable()

            for widget in [*self.players_menu.players, self.players_menu.client_player]:
                color = (
                    pg.Color("#b9a66d")
                    if widget.player.uid == uid
                    else pg.Color("white")
                )
                if widget.username.color != color:
                    widget.username.color = color
        elif queue == "boss":
            self.pass_move_button.hide()
            self.pass_move_button.disable()

            for widget in [*self.players_menu.players, self.players_menu.client_player]:
                color = pg.Color("white")
                if widget.username.color != color:
                    widget.username.color = color

        self.network_client.next()

    def on_fight(self, uid: int) -> None:
        if uid == self.players_menu.client_player.player.uid:
            if eids := self.__dict__.get("eids"):
                for enemy in self.field.enemies.values():
                    if enemy.data.eid in eids:
                        enemy.indicator = None
                del self.__dict__["eids"]
                self.field.update_field()
            self.pass_move_button.show()
            self.pass_move_button.enable()
        else:
            self.pass_move_button.hide()
            self.pass_move_button.disable()

        for widget in [*self.players_menu.players, self.players_menu.client_player]:
            color = pg.Color("red") if widget.player.uid == uid else pg.Color("white")
            if widget.username.color != color:
                widget.username.color = color

    def on_hit(self, cords: list[tuple[int, int]]) -> None:
        self.field.init_hit(cords)

    def on_kill_player(self, player: Player) -> None:
        self.update_player(player)

        for pos, character_widget in self.field.characters.items():
            if character_widget.data.uid == player.uid:
                character_widget.indicator = load_image(
                    "hp.png",
                    namespace=os.environ["UI_ICONS_PATH"],
                    size=(round(self.field.block_height), None),
                    save_ratio=True,
                )

    def on_boss_heal(self) -> None:
        def _remove_indicator():
            time.sleep(2)
            self.field.boss.indicator = None
            self.field.update_field()

        self.field.boss.indicator = load_image(
            "hp.png",
            namespace=os.environ["UI_ICONS_PATH"],
            size=(round(self.field.block_width), None),
            save_ratio=True,
        )
        self.field.update_field()

        if not self.boss_menu.hidden:
            self.boss_menu.hp.value.__setattr__(
                "text", str(self.network_client.room.boss.hp)
            )

        Thread(_remove_indicator).run()

    def on_need_choice_enemy(self, uid: int, eids: list[int]) -> None:
        icon_size = int(int(os.environ["icon_size"]) * 0.5)

        if uid == self.network_client.user.uid:
            self.__dict__["eids"] = eids
            for enemy in self.field.enemies.values():
                if enemy.data.eid in eids:
                    enemy.indicator = load_image(
                        "damage.png",
                        namespace=os.environ["UI_ICONS_PATH"],
                        size=(icon_size, icon_size),
                    )
            self.field.update_field()

    def rolling_the_dice(self, movement: list[tuple[int, int]]):
        self.dices_widget.dice.move_from_list(movement)

    def rolling_the_fight_dice(self, movement: list[tuple[int, int]]):
        self.dices_widget.dice2.move_from_list(movement)

    def exec(self) -> str:
        while self.running:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.terminate()
                self.handle_event(event)
                self.loading_screen.update()
            self.dices_widget.update()
            self.render()
            self.clock.tick()
        return self.finish_status

    def render(self) -> None:
        self.screen.fill("#f0f0f0")

        self.screen.blit(self._left_menu_image, self._left_menu_rect)
        self.screen.blit(self._right_menu_image, self._right_menu_rect)

        self.draw(self.screen)

        pg.display.flip()

    def terminate(self) -> None:
        self.running = False

    def handle_event(self, event: pg.event.Event) -> None:
        super(GameClientScreen, self).handle_event(event)
        if self.network_client.room is ...:
            return

        if self.enabled:
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    # Обработка открытия / закрытия меню
                    if self.esc_menu.parent.hidden:
                        self.esc_menu.show()
                    else:
                        self.esc_menu.settings.hide()
                        self.esc_menu.hide()
            elif event.type == ButtonClickEvent.type:
                # Кнопка покупки предмета
                if event.obj == self.shop.buy_button:
                    if self.shop.item_desc is not ...:
                        self.network_client.buy_item(
                            self.shop.item_desc.item_index,
                            fail_callback=lambda msg: self.info_alert.show_message(msg),
                        )
            elif event.type == DiceMovingStop.type:
                if event.obj == self.dices_widget.dice:
                    player = self.network_client.room.get_by_uid(
                        self.network_client.user.uid
                    )
                    if (
                        self.network_client.room.move_data.uid
                        == self.network_client.user.uid
                    ):
                        if not self.pass_move_button.hidden:
                            self.pass_move_button.enable()
                        self.field.init_ways(
                            get_ways(
                                player.character.pos,
                                self.network_client.room.move_data.num
                                + player.character.move_speed,
                                self.network_client.room.field,
                            )
                        )
                    else:
                        self.field.update_field()
                elif event.obj == self.dices_widget.dice2:
                    if not self.pass_move_button.hidden:
                        self.pass_move_button.enable()
                    self.field.update_field()
                    for player in self.network_client.room.players:
                        self.update_player(player)
                self.network_client.next("stop rolling")
            elif event.type == pg.MOUSEBUTTONDOWN:
                if event.button == pg.BUTTON_LEFT:
                    if self.field.enabled:
                        if pg.key.get_mods() & pg.KMOD_ALT:
                            pos = (
                                event.pos[1] // round(self.field.block_height),
                                (event.pos[0] - self.field.rect.left)
                                // round(self.field.block_width),
                            )
                            if self.network_client.room.field[pos[0]][pos[1]]:
                                self.network_client.ping(*pos)
                                return

                        for pos, rect in self.field.ways.items():
                            if self.field.get_global_rect_of(rect).collidepoint(
                                event.pos
                            ):
                                self.network_client.move(
                                    *pos, fail_callback=self.info_alert.show_message
                                )

                        if self.field.boss is not ...:
                            if self.field.boss.data.hp > 0:
                                if self.field.get_global_rect_of(
                                    self.field.boss.rect
                                ).collidepoint(event.pos):
                                    if self.__dict__.get("eids"):
                                        self.network_client.choice_enemy(
                                            -1,
                                            fail_callback=self.info_alert.show_message,
                                        )
                                    self.enemy_menu.hide()
                                    self.player_nemu.hide()
                                    self.player_nemu.disable()
                                    self.boss_menu.init(self.field.boss)
                                    return
                        for enemy in self.field.enemies.values():
                            if self.field.get_global_rect_of(enemy.rect).collidepoint(
                                event.pos
                            ):
                                if self.__dict__.get("eids"):
                                    self.network_client.choice_enemy(
                                        enemy.data.eid,
                                        fail_callback=self.info_alert.show_message,
                                    )
                                self.boss_menu.hide()
                                self.player_nemu.hide()
                                self.player_nemu.disable()
                                self.enemy_menu.init(enemy)
                                return
                        for player in self.field.characters.values():
                            if (
                                player.data.uid
                                != self.players_menu.client_player.player.uid
                            ):
                                if self.field.get_global_rect_of(
                                    player.rect
                                ).collidepoint(event.pos):
                                    self.boss_menu.hide()
                                    self.enemy_menu.hide()
                                    self.player_nemu.update_data(player.data)
                                    self.player_nemu.show()
                                    self.player_nemu.enable()
                                    return

                        if self.field.finish is not ...:
                            if self.field.get_global_rect_of(
                                self.field.finish
                            ).collidepoint(event.pos):
                                self.loading_screen.show_message(
                                    "Переход на новый уровень"
                                )
                                self.network_client.start_game(
                                    fail_callback=self.info_alert.show_message
                                )
                    if self.dices_widget.enabled:
                        if self.dices_widget.dice.get_global_rect().collidepoint(
                            event.pos
                        ):
                            self.pass_move_button.disable()
                            self.network_client.roll_the_dice(
                                lambda msg: (
                                    self.info_alert.show_message(msg),
                                    self.pass_move_button.enable(),
                                )
                            )
                        if self.dices_widget.dice2.get_global_rect().collidepoint(
                            event.pos
                        ):
                            self.pass_move_button.disable()
                            self.network_client.roll_the_fight_dice(
                                lambda msg: (
                                    self.info_alert.show_message(msg),
                                    self.pass_move_button.enable(),
                                )
                            )
