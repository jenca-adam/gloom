#!/usr/bin/env python3
import tkinter
import enum
import time
import queue
import random
import itertools
import math
import cmath
import io

"""
This program contains a wrapper around tkinter's functions to make it less of a pain to use.
"""

### BEGIN


class Shape(enum.Enum):
    RECTANGLE = "create_rectangle"
    OVAL = "create_oval"
    TEXT = "create_text"


class Vector2:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    @property
    def norm(self):
        return math.sqrt(self.x**2 + self.y**2)

    @property
    def polar(self):
        return math.degrees(math.atan2(self.y, self.x)), self.norm

    @classmethod
    def from_polar(cls, angle, radius):
        angle = math.radians(angle)
        z = radius * (cmath.exp(1j * angle))
        return cls(z.real, z.imag)

    def rotate_around_origin(self, theta):
        angle, radius = self.polar
        return self.__class__.from_polar(angle + theta, radius)

    def normalize(self):
        return self * (1 / self.norm)

    def __repr__(self):
        return f"Vector2({self.x}, {self.y})"

    def __truediv__(self, num):
        return Vector2(self.x / num, self.y / num)

    def __floordiv__(self, num):
        return Vector2(self.x // num, self.y // num)

    def __rtruediv__(self, num):
        return Vector2(num / self.x, num / self.y)

    def __rfloordiv__(self, num):
        return Vector2(num // self.x, num // self.y)

    def __add__(self, v2):
        return Vector2(v2.x + self.x, v2.y + self.y)

    def __sub__(self, v2):
        return Vector2(self.x - v2.x, self.y - v2.y)

    def __mul__(self, num):
        return Vector2(self.x * num, self.y * num)

    def notdot(self, v2):
        return Vector2(self.x * v2.x, self.y * v2.y)

    def __iter__(self):
        return iter((self.x, self.y))

    def as_tuple(self):
        return (self.x, self.y)


class Coords:
    def __init__(self, *coords):
        self.coords = [
            Vector2(*coor) if not isinstance(coor, Vector2) else coor for coor in coords
        ]

    def as_list(self):
        return [
            item
            for sublist in [coor.as_tuple() for coor in self.coords]
            for item in sublist
        ]

    def __getitem__(self, item):
        return self.coords[item]

    def __setitem__(self, item, value):
        self.coords[item] = value

    def __add__(self, vec):
        return Coords(*[v + vec for v in self.coords])

    def __sub__(self, vec):
        return Coords(*[v - vec for v in self.coords])

    def __mul__(self, num):
        return Coords(*[v * num for v in self.coords])


class TkWrapper:
    def __init__(self, canvas):
        self.canvas = canvas

    def draw_call(self, shape, coords, kwargs):
        return self._call(shape.value, coords.as_list(), kwargs)

    def itemconfig_call(self, itemid, kwargs):
        return self._call("itemconfig", [itemid], kwargs)

    def coords_call(self, itemid, coords):
        return self._call("coords", [itemid, *coords.as_list()], {})

    def destroy_call(self, itemid):
        return self._call("delete", [itemid], {})

    def _call(self, *fargs):
        method, args, kwargs = fargs
        return getattr(self.canvas, method)(*args, **kwargs)


class Sprite:
    game = None
    name = "Sprite"
    shape = None
    fill = None
    kwargs = {}

    def __init__(self, coords, shape=None, **kwargs):
        self.coords = coords
        self.kwargs = self.kwargs.copy()
        self.kwargs.update(kwargs)
        self.kwargs["fill"] = kwargs.get("fill") or self.fill
        self.shape = shape or self.shape
        self.timer = self._add()
        self.render()

    def render(self):
        self.id = self.game.canvas_wrapper.draw_call(
            self.shape, self.coords, self.kwargs
        )

    def update(self, coords=True, kwargs=True):
        if coords:
            self.game.canvas_wrapper.coords_call(self.id, self.coords)
        if kwargs:
            self.game.canvas_wrapper.itemconfig_call(self.id, self.kwargs)

    def send_event(self, etype, *args):
        self.game.event_queue.put((etype, self, args))

    def _tick(self):
        self.tick()

    def tick(self):
        pass

    def ready(self):
        pass

    def join(self):
        self.thread.join()

    def quit(self):
        self.game.remove_sprite(self)
        self.game.canvas_wrapper.destroy_call(self.id)
        self.timer.stop()

    def _add(self):
        return self.game.add_sprite(self)

    @classmethod
    def instantiate(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    @property
    def center_point(self):
        return (self.coords[0] + self.coords[1]) * 0.5

    @property
    def fill(self):
        return self.kwargs["fill"]

    @fill.setter
    def fill(self, to):
        self.kwargs["fill"] = to

    @property
    def text(self):
        return self.kwargs["text"]

    @text.setter
    def text(self, to):
        self.kwargs["text"] = to


class Sprites:
    def __init__(self, sprites=set()):
        self.sprites = set(sprites)

    def __iter__(self):
        return iter(self.sprites)

    def by_name(self, name):
        return Sprites({sprite for sprite in self.sprites if sprite.name == name})

    def add_sprite(self, sprite):
        self.sprites.add(sprite)

    def remove_sprite(self, sprite):
        self.sprites.remove(sprite)

    def run_all_threads(self):
        for sprite in self.sprites:
            sprite.start()

    def destroy(self):
        for sprite in self.sprites.copy():
            sprite.quit()

    def try_run(self, funname):
        for sprite in self.sprites:
            if hasattr(sprite, funname):
                getattr(sprite, funname)()


class Timer:
    def __init__(self, timeout, callback, root):
        self.timeout = timeout
        self.callback = callback
        self.root = root
        self.stopped = False

    def __call__(self):
        if not self.stopped:
            self.callback()
            self.root.after(self.timeout, self)

    def stop(self):
        # print("tpause")
        self.stopped = True

    def resume(self):
        # print("tresume")
        if self.stopped:
            self.stopped = False
            self()


class Game:
    screen_size = (720, 720)
    screen_color = "white"
    fps = 60
    fullscreen = False
    _spriteclasses = set()
    _event_handlers = {}
    _ons = {}

    def __init__(self):
        for spriteclass in self._spriteclasses:
            spriteclass.game = self
        self.root = tkinter.Tk()
        if self.fullscreen:
            self.root.attributes("-fullscreen", True)
        self.timers = []
        self.started = False
        self._time = time.perf_counter()
        self.event_handlers = self._event_handlers
        self.canvas = tkinter.Canvas()
        self.canvas.pack()
        self.sprites = Sprites()
        self.event_queue = queue.Queue()
        self.canvas_wrapper = TkWrapper(self.canvas)
        self.canvas["width"], self.canvas["height"] = self.screen_size
        self.screen_size = Vector2(*self.screen_size)
        self.canvas.config(bg=self.screen_color)
        self.root.protocol("WM_DELETE_WINDOW", self.destroy)
        self.create_timer(1000 / self.fps)(self._internal_tick)
        self._bind_all_inputs()

    @classmethod
    def sprite(cls, name=None, shape=None, fill=None):
        def decorator(spriteclass):
            spriteclass.game = None
            spriteclass.name = name or spriteclass.__name__
            spriteclass.shape = shape or spriteclass.shape
            cls._spriteclasses.add(spriteclass)
            return spriteclass

        return decorator

    def _bind_one_input(self, input_type, func, bind_all):
        # tkinter sucks
        def _to_bind(*args):
            func(self, *args)

        if bind_all:
            self.root.bind_all(input_type, _to_bind)
        else:
            self.root.bind(input_type, _to_bind)

    def _bind_all_inputs(self):
        for input_type, (func, bind_all) in self._ons.items():
            self._bind_one_input(input_type, func, bind_all)

    def ready(self):
        pass

    def destroy(self):
        self.sprites.destroy()
        self.root.destroy()
        exit(0)

    @classmethod
    def add_on(self, input_type, func, bind_all=False):
        self._ons[input_type] = (func, bind_all)

    @classmethod
    def on(self, input_type, bind_all=False):
        def decorator(func):
            self.add_on(input_type, func, bind_all)
            return func

        return decorator

    def add_sprite(self, sprite):
        self.sprites.add_sprite(sprite)
        timer = self.create_timer(1000 / self.fps)(sprite._tick)
        if self.started:
            # timer()
            pass
        return timer

    def remove_sprite(self, sprite):
        pass

    @classmethod
    def add_event_handler(self, event_type, func):
        self._event_handlers[event_type] = func

    @classmethod
    def event_handler(self, event_type):
        def decorator(func):
            self.add_event_handler(event_type, func)
            return func

        return decorator

    def tick(self):
        pass

    def _internal_tick(self):
        tm = time.perf_counter()
        delta = tm - self._time
        self._time = tm
        while not self.event_queue.empty():
            event, caller, args = self.event_queue.get()
            if event in self.event_handlers:
                self.event_handlers[event](self, caller, *args)
        self.tick(delta)

    def after(self, timeout, callback):
        self.root.after(int(timeout), callback)

    def create_timer(self, timeout, run_on_startup=True):
        def _decorator(callback):
            timer = Timer(timeout, callback, self)
            if run_on_startup:
                self.timers.append(timer)
            return timer

        return _decorator

    def start(self):
        self.started = True
        self.ready()
        for timer in self.timers:
            timer()
        self.root.mainloop()

    @property
    def screen_center(self):
        return self.screen_size * 0.5


UP = Vector2(0, -1)
LEFT = Vector2(-1, 0)
RIGHT = Vector2(1, 0)
DOWN = Vector2(0, 1)
### END

GLOOM_FILE_VER = 1
WEAPON_PICKUP_CLASSES = {}
KEYCARDS = {}


def intersect(p1, p2, p3, p4):
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
    if denom == 0:  # parallel
        return None
    ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
    if ua < 0 or ua > 1:  # out of range
        return None
    ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom
    if ub < 0 or ub > 1:  # out of range
        return None
    x = x1 + ua * (x2 - x1)
    y = y1 + ua * (y2 - y1)
    return (x, y)


def uncomment(string):
    if not string:
        return None
    if "#" in string:
        return string[: string.index("#")].strip()
    return string.strip()


def parse_class_array(stream, class_dict):
    cl_array = []
    while True:
        line = uncomment(stream.readline())
        if line is None:
            break
        elif line.startswith(":"):
            item = line.removeprefix(":")
            if item == "end":
                break
            cl_array.append(class_dict[item])
    return cl_array


def rgb2hex(r, g, b):
    return f"#{r:02x}{g:02x}{b:02x}"


class Weapon:
    def __init__(self, num_bullets):
        self.num_bullets = num_bullets
        self._until_shoot = 0
        self._until_reload = 0
        self._bullets_left_in_magazine = self.bullets_per_mg
        self._bullets_left = num_bullets
        self._bullet_angle = self.spread / self.bullets_per_shot
        self._bullet_angles = tuple(
            self._bullet_angle * mult
            for mult in itertools.chain(
                range(-(self.bullets_per_shot // 2), self.bullets_per_shot % 2),
                range(1, self.bullets_per_shot // 2 + 1),
            )
        )

    def pickup_mg(self):
        self._bullets_left += self.bullets_per_mg
        self._bullets_left_in_magazine = self.bullets_per_mg

    def reload(self):
        self._until_reload = self.reload_rate
        self._bullets_left -= self._bullets_left_in_magazine
        self._bullets_left_in_magazine += self.bullets_per_mg
        # print("reload", self._bullets_left, self._bullets_left_in_magazine)

    def shoot(self, source, target, friendly, acc):
        # print("shoot", source, target, target - source)
        self._until_shoot = self.rate
        if self.bullets_per_shot > self._bullets_left_in_magazine:
            self.reload()
            return
        self._bullets_left_in_magazine -= self.bullets_per_shot
        self._bullets_left -= self.bullets_per_shot
        general_direction_vector = (target - source).normalize().rotate_around_origin(random.randint(-acc,acc))
        bullargs = []
        for angle in self._bullet_angles:
            bullargs.append(
                (
                    Coords(
                        source - Vector2(self.bullet_size // 2, self.bullet_size // 2),
                        source + Vector2(self.bullet_size // 2, self.bullet_size // 2),
                    ),
                    friendly,
                    self.speed,
                    general_direction_vector.rotate_around_origin(angle),
                    # general_direction_vector,
                    self.rng,
                    self.dmg,
                    self.pierce,
                )
            )
        return bullargs

    def tick(self, shoot=None):
        self._until_shoot = max(self._until_shoot - 1, 0)
        self._until_reload = max(self._until_reload - 1, 0)
        if shoot is None:
            return []
        elif self._bullets_left_in_magazine < self.bullets_per_shot:
            if self._bullets_left > 0:
                self.reload()
            return []
        elif self._until_shoot == self._until_reload == 0:
            src, dst, fnd, acc = shoot
            return self.shoot(src, dst, fnd, acc)
        return []


class GloomFile:
    def __init__(
        self,
        gloomfilepath,
        screen_size,
    ):
        self.gloom_properties = {}
        self.screen_size = Vector2(*screen_size)
        self.levels = []
        with open(gloomfilepath, "r") as self.stream:
            while True:
                line = uncomment(self.stream.readline())
                if line is None:
                    break
                elif line.startswith("@"):
                    cmd, *_val = line.removeprefix("@").split(None, 1)
                    value = _val[0] if _val else None
                    if cmd == "end":
                        break
                    elif cmd == "level":
                        self.levels.append(Level(int(value), self.stream, self))
                    else:
                        self.gloom_properties[cmd] = value
                        if cmd == "gloomver":
                            if int(value) != GLOOM_FILE_VER:
                                raise ValueError(
                                    f"unknown gloom file version: {value}!={GLOOM_FILE_VER}"
                                )
                            self.gloomver = int(value)
                        elif cmd == "resolution":
                            self.resolution = Vector2(*map(int, value.split("x")))


class Level:
    def __init__(self, level_id, stream, parent):
        self.stream = stream
        self.parent = parent
        self.level_properties = {}
        self.level_id = level_id
        while True:
            line = uncomment(self.stream.readline())
            if line is None:
                break
            elif line.startswith("!"):
                cmd, *_val = line.removeprefix("!").split(None, 1)
                value = _val[0] if _val else None
                if cmd == "end":
                    break
                elif cmd == "items":
                    self.item_array = parse_class_array(self.stream, ITEM_CLASSES)
                elif cmd == "enemies":
                    self.enemy_array = parse_class_array(self.stream, ENEMY_CLASSES)
                elif cmd == "doors":
                    self.door_array = parse_class_array(self.stream, DOOR_CLASSES)
                elif cmd == "map":
                    self.map = Tilemap(
                        self.parent.resolution,
                        self.parent.screen_size,
                        self.stream,
                        self.enemy_array,
                        self.item_array,
                        self.door_array,
                    )


class Tilemap:
    def __init__(
        self, resolution, screen_size, tilemap, enemy_array, item_array, door_array
    ):
        self.resolution = resolution
        self.cell_size = screen_size.notdot(1 / resolution)
        self.player_coords = None
        self.items = []
        self.doors = []
        self.walls = []
        self.enemies = []
        self.tilemap = [
            [(None, None) for _ in range(resolution.x)] for _ in range(resolution.y)
        ]
        self._tilemap = tilemap
        merged_vertical = set()
        merged_horizontal = set()
        wall_indices = {}
        y = 0

        while True:
            nl = (
                self._tilemap.readline().rstrip().replace("\t", "    ")
            )  # important shit
            if nl.strip() == "!end":
                break
            for x, char in enumerate(nl):
                cell_coords = self.calculate_cell_coords(x, y)
                if char == "#":
                    # wall
                    if (
                        x > 0
                        and (x - 1, y) in wall_indices
                        and (x - 1, y) not in merged_vertical
                    ):
                        print("hmerge", x, y)
                        wall_indices[(x, y)] = wall_indices[(x - 1, y)]
                        self.walls[wall_indices[(x - 1, y)]][1][1] = cell_coords[1]
                        merged_horizontal.add((x, y))
                        merged_horizontal.add((x - 1, y))
                    elif (
                        y > 0
                        and (x, y - 1) in wall_indices
                        and (x, y - 1) not in merged_horizontal
                    ):
                        print("vmerge", x, y)
                        wall_indices[(x, y)] = wall_indices[(x, y - 1)]
                        self.walls[wall_indices[(x, y - 1)]][1][1] = cell_coords[1]
                        merged_vertical.add((x, y))
                        merged_vertical.add((x, y - 1))

                    else:
                        print("new", x, y)
                        self.tilemap[y][x] = [Wall, cell_coords]
                        wall_indices[(x, y)] = len(self.walls)
                        self.walls.append([Wall, cell_coords])
                elif char.isalpha() and char.isupper():
                    # enemy
                    self.tilemap[y][x] = (
                        enemy_array[ord(char) - ord("A")],
                        cell_coords,
                    )
                    self.enemies.append(
                        [
                            enemy_array[ord(char) - ord("A")],
                            cell_coords,
                        ]
                    )
                elif char.isalpha() and char.islower():
                    # item
                    self.tilemap[y][x] = [
                        item_array[ord(char) - ord("a")],
                        cell_coords,
                    ]
                    self.items.append(
                        [
                            item_array[ord(char) - ord("a")],
                            cell_coords,
                        ]
                    )
                elif char.isnumeric():
                    # door
                    # TODO Merge doors too
                    self.tilemap[y][x] = [
                        door_array[ord(char) - ord("1")],
                        cell_coords,
                    ]
                    self.doors.append(
                        [
                            door_array[ord(char) - ord("1")],
                            cell_coords,
                        ]
                    )
                elif char == "^":
                    self.player_coords = cell_coords
            y += 1
        print(self.walls, len(self.walls))

    def instantiate_all(self):  # DOESNT
        return (
            [w.instantiate(c) for (w, c) in self.walls],
            [e.instantiate(c) for (e, c) in self.enemies],
            [i.instantiate(c) for (i, c) in self.items],
            [d.instantiate(c) for (d, c) in self.doors],
            Player.instantiate(self.player_coords),
        )

    def calculate_cell_coords(self, x, y):
        return Coords(
            Vector2(x, y).notdot(self.cell_size),
            (Vector2(x, y) + Vector2(1, 1)).notdot(self.cell_size),
        )


class Pistol(Weapon):
    rng = 500
    dmg = 10
    pierce = 50
    speed = 10
    spread = 0
    bullets_per_mg = 15
    bullets_per_shot = 1
    bullet_size = 3
    rate = 50
    reload_rate = 200


class Shotgun(Weapon):
    rng = 400
    dmg = 20
    pierce = 40
    speed = 15
    spread = 12
    bullets_per_mg = 5
    bullets_per_shot = 5
    bullet_size = 2
    rate = 0
    reload_rate = 100


class MachineGun(Weapon):
    rng = 600
    dmg = 5
    pierce = 60
    speed = 12
    spread = 0
    bullets_per_mg = 50
    bullets_per_shot = 1
    bullet_size = 1
    rate = 5
    reload_rate = 200


class GLOOM(Game):
    screen_size = Vector2(960, 540)
    screen_color = "#000"
    player_speed = 2
    fps = 120
    player_size = Vector2(20, 20)
    enemy_size = Vector2(20, 20)
    """
    wall_coords = (
        # wall 1 - starting room NE wall (doorway)
        Coords(
            (screen_size.x * (1 / 4), screen_size.y * (1 / 3)),
            (screen_size.x * 0.27, screen_size.y * (5 / 12)),
        ),
        # wall 2 - starting room N wall (wall)
        Coords(
            (screen_size.x * (1 / 4), screen_size.y * (1 / 3)),
            (screen_size.x * (3 / 4), screen_size.y * (53 / 150)),
        ),
    )"""

    def __init__(self, *args):
        self.keys_down = set()
        self.keycards = set()
        self.walls = []
        self.bullets = []
        self.mouse_pos = (0, 0)
        self.mouse_held = False
        self.weapon = MachineGun(200)
        self.weapons = [self.weapon]
        self.known_weapons = [w.__class__ for w in self.weapons]
        self.curr_weapon_index = 0
        super().__init__(*args)

    def ready(self):
        """
        self.enemies = [
            Pistoller.instantiate(
                Coords(
                    self.screen_center * (1 / 8) - self.enemy_size * 0.5,
                    self.screen_center * (1 / 8) + self.enemy_size * 0.5,
                ),
            ),
            Pistoller.instantiate(
                Coords(
                    self.screen_center * (15 / 8) - self.enemy_size * 0.5,
                    self.screen_center * (15 / 8) + self.enemy_size * 0.5,
                ),
            ),
        ]
        self.items = [
            PistolPickupItem.instantiate(
                Coords(
                    self.screen_center + Vector2(40, 40) - self.player_size * 0.5,
                    self.screen_center + Vector2(40, 40) + self.player_size * 0.5,
                )
            ),
            BlueKeyCard(Coords((0, 0), (20, 20))),
        ]"""

        self.ammo_label = AmmoMeter.instantiate(Coords((840, 510)))
        self.health_label = HealthMeter.instantiate(Coords((120, 510)))
        self.fps_meter = FPSMeter.instantiate(Coords((200, 30)))
        self.walls, self.enemies, self.items, self.doors, self.player = (
            GloomFile("testlevel.gloom", self.screen_size)
            .levels[0]
            .map.instantiate_all()
        )
        self.walls.extend(self.doors)
        """
        for wc in self.wall_coords:
            self.walls.append(Wall.instantiate(wc))
        """
        # self.walls.append(BlueDoor((Coords((500, 200), (510, 300)))))
        self.kc_indicator = KeycardIndicator.instantiate(Coords((840, 20)))
        self.pline = Pline.instantiate(Coords((500, 20)))
        self.sprites.try_run("check")

    def is_pressed(self, *keys):
        return all(key in self.keys_down for key in keys)

    def tick(self, delta):
        deltamult = delta / (1 / self.fps)
        self.fps_meter.update_text(delta)
        # print(self.keys_down)
        if self.is_pressed("w"):
            self.player.move(UP * self.player_speed * deltamult)
        if self.is_pressed("a"):
            self.player.move(LEFT * self.player_speed * deltamult)
        if self.is_pressed("s"):
            self.player.move(DOWN * self.player_speed * deltamult)
        if self.is_pressed("d"):
            self.player.move(RIGHT * self.player_speed * deltamult)
        if self.mouse_held:
            bullargss = self.weapon.tick(
                (self.player.center_point, self.mouse_pos, True, 1)
            )
            for bullargs in bullargss:
                self.bullets.append(Bullet.instantiate(*bullargs))
        else:
            self.weapon.tick()
        if self.weapon._bullets_left == 0:
            if len(self.weapons) > 1:
                self.weapons.remove(self.weapon)
                self.weapon = self.weapons[-1]
        for dig in "12345678":
            if self.is_pressed(dig):
                if len(self.weapons) >= int(dig):
                    self.weapons[self.curr_weapon_index] = self.weapon
                    self.weapon = self.weapons[int(dig) - 1]
                    self.curr_weapon_index = int(dig) - 1
        # print(len(self.bullets))
        for bullet in self.bullets:
            if not bullet.flying:
                self.bullets.remove(bullet)
            bullet.move()
        for item in self.items:
            if item.collision_check(self.player.coords, self.player):
                item.on_pickup()
                item.quit()
                self.items.remove(item)

    def check_wall_collision(self, coords, sprite):
        for wall in self.walls:
            if wall.collision_check(coords, sprite):
                return True
        return False

    def check_line_collision(self, p1, p2, ignore=None):
        walls = self.walls.copy()
        if ignore in walls:
            # print(ignore)
            walls.remove(ignore)
        for wall in walls:
            if wall.line_cross_check(p1, p2):
                return True
        return False

    def get_sentient(self, friendly):
        if not friendly:
            return [self.player]
        else:
            return self.enemies

    def has_keycard(self, keycardid):
        return keycardid in self.keycards

    @Game.event_handler("die")
    def _on_die(self, who):
        if who in self.enemies:
            self.enemies.remove(who)
        elif who == self.player:
            self.destroy()

    @Game.event_handler("shoot")
    def _on_shoot(self, who, with_what, whom, from_where, how_accurate=0):
        bullargss = with_what.tick((from_where, whom, False, how_accurate))
        for bullargs in bullargss:
            self.bullets.append(Bullet.instantiate(*bullargs))

    @Game.on("<KeyPress>", True)
    def _on_key_press(self, event):
        if event.keysym:
            self.keys_down.add(event.keysym.lower())

    @Game.on("<KeyRelease>", True)
    def _on_key_release(self, event):
        if event.keysym and event.keysym.lower() in self.keys_down:
            self.keys_down.remove(event.keysym.lower())

    @Game.on("<Motion>", True)
    def _on_mouse_move(self, event):
        self.mouse_pos = Vector2(event.x, event.y)

    @Game.on("<Button-1>")
    def _on_mouse_click(self, event):
        self.mouse_pos = Vector2(event.x, event.y)
        self.mouse_held = True

    @Game.on("<ButtonRelease-1>")
    def _on_mouse_unclick(self, event):
        self.mouse_pos = Vector2(event.x, event.y)
        self.mouse_held = False


class Label(Sprite):
    shape = Shape.TEXT

    def tick(self):
        self.text = eval("f" + repr(self.fmt))
        self.label_tick()
        self.update()

    def label_tick(self):
        pass


class GameElement(Sprite):
    def __init__(self, *args, **kwargs):
        self.active = False
        self.seen = False
        self._defaultfill = self.kwargs.get("fill", "#000")
        super().__init__(*args, **kwargs)

    def check(self):
        line = (self.center_point, self.game.player.center_point)

        if self.game.check_line_collision(*line, ignore=self):
            self.active = False
            if self.seen:
                self.fill = self.remembered_color_hook()
            else:
                self.fill = "#000"
        else:
            self.active = True
            self.seen = True
            self.fill = self.active_color_hook()
        self.kwargs["outline"] = self.fill
        self.update(coords=False)  #

    def tick(self):
        self.sprite_tick()

    def active_color_hook(self):
        return self._defaultfill

    def remembered_color_hook(self):
        return self._defaultfill

    def sprite_tick(self):
        pass


class HasCollision(GameElement):
    def __init__(self, coords, *args):
        self.points = (
            coords[0],
            coords[1],
            Vector2(coords[0].x, coords[1].y),
            Vector2(coords[1].x, coords[0].y),
        )
        self.can_collide = True
        self.lines = (
            (coords[0], coords[1]),
            (Vector2(coords[0].x, coords[1].y), Vector2(coords[1].x, coords[0].y)),
        )
        super().__init__(coords, *args)

    def collision_check(self, other, sprite):
        if not self.can_collide:
            return False
        other_points = (
            other.coords[0],
            other.coords[1],
            Vector2(other.coords[0].x, other.coords[1].y),
            Vector2(other.coords[1].x, other.coords[0].y),
        )
        collides = any(
            self.coords[0].x <= point.x <= self.coords[1].x
            and self.coords[0].y <= point.y <= self.coords[1].y
            for point in other_points
        ) or any(
            other[0].x <= point.x <= other[1].x and other[0].y <= point.y <= other[1].y
            for point in self.points
        )
        if collides:
            self.on_collide(sprite)
        return collides

    def line_cross_check(self, p1, p2):
        return any(intersect(p1, p2, b1, b2) for (b1, b2) in self.lines)

    def on_collide(self, sprite):
        pass


class PlayerOrEnemy(HasCollision):
    shape = Shape.RECTANGLE

    def __init__(self, coords, hp=100, armor=0, *args, **kwargs):
        self.hp = hp
        self.armor = armor
        self.active = True
        self.dead = False
        super().__init__(coords, *args, **kwargs)

    def move(self, delta):
        ncoords = self.coords + delta
        if (
            0 <= ncoords[0].x
            and ncoords[1].x <= self.game.screen_size.x
            and 0 <= ncoords[0].y
            and ncoords[1].y <= self.game.screen_size.y
        ):
            if not self.game.check_wall_collision(ncoords, self):
                self.coords = ncoords
                if self.active:
                    self.update()
        self.on_move()

    def hit(self, bullet):
        if not self.dead:
            body_damage_ratio = (bullet.pierce) / 100
            armor_damage_ratio = 1 - body_damage_ratio
            self.hp -= bullet.dmg * body_damage_ratio
            self.armor -= bullet.dmg * armor_damage_ratio
            self.armor = max(self.armor, 0)
            if self.hp <= 0:
                self.dead = True
                self.on_die()
                self.send_event("die")
                self.quit()
            self.on_hit()
        # print(self.hp, self.armor)

    def on_hit(self):
        pass

    def on_die(self):
        pass

    def on_move(self):
        pass


class Item(HasCollision):
    shape = Shape.OVAL

    def __init__(self, *args, **kwargs):
        self.picked_up = False
        super().__init__(*args, **kwargs)

    def on_pickup(self):
        if not self.picked_up:
            self.on_pickup_item()
            self.picked_up = True


class WeaponPickupItem(Item):
    kwargs = {"fill": "#a50"}

    def __init_subclass__(cls):
        WEAPON_PICKUP_CLASSES[cls.weapclass.__name__] = cls

    def on_pickup_item(self):
        self.game.pline.pline(f"Picked up a {self.weapclass.__name__}")
        for weap in self.game.weapons:
            if weap.__class__ == self.weapclass:
                weap._bullets_left += weap.bullets_per_mg
                weap._bullets_left_in_magazine = weap.bullets_per_mg
                break
        else:
            weapon = self.weapclass(self.weapclass.bullets_per_mg)
            self.game.weapons.append(weapon)
            if self.weapclass not in self.game.known_weapons:
                self.game.known_weapons.append(self.weapclass)
                self.game.curr_weapon_index = len(self.game.weapons) - 1
                self.game.weapon = weapon

    def remembered_color_hook(self):
        return "#650"


class Door(HasCollision):
    shape = Shape.RECTANGLE

    def on_collide(self, sprite):
        # print("coll")
        if sprite.name == "Player":
            # print("collPlayer")
            if self.game.has_keycard(self.keycardid):
                self.game.walls.remove(self)
                self.can_collide = False
                self.quit()


class KeyCard(Item):
    def __init_subclass__(cls):
        KEYCARDS[cls.keycardid] = cls

    def on_pickup_item(self):
        self.game.pline.pline(f"Picked up a {self.keycardname} keycard")
        self.game.keycards.add(self.keycardid)


@GLOOM.sprite()
class Pline(Sprite):
    shape = Shape.TEXT
    kwargs = {"fill": "#fff", "text": "", "font": ("Stencil", 20)}

    def __init__(self, *args, **kwargs):
        self.lines = []
        super().__init__(*args, **kwargs)

    def depline(self):
        del self.lines[0]
        self.coords -= Vector2(0, self.kwargs["font"][1])
        self._refresh()

    def pline(self, text):
        self.coords += Vector2(0, self.kwargs["font"][1])
        self.lines.append(text)
        self._refresh()
        self.game.after(1000, self.depline)

    def _refresh(self):
        self.text = "\n".join(self.lines)
        self.update()


@GLOOM.sprite()
class BlueDoor(Door):
    keycardid = 1
    kwargs = {"fill": "#33d"}

    def remembered_color_hook(self):
        return "#449"


@GLOOM.sprite()
class BlueKeyCard(KeyCard):
    keycardid = 1
    keycardname = "blue"
    kwargs = {"fill": "#33d"}

    def remembered_color_hook(self):
        return "#449"


@GLOOM.sprite()
class PistolPickupItem(WeaponPickupItem):
    weapclass = Pistol


@GLOOM.sprite()
class ShotgunPickupItem(WeaponPickupItem):
    weapclass = Shotgun


@GLOOM.sprite()
class MachineGunPickupItem(WeaponPickupItem):
    weapclass = MachineGun


@GLOOM.sprite()
class SpeedBooster(Item):
    kwargs = {"fill": "#f0f"}

    def on_pickup_item(self):
        self.game.pline.pline("Picked up a speed boost")
        self._reset_to = self.game.player_speed
        self.game.player_speed += 1
        self.game.after(20000, self._reset_player_speed)

    def _reset_player_speed(self):
        self.game.player.speed = self._reset_to

    def remembered_color_hook(self):
        return "#a0a"


@GLOOM.sprite()
class MediKit(Item):
    kwargs = {"fill": "#0f0"}

    def on_pickup_item(self):
        self.game.pline.pline("Picked up a medikit")
        if self.game.player.hp < 100:
            self.game.player.hp = min(self.game.player.hp + 25, 100)

    def remembered_color_hook(self):
        return "#0a0"


@GLOOM.sprite()
class Armor(Item):
    kwargs = {"fill": "#888"}

    def on_pickup_item(self):
        self.game.pline.pline("Picked up the armor")
        self.game.player.armor = 100

    def remembered_color_hook(self):
        return "#333"


@GLOOM.sprite()
class StimPack(Item):
    kwargs = {"fill": "#070"}

    def on_pickup_item(self):
        self.game.pline.pline("Picked up a stimpack")
        if self.game.player.hp < 100:
            self.game.player.hp = min(self.game.player.hp + 10, 100)

    def remembered_color_hook(self):
        return "#040"


@GLOOM.sprite()
class FPSMeter(Sprite):
    shape = Shape.TEXT
    kwargs = {"text": "", "font": ("Stencil", 10), "fill": "#ddd"}

    def update_text(self, delta):
        self.text = f"FPS: {1/delta:.2f}"
        self.update()


@GLOOM.sprite()
class AmmoMeter(Label):
    kwargs = {"text": "", "font": ("Stencil", 20), "fill": "#00e"}
    fmt = "{self.game.weapon.__class__.__name__}:{self.game.weapon._bullets_left_in_magazine}|{self.game.weapon._bullets_left}{'(R)' if self.game.weapon._until_reload>0 else ''}"


@GLOOM.sprite()
class KeycardIndicator(Label):
    kwargs = {"text": "", "font": ("Stencil", 20), "fill": "#ea0"}
    fmt = "Keycards: {','.join(KEYCARDS[kc].keycardname for kc in self.game.keycards)}"


@GLOOM.sprite()
class HealthMeter(Label):
    kwargs = {"text": "", "font": ("Stencil", 20), "fill": "#0a0"}
    fmt = "HEALTH:{int(self.game.player.hp)}"

    def label_tick(self):
        if self.game.player.hp == 100:
            self.fill = "#0a0"
        elif self.game.player.hp >= 90:
            self.fill = "#190"
        elif self.game.player.hp >= 80:
            self.fill = "#280"
        elif self.game.player.hp >= 70:
            self.fill = "#370"
        elif self.game.player.hp >= 60:
            self.fill = "#460"
        elif self.game.player.hp >= 50:
            self.fill = "#550"
        elif self.game.player.hp >= 40:
            self.fill = "#640"
        elif self.game.player.hp >= 30:
            self.fill = "#730"
        elif self.game.player.hp >= 20:
            self.fill = "#820"
        elif self.game.player.hp >= 10:
            self.fill = "#910"
        else:
            self.fill = "#a00"


@GLOOM.sprite()
class Wall(HasCollision):
    kwargs = {"outline": "#eee", "fill": "#eee"}
    shape = Shape.RECTANGLE


@GLOOM.sprite()
class Player(PlayerOrEnemy):
    kwargs = {"fill": "#aaf"}
    friendly = True

    def on_hit(self):
        print(self.hp)

    def on_move(self):
        self.game.sprites.try_run("check")


class Enemy(PlayerOrEnemy):
    kwargs = {"fill": "#000"}
    friendly = False

    def __init__(self, *args, **kwargs):
        self.active = False
        self.target = None
        self.seen = False
        self.accuracy = self._accuracy
        self.weapon = self._weapon(self._ammo)
        self.speed = self._speed
        self.hp = self.maxhp = self._hp
        self.armor = self._armor
        super().__init__(*args, hp=self.hp, armor=self.armor, **kwargs)

    def remembered_color_hook(self):
        return self._remembered_color

    def active_color_hook(self):
        return self._active_colors[int(self.hp / (self.maxhp / 10))]

    def sprite_tick(self):
        line = (self.center_point, self.game.player.center_point)
        if self.active:
            self.target = self.game.player.center_point
            self.update()
        if self.target is not None:
            if (
                self.target - self.center_point
            ).norm > 10 and self.weapon._bullets_left > 0:  # arbitrary/placeholder
                movevect = (
                    (self.target - self.center_point).normalize()
                    * self.speed
                    * ((self.target - self.center_point).norm / self.weapon.rng)
                )
                # move in each direction separately to avoid getting stuck on walls
                self.move(movevect.notdot(Vector2(1, 0)))
                self.move(movevect.notdot(Vector2(0, 1)))
            if (
                self.weapon._bullets_left == 0
                and (self.target - self.center_point).norm <= self.game.weapon.rng
            ):
                movevect = (
                    (self.target - self.center_point).normalize()
                    * self.speed
                    * ((self.target - self.center_point).norm / self.weapon.rng)
                    * -1
                )
                self.move(movevect.notdot(Vector2(1, 0)))
                self.move(movevect.notdot(Vector2(0, 1)))

            # only shoot when in range and active
            # the enemies will generally get worse weapons because their aim is better
            if (
                self.active
                and (self.target - self.center_point).norm <= self.weapon.rng
                and self.weapon._bullets_left > 0
            ):
                self.send_event("shoot", self.weapon, self.target, self.center_point, self.accuracy)
            else:
                self.weapon.tick()  # allow cooldown

    def on_die(self):
        wp = WEAPON_PICKUP_CLASSES[self.weapon.__class__.__name__].instantiate(
            self.coords
        )
        self.game.items.append(wp)


@GLOOM.sprite()
class Pistoller(Enemy):
    _weapon = Pistol
    _ammo = 30
    _accuracy = 3
    _speed = 1.5
    _hp = 100
    _armor = 0
    _remembered_color = "#a00"
    _active_colors = [
        "#f00",
        "#f11",
        "#f22",
        "#f33",
        "#f44",
        "#f55",
        "#f66",
        "#f77",
        "#f88",
        "#f99",
        "#faa",
    ]


@GLOOM.sprite()
class Shotgunner(Enemy):
    _weapon = Shotgun
    _ammo = 100
    _speed = 1
    _accuracy = 2
    _hp = 75
    _armor = 0
    _remembered_color = "#aa0"
    _active_colors = [
        "#f50",
        "#f61",
        "#f72",
        "#f83",
        "#f94",
        "#fa5",
        "#fb6",
        "#fc7",
        "#fd8",
        "#fe9",
        "#ffa",
    ]


@GLOOM.sprite()
class Defender(Enemy):
    _weapon = Pistol
    _ammo = 200
    _speed = 0
    _hp = 100
    _accuracy = 10
    _armor = 100
    _remembered_color = "#aaa"
    _active_colors = [
        "#d66",
        "#d77",
        "#d88",
        "#d99",
        "#daa",
        "#dbb",
        "#dcc",
        "#fdd",
        "#edd",
        "#dcc",
        "#cbb",
        "#bbb",
    ]


@GLOOM.sprite()
class Bullet(Sprite):
    shape = Shape.RECTANGLE
    kwargs = {"outline": "#ccc", "fill": "#ccc"}

    def __init__(self, coords, friendly, speed, dir, rng, dmg, pierce, *args, **kwargs):
        self.speed = speed
        self.dir = dir
        # print(self.dir.x, self.dir.y, self.speed)
        self.rng = rng
        self.dmg = dmg
        self.flying = True
        self.friendly = friendly
        self.pierce = pierce
        self.lifetime = self.rng / self.speed
        super().__init__(coords, *args, **kwargs)

    def move(self):
        if self.lifetime <= 0 or self.game.check_wall_collision(self.coords, self):
            self.quit()
            self.flying = False
        for en in self.game.get_sentient(self.friendly):
            if en.collision_check(self.coords, self):
                en.hit(self)
                self.quit()
                self.flying = False
                # print("hit", en)

        self.lifetime -= 1
        self.coords += self.dir * self.speed
        self.update()


ITEM_CLASSES = {
    "medikit": MediKit,
    "stimpack": StimPack,
    "speedboost": SpeedBooster,
    "armor": Armor,
    "shotgunpickup": ShotgunPickupItem,
    "machinegunpickup": MachineGunPickupItem,
    "bluekeycard": BlueKeyCard,
}

ENEMY_CLASSES = {
    "pistoller": Pistoller,
    "shotgunner": Shotgunner,
    "defender": Defender,
}
DOOR_CLASSES = {
    "bluedoor": BlueDoor,
}
if __name__ == "__main__":
    GLOOM().start()
