# mcp-world

The interface. Translates between agent-core and any virtual world.
Speaks MCP to agent-core. Speaks game-specific to the world.

---

## What This Is

A collection of MCP servers — one per game/world.
Each adapter gives agent-core the same standardized tools and resources
regardless of what game is running underneath.

Swap the adapter, swap the world.
The agent doesn't know or care which world it's in.

---

## Architecture

```
mcp-world/
├── core/
│   ├── server.py             # MCP server base class
│   ├── tools.py              # tool registration helpers
│   └── resources.py          # resource registration helpers
│
├── adapters/
│   ├── base_adapter.py       # interface every adapter must implement
│   │
│   ├── open-world-mmo/       # primary adapter — most complete
│   │   ├── adapter.py        # implements base_adapter fully
│   │   ├── tools/
│   │   │   ├── movement.py   # go_to, follow, flee, patrol
│   │   │   ├── social.py     # say, tell, emote, approach
│   │   │   ├── economy.py    # trade, jobs, market
│   │   │   ├── world.py      # examine, interact, read
│   │   │   ├── inventory.py  # check gear, pick up, use
│   │   │   └── self.py       # recall memory, write journal
│   │   └── resources/
│   │       ├── world_state.py
│   │       ├── nearby_entities.py
│   │       ├── chat_log.py
│   │       └── map_data.py
│   │
│   ├── opensim/              # community contribution example
│   │   └── adapter.py        # thinner — social/movement only
│   │
│   └── vrchat/               # community contribution example
│       └── adapter.py        # social only
│
├── host-bridge/              # runs on HOST machine, not in Docker
│   ├── bridge.py             # screenshot capture + input injection
│   ├── requirements.txt
│   └── README.md             # setup instructions
│
└── lore/
    ├── open-world-mmo/       # lore files for the primary game
    │   ├── world_history.md
    │   ├── factions.md
    │   ├── zones.md
    │   ├── npcs.md
    │   └── lore_loader.py    # ingests markdown into agent-core vector DB
    └── README.md             # how to add lore for other games
```

---

## The Adapter Pattern

Every adapter implements the same base interface.
This is the contract between mcp-world and the game:

```python
class BaseAdapter:

    # --- REQUIRED: every adapter must implement these ---

    def get_world_state(self, agent_id) -> dict:
        """Current structured perception for this agent"""
        raise NotImplementedError

    def send_chat(self, message: str, channel: str = "say"):
        """Say something in the world"""
        raise NotImplementedError

    def move_to(self, destination: str | tuple):
        """Move to a location — engine handles pathfinding"""
        raise NotImplementedError

    def get_game_name(self) -> str:
        """Tell agent-core what game this is"""
        raise NotImplementedError

    # --- OPTIONAL: implement what the game supports ---

    def send_tell(self, player: str, message: str): ...
    def emote(self, emote: str): ...
    def follow(self, entity: str): ...
    def flee_from(self, entity: str): ...
    def interact_with(self, object: str): ...
    def pick_up(self, item: str): ...
    def post_job(self, job: dict): ...
    def accept_job(self, job_id: str): ...
    def hire_mercenary(self, criteria: dict): ...
    def check_job_board(self) -> list: ...
    def list_item_for_sale(self, item: str, price: int): ...
    def buy_item(self, item: str, from_entity: str): ...
```

agent-core asks "what tools are available?" at startup.
mcp-world returns only the tools this adapter actually implements.
The agent works with whatever subset is available.

---

## Full Tool List (open-world-mmo adapter)

This is what "full player-like capability" looks like.
The primary game adapter implements all of these.

### Movement
```
move_to_location(destination)     intent-based, engine handles pathfinding
follow_entity(name, distance)     follow a player or NPC
flee_from(entity)                 run away from a threat
patrol_waypoints(points[])        guard or patrol behavior
go_to_point_of_interest(name)     named locations the agent knows
enter_building(name)
mount()
dismount()
```

### Social
```
say(message)                      local chat, nearby players hear it
tell(player, message)             private message
shout(message)                    zone-wide
emote(emote_name)                 wave, bow, laugh, sit, dance
approach_entity(name)             walk up to someone
initiate_trade(player)
join_group(player)
leave_group()
```

### Economy
```
post_job(type, route, pay, notes) hire mercenaries or request help
accept_job(job_id)                take work from the job board
list_item_for_sale(item, price)
buy_item(item, from_entity)
make_offer(player, item, price)
check_job_board()                 see available work
check_market_prices(item)
```

### World Interaction
```
examine_object(object)
pick_up_item(item)
open_container(container)
use_object(object)
sit()
sleep()                           agents rest — creates interesting behavior
read_notice_board()
open_door(door)
```

### Self / Memory
```
check_inventory()
check_health()
check_surroundings()              structured world state snapshot
recall_memory(query)              query own vector DB
write_journal(entry)              log a significant moment
update_belief(belief, value)      change something the agent thinks is true
check_goals()                     what am I currently trying to do
update_goal(goal, status)
```

### Combat Adjacent (no direct combat)
```
hire_mercenary(criteria)          find and contract protection
dismiss_mercenary(name)
flee_combat()                     get out of a fight
call_for_help()                   alert nearby players/agents
```

---

## Resources (what the agent can read)

MCP resources are things the agent can query, not actions it can take.

```
world_state           full structured perception snapshot
nearby_entities       players, NPCs, agents within range
chat_log              recent chat in the area
map_data              current zone, known locations
job_board             available jobs
market_listings       items for sale nearby
time_and_weather      time of day, weather, season
my_status             health, inventory summary, active jobs
```

---

## The Host Bridge

This is the only piece that runs **outside Docker**.
It must run on the host machine because it needs to touch the game window.

Explorer agents (vision loop) require it.
City agents (structured state) do not — they connect directly to the game server.

```python
# host-bridge/bridge.py
# Minimal Flask server on the host
# Docker containers call it via host.docker.internal

# Endpoints:
GET  /screenshot          returns base64 PNG of game window
POST /action              executes keyboard/mouse input
GET  /health              confirm bridge is running

# Actions supported:
key_press(key)
key_hold(key, duration)
type_text(text)           handles chat open/send automatically
mouse_move(x, y)
mouse_click(x, y)
```

Setup is intentionally minimal — one Python file, four dependencies.
A non-developer can run it.

---

## How game-name Triggers Lore Loading

When an adapter connects, it reports its game name.
agent-core uses this to load the right lore into its vector DB:

```
adapter.get_game_name() → "open-world-mmo"
agent-core: load lore/open-world-mmo/ into ChromaDB collection "lore_open-world-mmo"
agent-core: agent now knows this world's history, factions, zones
```

Lore is stored as markdown files in `lore/{gamename}/`.
`lore_loader.py` chunks and ingests them into ChromaDB.
Adding lore for a new game is just adding markdown files.

---

## Docker Compose

mcp-world services run inside Docker (except host-bridge):

```yaml
services:

  mcp-open-world-mmo:
    build: ./adapters/open-world-mmo
    ports:
      - "8080:8080"
    environment:
      - GAME_SERVER_HOST=open-world-mmo-server
      - GAME_SERVER_PORT=7777
      - HOST_BRIDGE_URL=http://host.docker.internal:5000

  # Add other adapters as needed
  # mcp-opensim:
  #   build: ./adapters/opensim
```

---

## Adding a New Game Adapter

1. Create `adapters/{gamename}/adapter.py`
2. Extend `BaseAdapter`
3. Implement at minimum: `get_world_state`, `send_chat`, `move_to`, `get_game_name`
4. Add lore files to `lore/{gamename}/` (optional but recommended)
5. Add to docker-compose.yml

The agent will automatically discover which tools are available
and work with whatever the adapter provides.

---

## Development Order

1. `core/server.py` — base MCP server
2. `host-bridge/bridge.py` — screenshot + input on host
3. `adapters/base_adapter.py` — the contract
4. `adapters/open-world-mmo/` — primary adapter, build all tools
5. `lore/open-world-mmo/` — world knowledge files
6. Test: explorer agent + host bridge + open-world-mmo adapter running together

---

## Related Projects

- **agent-core** — the agent brain that connects to this
- **open-world-mmo** — the primary game this adapter talks to
