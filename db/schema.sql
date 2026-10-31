-- DubsiBhai PostgreSQL 17 schema. Generated from SQLAlchemy metadata.
-- Fresh EMPTY database only: psql -v ON_ERROR_STOP=1 -f db/schema.sql
-- Existing databases: use uv run alembic upgrade head instead.
-- Run app.workers.bootstrap after import to seed roads and an optional mayor.
-- All *_at columns are UTC Unix seconds, except password_history.retired_at (microseconds).
-- UUID-shaped IDs remain varchar(36) for compatibility with existing auth migrations.
-- No plaintext passwords, NID numbers, image bytes, or point balance caches.
BEGIN;
CREATE TABLE areas (
	id VARCHAR(36) NOT NULL,
	name VARCHAR(100) NOT NULL,
	ward VARCHAR(30),
	PRIMARY KEY (id),
	UNIQUE (name)
);

CREATE TABLE complaint_categories (
	code VARCHAR(40) NOT NULL,
	label VARCHAR(100) NOT NULL,
	base_priority INTEGER NOT NULL,
	PRIMARY KEY (code),
	CONSTRAINT ck_category_priority CHECK (base_priority BETWEEN 0 AND 100)
);

CREATE TABLE outbox_events (
	id VARCHAR(36) NOT NULL,
	event_type VARCHAR(80) NOT NULL,
	aggregate_id VARCHAR(36) NOT NULL,
	payload JSON NOT NULL,
	created_at BIGINT NOT NULL,
	delivered_at BIGINT,
	PRIMARY KEY (id)
);

CREATE INDEX ix_outbox_pending ON outbox_events (delivered_at, created_at);

CREATE TABLE users (
	id VARCHAR(36) NOT NULL,
	email VARCHAR(320) NOT NULL,
	name VARCHAR(100) NOT NULL,
	phone VARCHAR(16),
	date_of_birth DATE,
	blood_group VARCHAR(3),
	password_hash VARCHAR(255),
	email_verified BOOLEAN NOT NULL,
	is_active BOOLEAN NOT NULL,
	role VARCHAR(32) NOT NULL,
	created_at BIGINT NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_user_role CHECK (role IN ('citizen','worker','admin')),
	CONSTRAINT ck_blood_group CHECK (blood_group IS NULL OR blood_group IN ('A+','A-','B+','B-','AB+','AB-','O+','O-')),
	UNIQUE (email),
	UNIQUE (phone)
);

CREATE TABLE auth_action_tokens (
	token_hash VARCHAR(64) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	purpose VARCHAR(32) NOT NULL,
	expires_at BIGINT NOT NULL,
	PRIMARY KEY (token_hash),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_auth_action_tokens_expires_at ON auth_action_tokens (expires_at);

CREATE INDEX ix_auth_action_tokens_user_id ON auth_action_tokens (user_id);

CREATE TABLE auth_identities (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	provider VARCHAR(32) NOT NULL,
	subject VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (provider, subject),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_auth_identities_user_id ON auth_identities (user_id);

CREATE TABLE auth_sessions (
	id VARCHAR(36) NOT NULL,
	token_hash VARCHAR(64) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	created_at BIGINT NOT NULL,
	last_seen_at BIGINT NOT NULL,
	expires_at BIGINT NOT NULL,
	revoked BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (token_hash),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_auth_sessions_expires_at ON auth_sessions (expires_at);

CREATE INDEX ix_auth_sessions_user_id ON auth_sessions (user_id);

CREATE TABLE password_history (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	password_hash VARCHAR(255) NOT NULL,
	retired_at BIGINT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_password_history_user_id ON password_history (user_id);

CREATE TABLE roads (
	id VARCHAR(36) NOT NULL,
	area_id VARCHAR(36) NOT NULL,
	name VARCHAR(150) NOT NULL,
	latitude FLOAT NOT NULL,
	longitude FLOAT NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_road_area_name UNIQUE (area_id, name),
	CONSTRAINT ck_road_coordinates CHECK (latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180),
	FOREIGN KEY(area_id) REFERENCES areas (id)
);

CREATE INDEX ix_roads_area_id ON roads (area_id);

CREATE TABLE worker_applications (
	user_id VARCHAR(36) NOT NULL,
	nid_digest VARCHAR(64),
	nid_image_url VARCHAR(2048),
	status VARCHAR(20) NOT NULL,
	submitted_at BIGINT NOT NULL,
	reviewed_at BIGINT,
	reviewed_by VARCHAR(36),
	review_note VARCHAR(1000),
	PRIMARY KEY (user_id),
	CONSTRAINT ck_application_status CHECK (status IN ('pending','approved','rejected')),
	CONSTRAINT ck_application_identity CHECK (nid_digest IS NOT NULL OR nid_image_url IS NOT NULL),
	FOREIGN KEY(user_id) REFERENCES users (id),
	UNIQUE (nid_digest),
	FOREIGN KEY(reviewed_by) REFERENCES users (id)
);

CREATE INDEX ix_worker_review_queue ON worker_applications (status, submitted_at);

CREATE TABLE worker_locations (
	user_id VARCHAR(36) NOT NULL,
	latitude FLOAT NOT NULL,
	longitude FLOAT NOT NULL,
	updated_at BIGINT NOT NULL,
	available BOOLEAN NOT NULL,
	PRIMARY KEY (user_id),
	CONSTRAINT ck_worker_coordinates CHECK (latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180),
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE complaints (
	id VARCHAR(36) NOT NULL,
	author_id VARCHAR(36) NOT NULL,
	incident_id VARCHAR(36),
	road_id VARCHAR(36),
	category_code VARCHAR(40) NOT NULL,
	kind VARCHAR(20) NOT NULL,
	title VARCHAR(180) NOT NULL,
	description TEXT NOT NULL,
	address VARCHAR(300) NOT NULL,
	latitude FLOAT NOT NULL,
	longitude FLOAT NOT NULL,
	condition VARCHAR(10) NOT NULL,
	status VARCHAR(30) NOT NULL,
	created_at BIGINT NOT NULL,
	updated_at BIGINT NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_complaint_kind CHECK (kind IN ('complaint','road_update')),
	CONSTRAINT ck_road_condition CHECK (condition IN ('bad','good','unknown')),
	CONSTRAINT ck_complaint_status CHECK (status IN ('open','assigned','awaiting_confirmation','resolved','disputed','false')),
	CONSTRAINT ck_complaint_coordinates CHECK (latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180),
	CONSTRAINT ck_complaint_incident CHECK (incident_id IS NULL OR (kind = 'complaint' AND incident_id <> id)),
	FOREIGN KEY(author_id) REFERENCES users (id),
	FOREIGN KEY(incident_id) REFERENCES complaints (id),
	FOREIGN KEY(road_id) REFERENCES roads (id),
	FOREIGN KEY(category_code) REFERENCES complaint_categories (code)
);

CREATE INDEX ix_complaints_author_time ON complaints (author_id, created_at);

CREATE INDEX ix_complaints_created ON complaints (created_at);

CREATE INDEX ix_complaints_incident ON complaints (incident_id);

CREATE INDEX ix_complaints_queue ON complaints (status, category_code, created_at);

CREATE INDEX ix_complaints_road_time ON complaints (road_id, created_at);

CREATE INDEX ix_incident_candidates ON complaints (category_code, updated_at) WHERE kind = 'complaint' AND incident_id IS NULL;

CREATE TABLE assignments (
	id VARCHAR(36) NOT NULL,
	complaint_id VARCHAR(36) NOT NULL,
	worker_id VARCHAR(36) NOT NULL,
	assigned_by VARCHAR(36),
	source VARCHAR(10) NOT NULL,
	status VARCHAR(15) NOT NULL,
	created_at BIGINT NOT NULL,
	completed_at BIGINT,
	PRIMARY KEY (id),
	CONSTRAINT ck_assignment_status CHECK (status IN ('active','completed','cancelled')),
	CONSTRAINT ck_assignment_source CHECK (source IN ('admin','system')),
	FOREIGN KEY(complaint_id) REFERENCES complaints (id),
	FOREIGN KEY(worker_id) REFERENCES users (id),
	FOREIGN KEY(assigned_by) REFERENCES users (id)
);

CREATE INDEX ix_assignments_complaint_id ON assignments (complaint_id);

CREATE INDEX ix_assignments_worker_status ON assignments (worker_id, status, created_at);

CREATE UNIQUE INDEX uq_assignment_active ON assignments (complaint_id) WHERE status = 'active';

CREATE TABLE complaint_false_reports (
	complaint_id VARCHAR(36) NOT NULL,
	worker_id VARCHAR(36) NOT NULL,
	image_url VARCHAR(2048) NOT NULL,
	comment VARCHAR(1000) NOT NULL,
	created_at BIGINT NOT NULL,
	PRIMARY KEY (complaint_id, worker_id),
	FOREIGN KEY(complaint_id) REFERENCES complaints (id),
	FOREIGN KEY(worker_id) REFERENCES users (id)
);

CREATE TABLE complaint_images (
	id VARCHAR(36) NOT NULL,
	complaint_id VARCHAR(36) NOT NULL,
	url VARCHAR(2048) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(complaint_id) REFERENCES complaints (id) ON DELETE CASCADE
);

CREATE INDEX ix_complaint_images_complaint_id ON complaint_images (complaint_id);

CREATE TABLE complaint_predictions (
	complaint_id VARCHAR(36) NOT NULL,
	status VARCHAR(10) NOT NULL,
	predicted_category VARCHAR(40),
	confidence FLOAT,
	model_version VARCHAR(100),
	attempts INTEGER NOT NULL,
	next_attempt_at BIGINT NOT NULL,
	classified_at BIGINT,
	PRIMARY KEY (complaint_id),
	CONSTRAINT ck_prediction_status CHECK (status IN ('pending','ready')),
	CONSTRAINT ck_prediction_confidence CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
	FOREIGN KEY(complaint_id) REFERENCES complaints (id),
	FOREIGN KEY(predicted_category) REFERENCES complaint_categories (code)
);

CREATE INDEX ix_prediction_retry ON complaint_predictions (status, next_attempt_at);

CREATE TABLE complaint_votes (
	complaint_id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	value INTEGER NOT NULL,
	created_at BIGINT NOT NULL,
	PRIMARY KEY (complaint_id, user_id),
	CONSTRAINT ck_complaint_vote CHECK (value IN (-1,1)),
	FOREIGN KEY(complaint_id) REFERENCES complaints (id) ON DELETE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE resolutions (
	id VARCHAR(36) NOT NULL,
	assignment_id VARCHAR(36) NOT NULL,
	complaint_id VARCHAR(36) NOT NULL,
	worker_id VARCHAR(36) NOT NULL,
	comment VARCHAR(2000) NOT NULL,
	image_url VARCHAR(2048),
	status VARCHAR(15) NOT NULL,
	created_at BIGINT NOT NULL,
	confirmed_at BIGINT,
	PRIMARY KEY (id),
	CONSTRAINT ck_resolution_status CHECK (status IN ('pending','confirmed','disputed')),
	UNIQUE (assignment_id),
	FOREIGN KEY(assignment_id) REFERENCES assignments (id),
	FOREIGN KEY(complaint_id) REFERENCES complaints (id),
	FOREIGN KEY(worker_id) REFERENCES users (id)
);

CREATE INDEX ix_resolutions_complaint ON resolutions (complaint_id, created_at);

CREATE INDEX ix_resolutions_worker_id ON resolutions (worker_id);

CREATE TABLE moderation_cases (
	id VARCHAR(36) NOT NULL,
	subject_user_id VARCHAR(36) NOT NULL,
	complaint_id VARCHAR(36) NOT NULL,
	resolution_id VARCHAR(36),
	source_key VARCHAR(100) NOT NULL,
	kind VARCHAR(30) NOT NULL,
	status VARCHAR(15) NOT NULL,
	created_at BIGINT NOT NULL,
	reviewed_by VARCHAR(36),
	reviewed_at BIGINT,
	note VARCHAR(1000),
	PRIMARY KEY (id),
	CONSTRAINT ck_moderation_kind CHECK (kind IN ('false_complaint','worker_dispute')),
	CONSTRAINT ck_moderation_status CHECK (status IN ('open','dismissed','actioned')),
	FOREIGN KEY(subject_user_id) REFERENCES users (id),
	FOREIGN KEY(complaint_id) REFERENCES complaints (id),
	FOREIGN KEY(resolution_id) REFERENCES resolutions (id),
	UNIQUE (source_key),
	FOREIGN KEY(reviewed_by) REFERENCES users (id)
);

CREATE INDEX ix_moderation_cases_subject_user_id ON moderation_cases (subject_user_id);

CREATE INDEX ix_moderation_queue ON moderation_cases (status, created_at);

CREATE TABLE point_entries (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	delta INTEGER NOT NULL,
	reason VARCHAR(40) NOT NULL,
	source_key VARCHAR(120) NOT NULL,
	complaint_id VARCHAR(36),
	resolution_id VARCHAR(36),
	created_at BIGINT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id),
	UNIQUE (source_key),
	FOREIGN KEY(complaint_id) REFERENCES complaints (id),
	FOREIGN KEY(resolution_id) REFERENCES resolutions (id)
);

CREATE INDEX ix_point_entries_account ON point_entries (user_id, created_at);

CREATE TABLE resolution_votes (
	resolution_id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	value INTEGER NOT NULL,
	image_url VARCHAR(2048),
	comment VARCHAR(1000),
	created_at BIGINT NOT NULL,
	PRIMARY KEY (resolution_id, user_id),
	CONSTRAINT ck_resolution_vote CHECK (value IN (-1,1)),
	CONSTRAINT ck_dislike_evidence CHECK (value = 1 OR image_url IS NOT NULL),
	FOREIGN KEY(resolution_id) REFERENCES resolutions (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE EXTENSION IF NOT EXISTS cube;
CREATE EXTENSION IF NOT EXISTS earthdistance;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX ix_complaints_geo ON complaints USING gist (ll_to_earth(latitude, longitude));
CREATE INDEX ix_roads_geo ON roads USING gist (ll_to_earth(latitude, longitude));
CREATE INDEX ix_worker_locations_geo ON worker_locations USING gist (ll_to_earth(latitude, longitude));
CREATE INDEX ix_complaints_search ON complaints USING gin ((title || ' ' || description || ' ' || address) gin_trgm_ops);
CREATE INDEX ix_users_name_search ON users USING gin (name gin_trgm_ops);
CREATE INDEX ix_complaints_open ON complaints (created_at DESC) WHERE status IN ('open','assigned','disputed');
CREATE INDEX ix_users_role_active ON users (role, is_active);
CREATE INDEX ix_password_history_recent ON password_history (user_id, retired_at DESC);
ALTER TABLE complaints CLUSTER ON ix_complaints_road_time;
INSERT INTO complaint_categories (code, label, base_priority) VALUES
('blocked_drain', 'Blocked drain', 75),
('open_manhole', 'Open manhole', 95),
('road_flooding', 'Road flooding', 85),
('waterlogging_recurring', 'Recurring waterlogging', 70),
('sewage_overflow', 'Sewage overflow', 90),
('waste_cleaning', 'Waste cleaning', 55),
('road_damage', 'Road damage', 65),
('other', 'Other civic issue', 40);
CREATE TABLE alembic_version (version_num varchar(32) PRIMARY KEY);
INSERT INTO alembic_version VALUES ('20261031_05');
COMMIT;
