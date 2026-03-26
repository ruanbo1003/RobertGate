# API 规范

## 基础
- 所有路由统一前缀：/api/v1
- 使用 RESTful 风格

## 统一返回格式
成功：
{
  "code": 0,
  "data": {},
  "message": "ok"
}

失败：
{
  "code": <错误码>,
  "data": null,
  "message": "<错误描述>"
}

## 错误码约定
- 0：成功
- 1000-1999：认证/权限错误
- 2000-2999：参数错误
- 5000-5999：服务器内部错误

## 命名规范
- URL 使用小写 + 连字符：/api/v1/user-profile
- 资源用复数名词：/api/v1/users
- 操作用 HTTP 动词区分：GET 查询、POST 创建、PUT 更新、DELETE 删除

## CORS
- 开发环境允许 http://localhost:3000
- 生产环境只允许指定域名

## 认证
- 使用 JWT Bearer Token
- Header：Authorization: Bearer <token>
