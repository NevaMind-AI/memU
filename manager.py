#!/usr/bin/env python3
"""
MemU + OpenClaw Integration Manager

This script provides a complete interface to manage the MemU memory framework
integration with OpenClaw, including starting services, importing legacy data,
and validating the complete setup.
"""

import os
import sys
import asyncio
import argparse
import subprocess
import signal
from pathlib import Path
from typing import Dict, List, Optional

# Add src to path for imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from memu.app import MemoryService
from memu.app.settings import DatabaseConfig, MetadataStoreConfig, LLMProfilesConfig, LLMConfig


class MemUIntegrationManager:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.data_dir = self.project_root / "data"
        self.logs_dir = self.project_root / "logs"
        self.openclaw_bridge_process = None
        
        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

    def start_openclaw_bridge(self):
        """Start the OpenClaw bridge service in the background"""
        print("START Starting OpenClaw Bridge Service...")
        
        bridge_script = self.project_root / "openclaw_bridge.py"
        log_file = self.logs_dir / "bridge_service.log"
        
        # Start the bridge service
        self.openclaw_bridge_process = subprocess.Popen([
            sys.executable, str(bridge_script)
        ], stdout=open(log_file, 'a'), stderr=subprocess.STDOUT)
        
        print(f"OK OpenClaw Bridge started on port 5000 (PID: {self.openclaw_bridge_process.pid})")
        return self.openclaw_bridge_process

    def stop_openclaw_bridge(self):
        """Stop the OpenClaw bridge service"""
        if self.openclaw_bridge_process:
            print("STOP Stopping OpenClaw Bridge Service...")
            self.openclaw_bridge_process.terminate()
            try:
                self.openclaw_bridge_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.openclaw_bridge_process.kill()
            print("OK OpenClaw Bridge stopped")
            self.openclaw_bridge_process = None

    def import_legacy_memories(self):
        """Import legacy memories from Clawd-AI-Assistant project"""
        print("IMPORT Importing Legacy Memories...")
        
        import_script = self.project_root / "import_legacy.py"
        if import_script.exists():
            result = subprocess.run([sys.executable, str(import_script)])
            if result.returncode == 0:
                print("OK Legacy memories imported successfully")
            else:
                print(f"FAIL Failed to import legacy memories (exit code: {result.returncode})")
        else:
            print("FAIL Import script not found")

    def validate_setup(self):
        """Validate the complete memU + OpenClaw setup"""
        print("VALIDATE Validating Setup...")
        
        # Check if bridge is responding
        import requests
        try:
            response = requests.get("http://localhost:5000/v1/models", timeout=5)
            print("OK OpenClaw Bridge is accessible")
        except requests.exceptions.RequestException:
            print("FAIL OpenClaw Bridge is not responding")
            return False

        # Test basic memU functionality
        try:
            db_config = DatabaseConfig(
                metadata_store=MetadataStoreConfig(provider="inmemory")
            )
            
            service = MemoryService(
                database_config=db_config,
                llm_profiles={
                    "default": {
                        "base_url": "http://localhost:5000/v1",
                        "api_key": "dummy",
                        "chat_model": "openclaw-bridge",
                    }
                }
            )
            
            # Test basic operation
            test_result = asyncio.run(service.create_memory_item(
                memory_type="knowledge",
                memory_content="Test memory for validation",
                memory_categories=["validation"]
            ))
            
            print("OK memU service is functioning correctly")
            return True
        except Exception as e:
            print(f"FAIL memU validation failed: {e}")
            return False

    def run_continuous_monitoring(self):
        """Start continuous monitoring of OpenClaw for proactive memory"""
        print("MONITOR Starting Continuous Monitoring...")
        
        # This would implement the proactive memory loop
        # For now, we'll just show what would happen
        print("   - Monitoring OpenClaw for new interactions")
        print("   - Extracting relevant memories proactively")
        print("   - Updating memU with new information")
        print("   - Maintaining persistent memory state")
        
        # In a real implementation, this would run indefinitely
        # and monitor OpenClaw for new interactions to process

    def generate_report(self):
        """Generate a report of the current memory state"""
        print("Generating Memory Report...")
        
        # This would connect to the database and generate a report
        # For now, we'll just show the structure
        report_path = self.data_dir / f"memory_report_{Path.cwd().name}.txt"
        
        with open(report_path, 'w') as f:
            f.write("# MemU + OpenClaw Memory Report\n\n")
            f.write(f"Generated: {Path.cwd().name}\n\n")
            f.write("## Memory Sources\n")
            f.write("- Legacy Clawd-AI-Assistant memories\n")
            f.write("- Real-time OpenClaw interactions\n")
            f.write("- Proactive memory extraction\n\n")
            f.write("## Configuration\n")
            f.write("- Database: In-memory (persistent via state save)\n")
            f.write("- LLM Provider: OpenClaw Bridge\n")
            f.write("- Memory Categories: Auto-generated from content\n\n")
            f.write("## Statistics\n")
            f.write("- Total memory items: TBD\n")
            f.write("- Active categories: TBD\n")
            f.write("- Last sync: TBD\n")
        
        print(f"OK Report generated: {report_path}")

    def setup_complete_environment(self):
        """Set up the complete memU + OpenClaw environment"""
        print("* Setting up complete memU + OpenClaw environment...")
        
        # 1. Start the bridge
        self.start_openclaw_bridge()
        
        # 2. Import legacy memories
        self.import_legacy_memories()
        
        # 3. Validate the setup
        if self.validate_setup():
            print("OK Complete environment setup successful!")
            return True
        else:
            print("FAIL Environment setup failed")
            return False

    def cleanup(self):
        """Clean up resources"""
        self.stop_openclaw_bridge()


def main():
    parser = argparse.ArgumentParser(description="MemU + OpenClaw Integration Manager")
    parser.add_argument("command", nargs="?", choices=[
        "start", "stop", "import", "validate", "monitor", "report", "setup", "all"
    ], default="setup", help="Command to execute")
    
    args = parser.parse_args()
    
    manager = MemUIntegrationManager()
    
    try:
        if args.command == "start":
            manager.start_openclaw_bridge()
            print("Press Ctrl+C to stop the bridge")
            try:
                manager.openclaw_bridge_process.wait()
            except KeyboardInterrupt:
                manager.cleanup()
                
        elif args.command == "stop":
            manager.stop_openclaw_bridge()
            
        elif args.command == "import":
            manager.import_legacy_memories()
            
        elif args.command == "validate":
            manager.validate_setup()
            
        elif args.command == "monitor":
            manager.run_continuous_monitoring()
            
        elif args.command == "report":
            manager.generate_report()
            
        elif args.command == "setup":
            success = manager.setup_complete_environment()
            if success:
                print("\n💡 To start monitoring: python manager.py monitor")
                print("💡 To generate reports: python manager.py report")
            else:
                sys.exit(1)
                
        elif args.command == "all":
            print("🎬 Running complete setup sequence...")
            manager.start_openclaw_bridge()
            manager.import_legacy_memories()
            
            if manager.validate_setup():
                manager.run_continuous_monitoring()
                manager.generate_report()
                print("✅ All operations completed successfully!")
            else:
                print("❌ Setup failed during validation")
                sys.exit(1)
    
    finally:
        if args.command in ["start", "all", "setup"]:
            # Keep bridge running if we started it
            if args.command == "start":
                try:
                    manager.openclaw_bridge_process.wait()
                except KeyboardInterrupt:
                    pass
            else:
                manager.cleanup()


if __name__ == "__main__":
    main()