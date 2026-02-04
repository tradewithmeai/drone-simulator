"""FastAPI REST + WebSocket server for external drone control.

Wraps the Simulator and HAL interfaces so ESP32 mission computers,
test scripts, and dashboards can interact with the simulation over
HTTP and WebSocket.
"""

import asyncio
import json
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.serializers import (
    sanitize,
    serialize_imu,
    serialize_gps,
    serialize_altitude,
    serialize_battery,
    serialize_status,
    serialize_ground_truth,
    serialize_drone_state,
)


# ── Pydantic request models ──────────────────────────────────────

class PositionCommand(BaseModel):
    x: float
    y: float
    z: float
    yaw: float = 0.0


class VelocityCommand(BaseModel):
    vx: float
    vy: float
    vz: float
    yaw_rate: float = 0.0


class TakeoffCommand(BaseModel):
    altitude: float = 10.0


class FormationCommand(BaseModel):
    type: str


class RespawnCommand(BaseModel):
    preset: str
    num_drones: Optional[int] = None


class BoxObstacle(BaseModel):
    position: list  # [x, y, z]
    size: list      # [sx, sy, sz]
    color: Optional[list] = None


class CylinderObstacle(BaseModel):
    position: list  # [x, y, z]
    radius: float
    height: float
    color: Optional[list] = None


class AvoidanceConfigModel(BaseModel):
    enabled: bool = True
    sensor_range: float = 5.0
    repulsion_gain: float = 3.0
    velocity_limit: float = 2.0


class WindConfigModel(BaseModel):
    enabled: bool = True
    base_velocity: list = [0.0, 0.0, 0.0]
    gust_magnitude: float = 2.0
    gust_frequency: float = 0.1


# ── WebSocket connection manager ─────────────────────────────────

class ConnectionManager:
    """Manages active WebSocket connections and broadcasts state."""

    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


# ── App factory ──────────────────────────────────────────────────

def create_app(simulator, cors_origins: list = None, ws_push_rate: float = 10.0) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        simulator: A running Simulator instance.
        cors_origins: Allowed CORS origins (default ["*"]).
        ws_push_rate: WebSocket state push rate in Hz (default 10).
    """
    app = FastAPI(title="Drone Swarm Simulator API", version="1.0.0")

    # CORS
    origins = cors_origins or ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    manager = ConnectionManager()
    ws_interval = 1.0 / max(ws_push_rate, 1.0)

    # Store on app state for access in startup event
    app.state.simulator = simulator
    app.state.manager = manager
    app.state.ws_interval = ws_interval
    app.state._ws_task = None

    # ── Helpers ───────────────────────────────────────────────

    def _get_hal(drone_id: int):
        hal = simulator.get_hal(drone_id)
        if hal is None:
            raise HTTPException(status_code=404, detail=f"Drone {drone_id} not found")
        return hal

    # ── Simulation control ───────────────────────────────────

    @app.get("/api/sim/info")
    def sim_info():
        return sanitize(simulator.get_simulation_info())

    @app.post("/api/sim/pause")
    def sim_pause():
        simulator.pause()
        return {"status": "paused"}

    @app.post("/api/sim/resume")
    def sim_resume():
        simulator.resume()
        return {"status": "resumed"}

    @app.post("/api/sim/step")
    def sim_step():
        simulator.step_simulation()
        return {"status": "stepped"}

    # ── Drone listing ────────────────────────────────────────

    @app.get("/api/drones")
    def list_drones():
        states = simulator.get_drone_states()
        return [serialize_drone_state(s) for s in states]

    @app.get("/api/drones/{drone_id}")
    def get_drone(drone_id: int):
        states = simulator.get_drone_states()
        for s in states:
            if s['id'] == drone_id:
                return serialize_drone_state(s)
        raise HTTPException(status_code=404, detail=f"Drone {drone_id} not found")

    # ── Per-drone sensors ────────────────────────────────────

    @app.get("/api/drones/{drone_id}/sensors/imu")
    def drone_imu(drone_id: int):
        hal = _get_hal(drone_id)
        return serialize_imu(hal.get_imu())

    @app.get("/api/drones/{drone_id}/sensors/gps")
    def drone_gps(drone_id: int):
        hal = _get_hal(drone_id)
        return serialize_gps(hal.get_gps())

    @app.get("/api/drones/{drone_id}/sensors/altitude")
    def drone_altitude(drone_id: int):
        hal = _get_hal(drone_id)
        return serialize_altitude(hal.get_altitude())

    @app.get("/api/drones/{drone_id}/sensors/battery")
    def drone_battery(drone_id: int):
        hal = _get_hal(drone_id)
        return serialize_battery(hal.get_battery())

    @app.get("/api/drones/{drone_id}/status")
    def drone_status(drone_id: int):
        hal = _get_hal(drone_id)
        return serialize_status(hal.get_status())

    @app.get("/api/drones/{drone_id}/ground_truth")
    def drone_ground_truth(drone_id: int):
        hal = _get_hal(drone_id)
        return serialize_ground_truth(hal.get_ground_truth())

    # ── Per-drone commands ───────────────────────────────────

    @app.post("/api/drones/{drone_id}/command/position")
    def cmd_position(drone_id: int, cmd: PositionCommand):
        hal = _get_hal(drone_id)
        hal.set_position(cmd.x, cmd.y, cmd.z, cmd.yaw)
        return {"status": "ok", "drone_id": drone_id}

    @app.post("/api/drones/{drone_id}/command/velocity")
    def cmd_velocity(drone_id: int, cmd: VelocityCommand):
        hal = _get_hal(drone_id)
        hal.set_velocity(cmd.vx, cmd.vy, cmd.vz, cmd.yaw_rate)
        return {"status": "ok", "drone_id": drone_id}

    @app.post("/api/drones/{drone_id}/command/arm")
    def cmd_arm(drone_id: int):
        hal = _get_hal(drone_id)
        hal.arm()
        return {"status": "armed", "drone_id": drone_id}

    @app.post("/api/drones/{drone_id}/command/disarm")
    def cmd_disarm(drone_id: int):
        hal = _get_hal(drone_id)
        hal.disarm()
        return {"status": "disarmed", "drone_id": drone_id}

    @app.post("/api/drones/{drone_id}/command/takeoff")
    def cmd_takeoff(drone_id: int, cmd: TakeoffCommand = TakeoffCommand()):
        hal = _get_hal(drone_id)
        success = hal.takeoff(cmd.altitude)
        if not success:
            raise HTTPException(status_code=400, detail="Drone not armed")
        return {"status": "taking_off", "drone_id": drone_id}

    @app.post("/api/drones/{drone_id}/command/land")
    def cmd_land(drone_id: int):
        hal = _get_hal(drone_id)
        hal.land()
        return {"status": "landing", "drone_id": drone_id}

    # ── Formation ────────────────────────────────────────────

    @app.post("/api/formation")
    def set_formation(cmd: FormationCommand):
        simulator.set_formation(cmd.type)
        return {"status": "ok", "formation": cmd.type}

    @app.post("/api/respawn")
    def respawn(cmd: RespawnCommand):
        simulator.respawn_formation(cmd.preset, cmd.num_drones)
        return {"status": "ok", "preset": cmd.preset}

    # ── Obstacles ────────────────────────────────────────────

    @app.get("/api/obstacles")
    def list_obstacles():
        info = simulator.get_simulation_info()
        return sanitize(info.get('obstacles', []))

    @app.post("/api/obstacles/box")
    def add_box(obs: BoxObstacle):
        simulator.add_box_obstacle(obs.position, obs.size, obs.color)
        return {"status": "ok", "type": "box"}

    @app.post("/api/obstacles/cylinder")
    def add_cylinder(obs: CylinderObstacle):
        simulator.add_cylinder_obstacle(obs.position, obs.radius, obs.height, obs.color)
        return {"status": "ok", "type": "cylinder"}

    @app.delete("/api/obstacles/last")
    def remove_last_obstacle():
        simulator.remove_last_obstacle()
        return {"status": "ok"}

    @app.delete("/api/obstacles")
    def clear_obstacles():
        simulator.clear_all_obstacles()
        return {"status": "ok"}

    # ── Wind ────────────────────────────────────────────────

    @app.get("/api/wind")
    def get_wind():
        w = simulator.environment.wind
        return sanitize({
            "enabled": w.enabled,
            "base_velocity": w.base_velocity.tolist(),
            "gust_magnitude": w.gust_magnitude,
            "gust_frequency": w.gust_frequency,
        })

    @app.post("/api/wind")
    def set_wind(cfg: WindConfigModel):
        import numpy as _np
        w = simulator.environment.wind
        w.enabled = cfg.enabled
        w.base_velocity = _np.array(cfg.base_velocity, dtype=float)
        w.gust_magnitude = cfg.gust_magnitude
        w.gust_frequency = cfg.gust_frequency
        return {"status": "ok"}

    # ── Avoidance ────────────────────────────────────────────

    @app.get("/api/avoidance")
    def get_avoidance():
        hals = simulator.get_all_hals()
        if not hals:
            return {"enabled": False}
        hal = next(iter(hals.values()))
        ac = hal._drone.controller.avoidance.config
        return {
            "enabled": ac.enabled,
            "sensor_range": ac.sensor_range,
            "repulsion_gain": ac.repulsion_gain,
            "velocity_limit": ac.velocity_limit,
        }

    @app.post("/api/avoidance")
    def set_avoidance(cfg: AvoidanceConfigModel):
        hals = simulator.get_all_hals()
        for hal in hals.values():
            ac = hal._drone.controller.avoidance.config
            ac.enabled = cfg.enabled
            ac.sensor_range = cfg.sensor_range
            ac.repulsion_gain = cfg.repulsion_gain
            ac.velocity_limit = cfg.velocity_limit
        return {"status": "ok"}

    # ── WebSocket ────────────────────────────────────────────

    @app.websocket("/api/ws")
    async def websocket_endpoint(ws: WebSocket):
        await manager.connect(ws)
        try:
            while True:
                # Receive commands from client (non-blocking with timeout)
                try:
                    raw = await asyncio.wait_for(ws.receive_text(), timeout=ws_interval)
                    _handle_ws_command(raw)
                except asyncio.TimeoutError:
                    pass

                # Push current state
                state_frame = _build_state_frame()
                await ws.send_json(state_frame)

        except WebSocketDisconnect:
            manager.disconnect(ws)
        except Exception:
            manager.disconnect(ws)

    def _handle_ws_command(raw: str):
        """Process a JSON command received over WebSocket."""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        action = msg.get('action')
        if action == 'set_position':
            hal = simulator.get_hal(msg.get('drone_id', 0))
            if hal:
                hal.set_position(
                    msg.get('x', 0), msg.get('y', 0), msg.get('z', 0),
                    msg.get('yaw', 0),
                )
        elif action == 'set_velocity':
            hal = simulator.get_hal(msg.get('drone_id', 0))
            if hal:
                hal.set_velocity(
                    msg.get('vx', 0), msg.get('vy', 0), msg.get('vz', 0),
                    msg.get('yaw_rate', 0),
                )
        elif action == 'set_formation':
            simulator.set_formation(msg.get('type', 'line'))
        elif action == 'respawn':
            simulator.respawn_formation(
                msg.get('preset', 'line'), msg.get('num_drones')
            )
        elif action == 'pause':
            simulator.pause()
        elif action == 'resume':
            simulator.resume()
        elif action == 'arm':
            hal = simulator.get_hal(msg.get('drone_id', 0))
            if hal:
                hal.arm()
        elif action == 'disarm':
            hal = simulator.get_hal(msg.get('drone_id', 0))
            if hal:
                hal.disarm()
        elif action == 'takeoff':
            hal = simulator.get_hal(msg.get('drone_id', 0))
            if hal:
                hal.takeoff(msg.get('altitude', 10.0))
        elif action == 'land':
            hal = simulator.get_hal(msg.get('drone_id', 0))
            if hal:
                hal.land()
        elif action == 'enable_wind':
            simulator.environment.wind.enabled = True
        elif action == 'disable_wind':
            simulator.environment.wind.enabled = False
        elif action == 'set_wind':
            import numpy as _np
            w = simulator.environment.wind
            if 'base_velocity' in msg:
                w.base_velocity = _np.array(msg['base_velocity'], dtype=float)
            if 'gust_magnitude' in msg:
                w.gust_magnitude = msg['gust_magnitude']
            if 'gust_frequency' in msg:
                w.gust_frequency = msg['gust_frequency']
            if 'enabled' in msg:
                w.enabled = msg['enabled']

    def _build_state_frame() -> dict:
        """Build a JSON-safe state frame for WebSocket push."""
        states = simulator.get_drone_states()
        info = simulator.get_simulation_info()
        return sanitize({
            'type': 'state_update',
            'timestamp': time.time(),
            'sim_info': info,
            'drones': [serialize_drone_state(s) for s in states],
            'obstacles': info.get('obstacles', []),
        })

    return app
