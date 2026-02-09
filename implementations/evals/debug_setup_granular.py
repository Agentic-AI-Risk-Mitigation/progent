
print("Step 0: Start", flush=True)
import sys
print("Step 1: sys imported", flush=True)
import os
print("Step 2: os imported", flush=True)

# Test third party
try:
    print("Step 3: Importing pydantic...", flush=True)
    import pydantic
    print("Step 3: pydantic imported", flush=True)
except ImportError:
    print("Step 3: pydantic missing", flush=True)

try:
    print("Step 4: Importing openai...", flush=True)
    import openai
    print("Step 4: openai imported", flush=True)
except ImportError:
    print("Step 4: openai missing", flush=True)

try:
    print("Step 5: Importing langchain_core...", flush=True)
    import langchain_core
    print("Step 5: langchain_core imported", flush=True)
except ImportError:
    print("Step 5: langchain_core missing", flush=True)

try:
    print("Step 6: Importing langchain_openai...", flush=True)
    import langchain_openai
    print("Step 6: langchain_openai imported", flush=True)
except ImportError:
    print("Step 6: langchain_openai missing", flush=True)

print("Done", flush=True)
