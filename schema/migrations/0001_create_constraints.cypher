-- 0001_create_constraints.cypher
-- Create uniqueness constraints and useful indexes for core node types.
-- This script is idempotent when executed in Neo4j 4.x+ using the IF NOT EXISTS forms.

CREATE CONSTRAINT unique_frame_id IF NOT EXISTS
FOR (f:Frame) REQUIRE f.id IS UNIQUE;

CREATE CONSTRAINT unique_framearg_id IF NOT EXISTS
FOR (a:FrameArgument) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT unique_namedentity_id IF NOT EXISTS
FOR (n:NamedEntity) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT unique_tagocc_id IF NOT EXISTS
FOR (t:TagOccurrence) REQUIRE t.id IS UNIQUE;

CREATE CONSTRAINT unique_annotatedtext_id IF NOT EXISTS
FOR (d:AnnotatedText) REQUIRE d.id IS UNIQUE;

CREATE INDEX IF NOT EXISTS FOR (t:TagOccurrence) ON (t.tok_index_doc);
CREATE INDEX IF NOT EXISTS FOR (n:NamedEntity) ON (n.kb_id);
