"""
core/server.py

Base MCP server. Knows nothing about any specific game.
Takes any BaseAdapter, dynamically registers only what that adapter implements.

Usage:
    from core.server import WorldMCPServer
    from adapters.my_game.adapter import MyGameAdapter

    server = WorldMCPServer(MyGameAdapter())
    server.run()

Environment variables:
    MCP_HOST         - bind address (default: 0.0.0.0)
    MCP_PORT         - port (default: 8080)
    HOST_BRIDGE_URL  - host-bridge URL for vision agents (default: http://host.docker.internal:5001)
    AGENT_ID         - agent identifier passed to state queries (default: agent)
"""

import inspect
import json
import logging
import os
from dataclasses import dataclass, field

from mcp.server.fastmcp import FastMCP

from adapters.base_adapter import BaseAdapter, PerceptionMode

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
log = logging.getLogger(__name__)

MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", 8080))
HOST_BRIDGE_URL = os.environ.get("HOST_BRIDGE_URL", "http://host.docker.internal:5001")
AGENT_ID = os.environ.get("AGENT_ID", "agent")


# ---------------------------------------------------------------------------
# Tool and resource definitions
# ---------------------------------------------------------------------------

@dataclass
class ToolDef:
    name: str                                    # MCP tool name agent-core sees
    description: str
    adapter_method: str                          # method to call on the adapter
    fixed_kwargs: dict = field(default_factory=dict)  # baked-in kwargs (e.g. channel="say")


@dataclass
class ResourceDef:
    uri: str                                     # MCP resource URI
    name: str                                    # display name
    description: str
    adapter_method: str
    fixed_kwargs: dict = field(default_factory=dict)


# All possible tools — server registers only those whose adapter_method is implemented.
TOOL_MAP: list[ToolDef] = [

    # Movement
    ToolDef("move_to_location",         "Move to a location — engine handles pathfinding",                  "move_to"),
    ToolDef("follow_entity",            "Follow a player or NPC",                                           "follow"),
    ToolDef("flee_from",                "Run away from a threat",                                           "flee_from"),
    ToolDef("patrol_waypoints",         "Patrol a list of waypoints",                                       "patrol"),
    ToolDef("go_to_point_of_interest",  "Move to a named location the agent knows about",                   "go_to_poi"),
    ToolDef("enter_building",           "Enter a named building",                                           "enter_building"),
    ToolDef("mount",                    "Mount a mount",                                                    "mount"),
    ToolDef("dismount",                 "Dismount",                                                         "dismount"),

    # Social
    ToolDef("say",                      "Speak in local chat — nearby players hear it",                     "send_chat", {"channel": "say"}),
    ToolDef("tell",                     "Send a private message to a player",                               "send_tell"),
    ToolDef("shout",                    "Shout zone-wide",                                                  "send_chat", {"channel": "shout"}),
    ToolDef("emote",                    "Perform an emote (wave, bow, laugh, sit, dance...)",                "emote"),
    ToolDef("approach_entity",          "Walk up to a player or NPC",                                       "approach"),
    ToolDef("initiate_trade",           "Start a trade with a player",                                      "initiate_trade"),
    ToolDef("join_group",               "Join a player's group",                                            "join_group"),
    ToolDef("leave_group",              "Leave the current group",                                          "leave_group"),

    # Economy
    ToolDef("post_job",                 "Post a job to hire mercenaries or request help",                   "post_job"),
    ToolDef("accept_job",               "Accept a job from the job board",                                  "accept_job"),
    ToolDef("list_item_for_sale",       "List an item for sale on the market",                              "list_item_for_sale"),
    ToolDef("buy_item",                 "Buy an item from a player or vendor",                              "buy_item"),
    ToolDef("make_offer",               "Make an offer to a player for an item",                            "make_offer"),
    ToolDef("check_job_board",          "See available jobs on the job board",                              "check_job_board"),
    ToolDef("check_market_prices",      "Check market prices for an item",                                  "check_market_prices"),

    # World Interaction
    ToolDef("examine_object",           "Examine an object and get a description",                          "examine"),
    ToolDef("pick_up_item",             "Pick up an item from the ground",                                  "pick_up"),
    ToolDef("open_container",           "Open a container (chest, bag, etc.)",                              "open_container"),
    ToolDef("use_object",               "Use or interact with an object",                                   "use_object"),
    ToolDef("interact_with",            "Directly interact with a world object",                            "interact_with"),
    ToolDef("sit",                      "Sit down",                                                         "sit"),
    ToolDef("sleep",                    "Rest — agents sleeping creates emergent behavior",                  "sleep"),
    ToolDef("read_notice_board",        "Read a nearby notice board",                                       "read_notice_board"),
    ToolDef("open_door",                "Open a door",                                                      "open_door"),

    # Self / Memory
    ToolDef("check_inventory",          "Check what you're carrying",                                       "check_inventory"),
    ToolDef("check_health",             "Check your health and status",                                     "check_health"),
    ToolDef("check_surroundings",       "Get a structured snapshot of your current world state",            "get_world_state", {"agent_id": AGENT_ID}),
    ToolDef("recall_memory",            "Query your own memory (vector DB)",                                "recall_memory"),
    ToolDef("write_journal",            "Log a significant moment to your journal",                         "write_journal"),
    ToolDef("update_belief",            "Update something you believe to be true about the world",          "update_belief"),
    ToolDef("check_goals",              "See what you're currently trying to accomplish",                   "check_goals"),
    ToolDef("update_goal",              "Update the status of a goal",                                      "update_goal"),

    # Combat Adjacent
    ToolDef("hire_mercenary",           "Find and contract a mercenary for protection",                     "hire_mercenary"),
    ToolDef("dismiss_mercenary",        "Dismiss a hired mercenary",                                        "dismiss_mercenary"),
    ToolDef("flee_combat",              "Get out of a fight",                                               "flee_combat"),
    ToolDef("call_for_help",            "Alert nearby players or agents that you need help",                "call_for_help"),
]

# All possible resources — server registers only those whose adapter_method is implemented.
RESOURCE_MAP: list[ResourceDef] = [
    ResourceDef("world://world_state",      "World State",      "Full structured perception snapshot",              "get_world_state",      {"agent_id": AGENT_ID}),
    ResourceDef("world://nearby_entities",  "Nearby Entities",  "Players, NPCs, and agents within range",           "get_nearby_entities"),
    ResourceDef("world://chat_log",         "Chat Log",         "Recent chat in the area",                          "get_chat_log"),
    ResourceDef("world://map_data",         "Map Data",         "Current zone and known locations",                 "get_map_data"),
    ResourceDef("world://job_board",        "Job Board",        "Available jobs",                                   "get_job_board"),
    ResourceDef("world://market_listings",  "Market Listings",  "Items for sale nearby",                            "get_market_listings"),
    ResourceDef("world://time_and_weather", "Time and Weather", "Time of day, weather, and season",                 "get_time_and_weather"),
    ResourceDef("world://my_status",        "My Status",        "Health, inventory summary, and active jobs",       "get_my_status"),
]


# ---------------------------------------------------------------------------
# Function factories
# ---------------------------------------------------------------------------

def _make_tool_fn(adapter: BaseAdapter, tool_def: ToolDef):
    """
    Build a callable that:
    - Has the adapter method's real parameter signature (minus any fixed_kwargs)
    - Calls through to the adapter with those params + fixed_kwargs baked in
    - Returns something JSON-serializable
    FastMCP reads __signature__ to generate the tool's JSON schema.
    """
    method = getattr(adapter, tool_def.adapter_method)
    sig = inspect.signature(method)

    # Drop params that are baked into fixed_kwargs
    live_params = [
        p for name, p in sig.parameters.items()
        if name not in tool_def.fixed_kwargs
    ]

    def fn(**kwargs):
        result = method(**{**kwargs, **tool_def.fixed_kwargs})
        if result is None:
            return {"ok": True}
        if isinstance(result, (dict, list, str, int, float, bool)):
            return result
        return {"result": str(result)}

    fn.__name__ = tool_def.name
    fn.__doc__ = tool_def.description
    fn.__signature__ = inspect.Signature(live_params)
    fn.__annotations__ = {
        p.name: p.annotation
        for p in live_params
        if p.annotation is not inspect.Parameter.empty
    }
    return fn


def _make_resource_fn(adapter: BaseAdapter, res_def: ResourceDef):
    """Build a resource callable that returns a JSON string."""
    method = getattr(adapter, res_def.adapter_method)

    def fn() -> str:
        result = method(**res_def.fixed_kwargs)
        if isinstance(result, str):
            return result
        return json.dumps(result, indent=2, default=str)

    fn.__name__ = res_def.adapter_method
    fn.__doc__ = res_def.description
    return fn


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class WorldMCPServer:
    """
    Wraps any BaseAdapter as a fully-functional MCP server.
    Registers only the tools and resources the adapter actually implements.
    """

    def __init__(self, adapter: BaseAdapter):
        self.adapter = adapter
        self.mcp = self._build_server()

    def _build_server(self) -> FastMCP:
        game_name = self.adapter.get_game_name()
        perception_mode = self.adapter.get_perception_mode()
        mcp = FastMCP(game_name, host=MCP_HOST, port=MCP_PORT)
        log.info(f"Building MCP server — game: {game_name}  perception: {perception_mode.value}")
        self._register_connection_info(mcp, game_name, perception_mode)
        self._register_tools(mcp)
        self._register_resources(mcp)
        return mcp

    def _register_connection_info(self, mcp: FastMCP, game_name: str, perception_mode: PerceptionMode):
        """
        Expose connection metadata as a static resource.
        agent-core reads this on connect to know what game it's in and
        which perception loop to start (vision model vs. structured state receiver).
        """
        info = {
            "game": game_name,
            "perception_mode": perception_mode.value,
            "agent_id": AGENT_ID,
            "host_bridge_url": HOST_BRIDGE_URL if perception_mode == PerceptionMode.VISION else None,
        }
        info_json = json.dumps(info, indent=2)

        @mcp.resource("world://connection_info", name="Connection Info", description="Game identity and perception mode — read by agent-core on connect")
        def connection_info() -> str:
            return info_json

        log.info(f"Connection info: game={game_name}  perception_mode={perception_mode.value}  agent_id={AGENT_ID}")

    def _register_tools(self, mcp: FastMCP):
        implemented = set(self.adapter.get_implemented_tools())
        registered = []

        for tool_def in TOOL_MAP:
            if tool_def.adapter_method not in implemented:
                continue
            fn = _make_tool_fn(self.adapter, tool_def)
            mcp.tool(name=tool_def.name, description=tool_def.description)(fn)
            registered.append(tool_def.name)
            log.debug(f"  tool: {tool_def.name} → {tool_def.adapter_method}")

        log.info(f"Registered {len(registered)} tools: {', '.join(registered)}")

    def _register_resources(self, mcp: FastMCP):
        implemented = set(self.adapter.get_implemented_tools())
        registered = []

        for res_def in RESOURCE_MAP:
            if res_def.adapter_method not in implemented:
                continue
            fn = _make_resource_fn(self.adapter, res_def)
            mcp.resource(res_def.uri, name=res_def.name, description=res_def.description)(fn)
            registered.append(res_def.name)
            log.debug(f"  resource: {res_def.uri} → {res_def.adapter_method}")

        log.info(f"Registered {len(registered)} resources: {', '.join(registered)}")

    def run(self):
        game_name = self.adapter.get_game_name()
        perception_mode = self.adapter.get_perception_mode()
        log.info(f"Starting — game={game_name}  perception={perception_mode.value}  host={MCP_HOST}  port={MCP_PORT}")
        if perception_mode == PerceptionMode.VISION:
            log.info(f"Host bridge: {HOST_BRIDGE_URL}")
        self.mcp.run(transport="streamable-http")
