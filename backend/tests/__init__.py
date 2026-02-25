import sys
from pathlib import Path

# Add the parent directory (backend) to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))