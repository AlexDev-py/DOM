"""

Меню клиента.

"""

from __future__ import annotations

import os
import typing as ty

import pygame as pg

from app_info_alert import AppInfoAlert
from base import Button, WidgetsGroup, Group, Alert, Label
from base.events import ButtonClickEvent
from database.field_types import Resolution
from lobby import Lobby, LobbyInvite
from settings_alert import Settings
from social import Social
from utils import InfoAlert, FinishStatus, load_image, LoadingScreen

if ty.TYPE_CHECKING:
    from network import NetworkClient


class ExitAlert(Alert):
    def __init__(self, parent: MenuScreen):
        resolution = Resolution.converter(os.environ["resolution"])
        font_size = int(os.environ.get("font_size"))
        font = os.environ.get("font")

        super(ExitAlert, self).__init__(
            parent,
            "ExitAlert",
            parent_size=resolution,
            padding=20,
            background=pg.Color("#122321"),
            border_color=pg.Color("#b9a66d"),
            border_width=3,
        )

        self.title = Label(
            self,
            f"{self.name}-TitleLabel",
            x=lambda obj: round(
                (self.rect.width - self.padding * 2) / 2 - obj.rect.width / 2
            ),
            y=0,
            text="Выход",
            font=pg.font.Font(font, font_size),
        )

        self.cancel_button = Button(
            self,
            f"{self.name}-CancelButton",
            x=0,
            y=0,
            text=" X ",
            padding=5,
            active_background=pg.Color(222, 222, 222, 100),
            font=pg.font.Font(font, int(font_size * 0.7)),
            border_width=2,
            callback=lambda event: self.hide(),
        )

        self.exit_akk = Button(
            self,
            x=0,
            y=self.title.rect.bottom + 20,
            text="Выйти из аккаунта",
            padding=5,
            active_background=pg.Color(222, 222, 222, 100),
            font=pg.font.Font(font, font_size),
            border_width=2,
            callback=lambda event: (
                parent.terminate(),
                os.remove(os.environ["AUTH_PATH"])
                if os.path.isfile(os.environ["AUTH_PATH"])
                else ...,
            ),
        )

        self.exit_game = Button(
            self,
            x=self.exit_akk.rect.right + 5,
            y=self.title.rect.bottom + 20,
            width=self.exit_akk.rect.width,
            text="Выйти из игры",
            padding=5,
            active_background=pg.Color(222, 222, 222, 100),
            font=pg.font.Font(font, font_size),
            border_width=2,
            callback=lambda event: parent.terminate(),
        )

        self.update()


class MenuButtons(WidgetsGroup):
    def __init__(self, parent: MenuScreen):
        resolution = Resolution.converter(os.environ["resolution"])
        buttons_size = int(os.environ["buttons_size"])

        super(MenuButtons, self).__init__(
            parent,
            "MenuButtons",
            x=0,
            y=lambda obj: resolution.height - obj.rect.height,
            padding=20,
        )

        self.create_lobby_button = Button(
            self,
            f"{self.name}-CreateLobbyButton",
            x=0,
            y=0,
            width=lambda obj: obj.sprite.get_width(),
            height=lambda obj: obj.sprite.get_height(),
            sprite=load_image(
                "create_lobby_button.png",
                namespace=os.environ["BUTTONS_PATH"],
                size=(None, buttons_size),
                save_ratio=True,
            ),
            callback=lambda event: (
                self.disable(),
                parent.network_client.create_lobby(
                    callback=lambda: (parent.open_lobby())
                ),
            ),
        )

        self.settings_button = Button(
            self,
            f"{self.name}-SettingsButton",
            x=0,
            y=lambda btn: self.create_lobby_button.rect.y + 20 + btn.rect.h,
            width=lambda obj: obj.sprite.get_width(),
            height=lambda obj: obj.sprite.get_height(),
            sprite=load_image(
                "settings_button.png",
                namespace=os.environ["BUTTONS_PATH"],
                size=(None, buttons_size),
                save_ratio=True,
            ),
            callback=lambda event: parent.setting.show(),
        )

        self.exit_button = Button(
            self,
            f"{self.name}-ExitGameButton",
            x=0,
            y=lambda btn: self.settings_button.rect.y + 20 + btn.rect.h,
            width=lambda obj: obj.sprite.get_width(),
            height=lambda obj: obj.sprite.get_height(),
            sprite=load_image(
                "exit_button.png",
                namespace=os.environ["BUTTONS_PATH"],
                size=(None, buttons_size),
                save_ratio=True,
            ),
            callback=lambda event: parent.exit_alert.show(),
        )


class MenuScreen(Group):
    def __init__(self, network_client: NetworkClient = None):
        resolution = Resolution.converter(os.environ["resolution"])
        Settings.init_interface_size()
        font_size = int(os.environ.get("font_size"))
        font = os.environ.get("font")

        super(MenuScreen, self).__init__(name="MenuScreen")

        self.finish_status: str = FinishStatus.close
        self.running = True

        self.network_client = (
            self.network_client if hasattr(self, "network_client") else network_client
        )

        # Если выставлено максимально возможное разрешение, открываем окно в полный экран
        if resolution >= Resolution.converter(os.environ["MAX_RESOLUTION"]):
            self.screen = pg.display.set_mode(resolution, pg.FULLSCREEN)
        else:
            self.screen = pg.display.set_mode(resolution)

        self.app_info_button = Button(
            self,
            x=20,
            y=20,
            text=" i",
            padding=5,
            active_background=pg.Color("#171717"),
            font=pg.font.Font(font, font_size),
            border_width=2,
            callback=lambda event: self.app_info_alert.show(),
        )

        self.buttons = MenuButtons(self)
        self.lobby = Lobby(self, self.network_client)
        self.social = Social(self, self.network_client)
        self.setting = Settings(self)
        self.app_info_alert = AppInfoAlert(self)
        self.exit_alert = ExitAlert(self)

        self.info_alert = InfoAlert(
            self,
            f"{self.name}-InfoAlert",
            parent_size=resolution,
            width=int(resolution.width * 0.5),
        )

        # Приглашение в лобби
        self.lobby_invite: LobbyInvite = ...

        self.loading_screen = LoadingScreen(
            self, f"{self.name}-LoadingScreen", parent_size=resolution
        )

        # Подключаем обработчики событий
        self.network_client.on_lobby_invite(callback=self.on_lobby_invite)
        self.network_client.on_joining_the_lobby(callback=self.lobby.init)
        self.network_client.on_leaving_the_lobby(
            callback=lambda msg: (self.lobby.init(), self.info_alert.show_message(msg))
        )

        self.network_client.on_loading_game(
            callback=lambda: (
                self.loading_screen.show_message("Запуск игры"),
                self.update(),
            )
        )
        self.network_client.on_start_game(
            callback=lambda: (
                self.__setattr__("finish_status", FinishStatus.enter_game),
                self.terminate(),
            )
        )

        self.network_client.on_error(callback=self.info_alert.show_message)

        self.back_art = load_image(
            "backart.png", namespace=os.environ["APP_DIR"], size=resolution
        )  # Фоновая картинка

    def on_lobby_invite(self, msg: str, room_id: int) -> None:
        """
        Приглашение в лобби.
        :param msg: Сообщение.
        :param room_id: ID лобби.
        """
        if self.lobby_invite is not ...:  # Удаляем старое приглашение
            self.remove(self.lobby_invite)
            self.lobby_invite: LobbyInvite = ...
        self.lobby_invite = LobbyInvite(self.social, msg, room_id)
        self.app_info_button.disable()

    def open_lobby(self) -> None:
        """
        Скрывает кнопки меню и открывает лобби.
        """
        self.buttons.hide(),
        self.buttons.disable(),
        self.app_info_button.disable()
        self.app_info_button.hide()
        self.lobby.init(),
        self.lobby.show(),
        self.lobby.enable(),

    def exec(self) -> str:
        while self.running:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.terminate()
                elif event.type == ButtonClickEvent.type:
                    # Обработка нажатий на кнопки
                    if self.lobby_invite is not ...:
                        # Обработка взаимодействия с приглашением в лобби
                        if event.obj == self.lobby_invite.cancel:
                            self.remove(self.lobby_invite)  # Удаляем приглашение
                            self.lobby_invite: LobbyInvite = ...
                            self.app_info_button.enable()
                        elif event.obj == self.lobby_invite.accept:
                            self.remove(self.lobby_invite)  # Удаляем приглашение
                            self.network_client.join_lobby(
                                self.lobby_invite.room_id,
                                success_callback=self.open_lobby,
                                fail_callback=lambda msg: self.info_alert.show_message(
                                    msg
                                ),
                            )  # Присоединяемся к лобби
                            self.lobby_invite: LobbyInvite = ...
                    if self.lobby.buttons is not ...:
                        # Обработка кнопок в лобби
                        if event.obj == self.lobby.buttons.leave_lobby_button:
                            self.network_client.leave_lobby()
                            self.lobby.disable()
                            self.lobby.hide()
                            self.buttons.show()
                            self.buttons.enable()
                            self.app_info_button.enable()
                            self.app_info_button.show()

                self.handle_event(event)
            self.render()
        return self.finish_status

    def render(self) -> None:
        self.screen.blit(self.back_art, self.back_art.get_rect())
        self.draw(self.screen)

        pg.display.flip()

    def terminate(self) -> None:
        self.running = False
