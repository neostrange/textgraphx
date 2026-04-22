-- 0020_add_uid_constraints_for_mentions.cypher
--
-- Enforce stable UID identity for mention-layer nodes.
-- Idempotent for Neo4j 4.x+ via IF NOT EXISTS.

CREATE CONSTRAINT unique_namedentity_uid IF NOT EXISTS
FOR (n:NamedEntity) REQUIRE n.uid IS UNIQUE;

CREATE CONSTRAINT unique_entitymention_uid IF NOT EXISTS
FOR (m:EntityMention) REQUIRE m.uid IS UNIQUE;

CREATE INDEX namedentity_uid IF NOT EXISTS
FOR (n:NamedEntity) ON (n.uid);

CREATE INDEX entitymention_uid IF NOT EXISTS
FOR (m:EntityMention) ON (m.uid);

RETURN "UID constraints and indexes added for NamedEntity and EntityMention.";
