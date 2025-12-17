
import os
import json
from enum import Enum


class AccountType(str, Enum):
    ACCOUNT_PENDING = "AccountPending"
    PARTNER = "PartnerAccount"
    BUSINESS = "BusinessAccount"
    BRAND_SPECIALIST = "BrandSpecialistAccount"
    BRAND_PARTNER = "BrandPartnerAccount"
    BRAND = "BrandAccount"
    ADMIN = "AdministratorDreamboxInteractiveAccount"


# Default permissions (used if no config/roles.json override)
DEFAULT_ROLE_PERMISSIONS = {
    AccountType.ACCOUNT_PENDING: {
        "can_view_basic_dashboard": True,
        "can_view_game_data": False,
        "can_manage_games": False,
        "can_view_products": False,
        "can_view_brand_campaigns": False,
        "can_manage_brand": False,
        "can_pay_for_products": False,
        "can_admin": False,
    },
    AccountType.PARTNER: {
        "can_view_basic_dashboard": True,
        "can_view_game_data": True,
        "can_manage_games": True,
        "can_view_products": False,
        "can_view_brand_campaigns": False,
        "can_manage_brand": False,
        "can_pay_for_products": False,
        "can_admin": False,
    },
    AccountType.BUSINESS: {
        "can_view_basic_dashboard": True,
        "can_view_game_data": False,
        "can_manage_games": False,
        "can_view_products": True,
        "can_view_brand_campaigns": False,
        "can_manage_brand": False,
        "can_pay_for_products": True,
        "can_admin": False,
    },
    AccountType.BRAND_SPECIALIST: {
        "can_view_basic_dashboard": True,
        "can_view_game_data": False,
        "can_manage_games": False,
        "can_view_products": False,
        "can_view_brand_campaigns": True,
        "can_manage_brand": False,
        "can_pay_for_products": False,
        "can_admin": False,
    },
    AccountType.BRAND_PARTNER: {
        "can_view_basic_dashboard": True,
        "can_view_game_data": False,
        "can_manage_games": False,
        "can_view_products": True,
        "can_view_brand_campaigns": True,
        "can_manage_brand": True,
        "can_pay_for_products": True,
        "can_admin": False,
    },
    AccountType.BRAND: {
        "can_view_basic_dashboard": True,
        "can_view_game_data": False,
        "can_manage_games": False,
        "can_view_products": True,
        "can_view_brand_campaigns": True,
        "can_manage_brand": True,
        "can_pay_for_products": True,
        "can_admin": False,
    },
    AccountType.ADMIN: {
        "can_view_basic_dashboard": True,
        "can_view_game_data": True,
        "can_manage_games": True,
        "can_view_products": True,
        "can_view_brand_campaigns": True,
        "can_manage_brand": True,
        "can_pay_for_products": True,
        "can_admin": True,
    },
}


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
ROLES_CONFIG_PATH = os.path.join(CONFIG_DIR, "roles.json")


def load_role_permissions():
    """Load role permissions from config/roles.json if present, else use defaults."""
    try:
        with open(ROLES_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("[CONFIG] roles.json not found, using DEFAULT_ROLE_PERMISSIONS")
        return DEFAULT_ROLE_PERMISSIONS

    perms = {}
    for acct_type in AccountType:
        key = acct_type.value
        if key in data and isinstance(data[key], dict):
            perms[acct_type] = {
                **DEFAULT_ROLE_PERMISSIONS[acct_type],
                **data[key],
            }
        else:
            perms[acct_type] = DEFAULT_ROLE_PERMISSIONS[acct_type]

    return perms


ROLE_PERMISSIONS = load_role_permissions()
