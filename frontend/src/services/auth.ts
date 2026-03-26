import type {
  ApiResponse,
  AuthResponse,
  RegisterRequest,
  LoginRequest,
  ForgotPasswordRequest,
  ResetPasswordRequest,
  AvailabilityResponse,
} from '../types/auth'

const API_BASE = '/api/v1/auth'

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })
    return await res.json()
  } catch {
    return { code: 5000, data: null as T, message: '网络连接失败，请稍后重试' }
  }
}

export function register(
  data: RegisterRequest
): Promise<ApiResponse<AuthResponse>> {
  return request('/register', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function login(
  data: LoginRequest
): Promise<ApiResponse<AuthResponse>> {
  return request('/login', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function forgotPassword(
  data: ForgotPasswordRequest
): Promise<ApiResponse> {
  return request('/forgot-password', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function resetPassword(
  data: ResetPasswordRequest
): Promise<ApiResponse> {
  return request('/reset-password', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function checkUsername(
  username: string
): Promise<ApiResponse<AvailabilityResponse>> {
  return request(`/check-username/${encodeURIComponent(username)}`)
}

export function checkEmail(
  email: string
): Promise<ApiResponse<AvailabilityResponse>> {
  return request(`/check-email/${encodeURIComponent(email)}`)
}
