-- CVForge — final database schema
-- Generated from the live SQLAlchemy models (app/models.py) + applied dev DB.
-- Default engine: SQLite (DATABASE_URL=sqlite:///./cvforge.db).
-- A MySQL-compatible variant follows below for DATABASE_URL=mysql+pymysql://...

-- =====================================================================
-- SQLite (default)
-- =====================================================================

CREATE TABLE users (
	id INTEGER NOT NULL,
	email VARCHAR(255) NOT NULL,
	hashed_password VARCHAR(255) NOT NULL,
	full_name VARCHAR(255) NOT NULL DEFAULT '',
	credits INTEGER NOT NULL DEFAULT 0,
	plan VARCHAR(50) NOT NULL DEFAULT 'free',
	polar_customer_id VARCHAR(255),
	is_admin BOOLEAN NOT NULL DEFAULT 0,
	monthly_refill_at DATETIME,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE base_cvs (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	data JSON NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE applications (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	job_title VARCHAR(255) NOT NULL DEFAULT '',
	company VARCHAR(255) NOT NULL DEFAULT '',
	job_description TEXT NOT NULL,
	tailored_cv JSON NOT NULL,
	cover_letter TEXT NOT NULL,
	ats_score INTEGER NOT NULL DEFAULT 0,
	critique JSON NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_applications_user_id ON applications (user_id);

CREATE TABLE credit_ledger (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	delta INTEGER NOT NULL,
	reason VARCHAR(80) NOT NULL,
	balance_after INTEGER NOT NULL,
	ref VARCHAR(255) NOT NULL DEFAULT '',
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_credit_ledger_user_id ON credit_ledger (user_id);

CREATE TABLE payments (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	provider VARCHAR(40) NOT NULL,
	provider_ref VARCHAR(255) NOT NULL,
	plan_id VARCHAR(50) NOT NULL,
	amount_usd FLOAT NOT NULL DEFAULT 0.0,
	credits INTEGER NOT NULL DEFAULT 0,
	status VARCHAR(20) NOT NULL DEFAULT 'paid',
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_payments_user_id ON payments (user_id);
CREATE UNIQUE INDEX ix_payments_provider_ref ON payments (provider_ref);

CREATE TABLE audit_events (
	id INTEGER NOT NULL,
	user_id INTEGER,
	request_id VARCHAR(16) NOT NULL DEFAULT '',
	event VARCHAR(60) NOT NULL,
	status VARCHAR(20) NOT NULL DEFAULT 'ok',
	ip VARCHAR(64) NOT NULL DEFAULT '',
	meta JSON NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_audit_events_event ON audit_events (event);
CREATE INDEX ix_audit_events_user_id ON audit_events (user_id);
CREATE INDEX ix_audit_events_created_at ON audit_events (created_at);
CREATE INDEX ix_audit_events_request_id ON audit_events (request_id);


-- =====================================================================
-- MySQL variant (DATABASE_URL=mysql+pymysql://...)
-- Same shape; JSON/DATETIME/BOOLEAN map natively, AUTO_INCREMENT replaces
-- SQLite's implicit INTEGER PRIMARY KEY rowid behaviour.
-- =====================================================================

/*
CREATE TABLE users (
	id INTEGER NOT NULL AUTO_INCREMENT,
	email VARCHAR(255) NOT NULL,
	hashed_password VARCHAR(255) NOT NULL,
	full_name VARCHAR(255) NOT NULL DEFAULT '',
	credits INTEGER NOT NULL DEFAULT 0,
	plan VARCHAR(50) NOT NULL DEFAULT 'free',
	polar_customer_id VARCHAR(255),
	is_admin BOOL NOT NULL DEFAULT 0,
	monthly_refill_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	UNIQUE KEY ix_users_email (email)
);

CREATE TABLE base_cvs (
	id INTEGER NOT NULL AUTO_INCREMENT,
	user_id INTEGER NOT NULL,
	data JSON NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	UNIQUE KEY uq_base_cvs_user_id (user_id),
	FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE applications (
	id INTEGER NOT NULL AUTO_INCREMENT,
	user_id INTEGER NOT NULL,
	job_title VARCHAR(255) NOT NULL DEFAULT '',
	company VARCHAR(255) NOT NULL DEFAULT '',
	job_description TEXT NOT NULL,
	tailored_cv JSON NOT NULL,
	cover_letter TEXT NOT NULL,
	ats_score INTEGER NOT NULL DEFAULT 0,
	critique JSON NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	KEY ix_applications_user_id (user_id),
	FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE credit_ledger (
	id INTEGER NOT NULL AUTO_INCREMENT,
	user_id INTEGER NOT NULL,
	delta INTEGER NOT NULL,
	reason VARCHAR(80) NOT NULL,
	balance_after INTEGER NOT NULL,
	ref VARCHAR(255) NOT NULL DEFAULT '',
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	KEY ix_credit_ledger_user_id (user_id),
	FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE payments (
	id INTEGER NOT NULL AUTO_INCREMENT,
	user_id INTEGER NOT NULL,
	provider VARCHAR(40) NOT NULL,
	provider_ref VARCHAR(255) NOT NULL,
	plan_id VARCHAR(50) NOT NULL,
	amount_usd FLOAT NOT NULL DEFAULT 0.0,
	credits INTEGER NOT NULL DEFAULT 0,
	status VARCHAR(20) NOT NULL DEFAULT 'paid',
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	KEY ix_payments_user_id (user_id),
	UNIQUE KEY ix_payments_provider_ref (provider_ref),
	FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE audit_events (
	id INTEGER NOT NULL AUTO_INCREMENT,
	user_id INTEGER,
	request_id VARCHAR(16) NOT NULL DEFAULT '',
	event VARCHAR(60) NOT NULL,
	status VARCHAR(20) NOT NULL DEFAULT 'ok',
	ip VARCHAR(64) NOT NULL DEFAULT '',
	meta JSON NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	KEY ix_audit_events_event (event),
	KEY ix_audit_events_user_id (user_id),
	KEY ix_audit_events_created_at (created_at),
	KEY ix_audit_events_request_id (request_id),
	FOREIGN KEY (user_id) REFERENCES users (id)
);
*/
