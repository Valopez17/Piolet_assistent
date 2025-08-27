CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS rag_chunks (
  id UUID PRIMARY KEY,
  doc_type TEXT NOT NULL,
  doc_id TEXT NOT NULL,
  title TEXT,
  url TEXT,
  locale TEXT,
  chunk_index INT NOT NULL,
  text TEXT NOT NULL,
  embedding vector(1536),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS rag_chunks_embedding_idx
  ON rag_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS rag_chunks_text_trgm_idx
  ON rag_chunks USING gin (text gin_trgm_ops); 