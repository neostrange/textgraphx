#!/usr/bin/env python3
"""
Convenient pipeline runner with environment setup and health checks.
Provides a single-command entry point to run the full or selective phases.

Pipeline phase execution order keeps temporal extraction ahead of temporal link
recognition: TemporalPhase populates TIMEX and TEvent nodes before
TlinksRecognizer derives graph links between them.

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
from textgraphx.health_check import run_health_checks, print_health_check_report
from textgraphx.config import get_config
from textgraphx.neo4j_client import make_graph_from_config
from textgraphx.orchestration.orchestrator import PipelineOrchestrator
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
        default="en_core_web_trf",
        help="spaCy model name (default: en_core_web_trf)"
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
    parser.add_argument(
        "--preflight-safety",
        action="store_true",
        help="Print non-mutating safety posture (clear/block/fusion/gates) and exit",
    )
    
    args = parser.parse_args()

    def _parse_selected_phases(phases_arg):
        if phases_arg:
            return [p.strip().lower() for p in phases_arg.split(",") if p.strip()]
        return PipelineOrchestrator.default_phases(get_config())

    def _print_safety_posture(posture, phases):
        print("\n" + "=" * 70)
        print("Safety Preflight")
        print("=" * 70)
        print(f"Runtime mode:                  {posture.get('runtime_mode')}")
        print(f"Selected phases:               {', '.join(phases)}")
        print(f"Review preparation required:   {posture.get('review_preparation_required')}")
        print(f"Materialization gate required: {posture.get('materialization_gate_required')}")
        print(f"Strict transition gate:        {posture.get('strict_transition_gate')}")
        print(f"Cross-document fusion enabled: {posture.get('cross_document_fusion_enabled')}")
        print(f"Dataset files:                 {posture.get('dataset_file_count')}")
        print(f"Dataset identities:            {posture.get('dataset_identity_count')}")
        print(f"Existing AnnotatedText:        {posture.get('existing_document_count')}")
        print(f"Matched existing dataset docs: {posture.get('matched_existing_documents')}")
        print(f"Foreign docs present:          {posture.get('foreign_documents_present')}")
        print(f"Would clear graph:             {posture.get('would_clear_graph')}")
        print(f"Would block run:               {posture.get('would_block_run')}")
        print(f"Reason:                        {posture.get('reason')}")
        print("=" * 70 + "\n")

    
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

    if args.preflight_safety:
        phases = _parse_selected_phases(args.phases)
        try:
            posture = orchestrator.assess_review_run_safety(phases=phases)
        except Exception as e:
            print(f"\n❌ Error during safety preflight: {e}\n")
            sys.exit(1)
        _print_safety_posture(posture, phases)
        sys.exit(1 if posture.get("would_block_run") else 0)
    
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
            phases = _parse_selected_phases(args.phases)
            print(f"Running selected phases: {', '.join(phases)}\n")
        else:
            phases = _parse_selected_phases(None)
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
