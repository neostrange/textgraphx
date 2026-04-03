#!/usr/bin/env python3
"""
Convenient pipeline runner with environment setup.
Provides a single-command entry point to run the full or selective phases.

Usage:
    python run_pipeline.py                    # Full pipeline (all phases)
    python run_pipeline.py --dataset /path    # Full pipeline with custom dataset
    python run_pipeline.py --phases ingestion,refinement  # Selective phases
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path so textgraphx package is importable
project_root = str(Path(__file__).parent / "textgraphx")
sys.path.insert(0, project_root)
sys.path.insert(0, str(Path(__file__).parent))

# Now import and run orchestrator
from textgraphx.PipelineOrchestrator import PipelineOrchestrator
import argparse
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(
        description="Run the TextGraphX pipeline with flexible phase selection"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="textgraphx/datastore/dataset",
        help="Path to dataset directory (default: textgraphx/datastore/dataset)"
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
        help="Comma-separated phases to run (default: all). Options: ingestion,refinement,temporal,event_enrichment,tlinks"
    )
    
    args = parser.parse_args()
    
    # Validate dataset path
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"Error: Dataset directory '{args.dataset}' does not exist")
        sys.exit(1)
    
    # Initialize and run orchestrator
    orchestrator = PipelineOrchestrator(
        directory=str(dataset_path),
        model_name=args.model
    )
    
    print("=" * 70)
    print(f"TextGraphX Pipeline Runner")
    print(f"Start time: {datetime.now().isoformat()}")
    print(f"Dataset: {dataset_path.resolve()}")
    print(f"spaCy Model: {args.model}")
    print("=" * 70)
    
    try:
        if args.phases:
            # Parse phases
            phases = [p.strip().lower() for p in args.phases.split(",")]
            print(f"Running selected phases: {', '.join(phases)}")
            orchestrator.run_selected(phases)
        else:
            print("Running all phases in canonical order")
            orchestrator.run_selected([
                "ingestion",
                "refinement", 
                "temporal",
                "event_enrichment",
                "tlinks"
            ])
        
        print("=" * 70)
        print(f"Pipeline completed successfully")
        print(f"End time: {datetime.now().isoformat()}")
        print("=" * 70)
        
    except Exception as e:
        print(f"Error during pipeline execution: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
