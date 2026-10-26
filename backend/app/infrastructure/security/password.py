"""bcrypt 密码哈希实现（原 AuthService 的静态方法，逻辑原样搬运）。"""

from __future__ import annotations

import bcrypt


class BcryptHasher:
    def hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify(self, plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
