-- =========================================================
-- Tabel: user_login
-- Menyimpan data user + password login utama
CREATE TABLE user_login (
    user_id         INT PRIMARY KEY IDENTITY(1,1),
    username        VARCHAR(50)  NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    password_salt   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(100),
    email           VARCHAR(100),
    role            VARCHAR(30)  NOT NULL DEFAULT 'user',
    is_active       BIT          NOT NULL DEFAULT 1,
    is_locked       BIT          NOT NULL DEFAULT 0,
    failed_attempt  INT          NOT NULL DEFAULT 0,
    last_failed_at  DATETIME,
    last_login_at   DATETIME,
    created_at      DATETIME NOT NULL DEFAULT GETDATE(),
    created_by      VARCHAR(50),
    updated_at      DATETIME,
    updated_by      VARCHAR(50)
);

-- =========================================================
-- Tabel: user_lock
-- Menyimpan PIN 6 digit (hash) per user
CREATE TABLE user_lock (
    user_id              INT         NOT NULL,
    pin_hash             VARCHAR(255) NOT NULL,
    pin_salt             VARCHAR(255) NOT NULL,
    is_locked            BIT          NOT NULL DEFAULT 0,
    failed_attempt       INT          NOT NULL DEFAULT 0,
    max_attempt          INT          NOT NULL DEFAULT 10,
    lockout_until        DATETIME,
    erase_on_max_attempt BIT          NOT NULL DEFAULT 0,
    updated_at           DATETIME,
    updated_by           INT,
    CONSTRAINT pk_user_lock PRIMARY KEY (user_id),
    CONSTRAINT fk_user_lock_user
        FOREIGN KEY (user_id) REFERENCES user_login(user_id)
        ON DELETE CASCADE
);

-- =========================================================
-- Tabel: trans_login_lock
-- Menyimpan log semua kejadian login & PIN
-- =========================================================
CREATE TABLE trans_login_lock (
    trans_id        INT PRIMARY KEY IDENTITY(1,1),
    user_id         INT         NOT NULL,
    event_time      DATETIME    NOT NULL DEFAULT GETDATE(),
    event_type      VARCHAR(30) NOT NULL,     -- PIN_FAIL, LOGIN_SUCCESS, dll
    credential_type VARCHAR(20) NOT NULL,     -- LOGIN / PIN_LOCK
    reason          VARCHAR(500),
    actor_user_id   INT,
    client_info     VARCHAR(200),
    CONSTRAINT fk_tll_user
        FOREIGN KEY (user_id) REFERENCES user_login(user_id),
    CONSTRAINT fk_tll_actor
        FOREIGN KEY (actor_user_id) REFERENCES user_login(user_id)
);
