-- 0022_add_coref_uid_constraints.cypher
--
-- Enforce stable UID identity for coreference-layer nodes.
-- Prerequisite: migration 0021 must have been applied so all
-- Antecedent and CorefMention nodes carry a non-NULL uid.
-- Idempotent for Neo4j 4.x+ via IF NOT EXISTS.

CREATE CONSTRAINT unique_antecedent_uid IF NOT EXISTS
FOR (n:Antecedent) REQUIRE n.uid IS UNIQUE;

CREATE CONSTRAINT unique_corefmention_uid IF NOT EXISTS
FOR (n:CorefMention) REQUIRE n.uid IS UNIQUE;

CREATE INDEX antecedent_uid IF NOT EXISTS
FOR (n:Antecedent) ON (n.uid);

CREATE INDEX corefmention_uid IF NOT EXISTS
FOR (n:CorefMention) ON (n.uid);

RETURN "UID constraints and indexes added for Antecedent and CorefMention.";
