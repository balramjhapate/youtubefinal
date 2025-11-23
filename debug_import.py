
import sys
import os
import traceback

# Add local neutts_air_lib to path
current_dir = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.join(current_dir, 'downloader', 'neutts_air_lib')
sys.path.append(lib_path)

print(f"Added to sys.path: {lib_path}")

try:
    from neuttsair.neutts import NeuTTSAir
    print("Successfully imported NeuTTSAir")
except ImportError:
    print("Failed to import NeuTTSAir")
    traceback.print_exc()
except Exception:
    print("An unexpected error occurred during import")
    traceback.print_exc()
