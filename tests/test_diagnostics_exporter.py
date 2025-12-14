"""
Tests for diagnostics exporter.
"""

import pytest
import json
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from observability.diagnostics_exporter import DiagnosticsExporter


class TestDiagnosticsExporter:
    """Test diagnostics exporter."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories."""
        with TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            yield {
                'output_dir': base / 'output',
                'logs_dir': base / 'logs',
                'config_dir': base / 'config',
                'db_dir': base / 'db'
            }

    @pytest.fixture
    def exporter(self, temp_dirs):
        """Create exporter."""
        for dir_path in temp_dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)

        return DiagnosticsExporter(
            output_dir=temp_dirs['output_dir'],
            logs_dir=temp_dirs['logs_dir'],
            config_dir=temp_dirs['config_dir'],
            db_dir=temp_dirs['db_dir']
        )

    def test_export_bundle(self, exporter, temp_dirs):
        """Test creating diagnostic bundle."""
        # Create some test files
        log_file = temp_dirs['logs_dir'] / 'app.log'
        log_file.write_text("Test log entry\n")

        config_file = temp_dirs['config_dir'] / 'config.json'
        config_file.write_text(json.dumps({'key': 'value'}))

        # Export bundle
        bundle_path = exporter.export_bundle(
            execution_engine_stats={'total_executions': 10},
            scheduler_stats={'total_jobs': 5},
            recent_errors=['Error 1', 'Error 2']
        )

        assert bundle_path.exists()
        assert bundle_path.suffix == '.zip'

        # Verify bundle contents
        with zipfile.ZipFile(bundle_path, 'r') as zipf:
            files = zipf.namelist()
            assert 'system_info.json' in files
            assert 'app_metadata.json' in files
            assert 'system_metrics.json' in files
            assert 'logs/app.log' in files
            assert 'config/config.json' in files
            assert 'MANIFEST.json' in files

            # Check metadata
            metadata = json.loads(zipf.read('app_metadata.json'))
            assert metadata['execution_engine']['total_executions'] == 10
            assert metadata['scheduler']['total_jobs'] == 5
            assert len(metadata['recent_errors']) == 2

    def test_sanitize_config(self, exporter):
        """Test config sanitization."""
        config = {
            'database': 'sqlite.db',
            'api_key': 'secret123',
            'password': 'pass123',
            'nested': {
                'token': 'secret_token'
            }
        }

        sanitized = exporter._sanitize_config(config)

        assert sanitized['database'] == 'sqlite.db'
        assert sanitized['api_key'] == '***REDACTED***'
        assert sanitized['password'] == '***REDACTED***'
        assert sanitized['nested']['token'] == '***REDACTED***'

    def test_list_bundles(self, exporter):
        """Test listing bundles."""
        # Create bundles
        bundle1 = exporter.export_bundle()
        bundle2 = exporter.export_bundle()

        bundles = exporter.list_bundles()

        assert len(bundles) >= 2
        assert all('filename' in b for b in bundles)
        assert all('size_mb' in b for b in bundles)
        assert all('created_at' in b for b in bundles)

    def test_delete_bundle(self, exporter):
        """Test deleting bundle."""
        bundle = exporter.export_bundle()
        filename = bundle.name

        # Delete
        success = exporter.delete_bundle(filename)
        assert success is True
        assert not bundle.exists()

        # Try delete again
        success = exporter.delete_bundle(filename)
        assert success is False

    def test_cleanup_old_bundles(self, exporter):
        """Test cleanup of old bundles."""
        # Create multiple bundles
        for _ in range(15):
            exporter.export_bundle()

        # Cleanup, keep only 5
        exporter.cleanup_old_bundles(keep_count=5)

        bundles = exporter.list_bundles()
        assert len(bundles) == 5
