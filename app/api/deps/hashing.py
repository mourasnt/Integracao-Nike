# Try to use passlib when available, otherwise fall back to a PBKDF2-HMAC implementation for test/dev

def _truncate_to_72_bytes(s: str) -> str:
    """Truncate input string to a valid UTF-8 string whose UTF-8 encoding is at most 72 bytes.
    This prevents bcrypt backend errors when passwords exceed 72 bytes.
    """
    b = s.encode('utf-8')[:72]
    try:
        return b.decode('utf-8')
    except UnicodeDecodeError:
        # Remove trailing bytes until decodable
        while b:
            b = b[:-1]
            try:
                return b.decode('utf-8')
            except UnicodeDecodeError:
                continue
        return ""

import importlib
import hashlib
import os
import binascii
from typing import Optional

_pwd_context = None


def _get_pwd_context() -> Optional[object]:
    """Lazily import and instantiate a passlib CryptContext.

    Returns the CryptContext instance, or None if import/instantiation fails.
    """
    global _pwd_context
    if _pwd_context is not None:
        return _pwd_context
    try:
        passlib = importlib.import_module('passlib.context')
        CryptContext = getattr(passlib, 'CryptContext')
        _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        # Sanity-check the backend by hashing and verifying a tiny password; if this fails,
        # disable the context and fall back to PBKDF2 to avoid import-time crashes or noisy
        # passlib internal errors (e.g., AttributeError reading bcrypt.__about__)
        try:
            test_pw = "t"
            h = _pwd_context.hash(test_pw)
            if not _pwd_context.verify(test_pw, h):
                raise RuntimeError("CryptContext verify self-check failed")
        except Exception as e:
            try:
                from loguru import logger
                logger.warning("passlib CryptContext self-check failed, will use fallback: %s", str(e))
            except Exception:
                pass
            _pwd_context = None
            return None

        try:
            from loguru import logger
            logger.debug("passlib CryptContext instantiated successfully")
        except Exception:
            pass
        return _pwd_context
    except Exception as e:
        try:
            from loguru import logger
            logger.warning("passlib CryptContext unavailable: %s", str(e))
        except Exception:
            pass
        _pwd_context = None
        return None


def get_password_hash(password: str) -> str:
    pw = _truncate_to_72_bytes(password)
    ctx = _get_pwd_context()
    if ctx is not None:
        try:
            return ctx.hash(pw)
        except Exception:
            # fall back to PBKDF2-HMAC
            pass

    # Fallback PBKDF2-HMAC implementation (use truncated pw consistently)
    salt = os.urandom(8)
    dk = hashlib.pbkdf2_hmac('sha256', pw.encode(), salt, 100000)
    logger = None
    try:
        from loguru import logger as _logger
        logger = _logger
    except Exception:
        pass
    if logger:
        logger.debug("Using PBKDF2 fallback hashing (pw_len=%d)", len(pw))
    return binascii.hexlify(salt).decode() + '$' + binascii.hexlify(dk).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pw = _truncate_to_72_bytes(plain_password)
    ctx = _get_pwd_context()
    if ctx is not None:
        try:
            ok = ctx.verify(pw, hashed_password)
        except Exception:
            ok = False
        if ok:
            return True

    try:
        salt_hex, dk_hex = hashed_password.split('$', 1)
        salt = binascii.unhexlify(salt_hex)
        dk = binascii.unhexlify(dk_hex)
        newdk = hashlib.pbkdf2_hmac('sha256', pw.encode(), salt, 100000)
        return newdk == dk
    except Exception:
        return False
