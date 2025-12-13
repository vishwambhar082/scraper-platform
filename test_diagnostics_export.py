#!/usr/bin/env python
"""
Quick test script for the diagnostics exporter.

Usage:
    python test_diagnostics_export.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.devtools.diagnostics_exporter import DiagnosticsExporter


def test_json_export():
    """Test JSON export."""
    print("Testing JSON export...")
    exporter = DiagnosticsExporter(
        output_path=Path("test_diagnostics.json"),
        format="json",
    )

    output_file = exporter.export()
    print(f"✓ JSON export successful: {output_file}")
    print(f"  Size: {output_file.stat().st_size / 1024:.2f} KB")


def test_html_export():
    """Test HTML export."""
    print("\nTesting HTML export...")
    exporter = DiagnosticsExporter(
        output_path=Path("test_diagnostics.html"),
        format="html",
    )

    output_file = exporter.export()
    print(f"✓ HTML export successful: {output_file}")
    print(f"  Size: {output_file.stat().st_size / 1024:.2f} KB")


def test_zip_export():
    """Test ZIP export."""
    print("\nTesting ZIP export...")
    exporter = DiagnosticsExporter(
        output_path=Path("test_diagnostics.zip"),
        format="zip",
    )

    output_file = exporter.export()
    print(f"✓ ZIP export successful: {output_file}")
    print(f"  Size: {output_file.stat().st_size / 1024:.2f} KB")


def test_collection():
    """Test data collection."""
    print("\nTesting data collection...")
    exporter = DiagnosticsExporter()

    print("  Collecting system info...")
    sys_info = exporter._collect_system_info()
    print(f"    ✓ OS: {sys_info.get('os', {}).get('system')}")
    print(f"    ✓ Python: {sys_info.get('python', {}).get('version')}")
    print(f"    ✓ CPU cores: {sys_info.get('cpu', {}).get('logical_cores')}")

    print("  Collecting platform info...")
    platform_info = exporter._collect_platform_info()
    print(f"    ✓ Working directory: {platform_info.get('working_directory')}")

    print("  Collecting database info...")
    db_info = exporter._collect_database_info()
    print(f"    ✓ DB enabled: {db_info.get('enabled')}")
    print(f"    ✓ Schema version: {db_info.get('schema_version')}")

    print("  Collecting run history...")
    runs = exporter._collect_run_history()
    print(f"    ✓ Total runs: {runs.get('total_runs', 0)}")

    print("  Collecting logs...")
    logs = exporter._collect_logs()
    print(f"    ✓ Total log lines: {logs.get('total_lines', 0)}")
    print(f"    ✓ Error count: {logs.get('error_count', 0)}")

    print("  Collecting environment...")
    env = exporter._collect_environment()
    print(f"    ✓ Total env vars: {env.get('count', 0)}")
    print(f"    ✓ Redacted: {env.get('redacted_count', 0)}")

    print("  Collecting packages...")
    packages = exporter._collect_installed_packages()
    print(f"    ✓ Total packages: {packages.get('total_count', 0)}")

    print("  Collecting performance metrics...")
    perf = exporter._collect_performance_metrics()
    print(f"    ✓ CPU: {perf.get('current_cpu_percent')}%")
    print(f"    ✓ Memory: {perf.get('current_memory_percent')}%")

    print("\n✓ All collection tests passed!")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Diagnostics Exporter Test Suite")
    print("=" * 60)

    try:
        # Test data collection
        test_collection()

        # Test exports
        test_json_export()
        test_html_export()
        test_zip_export()

        print("\n" + "=" * 60)
        print("All tests passed successfully!")
        print("=" * 60)

        print("\nGenerated test files:")
        print("  - test_diagnostics.json")
        print("  - test_diagnostics.html")
        print("  - test_diagnostics.zip")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
