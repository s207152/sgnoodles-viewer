import threading
import dearpygui.dearpygui as dpg
import dearpygui.demo as demo
import pymem
import time


class Pointers:
    current_match = 0x95C7C8


class Offsets:
    current_player = 0x88
    hp = 0x38
    sp = 0xbc8
    attack = 0xbb6
    defense = 0xbc1
    parts_attack = 0xd4c
    parts_defense = 0xd50
    beam_reduction = 0xcac
    ballistic_reduction = 0xcb0
    melee_reduction = 0xcb4
    mid_reduction = 0xcb8
    long_reduction = 0xcbc
    constant_reduction = 0xcc0


class MemoryManager:
    def __init__(self):
        self.process: pymem.Pymem = None
        self.base: int = None

        self.game_ready_thread: threading.Thread = None
        self.sync_thread: threading.Thread = None

        self.current_match: int = 0
        self.current_player: int = 0

        self.values = dict()
        self.hp: int = 0
        self.sp: int = 0
        self.base_atk: int = 0
        self.base_def: int = 0
        self.parts_atk: int = 0
        self.parts_def: int = 0

        self.beam_reduction: float = 0
        self.ballistic_reduction: float = 0
        self.melee_reduction: float = 0
        self.mid_reduction: float = 0
        self.long_reduction: float = 0
        self.constant_reduction: float = 0

    def wait_for_process(self) -> pymem.Pymem:
        process = None
        while process is None:
            try:
                process = pymem.Pymem("Gonline.exe")
            except Exception:
                time.sleep(5)
        return process

    def safe_get_base(self) -> (int | None):
        try:
            return self.process.base_address
        except Exception:
            return None

    def wait_for_base(self) -> int:
        base = None
        while base is None:
            base = self.safe_get_base()
            time.sleep(1)
        return base

    def is_process_running(self):
        if self.process is None or self.base is None:
            return False

        if self.safe_get_base() is None:
            self.process = None
            self.base = None
            return False

        return True

    def wait_for_game_ready(self):
        while True:
            if self.is_process_running() == False:
                self.set_active_window("wait_process")
                self.process = self.wait_for_process()
                self.base = self.wait_for_base()
            time.sleep(3)

    def dispatch_wait_for_game_ready(self):
        if self.game_ready_thread is not None and self.game_ready_thread.is_alive:
            return

        self.game_ready_thread = threading.Thread(
            name="game_ready", target=self.wait_for_game_ready, args=(), daemon=True)
        self.game_ready_thread.start()

    def pointer_chain(self, base: int, offsets: list[int]):
        result = self.process.read_int(base)
        for offset in offsets[:-1]:
            result = self.process.read_int(result + offset)
        return result + offsets[-1]

    def read_byte(self, addr: int):
        return int.from_bytes(self.process.read_bytes(addr, 1), "big")

    def sdgo_xor(self, addr: int):
        xorBase = self.read_byte(addr)
        offset1 = self.read_byte(addr - 0xa)
        offset2 = self.read_byte(addr - 0x9)

        baseAddr = addr - 0x8
        result1 = self.read_byte(baseAddr + offset1) ^ xorBase
        result2 = self.read_byte(baseAddr + offset2) ^ xorBase

        return result1 + result2

    def update(self):
        if self.is_process_running() == False:
            return

        self.current_match = self.process.read_int(
            self.base + Pointers.current_match)
        if self.current_match == 0:
            self.set_active_window("wait_match")
            return

        self.current_player = self.process.read_int(
            self.current_match + Offsets.current_player)
        if self.current_player == 0:
            self.set_active_window("wait_match")
            return

        self.set_active_window("main")

        current_player = self.current_player
        process = self.process

        self.values["hp"] = process.read_int(current_player + Offsets.hp)
        self.values["sp"] = process.read_int(current_player + Offsets.sp)
        self.values["base_atk"] = self.sdgo_xor(
            current_player + Offsets.attack)
        self.values["base_def"] = self.sdgo_xor(
            current_player + Offsets.defense)
        self.values["parts_atk"] = process.read_int(
            current_player + Offsets.parts_attack)
        self.values["parts_def"] = process.read_int(
            current_player + Offsets.parts_defense)
        self.values["final_atk"] = self.values["base_atk"] + \
            self.values["parts_atk"]
        self.values["final_def"] = self.values["base_def"] + \
            self.values["parts_def"]

        self.values["reduction"] = dict()
        self.values["reduction"]["beam"] = process.read_float(
            current_player + Offsets.beam_reduction)
        self.values["reduction"]["ballistic"] = process.read_float(
            current_player + Offsets.ballistic_reduction)
        self.values["reduction"]["melee"] = process.read_float(
            current_player + Offsets.melee_reduction)
        self.values["reduction"]["mid"] = process.read_float(
            current_player + Offsets.mid_reduction)
        self.values["reduction"]["long"] = process.read_float(
            current_player + Offsets.long_reduction)
        self.values["reduction"]["constant"] = process.read_float(
            current_player + Offsets.constant_reduction)

        player_base = self.process.read_int(current_player + 0x9cc)
        weapon = self.process.read_int(player_base + 0x248)
        self.values["weapon"] = dict()
        self.values["weapon"]["type"] = dict()
        self.values["weapon"]["type"]["base"] = self.read_byte(weapon + 0x69)
        self.values["weapon"]["type"]["range"] = self.read_byte(weapon + 0x6a)
        self.values["weapon"]["type"]["damage"] = self.read_byte(weapon + 0x6b)
        self.values["weapon"]["dmg"] = self.process.read_int(weapon + 0x6c)
        self.values["weapon"]["base_speed"] = self.process.read_short(
            weapon + 0x70)
        self.values["weapon"]["range"] = self.process.read_short(weapon + 0x72)
        self.values["weapon"]["ammo"] = self.process.read_short(weapon + 0x7c)
        self.values["weapon"]["delay"] = self.process.read_short(weapon + 0x82)
        self.values["weapon"]["hitbox_x"] = self.process.read_float(
            weapon + 0x94)
        self.values["weapon"]["hitbox_y"] = self.process.read_float(
            weapon + 0x98)
        self.values["weapon"]["hitbox_z"] = self.process.read_float(
            weapon + 0x9c)
        self.values["weapon"]["splash"] = self.process.read_float(
            weapon + 0xa0)

        for i in self.values:
            if type(self.values[i]) is dict:
                continue
            dpg.configure_item(i, default_value=self.values[i])

        show_atk_detail = self.values["parts_atk"] != 0
        dpg.configure_item("atk_detail", show=show_atk_detail)
        dpg.configure_item("atk_detail_values", show=show_atk_detail)
        show_def_detail = self.values["parts_def"] != 0
        dpg.configure_item("def_detail", show=show_def_detail)
        dpg.configure_item("def_detail_values", show=show_def_detail)

        has_reduction = False
        for i in self.values["reduction"]:
            if (self.values["reduction"][i] != 1.0):
                dpg.configure_item(
                    i+"_reduction", default_value=self.values["reduction"][i])
                dpg.configure_item(i+"_reduction_row", show=True)
                has_reduction = True
            else:
                dpg.configure_item(i+"_reduction_row", show=False)
        dpg.configure_item("reduction_row", show=has_reduction)

        dpg.configure_item("weapon_type", default_value={
            1: "普通武器",
            2: "SP",
            3: "補血武器",
        }[self.values["weapon"]["type"]["base"]])
        dpg.configure_item("weapon_range_type", default_value={
            1: "近距離",
            2: "中距離",
            3: "遠距離",
            4: "浮游",
            5: "浮游刃",
            6: "防禦浮游",
            7: "反射浮游",
            8: "突進",
        }[self.values["weapon"]["type"]["range"]])
        dpg.configure_item("weapon_damage_type", default_value={
            0: "SP",
            1: "近戰",
            2: "實彈",
            3: "光束",
        }[self.values["weapon"]["type"]["damage"]])
        for i in self.values["weapon"]:
            if type(self.values["weapon"][i]) is dict:
                continue
            dpg.configure_item(
                "weapon_"+i, default_value=self.values["weapon"][i])

    def sync_values(self):
        while True:
            self.update()
            time.sleep(0.5)

    def dispatch_sync_values(self):
        self.sync_thread = threading.Thread(
            name="update", target=self.sync_values, args=(), daemon=True)
        self.sync_thread.start()

    def set_active_window(self, tag: str):
        for window in ["wait_process", "wait_match", "main"]:
            if tag == window:
                dpg.configure_item(window, show=True)
                dpg.set_primary_window(window, True)
            else:
                dpg.configure_item(window, show=False)


def setup_gui():
    dpg.create_context()

    with dpg.font_registry():
        with dpg.font('TaipeiSansTCBeta-Regular.ttf', 16) as default_font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)
    dpg.bind_font(default_font)

    with dpg.window(tag="wait_process", autosize=True):
        with dpg.group(horizontal=True):
            dpg.add_loading_indicator()
            dpg.add_text("Waiting for GOnline.exe...")

    with dpg.window(tag="wait_match", autosize=True, no_collapse=True, no_resize=True, no_close=True, no_move=True,
                    no_title_bar=True, show=False):
        with dpg.group(horizontal=True):
            dpg.add_loading_indicator()
            dpg.add_text("Waiting to enter a match...")

    with dpg.window(tag="main", autosize=True, no_collapse=True, no_resize=True, no_close=True, no_move=True,
                    no_title_bar=True, show=False):
        with dpg.group(horizontal=True):
            with dpg.table(header_row=False, row_background=True, width=250):
                dpg.add_table_column()
                dpg.add_table_column()

                with dpg.table_row():
                    dpg.add_text("HP")
                    dpg.add_text(tag="hp")
                with dpg.table_row():
                    dpg.add_text("SP")
                    dpg.add_text(tag="sp")
                with dpg.table_row():
                    with dpg.group():
                        dpg.add_text("攻擊")
                        with dpg.group(tag="atk_detail"):
                            dpg.add_text("基本", bullet=True)
                            dpg.add_text("部件", bullet=True)
                    with dpg.group():
                        dpg.add_text(tag="final_atk")
                        with dpg.group(tag="atk_detail_values"):
                            dpg.add_text(tag="base_atk", indent=16)
                            dpg.add_text(tag="parts_atk", indent=16)

                with dpg.table_row():
                    with dpg.group():
                        dpg.add_text("防禦")
                        with dpg.group(tag="def_detail"):
                            dpg.add_text("基本", bullet=True)
                            dpg.add_text("部件", bullet=True)
                    with dpg.group():
                        dpg.add_text(tag="final_def")
                        with dpg.group(tag="def_detail_values"):
                            dpg.add_text(tag="base_def", indent=16)
                            dpg.add_text(tag="parts_def", indent=16)

                with dpg.table_row(tag="reduction_row"):
                    dpg.add_text("減傷")
                with dpg.table_row(tag="beam_reduction_row"):
                    dpg.add_text("光束", bullet=True)
                    dpg.add_text(tag="beam_reduction")
                with dpg.table_row(tag="ballistic_reduction_row"):
                    dpg.add_text("實彈", bullet=True)
                    dpg.add_text(tag="ballistic_reduction")
                with dpg.table_row(tag="melee_reduction_row"):
                    dpg.add_text("抗近", bullet=True)
                    dpg.add_text(tag="melee_reduction")
                with dpg.table_row(tag="mid_reduction_row"):
                    dpg.add_text("抗中", bullet=True)
                    dpg.add_text(tag="mid_reduction")
                with dpg.table_row(tag="long_reduction_row"):
                    dpg.add_text("抗遠", bullet=True)
                    dpg.add_text(tag="long_reduction")
                with dpg.table_row(tag="constant_reduction_row"):
                    dpg.add_text("常設 / 光環", bullet=True)
                    dpg.add_text(tag="constant_reduction")

            with dpg.table(header_row=False, row_background=True, width=250):
                dpg.add_table_column()
                dpg.add_table_column()

                with dpg.table_row():
                    dpg.add_text("武器")
                    with dpg.group():
                        dpg.add_text(tag="weapon_type")
                        dpg.add_text(tag="weapon_range_type")
                        dpg.add_text(tag="weapon_damage_type")

                with dpg.table_row():
                    dpg.add_text("係數")
                    dpg.add_text(tag="weapon_dmg")
                with dpg.table_row():
                    dpg.add_text("彈速")
                    dpg.add_text(tag="weapon_base_speed")
                with dpg.table_row():
                    dpg.add_text("射程")
                    dpg.add_text(tag="weapon_range")
                with dpg.table_row():
                    dpg.add_text("彈藥")
                    dpg.add_text(tag="weapon_ammo")
                with dpg.table_row():
                    dpg.add_text("間隔")
                    dpg.add_text(tag="weapon_delay")
                with dpg.table_row():
                    dpg.add_text("x判定")
                    dpg.add_text(tag="weapon_hitbox_x")
                with dpg.table_row():
                    dpg.add_text("y判定")
                    dpg.add_text(tag="weapon_hitbox_y")
                with dpg.table_row():
                    dpg.add_text("z判定")
                    dpg.add_text(tag="weapon_hitbox_z")
                with dpg.table_row():
                    dpg.add_text("濺射範圍")
                    dpg.add_text(tag="weapon_splash")

    dpg.create_viewport(title="SGNoodles Viewer", width=500, height=600)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("wait_process", True)

    manager = MemoryManager()
    manager.dispatch_wait_for_game_ready()
    manager.dispatch_sync_values()

    dpg.start_dearpygui()
    dpg.destroy_context()


setup_gui()
