CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campus_id TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    role TEXT NOT NULL DEFAULT 'student',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS certifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    scope TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_certifications (
    user_id INTEGER NOT NULL,
    certification_id INTEGER NOT NULL,
    granted_by TEXT NOT NULL,
    granted_at TEXT NOT NULL,
    PRIMARY KEY (user_id, certification_id),
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (certification_id) REFERENCES certifications (id)
);

CREATE TABLE IF NOT EXISTS swipe_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    input_value TEXT NOT NULL,
    certification_checked INTEGER,
    timestamp TEXT NOT NULL,
    result TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (certification_checked) REFERENCES certifications (id)
);

CREATE TABLE IF NOT EXISTS staff_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    performed_by TEXT NOT NULL,
    performed_at TEXT NOT NULL,
    metadata TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
