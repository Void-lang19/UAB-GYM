import os
import unittest
from unittest.mock import patch

from config import load_config


class LoadConfigTests(unittest.TestCase):
    def test_builds_mysql_url_from_environment(self) -> None:
        environment = {
            "SECRET_KEY": "a" * 64,
            "DB_HOST": "127.0.0.1",
            "DB_PORT": "3307",
            "DB_NAME": "uab_gym",
            "DB_USER": "gym_user",
            "DB_PASSWORD": "p@ss word",
        }
        with patch.dict(os.environ, environment, clear=True):
            config = load_config()

        database_url = config["SQLALCHEMY_DATABASE_URI"]
        self.assertEqual(database_url.drivername, "mysql+pymysql")
        self.assertEqual(database_url.username, "gym_user")
        self.assertEqual(database_url.password, "p@ss word")
        self.assertEqual(database_url.host, "127.0.0.1")
        self.assertEqual(database_url.port, 3307)
        self.assertEqual(database_url.database, "uab_gym")
        self.assertEqual(database_url.query["charset"], "utf8mb4")

    def test_rejects_missing_or_example_secret(self) -> None:
        base_environment = {
            "DB_NAME": "uab_gym",
            "DB_USER": "root",
        }
        for secret in ("", "replace-me-with-a-random-secret", "too-short"):
            with self.subTest(secret=secret):
                with patch.dict(
                    os.environ,
                    {**base_environment, "SECRET_KEY": secret},
                    clear=True,
                ):
                    with self.assertRaisesRegex(RuntimeError, "SECRET_KEY"):
                        load_config()

    def test_rejects_non_numeric_database_port(self) -> None:
        environment = {
            "SECRET_KEY": "a" * 64,
            "DB_NAME": "uab_gym",
            "DB_USER": "root",
            "DB_PORT": "invalid",
        }
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(RuntimeError, "DB_PORT"):
                load_config()


if __name__ == "__main__":
    unittest.main()
