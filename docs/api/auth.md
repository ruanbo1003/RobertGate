# API: 用户认证

基础路径：`/api/v1/auth`

---

## 1. 用户注册

**POST** `/api/v1/auth/register`

### 请求
```json
{
  "username": "string  // 2-20字符，中英文、数字、下划线",
  "email": "string     // 合法邮箱格式",
  "password": "string  // 8-32字符，至少包含字母和数字"
}
```

### 响应

成功 — 注册后自动登录，返回 token：
```json
{
  "code": 0,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user": {
      "id": "uuid",
      "username": "your_username",
      "email": "you@example.com",
      "created_at": "2026-03-26T12:00:00Z"
    }
  },
  "message": "ok"
}
```

失败：
| code | message | 说明 |
|------|---------|------|
| 2001 | 用户名格式无效 | 不符合 2-20 字符规则 |
| 2002 | 邮箱格式无效 | 非法邮箱 |
| 2003 | 密码格式无效 | 不符合 8-32 字符或缺少字母/数字 |
| 2010 | 用户名已被使用 | 唯一性冲突 |
| 2011 | 邮箱已被注册 | 唯一性冲突 |

---

## 2. 用户登录

**POST** `/api/v1/auth/login`

### 请求
```json
{
  "email": "string",
  "password": "string"
}
```

### 响应

成功：
```json
{
  "code": 0,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user": {
      "id": "uuid",
      "username": "your_username",
      "email": "you@example.com"
    }
  },
  "message": "ok"
}
```

失败：
| code | message | 说明 |
|------|---------|------|
| 1001 | 邮箱或密码错误 | 不区分具体原因，防止枚举 |
| 1002 | 账号已被锁定，请稍后再试 | 连续失败 5 次，锁定 15 分钟 |

---

## 3. 请求密码重置

**POST** `/api/v1/auth/forgot-password`

### 请求
```json
{
  "email": "string"
}
```

### 响应

成功 — 无论邮箱是否存在，均返回成功（防止枚举）：
```json
{
  "code": 0,
  "data": null,
  "message": "如果该邮箱已注册，重置链接已发送"
}
```

失败：
| code | message | 说明 |
|------|---------|------|
| 2002 | 邮箱格式无效 | 格式校验失败 |
| 5001 | 邮件发送失败，请稍后重试 | 邮件服务异常 |

### 邮件内容
- 包含重置链接：`{FRONTEND_URL}/reset-password?token={reset_token}`
- token 有效期 30 分钟
- 一次性使用

---

## 4. 重置密码

**POST** `/api/v1/auth/reset-password`

### 请求
```json
{
  "token": "string     // 重置链接中的 token",
  "password": "string  // 新密码，8-32字符，至少包含字母和数字"
}
```

### 响应

成功：
```json
{
  "code": 0,
  "data": null,
  "message": "密码重置成功"
}
```

失败：
| code | message | 说明 |
|------|---------|------|
| 1003 | 重置链接无效或已过期 | token 不存在、已使用或超过 30 分钟 |
| 2003 | 密码格式无效 | 不符合规则 |

---

## 5. 检查用户名可用性

**GET** `/api/v1/auth/check-username/{username}`

### 响应

可用：
```json
{
  "code": 0,
  "data": { "available": true },
  "message": "ok"
}
```

不可用：
```json
{
  "code": 0,
  "data": { "available": false },
  "message": "ok"
}
```

---

## 6. 检查邮箱可用性

**GET** `/api/v1/auth/check-email/{email}`

### 响应

可用：
```json
{
  "code": 0,
  "data": { "available": true },
  "message": "ok"
}
```

不可用：
```json
{
  "code": 0,
  "data": { "available": false },
  "message": "ok"
}
```

---

## 通用说明

### 认证方式
登录/注册成功后返回 JWT token，后续请求通过 Header 传递：
```
Authorization: Bearer <access_token>
```

### 频率限制
| 接口 | 限制 |
|------|------|
| login | 5 次/分钟/IP |
| register | 3 次/分钟/IP |
| forgot-password | 3 次/分钟/IP |
| reset-password | 5 次/分钟/IP |
| check-username | 10 次/分钟/IP |
| check-email | 10 次/分钟/IP |

### 错误码范围
| 范围 | 类别 |
|------|------|
| 0 | 成功 |
| 1000-1999 | 认证/权限错误 |
| 2000-2999 | 参数校验错误 |
| 5000-5999 | 服务器内部错误 |
