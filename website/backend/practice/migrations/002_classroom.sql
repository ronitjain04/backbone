ALTER TABLE practice_progress ADD COLUMN outcome text;
ALTER TABLE practice_progress ADD COLUMN completed_at timestamptz;
UPDATE practice_progress SET outcome='historical_unclassified' WHERE completed;
CREATE TABLE practice_assistance (
 session_id uuid REFERENCES practice_sessions ON DELETE CASCADE, exercise_id text NOT NULL,
 source_key text NOT NULL, kind text NOT NULL, at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(session_id,source_key)
);
CREATE INDEX practice_assistance_exercise ON practice_assistance(session_id,exercise_id,at);
CREATE TABLE practice_visuals (
 session_id uuid REFERENCES practice_sessions ON DELETE CASCADE, exercise_id text NOT NULL,
 stage integer NOT NULL, address_bits integer NOT NULL, bits_per_location integer NOT NULL,
 PRIMARY KEY(session_id,exercise_id)
);
CREATE TABLE practice_interactions (
 session_id uuid REFERENCES practice_sessions ON DELETE CASCADE, request_key text NOT NULL,
 input jsonb NOT NULL, result jsonb NOT NULL, PRIMARY KEY(session_id,request_key)
);
CREATE TABLE practice_presence (
 session_id uuid REFERENCES practice_sessions ON DELETE CASCADE, tab_id uuid NOT NULL,
 sequence bigint NOT NULL, connected boolean NOT NULL, seen_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(session_id,tab_id)
);
