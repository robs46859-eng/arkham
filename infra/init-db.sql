-- Robco DB initialization
-- Runs once on first Postgres container startup.
-- Enables pgvector for semantic cache and memory vector lookups.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
