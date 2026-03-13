"""
adapters/mock_world/adapter.py

A fake game world for testing the full agent-core → mcp-world → adapter loop
without any real game running.

Simulates a small scene at the Ember Inn in Ashenveil. The scene rotates
every 30 seconds, giving the agent something new to notice and react to.

Scene cycle (120 seconds total):
  0–30s   Scene 1 — quiet evening, a dwarf at the bar
  30–60s  Scene 2 — dwarf gone, hooded stranger watching the door
  60–90s  Scene 3 — stranger and a woman talking quietly in the corner
  90–120s Scene 4 — everyone gone, a note left on the table near the door

Run with PerceptionMode.VISION to test the full vision loop path.
"""

import time
from datetime import datetime

from adapters.base_adapter import BaseAdapter, PerceptionMode

SCENE_DURATION = 30  # seconds per scene
SCENE_COUNT = 4


# ---------------------------------------------------------------------------
# Scene data
# ---------------------------------------------------------------------------

SCENES = [

    # --- Scene 1: quiet evening, dwarf at the bar ---
    {
        "index": 0,
        "time_of_day": "evening",
        "location": "The Ember Inn, Ashenveil — common room",
        "description": (
            "The common room is quiet. The fire has been going since midday and the stones "
            "around it have taken on a deep, settled warmth. A dwarf sits at the bar with a "
            "tankard he has barely touched, staring at nothing in particular. The innkeeper "
            "moves between the back room and the bar without making conversation."
        ),
        "nearby_entities": [
            {
                "name": "Dundar",
                "type": "npc",
                "description": "A dwarf in travel-worn clothes. Sits at the bar alone. Not drinking so much as sitting.",
                "mood": "distant",
                "position": "at the bar",
            },
            {
                "name": "Hadra",
                "type": "npc",
                "description": "The innkeeper. A woman who moves with the economy of someone who has run this place for decades. She does not encourage conversation.",
                "mood": "watchful",
                "position": "behind the bar",
            },
        ],
        "ambient_details": [
            "The fire pops and settles.",
            "Woodsmoke and old beer. Familiar smells.",
            "A key hangs on a hook behind the bar, uncollected. A small tag reads 'L — held'.",
            "A window faces north. The road outside is empty.",
        ],
        "notice_board": (
            "Several notices pinned up. Job postings, a missing dog, a warning about the north road "
            "written in someone's unsteady hand. And one that just says: 'North — don't.' "
            "No signature. Recently pinned."
        ),
        "chat_log": [
            {"speaker": "Hadra", "text": "He shouldn't have taken the north road. He knows it isn't safe."},
            {"speaker": "Dundar", "text": "...you know how he is."},
            {"speaker": "Hadra", "text": "I kept the room. Just in case."},
        ],
    },

    # --- Scene 2: dwarf gone, stranger watching the door ---
    {
        "index": 1,
        "time_of_day": "later evening",
        "location": "The Ember Inn, Ashenveil — common room",
        "description": (
            "The dwarf has gone. A stranger sits near the door — hooded, a cup of something "
            "warm in front of them, barely touched. They are watching the door the way someone "
            "watches a door when they are waiting for a specific person to come through it. "
            "Hadra is still behind the bar, occupied with something below the counter."
        ),
        "nearby_entities": [
            {
                "name": "Hooded stranger",
                "type": "npc",
                "description": "Dressed for travel, hood still up despite being indoors. Watchful. Has chosen the seat with the clearest view of the entrance.",
                "mood": "tense, waiting",
                "position": "near the door",
            },
            {
                "name": "Hadra",
                "type": "npc",
                "description": "The innkeeper. She glanced at the stranger when they came in and has not glanced again.",
                "mood": "deliberately uninterested",
                "position": "behind the bar",
            },
        ],
        "ambient_details": [
            "Wind against the north-facing window.",
            "The fire has dropped a little. Still warm.",
            "A key hangs on a hook behind the bar, uncollected. A small tag reads 'L — held'.",
            "The stranger's eyes move to the door whenever there is a sound outside.",
        ],
        "chat_log": [
            {"speaker": "Hooded stranger", "text": "Something warm. Whatever you have."},
            {"speaker": "Hadra", "text": "(sets a cup down without a word)"},
        ],
    },

    # --- Scene 3: stranger and a woman, talking quietly ---
    {
        "index": 2,
        "time_of_day": "night",
        "location": "The Ember Inn, Ashenveil — common room",
        "description": (
            "The stranger is no longer alone. A woman in traveling clothes has joined them — "
            "she arrived quietly, without announcing herself, and took the seat across from them "
            "as though she knew it would be free. They are speaking in voices too low to follow. "
            "The woman looks worried. The stranger looks like someone delivering news they have "
            "been dreading."
        ),
        "nearby_entities": [
            {
                "name": "Hooded stranger",
                "type": "npc",
                "description": "Still hooded. Speaking quietly. Hands flat on the table.",
                "mood": "grave",
                "position": "corner table",
            },
            {
                "name": "Woman in traveling clothes",
                "type": "npc",
                "description": "Road-dusty. She has been moving fast. Her hands are wrapped around a cup she is not drinking from.",
                "mood": "afraid, controlled",
                "position": "corner table",
            },
            {
                "name": "Hadra",
                "type": "npc",
                "description": "The innkeeper. She has not approached the corner table.",
                "mood": "giving them space",
                "position": "behind the bar",
            },
        ],
        "ambient_details": [
            "Their voices do not carry.",
            "The fire is the loudest thing in the room.",
            "A key hangs on a hook behind the bar, still uncollected.",
            "The woman shakes her head slowly at something the stranger says.",
        ],
        "chat_log": [
            {"speaker": "overheard", "text": "...said he'd be back by nightfall. That was three days ago..."},
            {"speaker": "overheard", "text": "(The rest is too quiet to make out. You catch the word 'Kesrath'.)"},
        ],
    },

    # --- Scene 4: everyone gone, note on the table ---
    {
        "index": 3,
        "time_of_day": "late night",
        "location": "The Ember Inn, Ashenveil — common room",
        "description": (
            "The room is empty. The stranger and the woman are gone — you did not hear them leave. "
            "The fire has burned down to deep orange coals. On the table nearest the door, where the "
            "stranger was sitting, there is a folded piece of paper. Someone left it there deliberately. "
            "Behind the bar, a key still hangs on its hook."
        ),
        "nearby_entities": [],
        "ambient_details": [
            "Silence. The fire barely makes a sound anymore.",
            (
                "The note on the table near the door. You unfold it and read: "
                "'The road north is not safe. He knows this. "
                "If you see him — tall, asks too many questions — tell him to turn back. "
                "He went anyway. Three days ago.' "
                "No signature. The handwriting is hurried."
            ),
            "A key hangs on a hook behind the bar. The tag reads 'L — held'. Nobody came for it.",
            "The door is closed. The north-facing window shows nothing but dark.",
        ],
        "chat_log": [
            {"speaker": "ambient", "text": "The fire pops once. Otherwise, silence."},
        ],
    },
]


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class MockWorldAdapter(BaseAdapter):
    """
    Fake game world for testing. Simulates a tavern scene that rotates
    every 30 seconds so the agent has something new to perceive and react to.
    """

    def __init__(self):
        self._chat_history: list[dict] = []

    # -------------------------------------------------------------------------
    # Required
    # -------------------------------------------------------------------------

    def get_game_name(self) -> str:
        return "mock_world"

    def get_perception_mode(self) -> PerceptionMode:
        return PerceptionMode.VISION

    def get_world_state(self, agent_id: str) -> dict:
        scene = self._current_scene()
        state = {
            "agent_id": agent_id,
            "location": scene["location"],
            "time_of_day": scene["time_of_day"],
            "description": scene["description"],
            "nearby_entities": scene["nearby_entities"],
            "ambient_details": scene["ambient_details"],
            "scene_index": scene["index"],
            "timestamp": datetime.utcnow().isoformat(),
        }
        if "notice_board" in scene:
            state["notice_board"] = scene["notice_board"]
        return state

    def send_chat(self, message: str, channel: str = "say"):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "channel": channel,
            "message": message,
        }
        self._chat_history.append(entry)
        print(f"[MOCK WORLD CHAT] [{channel.upper()}] {message}")

    def move_to(self, destination: str):
        print(f"[MOCK WORLD MOVE] → {destination}")
        return {"ok": True, "destination": destination}

    # -------------------------------------------------------------------------
    # Optional — implemented
    # -------------------------------------------------------------------------

    def get_nearby_entities(self) -> dict:
        scene = self._current_scene()
        return {
            "location": scene["location"],
            "entities": scene["nearby_entities"],
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_chat_log(self) -> dict:
        scene = self._current_scene()
        return {
            "location": scene["location"],
            "overheard": scene["chat_log"],
            "agent_sent": self._chat_history[-10:],  # last 10 messages Jezra sent
            "timestamp": datetime.utcnow().isoformat(),
        }

    def examine(self, object: str) -> dict:
        object_lower = object.lower().strip()
        scene_index = self._current_scene()["index"]

        if object_lower == "fireplace":
            return {
                "object": object,
                "description": (
                    "The fire has been burning a long time. The stones are blackened "
                    "in a pattern that suggests years of use — not neglect, but constancy. "
                    "Someone has kept this fire going for a very long time."
                ),
            }

        if object_lower in ("key", "hook", "key on hook"):
            return {
                "object": object,
                "description": (
                    "A room key on a worn leather tag. The tag reads 'L — held'. "
                    "The hook beside it has a small mark scratched into the wood — "
                    "someone who stayed here often enough to leave a mark without meaning to."
                ),
            }

        if object_lower == "table":
            if scene_index == 3:
                return {
                    "object": object,
                    "description": (
                        "The note is here. And the scratches in the wood — letters traced "
                        "absently near the edge, worn smooth now, almost gone. An L, maybe. "
                        "Or just wear from years of use. The same hand, maybe. "
                        "Or you are seeing patterns that aren't there."
                    ),
                }
            return {
                "object": object,
                "description": (
                    "An ordinary table near the window. Someone sat here recently — "
                    "there is still warmth in the wood. Faint scratches near the edge, "
                    "letters traced absently by someone's finger while they thought. "
                    "An L, maybe. Or just wear from years of use. Hard to say."
                ),
            }

        if object_lower == "note":
            if scene_index == 3:
                return {
                    "object": "note",
                    "description": (
                        "The road north is not safe. He knows this. "
                        "If you see him — tall, asks too many questions — tell him to turn back. "
                        "He went anyway. Three days ago.\n\n"
                        "The note is unsigned. The handwriting is hurried. "
                        "Whoever wrote this was scared, or in a hurry. Maybe both."
                    ),
                }
            return {
                "object": "note",
                "description": "There is no note here.",
            }

        return {
            "object": object,
            "description": "You look closely but find nothing remarkable.",
        }

    def read_notice_board(self) -> dict:
        scene = self._current_scene()
        if "notice_board" in scene:
            return {"notice_board": scene["notice_board"]}
        return {"notice_board": "The notice board is bare."}

    # -------------------------------------------------------------------------
    # Scene helpers
    # -------------------------------------------------------------------------

    def _current_scene_index(self) -> int:
        elapsed = int(time.time()) % (SCENE_DURATION * SCENE_COUNT)
        return elapsed // SCENE_DURATION

    def _current_scene(self) -> dict:
        return SCENES[self._current_scene_index()]
