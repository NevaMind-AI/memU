import json
import asyncio
import logging
import re
import time
import uuid
from typing import Callable, Awaitable, Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class OneBotConfig:
    """Configuration for the OneBot (NapCat) adapter."""
    
    def __init__(
        self,
        ws_url: str,
        access_token: Optional[str] = None,
    ):
        self.ws_url = ws_url
        self.access_token = access_token


class OneBotAdapter:
    """Adapter for connecting to a OneBot v11 implementation (e.g., NapCat) via WebSocket."""
    
    def __init__(
        self,
        config: OneBotConfig,
        on_message: Optional[Callable[[Dict[str, Any], "OneBotAdapter"], Awaitable[None]]] = None
    ):
        self.config = config
        self.on_message = on_message
        
        self._ws = None
        self._self_id: Optional[int] = None
        self._is_alive = False
        
        self._reconnect_attempts = 0
        self._max_reconnect_delay = 60.0
        self._last_message_at = 0.0
        self._pending_messages: List[Dict[str, Any]] = []
        self._pending_requests: Dict[str, asyncio.Future] = {}

    def get_self_id(self) -> Optional[int]:
        """Get the connected bot's user ID."""
        return self._self_id

    def is_connected(self) -> bool:
        """Check if the WebSocket connection is currently active."""
        return self._is_alive and self._ws is not None

    async def connect(self):
        """Main loop for managing WebSocket connection and auto-reconnection."""
        import websockets
        kwargs = {}
        if self.config.access_token:
            kwargs["additional_headers"] = {"Authorization": f"Bearer {self.config.access_token}"}

        while True:
            try:
                logger.info(f"Connecting to OneBot server at {self.config.ws_url}...")
                
                # Disable underlying ping to fully simulate Node.js ws library behavior.
                async with websockets.connect(self.config.ws_url, ping_interval=None, **kwargs) as ws:
                    self._ws = ws
                    self._is_alive = True
                    self._reconnect_attempts = 0
                    self._last_message_at = time.time()
                    logger.info("Connected to OneBot server successfully.")

                    if self._pending_messages:
                        to_flush = self._pending_messages[:]
                        self._pending_messages.clear()
                        sent = 0
                        for item in to_flush:
                            try:
                                await self._ws.send(json.dumps(item))
                                sent += 1
                            except Exception:
                                pass
                        if sent > 0:
                            logger.info(f"Flushed {sent}/{len(to_flush)} queued outbound message(s).")

                    # Wrap get_login_info in try-except and delay to prevent initialization shock.
                    async def fetch_bot_info():
                        try:
                            await asyncio.sleep(1.0)
                            info = await self.get_login_info()
                            logger.info(f"Bot logged in successfully. Basic info: {info}")
                        except Exception as e:
                            logger.warning(f"Failed to fetch Bot account info: {e}")
                    
                    asyncio.create_task(fetch_bot_info())

                    # Start application layer heartbeat detection task.
                    heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                    try:
                        async for message in ws:
                            self._is_alive = True
                            self._last_message_at = time.time()
                            self._handle_raw_message(message)
                            
                        # Log specific disconnection status codes for easier troubleshooting.
                        logger.warning(f"WebSocket loop exited cleanly. Close code: {ws.close_code}, reason: {ws.close_reason}")
                        
                    except websockets.exceptions.ConnectionClosed as cc:
                        logger.warning(f"WebSocket connection closed by server: Code={cc.code}, Reason={cc.reason}")
                    finally:
                        heartbeat_task.cancel()

            except Exception as e:
                logger.error(f"WebSocket Error: {e}")

            # Execute cleanup and backoff reconnection logic.
            self._cleanup()
            delay = min(1.0 * (2 ** self._reconnect_attempts), self._max_reconnect_delay)
            logger.info(f"Reconnecting in {delay}s (Attempt {self._reconnect_attempts + 1})...")
            await asyncio.sleep(delay)
            self._reconnect_attempts += 1

    def _cleanup(self):
        """Clean up connection state and discard all pending Futures."""
        self._is_alive = False
        self._ws = None
        for future in self._pending_requests.values():
            if not future.done():
                future.set_exception(Exception("Connection closed"))
        self._pending_requests.clear()

    async def _heartbeat_loop(self):
        """Heartbeat checker: forcefully disconnect to trigger a reconnect if the connection goes idle."""
        while True:
            await asyncio.sleep(45)
            stale_ms = (time.time() - self._last_message_at) * 1000
            if stale_ms > 180000:  # No inbound traffic for over 3 minutes.
                logger.warning(f"No inbound traffic for {int(stale_ms/1000)}s, forcing reconnect...")
                if self._ws:
                    await self._ws.close()
                break

    def _handle_raw_message(self, message: str):
        """Parse and route inbound messages."""
        try:
            event = json.loads(message)
        except json.JSONDecodeError:
            return

        # Process API responses (Echo callback mechanism)
        if "echo" in event and event["echo"] in self._pending_requests:
            future = self._pending_requests.pop(event["echo"])
            if not future.done():
                if event.get("status") == "ok":
                    future.set_result(event.get("data"))
                else:
                    future.set_exception(Exception(event.get("msg", "API request failed")))
            return

        # Process heartbeat meta events
        if event.get("post_type") == "meta_event" and event.get("meta_event_type") == "heartbeat":
            return

        # Record the bot's own User ID upon receiving login info
        if event.get("status") == "ok" and "data" in event and "user_id" in event["data"]:
            self._self_id = event["data"]["user_id"]

        # Trigger business message hook
        if event.get("post_type") == "message":
            # Clean CQ codes to extract pure text for LLM embedding and processing
            clean_text = re.sub(r'\[CQ:.*?\]', '', event.get("raw_message", "")).strip()
            event['clean_text'] = clean_text
            if self.on_message:
                asyncio.create_task(self.on_message(event, self))

    # ================= API Implementations =================
    
    async def _send_with_response(self, action: str, params: Dict[str, Any], timeout_ms: int = 5000) -> Any:
        """Send an API request with an Echo identifier and await its Promise (Future) response."""
        if not self.is_connected():
            raise Exception("WebSocket not open")

        echo = str(uuid.uuid4())
        req = {"action": action, "params": params, "echo": echo}
        
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[echo] = future

        await self._ws.send(json.dumps(req))

        try:
            return await asyncio.wait_for(future, timeout=timeout_ms / 1000.0)
        except asyncio.TimeoutError:
            self._pending_requests.pop(echo, None)
            raise Exception(f"Request timeout for action: {action}")

    def _send_safe(self, action: str, params: Dict[str, Any]):
        """Safely send a request without awaiting its response. Queues the request if disconnected."""
        req = {"action": action, "params": params}
        if self.is_connected():
            asyncio.create_task(self._ws.send(json.dumps(req)))
        else:
            if len(self._pending_messages) < 200:
                self._pending_messages.append(req)

    async def get_login_info(self) -> Any:
        """Fetch the login information of the current bot."""
        return await self._send_with_response("get_login_info", {})

    def send_private_msg(self, user_id: int, message: str):
        """Send a private message silently (no ack)."""
        self._send_safe("send_private_msg", {"user_id": user_id, "message": message})

    async def send_private_msg_ack(self, user_id: int, message: str) -> Any:
        """Send a private message and wait for the acknowledgment."""
        return await self._send_with_response("send_private_msg", {"user_id": user_id, "message": message}, 15000)

    def send_group_msg(self, group_id: int, message: str):
        """Send a group message silently (no ack)."""
        self._send_safe("send_group_msg", {"group_id": group_id, "message": message})

    async def send_group_msg_ack(self, group_id: int, message: str) -> Any:
        """Send a group message and wait for the acknowledgment."""
        return await self._send_with_response("send_group_msg", {"group_id": group_id, "message": message}, 15000)