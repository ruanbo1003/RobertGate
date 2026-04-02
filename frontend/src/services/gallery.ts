import type { ApiResponse } from '../types/auth'
import type { GalleryResponse } from '../types/gallery'

const API_BASE = '/api/v1/gallery'

export async function getPhotos(): Promise<ApiResponse<GalleryResponse>> {
  try {
    const res = await fetch(`${API_BASE}/photos`)

    if (!res.ok && res.status >= 500) {
      return { code: 5000, data: null as never, message: '服务器异常，请稍后重试' }
    }

    return await res.json()
  } catch {
    return { code: 5001, data: null as never, message: '网络连接失败，请检查网络' }
  }
}
