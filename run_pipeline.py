#!/usr/bin/env python3
"""
Convenient pipeline runner with environment setup and health checks.
Provides a single-command entry point to run the full or selective phases.

Usage:
    python run_pipeline.py                    # Full pipeline (all phases)
    python run_pipeline.py --dataset /path    # Full pipeline with custom dataset
    python run_pipeline.py --phases ingestion,refinement  # Selective phases
    python run_pipeline.py --check            # Pre-flight health check
"""

import sys
import os
import logging
from pathlib import Path

# Add the project root to Python path so textgraphx package is importable
project_root = str(Path(__file__).parent / "textgraphx")
sys.path.insert(0, project_root)
sys.path.insert(0, str(Path(__file__).parent))

# Now import and run the canonical orchestrator
from textgraphx.orchestration.orchestrator import PipelineOrchestrator
from textgraphx.health_check import run_health_checks, print_health_check_report
from textgraphx.config import get_config
from textgraphx.neo4j_client import make_graph_from_config
import argparse
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
)

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(
        description="Run the TextGraphX pipeline with flexible phase selection"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(Path(__file__).resolve().parent / "datastore" / "dataset"),
        help="Path to dataset directory (default: datastore/dataset)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="en_core_web_sm",
        help="spaCy model name (default: en_core_web_sm)"
    )
    parser.add_argument(
        "--phases",
        type=str,
        default=None,
        help=(
            "Comma-separated phases to run (default: config-aware canonical order). "
            "Options: ingestion,refinement,temporal,event_enrichment,dbpedia_enrichment,tlinks"
        )
    )
    parser.add_argument(
        "--cleanup",
        type=str,
        choices=["auto", "none", "full"],
        default="auto",
        help=(
            "Neo4j cleanup policy before running phases: "
            "auto=clear existing dataset docs in testing mode, "
            "none=never clear, full=wipe all graph nodes first"
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run pre-flight health checks without executing pipeline"
    )
    
    args = parser.parse_args()
    
    # Resolve dataset path
    dataset_path = Path(args.dataset)
    
    # Run health checks if requested
    _cfg = get_config()
    _neo4j_uri = _cfg.neo4j.uri
    _neo4j_user = _cfg.neo4j.user
    _neo4j_password = _cfg.neo4j.password
    if args.check:
        all_passed, messages = run_health_checks(str(dataset_path), args.model, neo4j_uri=_neo4j_uri, neo4j_user=_neo4j_user, neo4j_password=_neo4j_password)
        print_health_check_report(all_passed, messages)
        sys.exit(0 if all_passed else 1)
    
    # Validate dataset path exists
    if not dataset_path.exists():
        print(f"\n❌ Error: Dataset directory not found")
        print(f"   Path: {dataset_path.resolve()}")
        print(f"   Hint: Use --dataset to specify a valid dataset directory")
        print(f"   Example: python run_pipeline.py --dataset textgraphx/datastore/dataset")
        print(f"\n💡 Run 'python run_pipeline.py --check' to diagnose issues.\n")
        sys.exit(1)
    
    # Run health checks before pipeline execution
    print("\n🔍 Running pre-flight checks...")
    all_passed, check_messages = run_health_checks(str(dataset_path), args.model, neo4j_uri=_neo4j_uri, neo4j_user=_neo4j_user, neo4j_password=_neo4j_password)
    
    if not all_passed:
        print_health_check_report(all_passed, check_messages)
        print("❌ Cannot proceed with pipeline execution. Please fix issues above.\n")
        sys.exit(1)
    
    # Initialize and run orchestrator
    try:
        orchestrator = PipelineOrchestrator(
            directory=str(dataset_path),
            model_name=args.model
        )
    except Exception as e:
        print(f"\n❌ Error initializing pipeline: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("🚀 TextGraphX Pipeline Runner")
    print("=" * 70)
    print(f"Start time:  {datetime.now().isoformat()}")
    print(f"Dataset:     {dataset_path.resolve()}")
    print(f"spaCy Model: {args.model}")
    print(f"Cleanup:     {args.cleanup}")
    print("=" * 70 + "\n")
    
    try:
        if args.phases:
            # Parse phases
            phases = [p.strip().lower() for p in args.phases.split(",")]
            print(f"Running selected phases: {', '.join(phases)}\n")
        else:
            phases = PipelineOrchestrator.default_phases(get_config())
            print("Running all phases in canonical order:\n")

        if args.cleanup == "full":
            graph = make_graph_from_config()
            try:
                rows = graph.run("MATCH (n) DETACH DELETE n RETURN count(n) AS count").data()
                cleared = int(rows[0].get("count", 0)) if rows else 0
            finally:
                close_fn = getattr(graph, "close", None)
                if callable(close_fn):
                    close_fn()
            print(f"🧹 Full graph cleanup removed {cleared} nodes before execution.\n")
            orchestrator.run_selected(phases)
        elif args.cleanup == "auto":
            prep = orchestrator.run_for_review(phases=phases)
            if prep.get("already_processed"):
                print(
                    "🧹 Auto cleanup detected existing dataset documents and cleared "
                    f"{prep.get('cleared_node_count', 0)} nodes (mode={prep.get('runtime_mode')}).\n"
                )
        else:
            orchestrator.run_selected(phases)
        
        # Print execution summary
        summary = orchestrator.summary
        print("\n" + "=" * 70)
        print("📊 Pipeline Summary")
        print("=" * 70)
        print(f"Phases:   {summary.success_count}/{summary.phase_count} completed")
        print(f"Failed:   {summary.failed_count}")
        print(f"Duration: {summary.total_duration:.1f}s")
        print(f"Docs:     {summary.total_documents}")
        print("=" * 70 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        if orchestrator.summary.success_count > 0:
            summary = orchestrator.summary
            print("\nPartial results:")
            print(
                f"Completed phases: {summary.success_count}/{summary.phase_count}; "
                f"failed: {summary.failed_count}; duration: {summary.total_duration:.1f}s"
            )
        sys.exit(130)
    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print(f"   Valid phases: ingestion, refinement, temporal, event_enrichment, tlinks\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during pipeline execution: {e}")
        import traceback
        traceback.print_exc()
        
        # Print partial results if any phases completed
        if orchestrator.summary.success_count > 0:
            summary = orchestrator.summary
            print("\nPartial results:")
            print(
                f"Completed phases: {summary.success_count}/{summary.phase_count}; "
                f"failed: {summary.failed_count}; duration: {summary.total_duration:.1f}s"
            )
        
        print(f"\n💡 For diagnostics, run: python run_pipeline.py --check\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
