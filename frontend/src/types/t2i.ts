// 文生图任务化 类型定义
// 对应 docs/api/text-to-image-tasks.md

// 模板 code 现在完全动态，用户可自定义；保留 alias 便于阅读。
export type T2ITemplateCode = string
export type T2ITaskStatus = 'generating' | 'succeeded' | 'failed'
export type T2IBusinessStatus = 'done' | 'pending'
export type T2IImageStatus = 'generating' | 'succeeded' | 'failed'

export interface T2ITemplate {
  id: string
  code: string
  name: string
  description: string | null
  prompt: string
  order_index: number
  is_builtin: boolean
  created_at: string
  updated_at: string
}

export interface T2ITemplatesResponse {
  templates: T2ITemplate[]
}

export interface T2ITaskSummary {
  id: string
  template_code: string
  keywords: Record<string, string>
  summary: string
  status: T2ITaskStatus
  business_status: T2IBusinessStatus
  images_total: number
  images_available: number
  last_failed: boolean
  thumbnails?: string[]
  created_at: string
  updated_at: string
}

export interface T2ITaskListResponse {
  template: { code: string; name: string }
  page: number
  page_size: number
  total: number
  items: T2ITaskSummary[]
}

export interface T2ICreateTaskResponse {
  existing: boolean
  task: T2ITaskSummary
}

export interface T2IImage {
  id: string
  status: T2IImageStatus
  available: boolean
  url: string | null
  created_at: string
}

export interface T2ITaskDetail {
  task: T2ITaskSummary & { images_failed: number }
  images: T2IImage[]
}

export interface T2IPatchImageResponse {
  id: string
  available: boolean
  task_id: string
  task_business_status: T2IBusinessStatus
}

export interface T2IDeleteImageResponse {
  id: string
  task_id: string
  images_total: number
  images_available: number
  task_business_status: T2IBusinessStatus
}

export interface T2ICreateTemplatePayload {
  code: string
  name: string
  description?: string | null
  prompt: string
  order_index?: number
}

export interface T2IUpdateTemplatePayload {
  name: string
  description?: string | null
  prompt: string
  order_index?: number
}
