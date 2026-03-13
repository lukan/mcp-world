# host-bridge

Runs on your Windows PC — **not** in Docker.
Gives Docker containers access to your screen and keyboard/mouse.

This is what lets agents see the game and send keystrokes to it.

---

## Install

```
pip install -r requirements.txt
```

---

## Run

```
python bridge.py
```

Bridge starts on port 5001. Leave this terminal open while agents are running.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `BRIDGE_WINDOW_TITLE` | *(none)* | Partial title of the game window to capture. If not set, captures the full desktop. Example: `EverQuest` matches `EverQuest - Landon` |
| `BRIDGE_CHAT_PREFIX` | *(none)* | Set to any value to enable chat mode. When enabled, `type_text` actions will open chat, type the text, and press send. |
| `BRIDGE_CHAT_KEY` | `enter` | The key used to open and send chat. |
| `BRIDGE_PORT` | `5001` | Port the bridge listens on. |

### Example — EverQuest

```
set BRIDGE_WINDOW_TITLE=EverQuest
set BRIDGE_CHAT_PREFIX=1
python bridge.py
```

---

## Endpoints

### `GET /health`
Check that the bridge is running and whether the target window was found.

```json
{
  "status": "ok",
  "window_title_configured": "EverQuest",
  "window_found": true,
  "window_info": { "title": "EverQuest - Landon", "left": 0, "top": 0, "width": 1920, "height": 1080 }
}
```

### `GET /screenshot`
Returns a base64-encoded PNG of the game window (or full desktop if no window configured).

```json
{
  "image": "<base64 PNG>",
  "format": "png",
  "source": "window",
  "width": 1920,
  "height": 1080
}
```

### `POST /action`
Send a keyboard or mouse action.

```json
{ "type": "key_press", "key": "enter" }
{ "type": "key_hold", "key": "w", "duration": 2.0 }
{ "type": "type_text", "text": "hello world" }
{ "type": "mouse_move", "x": 100, "y": 200 }
{ "type": "mouse_click", "x": 100, "y": 200, "button": "left" }
```

### `GET /window/list`
List all visible windows — use this to find the exact title to put in `BRIDGE_WINDOW_TITLE`.

```json
{
  "windows": [
    { "title": "EverQuest - Landon", "left": 0, "top": 0, "width": 1920, "height": 1080 },
    ...
  ]
}
```

---

## How Docker Containers Call It

Inside any Docker container, the host machine is reachable at `host.docker.internal`.

```
http://host.docker.internal:5001/screenshot
http://host.docker.internal:5001/action
```

This address is set automatically in `docker-compose.yml` via the `HOST_BRIDGE_URL` environment variable. You don't need to configure it manually.
