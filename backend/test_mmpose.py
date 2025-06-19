# test_mmpose.py
import os
import subprocess

def test_mmpose():
    print("Testing MMPose setup...")
    print(f"Current directory: {os.getcwd()}")
    
    # Check if files exist
    demo_file = "ml_pipeline/demo/topdown_demo_mmdet_no_heatmap.py"
    print(f"Demo file exists: {os.path.exists(demo_file)}")
    
    # Try a simple Python command
    try:
        result = subprocess.run(
            ["python", "-c", "import torch; print(f'PyTorch version: {torch.__version__}, CUDA available: {torch.cuda.is_available()}')"],
            capture_output=True,
            text=True
        )
        print(f"Result: {result.stdout}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_mmpose()