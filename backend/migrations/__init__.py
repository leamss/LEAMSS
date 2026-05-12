"""Migrations package — versioned, idempotent DB migrations.

Each migration logs its run in the 'migrations' collection so it can be
safely re-executed without corrupting data.
"""
