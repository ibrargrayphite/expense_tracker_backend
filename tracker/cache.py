"""
tracker/cache.py
================
Central place for all cache key construction and per-resource invalidation helpers.

Swap the storage backend any time via .env CACHE_BACKEND — this module is
backend-agnostic and works identically with locmem, Memcached, and Redis.

Usage
-----
from tracker.cache import invalidate_user_transactions, CACHE_TTL
"""

from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Honour the TTL from settings (set via CACHE_TTL env var, default 5 min)
CACHE_TTL: int = getattr(settings, 'CACHE_TTL', 300)

# ── Key builders ─────────────────────────────────────────────────────────────

def _user_key(user_id: int, resource: str) -> str:
    """Pattern: u{user_id}:{resource} — KEY_PREFIX is added by the backend."""
    return f"u{user_id}:{resource}"


def transactions_list_key(user_id: int) -> str:
    return _user_key(user_id, "transactions")


def contacts_list_key(user_id: int) -> str:
    return _user_key(user_id, "contacts")


def accounts_list_key(user_id: int) -> str:
    return _user_key(user_id, "accounts")


def loans_list_key(user_id: int) -> str:
    return _user_key(user_id, "loans")


def planned_expenses_list_key(user_id: int) -> str:
    return _user_key(user_id, "planned_expenses")


# ── Invalidation helpers ──────────────────────────────────────────────────────

def invalidate_user_transactions(user_id: int) -> None:
    key = transactions_list_key(user_id)
    cache.delete(key)
    logger.debug("Cache invalidated [transactions] for user %s", user_id)


def invalidate_user_contacts(user_id: int) -> None:
    key = contacts_list_key(user_id)
    cache.delete(key)
    logger.debug("Cache invalidated [contacts] for user %s", user_id)


def invalidate_user_accounts(user_id: int) -> None:
    # Accounts appear inside transaction data, bust both
    keys = [accounts_list_key(user_id), transactions_list_key(user_id)]
    cache.delete_many(keys)
    logger.debug("Cache invalidated [accounts + transactions] for user %s", user_id)


def invalidate_user_loans(user_id: int) -> None:
    key = loans_list_key(user_id)
    cache.delete(key)
    logger.debug("Cache invalidated [loans] for user %s", user_id)


def invalidate_user_planned_expenses(user_id: int) -> None:
    key = planned_expenses_list_key(user_id)
    cache.delete(key)
    logger.debug("Cache invalidated [planned_expenses] for user %s", user_id)


def invalidate_all_user_caches(user_id: int) -> None:
    """Nuclear option — wipe every cached list for this user at once."""
    cache.delete_many([
        transactions_list_key(user_id),
        contacts_list_key(user_id),
        accounts_list_key(user_id),
        loans_list_key(user_id),
        planned_expenses_list_key(user_id),
    ])
    logger.debug("All caches invalidated for user %s", user_id)
