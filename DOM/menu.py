"""

Меню клиента.

"""

from __future__ import annotations

import os
import typing as ty

import pygame as pg

from app_info_alert import AppInfoAlert
from base import Button, WidgetsGroup, Group
from base.events import ButtonClickEvent
from database.field_types import Resolution
from lobby import Lobby, LobbyInvite
from settings_alert import Settings
from social import Social
from utils import InfoAlert, LoadingAlert, FinishStatus, load_image

if ty.TYPE_CHECKING:
    from network import NetworkClient


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
            callback=lambda event: parent.terminate(),
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
            color=pg.Color("red"),
            active_background=pg.Color("#171717"),
            font=pg.font.Font(font, font_size),
            border_color=pg.Color("red"),
            border_width=2,
            callback=lambda event: self.app_info_alert.show(),
        )

        self.buttons = MenuButtons(self)
        self.lobby = Lobby(self, self.network_client)
        self.social = Social(self, self.network_client)
        self.setting = Settings(self)
        self.app_info_alert = AppInfoAlert(self)

        self.info_alert = InfoAlert(
            self,
            f"{self.name}-InfoAlert",
            parent_size=resolution,
            width=int(resolution.width * 0.5),
        )
        self.loading_alert = LoadingAlert(
            self,
            f"{self.name}-LoadingAlert",
            parent_size=resolution,
            width=int(resolution.width * 0.5),
        )

        # Приглашение в лобби
        self.lobby_invite: LobbyInvite = ...

        # Подключаем обработчики событий
        self.network_client.on_lobby_invite(callback=self.on_lobby_invite)
        self.network_client.on_joining_the_lobby(callback=self.lobby.init)
        self.network_client.on_leaving_the_lobby(
            callback=lambda msg: (self.lobby.init(), self.info_alert.show_message(msg))
        )

        self.network_client.on_loading_game(
            callback=lambda: self.loading_alert.show_message("Запуск игры")
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

    def open_lobby(self) -> None:
        """
        Скрывает кнопки меню и открывает лобби.
        """
        self.buttons.hide(),
        self.buttons.disable(),
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

                self.handle_event(event)
            self.render()
        return self.finish_status

    def render(self) -> None:
        self.screen.blit(self.back_art, self.back_art.get_rect())
        self.draw(self.screen)

        pg.display.flip()

    def terminate(self) -> None:
        self.running = False
