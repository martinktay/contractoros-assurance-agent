import os
import sys
import subprocess
import time
import signal

def main():
    print("==================================================")
    print("ContractorOS Assurance Agent - Local Launcher")
    print("==================================================")
    
    # 1. Verify python environment has dependencies
    print("\n[1/3] Starting backend server (FastAPI)...")
    backend_cmd = [
        "uv", "run", "uvicorn", "backend.main:app", 
        "--host", "127.0.0.1", 
        "--port", "8000", 
        "--reload"
    ]
    
    backend_process = subprocess.Popen(
        backend_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        shell=True
    )
    
    # 2. Wait for backend to be ready
    time.sleep(2)
    
    # 3. Start frontend dev server (Vite)
    print("\n[2/3] Starting frontend development server (Vite)...")
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
    
    frontend_process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        shell=True
    )
    
    print("\n[3/3] System is launching!")
    print("--------------------------------------------------")
    print("Backend API is running at: http://127.0.0.1:8000")
    print("Frontend UI is running at: http://localhost:3000")
    print("--------------------------------------------------")
    print("Press Ctrl+C to terminate both servers.")
    
    # Helper to print outputs in non-blocking way
    try:
        while True:
            # Check backend output
            backend_line = backend_process.stdout.readline()
            if backend_line:
                print(f"[Backend] {backend_line.strip()}")
                
            # Check frontend output
            frontend_line = frontend_process.stdout.readline()
            if frontend_line:
                print(f"[Frontend] {frontend_line.strip()}")
                
            # Sleep a bit to prevent 100% CPU loop
            time.sleep(0.1)
            
            # Check if either crashed
            if backend_process.poll() is not None:
                print("[Backend] Process exited. Terminating system...")
                break
            if frontend_process.poll() is not None:
                print("[Frontend] Process exited. Terminating system...")
                break
                
    except KeyboardInterrupt:
        print("\nStopping servers...")
    finally:
        # Kill both processes clean
        backend_process.terminate()
        frontend_process.terminate()
        try:
            backend_process.wait(timeout=3)
            frontend_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            backend_process.kill()
            frontend_process.kill()
        print("Servers stopped successfully. Goodbye!")

if __name__ == "__main__":
    main()
