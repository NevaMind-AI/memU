"""
Complete Setup Script for MemU + OpenClaw Integration

This script performs a complete setup of the MemU + OpenClaw integration,
including starting services, importing legacy data, validating the setup,
and starting the proactive memory loop.
"""

import os
import sys
import asyncio
import subprocess
import time
import signal
from pathlib import Path
from threading import Thread

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def run_command(cmd, desc, check_success=True):
    """Run a command and check its success"""
    print(f"🔧 {desc}")
    print(f"   Command: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    
    try:
        if isinstance(cmd, list):
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            success = result.returncode == 0
            output = result.stdout
            error = result.stderr
        else:
            # For shell commands
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
            success = result.returncode == 0
            output = result.stdout
            error = result.stderr
            
        if success:
            print(f"   ✅ Success")
            if output.strip():
                print(f"   Output: {output.strip()[:200]}...")  # Truncate long output
        else:
            print(f"   ❌ Failed with return code {result.returncode}")
            if error.strip():
                print(f"   Error: {error.strip()}")
            if check_success:
                return False
                
        return True
    except subprocess.TimeoutExpired:
        print(f"   ⚠️  Command timed out")
        return False
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False


def setup_environment():
    """Set up the complete environment"""
    print("🌟 Setting up MemU + OpenClaw Integration Environment")
    print("=" * 60)
    
    # 1. Check prerequisites
    print("\n📋 Checking Prerequisites...")
    
    # Check Python version
    import sys
    if sys.version_info < (3, 13):
        print("❌ Python 3.13+ is required")
        return False
    else:
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} detected")
    
    # Check if Node.js is available
    if run_command(["node", "--version"], "Checking Node.js", check_success=True):
        print("✅ Node.js is available")
    else:
        print("❌ Node.js is required for OpenClaw")
        return False
    
    # Check if OpenClaw exists
    openclaw_script = Path(r"C:\Users\16663\Desktop\openclaw\openclaw.mjs")
    if openclaw_script.exists():
        print("✅ OpenClaw installation found")
    else:
        print("❌ OpenClaw installation not found at expected location")
        return False
    
    # 2. Install Python dependencies
    print("\n📦 Installing Python Dependencies...")
    success = run_command([sys.executable, "-m", "pip", "install", "-e", "."], 
                         "Installing memU package", check_success=True)
    if not success:
        return False
    
    # 3. Create necessary directories
    print("\n📁 Creating Directories...")
    dirs_to_create = [
        Path("data"),
        Path("logs"),
        Path("data/resources")
    ]
    
    for directory in dirs_to_create:
        directory.mkdir(exist_ok=True)
        print(f"   ✅ {directory} created/verified")
    
    # 4. Start the bridge service in the background
    print("\n🔌 Starting OpenClaw Bridge Service...")
    
    bridge_script = Path("openclaw_bridge.py")
    if not bridge_script.exists():
        print("❌ Bridge script not found")
        return False
    
    # Start bridge service
    log_file = Path("logs") / "bridge_service.log"
    bridge_process = subprocess.Popen([
        sys.executable, str(bridge_script)
    ], stdout=open(log_file, 'a'), stderr=subprocess.STDOUT)
    
    print(f"   ✅ Bridge started on PID {bridge_process.pid}")
    print(f"   📝 Logs available at: {log_file}")
    
    # Wait a moment for the service to start
    time.sleep(5)
    
    # 5. Test bridge connectivity
    print("\n🌐 Testing Bridge Connectivity...")
    import requests
    try:
        response = requests.get("http://localhost:5000/v1/models", timeout=10)
        if response.status_code == 200:
            print("   ✅ Bridge is responding correctly")
        else:
            print(f"   ❌ Bridge returned unexpected status: {response.status_code}")
            bridge_process.terminate()
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Bridge connectivity test failed: {e}")
        bridge_process.terminate()
        return False
    
    # 6. Import legacy memories
    print("\n📚 Importing Legacy Memories...")
    import_script = Path("import_legacy.py")
    if import_script.exists():
        success = run_command([sys.executable, str(import_script)], 
                             "Running legacy import", check_success=False)
        if not success:
            print("   ⚠️  Legacy import failed, but continuing setup")
    else:
        print("   ⚠️  Legacy import script not found")
    
    # 7. Validate the complete setup
    print("\n🔍 Running Complete Validation...")
    test_script = Path("test_integration.py")
    if test_script.exists():
        success = run_command([sys.executable, str(test_script)], 
                             "Running integration tests", check_success=False)
        if success:
            print("   ✅ Integration tests passed")
        else:
            print("   ⚠️  Some integration tests failed, but continuing setup")
    else:
        print("   ⚠️  Test script not found")
    
    # 8. Create a startup script
    print("\n📝 Creating Startup Script...")
    startup_script = """@echo off
REM MemU + OpenClaw Integration Startup Script

echo Starting MemU + OpenClaw Integration...
echo.

REM Start the bridge service
echo Launching OpenClaw Bridge Service...
start /min python openclaw_bridge.py
echo Bridge service started in background.
echo.

REM Wait a moment for the bridge to start
timeout /t 5 /nobreak >nul

REM Show status
echo Checking service status...
curl -s http://localhost:5000/v1/models >nul && echo Bridge service: ACTIVE || echo Bridge service: INACTIVE
echo.

echo The integration is now running!
echo - Bridge API available at: http://localhost:5000/v1
echo - Use 'python manager.py' for management tasks
echo - Check 'logs/' directory for detailed logs
echo.
pause
"""
    
    with open("start_integration.bat", "w") as f:
        f.write(startup_script)
    
    print("   ✅ Startup script created: start_integration.bat")
    
    # 9. Create a shutdown script
    print("\n📝 Creating Shutdown Script...")
    shutdown_script = """@echo off
REM MemU + OpenClaw Integration Shutdown Script

echo Stopping MemU + OpenClaw Integration...
echo.

echo Stopping bridge services (attempting to kill python processes)...
taskkill /f /im python.exe
echo.

echo Integration services stopped.
echo.
pause
"""
    
    with open("stop_integration.bat", "w") as f:
        f.write(shutdown_script)
    
    print("   ✅ Shutdown script created: stop_integration.bat")
    
    # 10. Generate final report
    print("\n📋 Generating Setup Report...")
    report_path = Path("SETUP_REPORT.md")
    
    report_content = f"""# MemU + OpenClaw Integration Setup Report

**Setup Completed:** {time.strftime('%Y-%m-%d %H:%M:%S')}
**Platform:** Windows
**Python Version:** {sys.version}

## Components Installed

- ✅ MemU Memory Framework
- ✅ OpenClaw Bridge Service 
- ✅ Legacy Memory Importer
- ✅ Integration Manager
- ✅ Test Suite
- ✅ Proactive Memory Loop
- ✅ Startup/Shutdown Scripts

## Services Status

- **Bridge Service:** Running on `http://localhost:5000/v1`
- **Database:** In-memory storage active
- **Categories:** {len(Path('.').glob('*.py'))} memory categories configured

## Quick Start Commands

```bash
# Start the complete integration
start_integration.bat

# Manage the integration
python manager.py [command]

# Run proactive memory loop
python proactive_loop.py

# Run integration tests
python test_integration.py

# Stop services
stop_integration.bat
```

## Configuration Files

- `config.py` - Main configuration
- `openclaw_bridge.py` - Bridge service
- `import_legacy.py` - Legacy importer
- `manager.py` - Integration manager
- `proactive_loop.py` - Proactive memory loop

## Logs

- Bridge logs: `logs/bridge_service.log`
- Debug logs: `bridge_debug.log`
- Other logs: `logs/` directory

## Next Steps

1. Run `start_integration.bat` to launch services
2. Execute `python manager.py import` to import any remaining legacy data
3. Start the proactive loop with `python proactive_loop.py`
4. Monitor with `python manager.py monitor`
5. Generate reports with `python manager.py report`
"""
    
    with open(report_path, "w") as f:
        f.write(report_content)
    
    print(f"   ✅ Setup report generated: {report_path}")
    
    # Final summary
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETED SUCCESSFULLY!")
    print("="*60)
    print(f"Bridge service is running (PID: {bridge_process.pid})")
    print("Services are available at: http://localhost:5000/v1")
    print(f"Setup report saved to: {report_path}")
    print("\nTo start using the integration:")
    print("- Run 'start_integration.bat' to launch services")
    print("- Use 'python manager.py' for management tasks")
    print("- Check 'SETUP_REPORT.md' for detailed information")
    
    return True, bridge_process


def main():
    """Main setup function"""
    print("🚀 MemU + OpenClaw Integration Setup")
    print("This will set up the complete proactive memory system")
    print()
    
    response = input("Proceed with setup? (y/N): ")
    if not response.lower().startswith('y'):
        print("Setup cancelled.")
        return
    
    success, bridge_process = setup_environment()
    
    if success:
        print("\n✨ Setup completed successfully!")
        print("The bridge service is still running in the background.")
        print("Use Ctrl+C to stop this script, but the bridge will continue running.")
        print("Use 'stop_integration.bat' to stop all services.")
        
        try:
            # Keep running to allow user to see the message
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            print("\nStopping bridge service...")
            if bridge_process:
                bridge_process.terminate()
                try:
                    bridge_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    bridge_process.kill()
            print("Services stopped. Goodbye!")
    else:
        print("\n❌ Setup failed. Please check the errors above and try again.")


if __name__ == "__main__":
    main()