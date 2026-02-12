"""
Proactive Memory Loop for MemU + OpenClaw Integration
Now with Event-Driven Architecture (Watchdog) for instant updates.
"""

import asyncio
import os
import sys
import time
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from memu.app import MemoryService
from config import SERVICE_CONFIG, PROACTIVE_SETTINGS

# Global event queue for async processing
fs_event_queue = asyncio.Queue()

class LogHandler(FileSystemEventHandler):
    """Watchdog handler that puts events into the async queue"""
    def on_modified(self, event):
        if not event.is_directory:
            fs_event_queue.put_nowait(event)

    def on_created(self, event):
        if not event.is_directory:
            fs_event_queue.put_nowait(event)

class ProactiveMemoryLoop:
    def __init__(self):
        self.service = MemoryService(**SERVICE_CONFIG)
        self.running = False
        self.data_dir = Path(__file__).parent / "data"
        self.state_file = self.data_dir / "proactive_state.json"
        self.data_dir.mkdir(exist_ok=True)
        self.last_processed = {} # Dedup limit

    async def process_file_event(self, event):
        """Process a file system event"""
        filepath = Path(event.src_path)
        
        # Debounce: skip if processed in last 2 seconds
        now = time.time()
        if filepath in self.last_processed:
            if now - self.last_processed[filepath] < 2:
                return
        self.last_processed[filepath] = now

        print(f"\n[EVENT] Detected change in: {filepath.name}")
        
        try:
            # Check file type
            if filepath.suffix not in ['.md', '.log', '.txt']:
                return

            # Wait a tiny bit for file write to complete
            await asyncio.sleep(0.5)

            content = ""
            try:
                content = filepath.read_text(encoding='utf-8', errors='ignore')
            except Exception as e:
                print(f"  [ERR] Retry read failed: {e}")
                return

            if not content.strip():
                return

            print(f"  [MEM] Memorizing content from {filepath.name}...")
            
            # Call MemU service
            # We treat it as a document update
            result = await self.service.memorize(
                resource_url=str(filepath),
                modality="document"
            )
            
            items = result.get('items', [])
            if items:
                print(f"  ✅ Extracted {len(items)} new memories!")
            else:
                print("  ⚠️ No new memories extracted.")
                
        except Exception as e:
            print(f"  ❌ Error processing file: {e}")

    async def run_continuous(self):
        """Run the event-driven loop"""
        print("[START] Starting Event-Driven Proactive Memory Loop...")
        print(f"   Mode: Watchdog (Real-time)")
        print(f"   Auto-commit: {PROACTIVE_SETTINGS['auto_commit_enabled']}")
        
        # Setup Watchdog Observers
        observer = Observer()
        handler = LogHandler()
        
        # Watch Diary
        diary_dir = Path(r"C:\Users\16663\Desktop\Clawd-AI-Assistant\diary")
        if diary_dir.exists():
            observer.schedule(handler, str(diary_dir), recursive=False)
            print(f"   👀 Watching: {diary_dir}")
            
        # Watch Logs
        logs_dir = Path(r"C:\Users\16663\Desktop\Clawd-AI-Assistant\logs")
        if logs_dir.exists():
            observer.schedule(handler, str(logs_dir), recursive=False)
            print(f"   👀 Watching: {logs_dir}")

        observer.start()
        self.running = True
        
        try:
            while self.running:
                # Process events from queue
                try:
                    event = await asyncio.wait_for(fs_event_queue.get(), timeout=1.0)
                    await self.process_file_event(event)
                    fs_event_queue.task_done()
                except asyncio.TimeoutError:
                    # No events, just heartbeat
                    pass
                except Exception as e:
                    print(f"Error in loop: {e}")
                
        except KeyboardInterrupt:
            print("\n[STOP] Stopping...")
        finally:
            observer.stop()
            observer.join()
            self.running = False

    def stop(self):
        self.running = False

async def main():
    loop = ProactiveMemoryLoop()
    print("[MEM] MemU + OpenClaw Proactive System (Event-Driven)")
    print("="*50)
    await loop.run_continuous()

if __name__ == "__main__":
    asyncio.run(main())