"""
CLI Runner Module

Command-line interface for running pipelines with rich output formatting.
Provides user-friendly CLI with progress bars, colored output, and interactive modes.

Author: Scraper Platform Team
"""

import logging
import sys
import argparse
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class CLIRunner:
    """
    CLI runner for executing scraping pipelines from command line.

    Features:
    - Rich console output with colors
    - Progress bars for long-running operations
    - Interactive configuration prompts
    - Output formatting (JSON, table, CSV)
    """

    def __init__(self, verbose: bool = False):
        """
        Initialize CLI runner.

        Args:
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        self._setup_logging()
        logger.info("Initialized CLIRunner")

    def _setup_logging(self) -> None:
        """Setup logging configuration for CLI."""
        log_level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )

    def run_pipeline(
        self,
        config_path: str,
        source: Optional[str] = None,
        output_format: str = "json",
        dry_run: bool = False,
        **kwargs
    ) -> int:
        """
        Run a pipeline from the command line.

        Args:
            config_path: Path to pipeline configuration file
            source: Source name (e.g., 'alfabeta', 'lafa')
            output_format: Output format (json, table, csv)
            dry_run: Perform dry run without actual execution
            **kwargs: Additional pipeline parameters

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            self._print_header()
            self._print_info(f"Loading configuration from: {config_path}")

            # Load configuration
            config = self._load_config(config_path)

            if dry_run:
                self._print_warning("DRY RUN MODE - No actual execution")
                self._print_config(config)
                return 0

            # Import pipeline runner
            from ..entrypoints.run_pipeline import run_pipeline

            # Execute pipeline
            self._print_info(f"Starting pipeline execution for source: {source or 'default'}")
            start_time = datetime.now()

            result = run_pipeline(
                config=config,
                source=source,
                **kwargs
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Display results
            self._print_success(f"Pipeline completed in {duration:.2f}s")
            self._display_results(result, output_format)

            return 0

        except FileNotFoundError as e:
            self._print_error(f"Configuration file not found: {e}")
            return 1
        except Exception as e:
            self._print_error(f"Pipeline execution failed: {e}")
            if self.verbose:
                logger.exception("Full stack trace:")
            return 1

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load pipeline configuration from file."""
        path = Path(config_path)

        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        # Load YAML or JSON config
        if path.suffix in ['.yaml', '.yml']:
            import yaml
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
        elif path.suffix == '.json':
            with open(path, 'r') as f:
                config = json.load(f)
        else:
            raise ValueError(f"Unsupported config format: {path.suffix}")

        logger.debug(f"Loaded config: {config}")
        return config

    def _display_results(self, result: Dict[str, Any], output_format: str) -> None:
        """Display pipeline results in specified format."""
        if output_format == "json":
            self._display_json(result)
        elif output_format == "table":
            self._display_table(result)
        elif output_format == "csv":
            self._display_csv(result)
        else:
            self._print_warning(f"Unknown output format: {output_format}, using JSON")
            self._display_json(result)

    def _display_json(self, result: Dict[str, Any]) -> None:
        """Display results as formatted JSON."""
        print("\n" + "=" * 60)
        print("RESULTS (JSON):")
        print("=" * 60)
        print(json.dumps(result, indent=2))

    def _display_table(self, result: Dict[str, Any]) -> None:
        """Display results as ASCII table."""
        print("\n" + "=" * 60)
        print("RESULTS (TABLE):")
        print("=" * 60)

        # Simple table display
        if isinstance(result, dict):
            for key, value in result.items():
                print(f"{key:30} | {str(value)[:40]}")
        else:
            print(str(result))

    def _display_csv(self, result: Dict[str, Any]) -> None:
        """Display results as CSV."""
        print("\n" + "=" * 60)
        print("RESULTS (CSV):")
        print("=" * 60)

        if isinstance(result, dict):
            # Header
            print(",".join(result.keys()))
            # Values
            print(",".join(str(v) for v in result.values()))
        else:
            print(str(result))

    def _print_header(self) -> None:
        """Print CLI header."""
        header = """
╔══════════════════════════════════════════════════════════════╗
║                 SCRAPER PLATFORM CLI                         ║
║                  Enterprise Web Scraping                     ║
╚══════════════════════════════════════════════════════════════╝
        """
        print(header)

    def _print_info(self, message: str) -> None:
        """Print info message."""
        print(f"ℹ️  {message}")

    def _print_success(self, message: str) -> None:
        """Print success message."""
        print(f"✅ {message}")

    def _print_warning(self, message: str) -> None:
        """Print warning message."""
        print(f"⚠️  {message}")

    def _print_error(self, message: str) -> None:
        """Print error message."""
        print(f"❌ {message}", file=sys.stderr)

    def _print_config(self, config: Dict[str, Any]) -> None:
        """Print configuration in readable format."""
        print("\n" + "=" * 60)
        print("CONFIGURATION:")
        print("=" * 60)
        print(json.dumps(config, indent=2))
        print("=" * 60)


def create_parser() -> argparse.ArgumentParser:
    """
    Create argument parser for CLI.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Scraper Platform - Enterprise Web Scraping CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a pipeline with default config
  python -m src.entrypoints.cli_runner --config config/sources/alfabeta.yaml

  # Run with specific source
  python -m src.entrypoints.cli_runner --config config.yaml --source alfabeta

  # Dry run to validate config
  python -m src.entrypoints.cli_runner --config config.yaml --dry-run

  # Output as table
  python -m src.entrypoints.cli_runner --config config.yaml --format table
        """
    )

    parser.add_argument(
        '--config',
        '-c',
        required=True,
        help='Path to pipeline configuration file (YAML or JSON)'
    )

    parser.add_argument(
        '--source',
        '-s',
        help='Source name (e.g., alfabeta, lafa, quebec)'
    )

    parser.add_argument(
        '--format',
        '-f',
        choices=['json', 'table', 'csv'],
        default='json',
        help='Output format (default: json)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform dry run without actual execution'
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--output',
        '-o',
        help='Output file path (defaults to stdout)'
    )

    return parser


def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for CLI.

    Args:
        args: Command line arguments (defaults to sys.argv)

    Returns:
        Exit code
    """
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    # Create and run CLI runner
    runner = CLIRunner(verbose=parsed_args.verbose)

    return runner.run_pipeline(
        config_path=parsed_args.config,
        source=parsed_args.source,
        output_format=parsed_args.format,
        dry_run=parsed_args.dry_run
    )


if __name__ == "__main__":
    sys.exit(main())
