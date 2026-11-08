from flask_appbuilder.security.sqla.manager import SecurityManager
from flask_appbuilder.security.sqla.models import PermissionView, Role


ROLE_PERMISSIONS: dict[str, frozenset[tuple[str, str]]] = {
    "Recepcionista": frozenset(
        {
            ("menu_access", "Gimnasio"),
            ("menu_access", "Socios"),
            ("menu_access", "Entrenadores"),
            ("menu_access", "Planes"),
            ("can_list", "SocioModelView"),
            ("can_show", "SocioModelView"),
            ("can_add", "SocioModelView"),
            ("can_edit", "SocioModelView"),
            ("desactivar", "SocioModelView"),
            ("can_list", "EntrenadorModelView"),
            ("can_show", "EntrenadorModelView"),
            ("can_list", "PlanModelView"),
            ("can_show", "PlanModelView"),
        }
    ),
    "Entrenador": frozenset(
        {
            ("menu_access", "Gimnasio"),
            ("menu_access", "Planes"),
            ("can_list", "PlanModelView"),
            ("can_show", "PlanModelView"),
        }
    ),
}

MANAGED_VIEW_MENUS = frozenset(
    {
        "Gimnasio",
        "Socios",
        "SocioModelView",
        "Entrenadores",
        "EntrenadorModelView",
        "Planes",
        "PlanModelView",
    }
)


def _permission_pair(permission_view: PermissionView) -> tuple[str, str]:
    return permission_view.permission.name, permission_view.view_menu.name


def _get_or_create_role(security_manager: SecurityManager, name: str) -> Role:
    role = security_manager.find_role(name)
    if role is None:
        role = security_manager.add_role(name)
    if role is None:
        raise RuntimeError(f"No se pudo crear el rol {name}.")
    return role


def configure_application_roles(security_manager: SecurityManager) -> None:
    for role_name, desired_permissions in ROLE_PERMISSIONS.items():
        role = _get_or_create_role(security_manager, role_name)

        for permission_view in list(role.permissions):
            view_name = permission_view.view_menu.name
            if (
                view_name in MANAGED_VIEW_MENUS
                and _permission_pair(permission_view) not in desired_permissions
            ):
                security_manager.del_permission_role(role, permission_view)
                if permission_view in role.permissions:
                    raise RuntimeError(
                        f"No se pudo retirar el permiso "
                        f"{_permission_pair(permission_view)} del rol {role_name}."
                    )

        for permission_name, view_name in desired_permissions:
            permission_view = security_manager.add_permission_view_menu(
                permission_name,
                view_name,
            )
            if permission_view is None:
                raise RuntimeError(
                    f"No se pudo registrar el permiso "
                    f"{(permission_name, view_name)}."
                )
            if permission_view not in role.permissions:
                security_manager.add_permission_role(role, permission_view)
                if permission_view not in role.permissions:
                    raise RuntimeError(
                        f"No se pudo asignar el permiso "
                        f"{(permission_name, view_name)} al rol {role_name}."
                    )
