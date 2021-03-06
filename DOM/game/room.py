from __future__ import annotations

import typing as ty
from dataclasses import dataclass

from .boss import Boss
from .enemy import Enemy
from .item import Item
from .player import Player

if ty.TYPE_CHECKING:
    from ..network import User


@dataclass
class Move:
    uid: int
    num: int  # Число, выпавшее на кости
    movement: list[tuple[int, int]]  # Движение кости


class Room:
    def __init__(self, room_id: int):
        self.room_id = room_id
        self.game = False
        self.lvl = 1

        self.players: list[Player] = []
        self.boss: Boss = ...
        self.enemies: list[Enemy] = []

        self.queue: str = ""
        self.move_data: Move = ...

        self.field: list[list[True | False]] = ...
        self.location_name: str = ...
        self.location: list[list[int]] = ...
        self.shop: list[Item | None] = ...

    def join(self, user: User | Player, is_owner: True | False = False) -> None:
        self.players.append(
            user if isinstance(user, Player) else Player.from_user(user, is_owner)
        )

    def leave(self, uid: int) -> None:
        if player := self.get_by_uid(uid):
            self.players.remove(player)
        if len(self.players):
            self.players[0].is_owner = True

    def get_by_uid(self, uid: int) -> Player | None:
        if players := [player for player in self.players if player.uid == uid]:
            return players[0]

    def get_by_eid(self, eid: int) -> Enemy | None:
        if enemies := [enemy for enemy in self.enemies if enemy.eid == eid]:
            return enemies[0]

    def update_player(self, player: dict) -> None:
        self.players[self.players.index(self.get_by_uid(player["uid"]))].update(player)

    def update_enemies(self, enemies: list[dict]) -> None:
        self.enemies = [Enemy(**enemy) for enemy in enemies]

    def update_enemy(self, enemy: dict) -> None:
        self.enemies[self.enemies.index(self.get_by_eid(enemy["eid"]))].__dict__.update(
            enemy
        )

    def update_boss(self, boss: dict) -> None:
        self.boss.__dict__.update(boss)

    def init_lvl(
        self,
        lvl: int,
        field: list[list],
        location_name: str,
        location: list[list],
        shop: list[dict],
        players: list[dict],
        boss: dict,
        enemies: list[dict],
        queue: str,
    ) -> None:
        self.lvl = lvl
        self.field = field
        self.location_name = location_name
        self.location = location
        self.shop = [Item(**item) if item else None for item in shop]
        self.players = [Player(**player) for player in players]
        self.boss = Boss(**boss)
        self.enemies = [Enemy(**enemy) for enemy in enemies]
        self.queue = queue
