"""
adapters/base_adapter.py

The contract every adapter must implement.
Required methods raise NotImplementedError — the adapter must override them.
Optional methods return None by default — override what your game supports.

server.py calls get_implemented_tools() to discover what's been overridden,
then registers only those as MCP tools/resources.
"""

import inspect
from enum import Enum


class PerceptionMode(Enum):
    VISION = "vision"
    # Agent perceives the world via screenshots fed to a vision model.
    # Used for: legacy games (EQ, etc.) AND demo MMO vision explorers.
    # Requires: game client window running on host + host-bridge.
    # Human-like — the agent sees what a player sees, flaws and all.

    MAP = "map"
    # Agent perceives the world via structured state from the game server.
    # Used for: demo MMO map explorers only.
    # Fog of war — agent only sees within their immediate radius.
    # No window, no vision model needed. Scales well, less "human-like".


class BaseAdapter:

    # -------------------------------------------------------------------------
    # REQUIRED — every adapter must implement these four
    # -------------------------------------------------------------------------

    def get_game_name(self) -> str:
        """Return the game identifier (e.g. 'open-world-mmo'). Used to load lore."""
        raise NotImplementedError

    def get_perception_mode(self) -> PerceptionMode:
        """
        How this agent perceives the world.
        agent-core uses this to start the right perception loop on connection.

        Default is VISION — works for any game with a visible window.
        Override to return MAP for structured-state agents (demo MMO only).

        City agents: always MAP.
        Legacy game explorers: always VISION.
        Demo MMO explorers: either — configured per agent in agents.yaml.
        """
        return PerceptionMode.VISION

    def get_world_state(self, agent_id: str) -> dict:
        """Full structured perception for this agent — position, nearby entities, etc."""
        raise NotImplementedError

    def send_chat(self, message: str, channel: str = "say"):
        """Say something in the world. channel: 'say' | 'shout' | 'group' | etc."""
        raise NotImplementedError

    def move_to(self, destination: str):
        """Move to a named location or coordinate string. Engine handles pathfinding."""
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # OPTIONAL — Movement
    # -------------------------------------------------------------------------

    def follow(self, entity: str, distance: float = None): ...
    def flee_from(self, entity: str): ...
    def patrol(self, waypoints: list): ...
    def go_to_poi(self, name: str): ...
    def enter_building(self, name: str): ...
    def mount(self): ...
    def dismount(self): ...

    # -------------------------------------------------------------------------
    # OPTIONAL — Social
    # -------------------------------------------------------------------------

    def send_tell(self, player: str, message: str): ...
    def emote(self, emote_name: str): ...
    def approach(self, entity: str): ...
    def initiate_trade(self, player: str): ...
    def join_group(self, player: str): ...
    def leave_group(self): ...

    # -------------------------------------------------------------------------
    # OPTIONAL — Economy
    # -------------------------------------------------------------------------

    def post_job(self, job: dict): ...
    def accept_job(self, job_id: str): ...
    def list_item_for_sale(self, item: str, price: int): ...
    def buy_item(self, item: str, from_entity: str): ...
    def make_offer(self, player: str, item: str, price: int): ...
    def check_job_board(self) -> list: ...
    def check_market_prices(self, item: str): ...

    # -------------------------------------------------------------------------
    # OPTIONAL — World Interaction
    # -------------------------------------------------------------------------

    def examine(self, object: str): ...
    def interact_with(self, object: str): ...
    def pick_up(self, item: str): ...
    def open_container(self, container: str): ...
    def use_object(self, object: str): ...
    def sit(self): ...
    def sleep(self): ...
    def read_notice_board(self): ...
    def open_door(self, door: str): ...

    # -------------------------------------------------------------------------
    # OPTIONAL — Self / Memory
    # -------------------------------------------------------------------------

    def check_inventory(self) -> dict: ...
    def check_health(self) -> dict: ...
    def recall_memory(self, query: str) -> list: ...
    def write_journal(self, entry: str): ...
    def update_belief(self, belief: str, value: str): ...
    def check_goals(self) -> list: ...
    def update_goal(self, goal: str, status: str): ...

    # -------------------------------------------------------------------------
    # OPTIONAL — Combat Adjacent
    # -------------------------------------------------------------------------

    def hire_mercenary(self, criteria: dict): ...
    def dismiss_mercenary(self, name: str): ...
    def flee_combat(self): ...
    def call_for_help(self): ...

    # -------------------------------------------------------------------------
    # OPTIONAL — Resources (read-only state the agent can query)
    # -------------------------------------------------------------------------

    def get_nearby_entities(self) -> dict: ...
    def get_chat_log(self) -> dict: ...
    def get_map_data(self) -> dict: ...
    def get_job_board(self) -> list: ...
    def get_market_listings(self) -> list: ...
    def get_time_and_weather(self) -> dict: ...
    def get_my_status(self) -> dict: ...

    # -------------------------------------------------------------------------
    # Discovery
    # -------------------------------------------------------------------------

    def get_implemented_tools(self) -> list[str]:
        """
        Return the names of all methods this adapter has overridden from BaseAdapter.
        server.py uses this to register only the tools and resources this adapter supports.
        """
        implemented = []
        for name in dir(BaseAdapter):
            if name.startswith("_") or name == "get_implemented_tools":
                continue
            base_attr = getattr(BaseAdapter, name, None)
            if not callable(base_attr):
                continue
            # If this class's method is different from BaseAdapter's, it's overridden
            if getattr(type(self), name) is not base_attr:
                implemented.append(name)
        return implemented
