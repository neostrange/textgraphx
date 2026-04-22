-- Migration: create uniqueness constraint for token_id on NamedEntity
-- This is idempotent when using modern Neo4j that supports IF NOT EXISTS
CREATE CONSTRAINT IF NOT EXISTS FOR (n:NamedEntity) REQUIRE n.token_id IS UNIQUE;
