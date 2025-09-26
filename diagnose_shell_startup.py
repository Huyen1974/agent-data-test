#!/usr/bin/env python3
"""
Shell Startup Diagnostic Script
Measures the execution time of different shell initialization components
"""

import time
import subprocess
import sys
from pathlib import Path

def measure_command_time(command, description):
    """Measure how long a command takes to execute"""
    print(f"⏱️  Measuring: {description}")
    start_time = time.time()

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        end_time = time.time()
        duration = end_time - start_time

        if result.returncode == 0:
            print(f"   ✅ {duration:.2f}s - {description}")
            return duration, True, result.stdout
        else:
            print(f"   ❌ {duration:.2f}s - {description} (failed)")
            return duration, False, result.stderr

    except subprocess.TimeoutExpired:
        print(f"   ⏰ TIMEOUT (>30s) - {description}")
        return 30.0, False, "Command timed out"
    except Exception as e:
        print(f"   💥 ERROR - {description}: {str(e)}")
        return 0.0, False, str(e)

def main():
    print("🔍 SHELL STARTUP DIAGNOSTIC")
    print("=" * 50)

    # Test individual components from ~/.zshrc
    tests = [
        # Basic PATH setup (should be fast)
        ('export PATH="/opt/homebrew/bin:$PATH"', "Homebrew PATH setup"),

        # Google Cloud SDK (potentially slow)
        ('[ -f "/Users/nmhuyen/google-cloud-sdk/path.zsh.inc" ] && source "/Users/nmhuyen/google-cloud-sdk/path.zsh.inc"', "Google Cloud SDK PATH"),

        # Pyenv (can be slow)
        ('export PYENV_ROOT="$HOME/.pyenv" && export PATH="$PYENV_ROOT/bin:$PATH"', "Pyenv PATH setup"),
        ('pyenv init -', "Pyenv initialization"),

        # Conda (can be slow)
        ('/Users/nmhuyen/miniconda/bin/conda shell.zsh hook', "Conda shell hook"),

        # Most problematic: Secret Manager calls
        ('gcloud secrets versions access latest --secret=openai-api-key-sg --project=github-chatgpt-ggcloud', "OpenAI API key from Secret Manager"),
        ('gcloud secrets versions access latest --secret=Qdrant_agent_data_N1D8R2vC0_5 --project=github-chatgpt-ggcloud', "Qdrant API key from Secret Manager"),
        ('gcloud secrets versions access latest --secret=Qdrant_cloud_management_key --project=github-chatgpt-ggcloud', "Management key from Secret Manager"),

        # SSH agent
        ('ssh-agent -s', "SSH agent initialization"),
    ]

    total_time = 0
    results = []

    for command, description in tests:
        duration, success, output = measure_command_time(f"zsh -c '{command} >/dev/null 2>&1'", description)
        total_time += duration
        results.append((description, duration, success))

    print("\n" + "=" * 50)
    print(f"📊 TOTAL ESTIMATED STARTUP TIME: {total_time:.2f}s")

    print("\n🚨 PROBLEMATIC COMPONENTS:")
    slow_components = [r for r in results if r[1] > 2.0]  # Components taking more than 2 seconds
    for desc, duration, success in slow_components:
        print(f"   ⚠️  {desc}: {duration:.2f}s {'✅' if success else '❌'}")

    if slow_components:
        print("\n💡 RECOMMENDATIONS:")
        print("1. Move Secret Manager calls to lazy-loaded functions")
        print("2. Cache API keys in local files")
        print("3. Use async initialization for non-critical components")
        print("4. Consider using gcloud auth application-default login instead")
    else:
        print("\n✅ All components are running within acceptable time limits")

if __name__ == "__main__":
    main()
