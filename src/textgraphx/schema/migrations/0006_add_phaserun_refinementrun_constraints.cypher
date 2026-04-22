-- 0006_add_phaserun_refinementrun_constraints.cypher
--
-- Add uniqueness constraints for pipeline bookkeeping nodes.
-- These ensure phase and refinement run markers are deduplicated
-- even if phases are executed multiple times concurrently.
--
-- Idempotent: IF NOT EXISTS forms are safe to re-run.

CREATE CONSTRAINT unique_phaserun_id IF NOT EXISTS
FOR (n:PhaseRun) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT unique_refinementrun_id IF NOT EXISTS
FOR (n:RefinementRun) REQUIRE n.id IS UNIQUE;
