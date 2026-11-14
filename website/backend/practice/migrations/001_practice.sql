CREATE TABLE IF NOT EXISTS practice_classrooms (
 id uuid PRIMARY KEY, name text NOT NULL
);
CREATE TABLE IF NOT EXISTS practice_students (
 id uuid PRIMARY KEY, display_name varchar(60) NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS practice_memberships (
 student_id uuid REFERENCES practice_students ON DELETE CASCADE,
 classroom_id uuid REFERENCES practice_classrooms, PRIMARY KEY(student_id, classroom_id)
);
CREATE TABLE IF NOT EXISTS practice_exercises (
 version text NOT NULL, id text NOT NULL, definition jsonb NOT NULL, PRIMARY KEY(version,id)
);
CREATE TABLE IF NOT EXISTS practice_sessions (
 id uuid PRIMARY KEY, student_id uuid NOT NULL REFERENCES practice_students ON DELETE CASCADE,
 classroom_id uuid NOT NULL REFERENCES practice_classrooms, token_digest text NOT NULL UNIQUE,
 bank_version text NOT NULL, next_seq bigint NOT NULL DEFAULT 1,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS practice_progress (
 session_id uuid REFERENCES practice_sessions ON DELETE CASCADE, exercise_id text NOT NULL,
 answer text NOT NULL DEFAULT '', work text NOT NULL DEFAULT '', revision integer NOT NULL DEFAULT 0,
 completed boolean NOT NULL DEFAULT false, hint_level integer NOT NULL DEFAULT 0,
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp(), PRIMARY KEY(session_id,exercise_id)
);
CREATE TABLE IF NOT EXISTS practice_submissions (
 id uuid PRIMARY KEY, session_id uuid NOT NULL REFERENCES practice_sessions ON DELETE CASCADE,
 exercise_id text NOT NULL, request_key text NOT NULL, kind text NOT NULL CHECK(kind IN ('check','hint')),
 input jsonb NOT NULL, result jsonb, hint_level integer, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(session_id,request_key)
);
CREATE TABLE IF NOT EXISTS practice_feedback (
 submission_id uuid PRIMARY KEY REFERENCES practice_submissions ON DELETE CASCADE,
 content jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS practice_hints (
 submission_id uuid PRIMARY KEY REFERENCES practice_submissions ON DELETE CASCADE,
 level integer NOT NULL CHECK(level BETWEEN 1 AND 3), content jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS practice_events (
 session_id uuid REFERENCES practice_sessions ON DELETE CASCADE, seq bigint NOT NULL,
 at timestamptz NOT NULL DEFAULT clock_timestamp(), kind text NOT NULL, exercise_id text,
 payload jsonb NOT NULL, PRIMARY KEY(session_id,seq)
);
CREATE INDEX IF NOT EXISTS practice_submissions_history ON practice_submissions(session_id,exercise_id,created_at);

ALTER TABLE practice_sessions ADD COLUMN IF NOT EXISTS selected_exercise text NOT NULL DEFAULT 'num-01';

CREATE TABLE IF NOT EXISTS practice_budgets (
 kind text NOT NULL, bucket timestamptz NOT NULL, used integer NOT NULL,
 PRIMARY KEY(kind,bucket)
);
