"""
Proactive Memory Loop for MemU + OpenClaw Integration

This script implements the continuous proactive memory loop that monitors
OpenClaw for new interactions and automatically extracts and stores memories.
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

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from memu.app import MemoryService
from config import SERVICE_CONFIG, OPENCLAW_SETTINGS, PROACTIVE_SETTINGS


class ProactiveMemoryLoop:
    def __init__(self):
        self.service = MemoryService(**SERVICE_CONFIG)
        self.scan_interval = PROACTIVE_SETTINGS["scan_interval_seconds"]
        self.last_scan_time = datetime.min
        self.running = False
        self.data_dir = Path(__file__).parent / "data"
        self.state_file = self.data_dir / "proactive_state.json"
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
        
        # Load previous state
        self.load_state()

    def load_state(self):
        """Load the previous state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.last_scan_time = datetime.fromisoformat(state.get('last_scan_time', datetime.min.isoformat()))
                print(f"Loaded previous state - Last scan: {self.last_scan_time}")
            except Exception as e:
                print(f"Could not load state file: {e}")
                self.last_scan_time = datetime.min
        else:
            print("Fresh start - no previous state found")

    def save_state(self):
        """Save the current state to file"""
        try:
            state = {
                'last_scan_time': self.last_scan_time.isoformat(),
                'timestamp': datetime.now().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Could not save state file: {e}")

    async def scan_openclaw_activity(self) -> List[Dict[str, Any]]:
        """Scan for recent OpenClaw activity that might contain memories to extract"""
        print("Scanning for new OpenClaw activity...")
        
        # In a real implementation, this would:
        # 1. Monitor OpenClaw logs
        # 2. Watch for new conversations/interactions
        # 3. Identify potentially memorable content
        
        # For now, we'll simulate by checking if there are any recent diary entries
        # from the Clawd-AI-Assistant project
        recent_memories = []
        
        # Look for recent diary entries
        diary_dir = Path(r"C:\Users\16663\Desktop\Clawd-AI-Assistant\diary")
        if diary_dir.exists():
            for diary_file in diary_dir.glob("*.md"):
                mod_time = datetime.fromtimestamp(diary_file.stat().st_mtime)
                if mod_time > self.last_scan_time:
                    print(f"  Found updated diary: {diary_file.name}")
                    
                    # Read the content and look for memorable information
                    try:
                        content = diary_file.read_text(encoding='utf-8')
                        
                        # Extract potential memories (this is simplified)
                        # In reality, you'd use more sophisticated NLP
                        if len(content) > 100:  # Only if substantial content
                            recent_memories.append({
                                'source': str(diary_file),
                                'content': content[:500] + "..." if len(content) > 500 else content,
                                'timestamp': mod_time.isoformat(),
                                'type': 'diary_entry'
                            })
                    except Exception as e:
                        print(f"  Could not read {diary_file}: {e}")
        
        # Also check for log files that might contain new interactions
        logs_dir = Path(r"C:\Users\16663\Desktop\Clawd-AI-Assistant\logs")
        if logs_dir.exists():
            for log_file in logs_dir.glob("*.log"):
                mod_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mod_time > self.last_scan_time:
                    print(f"  Found updated log: {log_file.name}")
                    
                    try:
                        content = log_file.read_text(encoding='utf-8')
                        # Find the last few lines that might contain new activity
                        lines = content.split('\n')[-10:]  # Last 10 lines
                        recent_content = '\n'.join(lines).strip()
                        
                        if recent_content and len(recent_content) > 50:
                            recent_memories.append({
                                'source': str(log_file),
                                'content': recent_content,
                                'timestamp': mod_time.isoformat(),
                                'type': 'log_entry'
                            })
                    except Exception as e:
                        print(f"  Could not read {log_file}: {e}")
        
        print(f"  Found {len(recent_memories)} potential memory sources")
        return recent_memories

    async def extract_memories(self, activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract specific memories from the detected activities"""
        print("Extracting memories from detected activities...")
        
        extracted_memories = []
        
        for activity in activities:
            try:
                print(f"  Processing {activity['type']} from {activity['source']}")
                
                # Use the memorize function to extract structured memories
                result = await self.service.memorize(
                    resource_url=activity['source'],
                    modality="document"  # Treating all sources as documents for now
                )
                
                # Add metadata about the source
                for item in result.get('items', []):
                    item['source_metadata'] = {
                        'original_source': activity['source'],
                        'detected_at': activity['timestamp'],
                        'activity_type': activity['type']
                    }
                    extracted_memories.append(item)
                
                print(f"    Extracted {len(result.get('items', []))} memories")
                
            except Exception as e:
                print(f"  Error extracting memories from {activity['source']}: {e}")
        
        print(f"  Total extracted: {len(extracted_memories)} memories")
        return extracted_memories

    async def consolidate_memories(self):
        """Consolidate and organize memories (periodic maintenance)"""
        print("Consolidating memories...")
        
        # This would involve:
        # 1. Identifying duplicate or related memories
        # 2. Merging similar items
        # 3. Creating higher-level abstractions
        # 4. Pruning old or irrelevant memories
        
        # For now, we'll just print a summary
        try:
            # Get a sample of recent memories to show the consolidation concept
            recent_query = await self.service.retrieve(
                queries=[{"role": "user", "content": "recent memories"}]
            )
            
            total_items = len(recent_query.get('items', []))
            total_categories = len(recent_query.get('categories', []))
            
            print(f"  Current state: {total_items} items in {total_categories} categories")
            
            # In a real system, we would perform actual consolidation here
            print("  Memory consolidation completed")
            
        except Exception as e:
            print(f"  Error during consolidation: {e}")

    async def run_single_iteration(self):
        """Run one iteration of the proactive memory loop"""
        print(f"Starting proactive memory iteration at {datetime.now()}")
        
        try:
            # 1. Scan for new activity
            new_activities = await self.scan_openclaw_activity()
            
            if new_activities:
                # 2. Extract memories from new activity
                extracted = await self.extract_memories(new_activities)
                
                if extracted:
                    print(f"  Successfully extracted {len(extracted)} new memories!")
                    
                    # Update the last scan time to now
                    self.last_scan_time = datetime.now()
                else:
                    print("  Activities found but no specific memories extracted")
            else:
                print("  No new activity detected since last scan")
            
            # 3. Perform periodic consolidation (daily)
            if datetime.now() - self.last_scan_time > timedelta(days=1):
                await self.consolidate_memories()
                self.last_scan_time = datetime.now()  # Update after consolidation
            
            # 4. Save state
            self.save_state()
            
            print(f"Iteration completed at {datetime.now()}")
            
        except Exception as e:
            print(f"Error in proactive memory iteration: {e}")
            import traceback
            traceback.print_exc()

    async def run_continuous(self):
        """Run the proactive memory loop continuously"""
        print("Starting continuous proactive memory loop...")
        print(f"   Scan interval: {self.scan_interval} seconds")
        print(f"   Auto-commit: {PROACTIVE_SETTINGS['auto_commit_enabled']}")
        print(f"   Memory retention: {PROACTIVE_SETTINGS['memory_retention_days']} days")

        self.running = True
        
        try:
            while self.running:
                await self.run_single_iteration()
                
                print(f"   Sleeping for {self.scan_interval} seconds...")
                await asyncio.sleep(self.scan_interval)
                
        except KeyboardInterrupt:
            print("\nReceived interrupt signal")
        finally:
            self.running = False
            print("Proactive memory loop stopped")

    def stop(self):
        """Stop the continuous loop"""
        self.running = False


async def main():
    """Main function to run the proactive memory loop"""
    loop = ProactiveMemoryLoop()
    
    print("MemU + OpenClaw Proactive Memory System")
    print("="*50)
    
    # Run one iteration for testing
    print("Running one test iteration...")
    await loop.run_single_iteration()
    
    # Ask user if they want to run continuously
    response = input("\nWould you like to run continuously? (y/n): ")
    if response.lower().startswith('y'):
        print("\nStarting continuous mode. Press Ctrl+C to stop.")
        await loop.run_continuous()
    else:
        print("One-time scan completed. Exiting.")


if __name__ == "__main__":
    asyncio.run(main())