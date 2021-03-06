"""

Интерфейс авторизации и регистрации.

"""

from __future__ import annotations

import os
import typing as ty

import pygame as pg

from base import Group, Button, Label, WidgetsGroup, InputBox
from utils import (
    FinishStatus,
    check_password,
    NickTextFilter,
    PasswordTextFilter,
    InfoAlert,
)

if ty.TYPE_CHECKING:
    from network import NetworkClient


class Login(WidgetsGroup):
    """
    Интерфейс авторизации.
    """

    def __init__(self, parent: AuthScreen):
        font = os.environ.get("font")

        super(Login, self).__init__(
            parent,
            f"{parent.name}-Login",
            x=0,
            y=0,
            width=parent.SIZE[0],
            height=parent.SIZE[1],
            padding=20,
        )

        self.title = Label(
            self,
            f"{self.name}-TitleLabel",
            x=lambda obj: round(self.rect.width / 2 - obj.rect.width / 2 - 20),
            y=int(parent.SIZE[1] * 0.2),
            text="Авторизация",
            padding=7,
            border_width=3,
            font=pg.font.Font(font, 30),
        )

        self.login = InputBox(
            self,
            f"{self.name}-LoginInputBox",
            x=0,
            y=self.title.rect.bottom + 40,
            description="Имя пользователя",
            width=self.rect.width * 0.9,
            padding=5,
            font=pg.font.Font(font, 25),
            inactive_border_color=pg.Color("#b9a66d"),
            active_border_color=pg.Color("#f0ce69"),
            border_width=2,
            text_filter=NickTextFilter,
        )

        self.password = InputBox(
            self,
            f"{self.name}-PasswordInputBox",
            x=0,
            y=self.login.rect.bottom + 30,
            description="Пароль",
            width=self.rect.width * 0.9,
            padding=5,
            font=pg.font.Font(font, 20),
            inactive_border_color=pg.Color("#b9a66d"),
            active_border_color=pg.Color("#f0ce69"),
            border_width=2,
            is_password=True,
            text_filter=PasswordTextFilter,
        )

        self.login_button = Button(
            self,
            f"{self.name}-LoginButton",
            x=lambda obj: round(self.rect.width / 2 - obj.rect.width / 2) - 20,
            y=self.password.rect.bottom + 30,
            text="Войти",
            padding=5,
            active_background=pg.Color(222, 222, 222, 100),
            font=pg.font.Font(font, 17),
            border_width=2,
            callback=lambda event: self.auth(parent),
        )

        self.signup_button = Button(
            self,
            f"{self.name}-SignupButton",
            x=lambda obj: round(self.rect.width / 2 - obj.rect.width / 2) - 20,
            y=self.login_button.rect.bottom + 5,
            text="зарегистрироваться",
            padding=5,
            color=pg.Color("#f0ce69"),
            font=pg.font.Font(font, 13),
            callback=lambda event: parent.show_signup_group(),
        )

    def auth(self, parent: AuthScreen) -> None:
        """
        Попытка авторизации пользователя
        :param parent:
        """
        if not (login := self.login.input_line.text):
            self.login.input_line.active = True
            return
        if not (password := self.password.input_line.value()):
            self.password.input_line.active = True
            return

        self.disable()
        parent.network_client.login(
            username=login,
            password=password,
            success_callback=lambda: parent.auth(login, password),
            fail_callback=lambda msg: (
                self.enable(),
                parent.error_alert.show_message(msg),
            ),
        )


class Signup(WidgetsGroup):
    """
    Интерфейс регистрации.
    """

    def __init__(self, parent: AuthScreen):
        font = os.environ.get("font")

        super(Signup, self).__init__(
            parent,
            f"{parent.name}-Signup",
            x=0,
            y=0,
            width=parent.SIZE[0],
            height=parent.SIZE[1],
            padding=20,
        )

        self.title = Label(
            self,
            f"{self.name}-TitleLabel",
            x=lambda obj: round(self.rect.width / 2 - obj.rect.width / 2 - 20),
            y=int(parent.SIZE[1] * 0.1),
            text="Регистрация",
            border_width=3,
            padding=7,
            font=pg.font.Font(font, 30),
        )

        self.login = InputBox(
            self,
            f"{self.name}-LoginInputBox",
            x=0,
            y=self.title.rect.bottom + 40,
            description="Имя пользователя",
            width=self.rect.width * 0.9,
            padding=5,
            font=pg.font.Font(font, 20),
            inactive_border_color=pg.Color("#b9a66d"),
            active_border_color=pg.Color("#f0ce69"),
            border_width=2,
            text_filter=NickTextFilter,
        )

        self.password = InputBox(
            self,
            f"{self.name}-PasswordInputBox",
            x=0,
            y=self.login.rect.bottom + 30,
            description="Пароль",
            width=self.rect.width * 0.9,
            padding=5,
            font=pg.font.Font(font, 20),
            inactive_border_color=pg.Color("#b9a66d"),
            active_border_color=pg.Color("#f0ce69"),
            border_width=2,
            is_password=True,
            text_filter=PasswordTextFilter,
        )

        self.password2 = InputBox(
            self,
            f"{self.name}-Password2InputBox",
            x=0,
            y=self.password.rect.bottom + 30,
            description="Повторите пароль",
            width=self.rect.width * 0.9,
            padding=5,
            font=pg.font.Font(font, 20),
            inactive_border_color=pg.Color("#b9a66d"),
            active_border_color=pg.Color("#f0ce69"),
            border_width=2,
            is_password=True,
            text_filter=PasswordTextFilter,
        )

        self.signup_button = Button(
            self,
            f"{self.name}-SignupButton",
            x=lambda obj: round(self.rect.width / 2 - obj.rect.width / 2) - 20,
            y=self.password2.rect.bottom + 30,
            text="Создать аккаунт",
            padding=5,
            active_background=pg.Color(222, 222, 222, 100),
            font=pg.font.Font(font, 17),
            border_width=2,
            callback=lambda event: self.auth(parent),
        )

        self.login_button = Button(
            self,
            f"{self.name}-LoginButton",
            x=lambda obj: round(self.rect.width / 2 - obj.rect.width / 2) - 20,
            y=self.signup_button.rect.bottom + 5,
            text="авторизоваться",
            padding=5,
            color=pg.Color("#f0ce69"),
            font=pg.font.Font(font, 13),
            callback=lambda event: parent.show_login_group(),
        )

    def auth(self, parent: AuthScreen) -> None:
        """
        Попытка регистрации пользователя.
        :param parent:
        """
        if not (login := self.login.input_line.text):
            self.login.input_line.active = True
            return
        if not (password := self.password.input_line.value()):
            self.password.input_line.active = True
            return
        if not (password2 := self.password2.input_line.value()):
            self.password2.input_line.active = True
            return
        if password != password2:
            parent.error_alert.show_message("Пароли не совпадают")
            return
        if not check_password(password):
            parent.error_alert.show_message("Пароль слишком легкий")
            return

        self.disable()
        parent.network_client.signup(
            username=login,
            password=password,
            success_callback=lambda: parent.auth(login, password),
            fail_callback=lambda msg: (
                self.enable(),
                parent.error_alert.show_message(msg),
            ),
        )


class AuthScreen(Group):
    SIZE = (450, 550)

    def __init__(self, network_client: NetworkClient, error: str = ""):
        super(AuthScreen, self).__init__(name="AuthScreen")

        self.network_client = network_client

        self.screen = pg.display.set_mode(self.SIZE)
        pg.display.set_caption("DOM Auth")

        self.login_group = Login(self)
        self.signup_group = Signup(self)
        self.show_login_group()

        self.error_alert = InfoAlert(
            self,
            f"{self.name}-InfoAlert",
            parent_size=self.SIZE,
            width=int(self.SIZE[0] * 0.9),
        )
        if error:
            self.error_alert.show_message(error)

        self.running = True
        self.finish_status: str = FinishStatus.close

    def show_login_group(self) -> None:
        """
        Отображает интерфейс авторизации.
        """
        self.signup_group.disable()
        self.signup_group.hide()
        self.login_group.enable()
        self.login_group.show()

    def show_signup_group(self) -> None:
        """
        Отображает интерфейс регистрации.
        """
        self.login_group.disable()
        self.login_group.hide()
        self.signup_group.enable()
        self.signup_group.show()

    def auth(self, login: str, password: str) -> None:
        """
        Завершает авторизацию пользователя.
        Сохраняет данные от аккаунта.
        :param login: Имя пользователя.
        :param password: Пароль.
        """
        with open(os.environ["AUTH_PATH"], "w", encoding="utf-8") as file:
            file.write(f"{login}\n{password}")

        self.finish_status = FinishStatus.ok
        self.screen.fill("black")
        pg.display.flip()
        self.terminate()

    def exec(self) -> str:
        """
        :return: FinishStatus.
        """
        while self.running:  # Цикл окна
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.terminate()
                self.handle_event(event)
            self.render()
        return self.finish_status

    def render(self) -> None:
        """
        Отрисовка интерфейса.
        """
        self.screen.fill("#152622")
        pg.draw.rect(
            self.screen,
            "#b9a66d",
            pg.Rect(5, 5, self.SIZE[0] - 10, self.SIZE[1] - 10),
            width=3,
        )
        self.draw(self.screen)
        pg.display.flip()

    def terminate(self) -> None:
        """
        Остановка приложения.
        """
        self.running = False
