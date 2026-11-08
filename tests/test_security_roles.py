import unittest
from unittest.mock import patch

from flask_appbuilder.security.manager import AUTH_DB
from flask_appbuilder.security.sqla.models import Role

import app as app_module
from app.security import ROLE_PERMISSIONS


def permission_pairs(role: Role) -> set[tuple[str, str]]:
    return {
        (permission.permission.name, permission.view_menu.name)
        for permission in role.permissions
    }


class SecurityRoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config = {
            "SECRET_KEY": "test-secret-key-" + "x" * 48,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "AUTH_TYPE": AUTH_DB,
            "AUTH_ROLE_ADMIN": "Admin",
            "AUTH_USER_REGISTRATION": False,
            "AUTH_ROLES_SYNC_AT_LOGIN": False,
            "WTF_CSRF_ENABLED": False,
            "TESTING": True,
        }
        with patch.object(app_module, "load_config", return_value=config):
            cls.app = app_module.create_app()

        cls.security_manager = app_module.appbuilder.sm
        with cls.app.app_context():
            result = cls.app.test_cli_runner().invoke(args=["init-db"])
            if result.exception:
                raise result.exception
            cls.admin_permissions_before = permission_pairs(
                cls.security_manager.find_role("Admin")
            )
            cls.public_permissions_before = permission_pairs(
                cls.security_manager.find_role("Public")
            )
            result = cls.app.test_cli_runner().invoke(args=["configure-roles"])
            if result.exception:
                raise result.exception
            cls._create_test_users()

    @classmethod
    def tearDownClass(cls) -> None:
        with cls.app.app_context():
            app_module.db.session.remove()
            app_module.db.engine.dispose()

    @classmethod
    def _create_test_users(cls) -> None:
        users = (
            ("test-receptionist", "Recepcionista"),
            ("test-trainer", "Entrenador"),
            ("test-admin", "Admin"),
        )
        for username, role_name in users:
            role = cls.security_manager.find_role(role_name)
            user = cls.security_manager.add_user(
                username,
                "Test",
                role_name,
                f"{username}@example.test",
                role,
                password="test-password",
            )
            if user is None:
                raise RuntimeError(f"No se pudo crear el usuario de prueba {username}.")

    def test_role_configuration_is_idempotent_and_preserves_admin(self) -> None:
        with self.app.app_context():
            admin = self.security_manager.find_role("Admin")
            self.assertEqual(permission_pairs(admin), self.admin_permissions_before)

            result = self.app.test_cli_runner().invoke(args=["configure-roles"])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(permission_pairs(admin), self.admin_permissions_before)
            self.assertEqual(
                permission_pairs(self.security_manager.find_role("Public")),
                self.public_permissions_before,
            )

            for role_name, expected_permissions in ROLE_PERMISSIONS.items():
                role = self.security_manager.find_role(role_name)
                self.assertIsNotNone(role)
                actual_permissions = {
                    pair
                    for pair in permission_pairs(role)
                    if pair[1]
                    in {
                        "Gimnasio",
                        "Socios",
                        "SocioModelView",
                        "Entrenadores",
                        "EntrenadorModelView",
                        "Planes",
                        "PlanModelView",
                    }
                }
                self.assertEqual(actual_permissions, set(expected_permissions))

    def test_receptionist_can_manage_members_and_only_read_other_current_modules(
        self,
    ) -> None:
        client = self.app.test_client()
        response = client.post(
            "/login/",
            data={
                "username": "test-receptionist",
                "password": "test-password",
            },
        )
        self.assertEqual(response.status_code, 302)

        for path in (
            "/socios/list/",
            "/socios/add",
            "/entrenadores/list/",
            "/planes/list/",
        ):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 200)

        for path in ("/entrenadores/add", "/planes/add", "/socios/download/csv"):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 403)

        self.assertEqual(client.get("/socios/delete/1").status_code, 404)

    def test_trainer_is_limited_to_plans_until_assignment_filters_exist(self) -> None:
        client = self.app.test_client()
        response = client.post(
            "/login/",
            data={"username": "test-trainer", "password": "test-password"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(client.get("/planes/list/").status_code, 200)

        for path in (
            "/socios/list/",
            "/socios/edit/1",
            "/entrenadores/list/",
            "/entrenadores/add",
            "/planes/add",
        ):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 403)

    def test_admin_keeps_access_and_physical_delete_route_is_absent(self) -> None:
        client = self.app.test_client()
        response = client.post(
            "/login/",
            data={"username": "test-admin", "password": "test-password"},
        )
        self.assertEqual(response.status_code, 302)

        for path in (
            "/socios/add",
            "/entrenadores/add",
            "/planes/add",
        ):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 200)

        self.assertEqual(client.get("/socios/delete/1").status_code, 404)

    def test_session_role_switch_does_not_keep_previous_permissions(self) -> None:
        client = self.app.test_client()
        client.post(
            "/login/",
            data={
                "username": "test-receptionist",
                "password": "test-password",
            },
        )
        self.assertEqual(client.get("/socios/list/").status_code, 200)
        client.get("/logout/")
        client.post(
            "/login/",
            data={"username": "test-trainer", "password": "test-password"},
        )

        self.assertEqual(client.get("/socios/list/").status_code, 403)
        self.assertEqual(client.get("/planes/list/").status_code, 200)


if __name__ == "__main__":
    unittest.main()
