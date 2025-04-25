import os
import sys
from pathlib import Path

def main():
    print(f"Python version: {sys.version}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Script directory: {Path(__file__).resolve().parent}")
    
    # Check downloaded directory paths
    relative_path = "../downloaded"
    absolute_path = Path(__file__).resolve().parent.parent / "downloaded"
    
    print(f"\nChecking paths:")
    print(f"Relative path '../downloaded': {relative_path}")
    print(f"Exists? {os.path.exists(relative_path)}")
    
    print(f"Absolute path: {absolute_path}")
    print(f"Exists? {os.path.exists(absolute_path)}")
    
    # Check files in the downloaded directory if it exists
    if os.path.exists(relative_path):
        print(f"\nFiles in relative path:")
        for file in os.listdir(relative_path):
            print(f"  - {file}")
    
    if os.path.exists(absolute_path):
        print(f"\nFiles in absolute path:")
        for file in os.listdir(absolute_path):
            print(f"  - {file}")

if __name__ == "__main__":
    main() 