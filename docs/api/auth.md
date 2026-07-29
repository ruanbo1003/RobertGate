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

---

## 3. 检查用户名可用性

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

## 4. 检查邮箱可用性

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
| check-username | 10 次/分钟/IP |
| check-email | 10 次/分钟/IP |

### 错误码范围
| 范围 | 类别 |
|------|------|
| 0 | 成功 |
| 1000-1999 | 认证/权限错误 |
| 2000-2999 | 参数校验错误 |
| 5000-5999 | 服务器内部错误 |
