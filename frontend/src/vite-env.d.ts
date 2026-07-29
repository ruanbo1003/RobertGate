/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * 后端 API 基础地址。留空则使用相对路径 `/api/...`，由 Vite dev proxy 或 nginx 反向代理转发。
   * 若前端与后端不同域，请设置为完整 URL，如 `https://api.example.com`。
   */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
