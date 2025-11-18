# 🎨 Web Viewer Visual Overview

## What You'll See When You Open `game_replay.html`

```
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║  ┌─────────────────────┐                        ┌────────────────┐  ║
║  │ 🎮 Game Status      │                        │ 🏷️ Legend      │  ║
║  │                     │                        │                │  ║
║  │ Time: 01:52         │                        │ 🟢 Seekers     │  ║
║  │ Caught: 1/7         │                        │ 🔴 Hiders      │  ║
║  │ Free: 6             │                        │ 🟤 Caught      │  ║
║  │ Status: ACTIVE      │                        │ 🟫 Obstacles   │  ║
║  └─────────────────────┘                        └────────────────┘  ║
║                                                                      ║
║                           ╔════════════╗                             ║
║                           ║  3D ARENA  ║                             ║
║                           ║            ║                             ║
║         🟩                ║    🟫🟫    ║                             ║
║      (Seeker #1)          ║            ║              🟫             ║
║                           ║  🟢 ←──→ 🔴║         (Obstacle)          ║
║                           ║ (Chase!)   ║                             ║
║       🟫                  ║            ║                             ║
║    (Obstacle)             ║   🟤       ║        🟫                   ║
║                           ║ (Caught)   ║    (Obstacle)               ║
║                           ║            ║                             ║
║    🟫      🔴             ║    🟫      ║                             ║
║         (Hiding)          ║            ║         🟩                  ║
║                           ║            ║      (Seeker #2)            ║
║                           ╚════════════╝                             ║
║                                                                      ║
║  ┌──────────────────────────────────────────────────────────────┐   ║
║  │  ▶ Play  │  ⟲ Restart │ ▓▓▓▓▓░░░░░░░░░░░ │ 0:06/0:30 │ 1x  │   ║
║  └──────────────────────────────────────────────────────────────┘   ║
║                         (Playback Controls)                          ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Interactive Elements

### 🎮 Game HUD (Top-Left)
```
┌─────────────────────┐
│ 🎮 Game Status      │
│                     │
│ Time: 01:45         │  ← Countdown timer (MM:SS)
│ Caught: 2/7         │  ← Progress (caught/total)
│ Free: 5             │  ← Remaining free hiders
│ Status: GAME ACTIVE │  ← Current game state
└─────────────────────┘
```

When game ends:
```
Status: WINNER: SEEKERS! ✨ (Gold text)
```

### 🏷️ Legend (Top-Right)
```
┌────────────────┐
│ 🏷️ Legend      │
│                │
│ 🟢 Seekers     │
│ 🔴 Hiders      │
│ 🟤 Caught      │
│ 🟫 Obstacles   │
└────────────────┘
```

### 🎬 Playback Controls (Bottom)
```
┌────────────────────────────────────────────────────────┐
│  [▶ Play]  [⟲ Restart]                                │
│                                                        │
│  Timeline: ▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░        │
│            ↑                                           │
│         Click anywhere to jump                         │
│                                                        │
│  Time: 0:06 / 0:30    Speed: [1x ▼]                  │
│                              0.25x                     │
│                              0.5x                      │
│                              1x   ← Current            │
│                              2x                        │
│                              4x                        │
└────────────────────────────────────────────────────────┘
```

## 3D Scene Features

### Camera Perspective
```
              Sky (Dark blue with fog)
                      ↑
                      │
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        │          Camera           │
        │        (You control)      │
        │             │             │
        │             ↓             │
        │      ┌─────────────┐     │
        │      │   Drones    │     │
        │      │  Obstacles  │     │
        │      │   Moving!   │     │
        │      └─────────────┘     │
        │                          │
        └──────────────────────────┘
              Grid Floor
```

### Lighting & Shadows
```
       ☀️ Light Source
        │
        ↓
     🟩 Seeker
    ╱  │  ╲
   ╱   │   ╲
  ╱    │    ╲
 ╱     │     ╲
└──────┴──────┘
   Shadow on ground
```

## Mouse Controls Visual Guide

### Rotate Camera
```
Click and Drag Left/Right:

    Before          →          After

    Camera                    Camera
      ↓                         ↓
    🟩 🟫 🔴              🟫 🟩 🔴

  (Side view)            (Different angle)
```

### Zoom In/Out
```
Scroll Wheel:

  Scroll Up (Zoom In)      Scroll Down (Zoom Out)
       ↓                          ↓

   🟩 🟫 🔴                    🟩 🟫 🔴
   (Close-up)                  (Far away)
```

## Example Game Moments

### Start of Game
```
Time: 02:00 | Caught: 0/7 | Status: ACTIVE

  🟫    🟫        Hiders rushing to
               hide behind obstacles
  🟫  🔴→🟫  🔴→

     🟢  🟢      Seekers starting patrol
   (Patrol)
```

### Chase Scene!
```
Time: 01:45 | Caught: 0/7

       🟢 ──→ 🔴
    (Seeker)  (Fleeing!)

  "Seeker #0 is chasing Hider #2!"
```

### Capture!
```
Time: 01:40 | Caught: 1/7

       🟢  🟤
           ↑
        (CAUGHT!)

  "Seeker #0 caught Hider #2!"
```

### End Game - Seekers Win
```
Time: 00:00 | Caught: 7/7

  🟤 🟤 🟤 🟤
  🟤 🟤 🟤

  🟢    🟢

  WINNER: SEEKERS! ✨
```

## Color Coding System

### Drone States
```
🟢 Green Sphere     = Seeker (Active hunter)
🔴 Bright Red       = Hider (Free, hiding/fleeing)
🟤 Dark Red         = Hider (Caught, stationary)
```

### Environment
```
🟫 Brown Boxes      = Obstacles (cover for hiders)
⬜ Gray Grid        = Ground plane (50x50m)
🌫️ Blue Fog         = Atmosphere (depth effect)
```

## Timeline Markers

```
Timeline with key events:

0:00      0:10      0:20      0:30
│─────────●─────────●─────────│
│         ↑         ↑         │
│     Detected   Caught       │
│     Hider #2   Hider #2     │
│                             │
▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░
↑
Current position (0:09)
```

## Performance Indicators

### Smooth Playback
```
60 FPS Animation
    ↓
🟩→🟩→🟩→🟩  (Smooth movement)

vs

15 FPS Animation
    ↓
🟩...🟩...🟩  (Choppy)
```

### Browser Compatibility
```
✅ Chrome   - Excellent (Hardware acceleration)
✅ Firefox  - Excellent
✅ Safari   - Good
✅ Edge     - Excellent
❌ IE11     - Not supported (Use modern browser)
```

## File Size Reference

```
Recording Duration    →    File Size
─────────────────────────────────────
10 seconds                  ~2.4 MB
30 seconds                  ~7.3 MB
60 seconds (1 min)          ~14 MB
120 seconds (2 min)         ~29 MB
```

## What Makes This Cool?

### 1. No Installation Required
```
Just open HTML file → Works immediately!
```

### 2. Shareable
```
Email file → Friend opens → Watches game!
```

### 3. Portable
```
Works offline after first load (Three.js cached)
```

### 4. Interactive
```
Not a video! Control playback, camera, explore freely
```

### 5. High Quality
```
WebGL rendering = Smooth, beautiful 3D graphics
```

---

## 🎬 Next Steps

1. **Record a session**:
   ```bash
   python record_and_export.py --duration 30
   ```

2. **Open in browser**:
   - Double-click `game_replay.html`
   - Or drag into browser window

3. **Enjoy watching**:
   - Click Play ▶
   - Drag to rotate camera
   - Scroll to zoom
   - Click timeline to jump around

**Have fun exploring your drone game in 3D!** 🚁✨
