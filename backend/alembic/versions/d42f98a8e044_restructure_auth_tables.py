"""restructure auth tables

Revision ID: d42f98a8e044
Revises: a1c4e7f2b835
Create Date: 2026-05-09 22:25:18.671114

Schema changes:
  - users: drop google_id + avatar_url, add role + auth_type (enum)
  - new: google_auth_users (user_id FK, google_id, avatar_url)
  - new: email_auth_users  (user_id FK, password_hash)

Data migration:
  - All existing users (Google) are copied into google_auth_users
  - role='user', auth_type='google' set on all pre-existing rows
  - Admin user seeded into users + email_auth_users
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d42f98a8e044"
down_revision: Union[str, None] = "a1c4e7f2b835"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Fixed UUID so the seed row is idempotent across envs
_ADMIN_USER_ID = "00000000-0000-4000-a000-000000000001"
_ADMIN_EMAIL = "k@gmail.com"
_ADMIN_NAME = "Admin"
_ADMIN_PASSWORD_HASH = "$2a$12$HJpghHCt0C6xJg3NsVUp6.LRDgFdwbbpr00P5XlxHDJCyXaw7psM2"


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Create new auth-detail tables
    # ------------------------------------------------------------------
    op.create_table(
        "email_auth_users",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "google_auth_users",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("google_id", sa.String(length=255), nullable=False),
        sa.Column("avatar_url", sa.String(length=2048), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(
        op.f("ix_google_auth_users_google_id"),
        "google_auth_users",
        ["google_id"],
        unique=True,
    )

    # ------------------------------------------------------------------
    # 2. Create PostgreSQL ENUM types explicitly — op.add_column does
    #    not auto-create them, so they must exist before column creation.
    # ------------------------------------------------------------------
    op.execute(sa.text("CREATE TYPE userrole AS ENUM ('user', 'admin')"))
    op.execute(sa.text("CREATE TYPE authtype AS ENUM ('google', 'email')"))

    # ------------------------------------------------------------------
    # 3. Add role + auth_type as NULLABLE first — existing rows would
    #    violate NOT NULL if we added them constrained immediately.
    # ------------------------------------------------------------------
    op.add_column(
        "users",
        sa.Column("role", sa.Enum("user", "admin", name="userrole", create_type=False), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("auth_type", sa.Enum("google", "email", name="authtype", create_type=False), nullable=True),
    )

    # ------------------------------------------------------------------
    # 4. Data migration — copy Google credentials out of users before
    #    those columns are dropped, and stamp every existing row.
    # ------------------------------------------------------------------
    op.execute("""
        INSERT INTO google_auth_users (user_id, google_id, avatar_url)
        SELECT id, google_id, avatar_url
        FROM users
    """)

    op.execute("UPDATE users SET role = 'user', auth_type = 'google'")

    # ------------------------------------------------------------------
    # 5. Now that every existing row has values, enforce NOT NULL
    # ------------------------------------------------------------------
    op.alter_column("users", "role", nullable=False)
    op.alter_column("users", "auth_type", nullable=False)

    # ------------------------------------------------------------------
    # 6. Drop Google-specific columns — must happen BEFORE the admin
    #    seed because google_id is still NOT NULL and the admin row
    #    has no google_id.
    # ------------------------------------------------------------------
    op.drop_index(op.f("ix_users_google_id"), table_name="users")
    op.drop_constraint(op.f("uq_users_google_id"), "users", type_="unique")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "google_id")

    # ------------------------------------------------------------------
    # 7. Seed admin user (email auth).
    #    ON CONFLICT DO NOTHING makes this safe to re-run.
    # ------------------------------------------------------------------
    op.execute(f"""
        INSERT INTO users (id, email, name, role, auth_type, created_at, updated_at)
        VALUES (
            '{_ADMIN_USER_ID}',
            '{_ADMIN_EMAIL}',
            '{_ADMIN_NAME}',
            'admin',
            'email',
            now(),
            now()
        )
        ON CONFLICT (email) DO NOTHING
    """)
    op.execute(f"""
        INSERT INTO email_auth_users (user_id, password_hash)
        SELECT '{_ADMIN_USER_ID}', '{_ADMIN_PASSWORD_HASH}'
        WHERE EXISTS (
            SELECT 1 FROM users WHERE id = '{_ADMIN_USER_ID}'
        )
        ON CONFLICT (user_id) DO NOTHING
    """)


def downgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Restore Google-specific columns (nullable while we backfill)
    # ------------------------------------------------------------------
    op.add_column(
        "users",
        sa.Column("google_id", sa.VARCHAR(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("avatar_url", sa.VARCHAR(length=2048), nullable=True),
    )

    # ------------------------------------------------------------------
    # 2. Backfill from google_auth_users
    # ------------------------------------------------------------------
    op.execute("""
        UPDATE users u
        SET google_id  = g.google_id,
            avatar_url = g.avatar_url
        FROM google_auth_users g
        WHERE u.id = g.user_id
    """)

    # ------------------------------------------------------------------
    # 3. Remove email-auth users (they have no google_id; can't exist
    #    in the old schema). This includes the seeded admin row.
    # ------------------------------------------------------------------
    op.execute("DELETE FROM users WHERE auth_type = 'email'")

    # ------------------------------------------------------------------
    # 4. Restore NOT NULL + unique constraints on google_id
    # ------------------------------------------------------------------
    op.alter_column("users", "google_id", nullable=False)
    op.create_unique_constraint("uq_users_google_id", "users", ["google_id"])
    op.create_index("ix_users_google_id", "users", ["google_id"], unique=False)

    # ------------------------------------------------------------------
    # 5. Drop the new columns and their PostgreSQL ENUM types
    # ------------------------------------------------------------------
    op.drop_column("users", "auth_type")
    op.drop_column("users", "role")

    bind = op.get_bind()
    sa.Enum(name="authtype").drop(bind, checkfirst=True)
    sa.Enum(name="userrole").drop(bind, checkfirst=True)

    # ------------------------------------------------------------------
    # 6. Drop new tables
    # ------------------------------------------------------------------
    op.drop_index(op.f("ix_google_auth_users_google_id"), table_name="google_auth_users")
    op.drop_table("google_auth_users")
    op.drop_table("email_auth_users")
