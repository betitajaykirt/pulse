import os
from unittest.mock import patch

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from mysite.command_safety import (
    assert_safe_for_destructive_commands,
    production_block_reason,
)


class CommandSafetyTests(SimpleTestCase):
    def test_allows_local_debug_database(self):
        env = {
            'DEBUG': 'true',
            'DB_HOST': 'localhost',
            'ALLOW_PROD_COMMANDS': '',
        }
        with patch.dict(os.environ, env, clear=False):
            self.assertIsNone(production_block_reason('seed_dummy_reports'))

    def test_blocks_when_debug_is_false(self):
        env = {
            'DEBUG': 'false',
            'DB_HOST': 'localhost',
            'ALLOW_PROD_COMMANDS': '',
        }
        with patch.dict(os.environ, env, clear=False):
            reason = production_block_reason('seed_dummy_reports')
            self.assertIsNotNone(reason)
            self.assertIn('DEBUG is False', reason)

    def test_blocks_hostinger_even_when_debug_true(self):
        env = {
            'DEBUG': 'true',
            'DB_HOST': 'auth-db1322.hstgr.io',
            'ALLOW_PROD_COMMANDS': '',
        }
        with patch.dict(os.environ, env, clear=False):
            reason = production_block_reason('seed_admins.py')
            self.assertIsNotNone(reason)
            self.assertIn('hstgr.io', reason)

    def test_blocks_aiven_wipe_host(self):
        env = {
            'DEBUG': 'true',
            'DB_HOST': 'mysql-example.j.aivencloud.com',
            'ALLOW_PROD_COMMANDS': '',
        }
        with patch.dict(os.environ, env, clear=False):
            reason = production_block_reason('import_db.py')
            self.assertIsNotNone(reason)
            self.assertIn('aivencloud.com', reason)

    def test_override_allows_explicit_break_glass(self):
        env = {
            'DEBUG': 'false',
            'DB_HOST': 'auth-db1322.hstgr.io',
            'ALLOW_PROD_COMMANDS': '1',
        }
        with patch.dict(os.environ, env, clear=False):
            self.assertIsNone(production_block_reason('seed_dummy_reports'))

    def test_assert_raises_command_error(self):
        env = {
            'DEBUG': 'false',
            'DB_HOST': 'localhost',
            'ALLOW_PROD_COMMANDS': '',
        }
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaises(CommandError):
                assert_safe_for_destructive_commands('import_db.py')
