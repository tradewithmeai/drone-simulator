# 🌐 Web-Based 3D Viewer for Drone Simulator

## Overview

The web viewer allows you to **record hide-and-seek game sessions** and **watch them in any web browser** with full 3D visualization, interactive playback controls, and timeline scrubbing.

## ✨ Features

### 3D Visualization
- **Three.js powered** - High-quality WebGL rendering
- **Color-coded drones**:
  - 🟢 Green = Seekers
  - 🔴 Red = Free hiders
  - 🟤 Dark red = Caught hiders
- **Brown box obstacles** with realistic lighting
- **Grid floor** with fog effects
- **Dynamic shadows** and ambient lighting

### Interactive Controls
- **Play/Pause** - Control playback
- **Restart** - Jump back to beginning
- **Timeline scrubber** - Click anywhere to jump to that moment
- **Playback speed** - Adjust from 0.25x to 4x speed
- **Camera controls**:
  - Drag mouse to rotate camera
  - Scroll wheel to zoom in/out
  - Automatic center on play area

### Game HUD
- **Live game statistics**:
  - Remaining time (MM:SS format)
  - Caught hiders count (X/7)
  - Free hiders count
  - Game status (ACTIVE / WINNER)
- **Color-coded legend**
- **Timestamp display** (current / total)

## 🚀 Quick Start

### 1. Record a Game Session

```bash
# Record 30 second session
python record_and_export.py --duration 30

# Record longer session (60 seconds)
python record_and_export.py --duration 60 --output my_game.html

# Record until game ends or Ctrl+C
python record_and_export.py --duration 120
```

### 2. Open in Browser

Simply **double-click `game_replay.html`** or open it in your browser:
```bash
# Linux/Mac
open game_replay.html

# Windows
start game_replay.html

# Or drag and drop into browser window
```

### 3. Watch and Enjoy!

The viewer will:
- ✅ Load automatically
- ✅ Show 3D arena with obstacles and drones
- ✅ Display game statistics
- ✅ Enable interactive playback

## 🎮 Viewer Controls

### Playback Controls
- **▶ Play** - Start playback
- **⏸ Pause** - Pause playback
- **⟲ Restart** - Reset to beginning
- **Timeline** - Click to jump to any time
- **Speed** - Dropdown to change playback speed

### Camera Controls
- **Mouse Drag** - Rotate camera around arena
- **Mouse Wheel** - Zoom in/out
- **Auto-center** - Camera focuses on play area center

### Keyboard Shortcuts
- `Space` - Play/Pause (planned)
- `R` - Restart (planned)
- `← →` - Step frame by frame (planned)

## 📊 Example Recording Session

```bash
$ python record_and_export.py --duration 30

============================================================
RECORDING HIDE-AND-SEEK GAME SESSION
============================================================

[RECORD] Starting game...
[RECORD] Recording for 30 seconds...

[  1.1s] Caught: 0/7 | Time: 117.9s | Frames: 60
[GAME] Seeker #0 detected Hider #2!
[  6.6s] Caught: 1/7 | Time: 112.4s | Frames: 360
[GAME] Seeker #0 caught Hider #2! (1/7)
[ 12.9s] Caught: 1/7 | Time: 106.1s | Frames: 720
[GAME] Seeker #1 detected Hider #3!

============================================================
EXPORT COMPLETE!
============================================================

✅ Recorded 1697 frames
✅ Duration: 30.0 seconds
✅ Web viewer: game_replay.html

🌐 Open 'game_replay.html' in your web browser!
```

## 📁 Generated Files

### `game_replay.html`
- **Self-contained** - No external dependencies (besides Three.js CDN)
- **Portable** - Share with anyone, works offline after first load
- **Size** - ~7MB for 30 seconds at 60 FPS

### `simulation_data.json`
- **Intermediate format** - Raw recorded data
- **Can be re-used** - Inject into different viewer templates
- **Format**:
  ```json
  {
    "metadata": {...},
    "obstacles": [...],
    "frames": [
      {
        "timestamp": 0.0,
        "drones": [...],
        "game_status": {...}
      }
    ],
    "events": [...]
  }
  ```

## 🎨 Customization

### Recording Options

```python
# In record_and_export.py, modify these parameters:

# Record at different frame rates
time.sleep(1/30)  # 30 FPS instead of 60 FPS

# Record different events
recorder.record_event('detection', {
    'seeker_id': 0,
    'hider_id': 2,
    'distance': 5.0
})

# Add metadata
recorder.metadata['custom_field'] = 'value'
```

### Viewer Customization

Edit `viewer_template.html`:

```javascript
// Change colors
scene.background = new THREE.Color(0x000000); // Black background

// Adjust fog
scene.fog = new THREE.Fog(0x0a0a1a, 30, 80); // Denser fog

// Change drone colors
const seekerColor = 0x00ff00;  // Green
const hiderColor = 0xff0000;   // Red

// Adjust camera start position
camera.position.set(50, 50, 50); // Further away
```

## 🔧 Technical Details

### Architecture

```
User runs record_and_export.py
         ↓
Simulator runs with recorder attached
         ↓
Every frame: drone states → recorder
         ↓
Export to JSON: simulation_data.json
         ↓
Inject JSON into HTML template
         ↓
Output: game_replay.html (standalone)
```

### Performance

- **Recording**: ~60 FPS capture
- **File size**: ~240KB per second of recording
- **Playback**: Smooth at all speeds on modern browsers
- **Browser requirements**: WebGL support (any modern browser)

### Data Format

Each frame contains:
```json
{
  "timestamp": 5.5,
  "drones": [
    {
      "id": 0,
      "position": [8.5, 4.0, -18.7],
      "velocity": [2.1, 0.0, -1.3],
      "color": [0.0, 1.0, 0.0],
      "role": "seeker",
      "detected": false,
      "caught": false,
      "behavior_state": "chase"
    }
  ],
  "game_status": {
    "active": true,
    "remaining_time": 114.5,
    "caught_count": 1,
    "total_hiders": 7,
    "winner": null
  }
}
```

## 🚀 Advanced Usage

### Record Multiple Sessions

```bash
# Record several games
for i in {1..5}; do
    python record_and_export.py --duration 60 --output game_$i.html
done
```

### Extract Specific Moments

```python
# In record_and_export.py, add filtering:
if game_status['caught_count'] > 0:
    recorder.record_frame(drone_states, game_status)
```

### Create Compilation Videos

1. Record multiple sessions
2. Open each HTML in browser
3. Use screen recording software (OBS, etc.)
4. Compile into video

## 📈 Future Enhancements

Planned features:

- [ ] Event markers on timeline (detections, catches)
- [ ] Drone trails showing path history
- [ ] Click drone to follow/highlight
- [ ] Mini-map view (top-down)
- [ ] Export to video directly (ffmpeg)
- [ ] VR support for immersive viewing
- [ ] Side-by-side comparison of multiple recordings

## 🐛 Troubleshooting

### Viewer won't load
- **Check browser console** for errors
- **Ensure JavaScript enabled**
- **Try different browser** (Chrome, Firefox, Safari all work)

### Playback stuttering
- **Lower playback speed** (0.5x)
- **Use modern browser** with good GPU
- **Close other tabs** to free resources

### File too large
- **Record shorter sessions** (< 60 seconds)
- **Reduce frame rate** in recording script
- **Compress JSON** (planned feature)

## 📝 Example Use Cases

1. **Game Analysis** - Review seeker strategies
2. **Debugging AI** - See why drones behave certain ways
3. **Demonstrations** - Show game to others without running simulator
4. **Documentation** - Include in presentations/reports
5. **Competitions** - Share best game recordings

## 🎓 Technical Stack

- **Three.js** - 3D rendering library
- **WebGL** - Hardware-accelerated graphics
- **Vanilla JavaScript** - No frameworks needed
- **Python** - Recording and export
- **JSON** - Data interchange format

---

**Enjoy watching your drone games in beautiful 3D!** 🚁✨
