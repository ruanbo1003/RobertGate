export type UserRole = 'user' | 'admin'

export interface User {
  id: string
  username: string
  email: string
  role: UserRole
  created_at?: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface ApiResponse<T = null> {
  code: number
  data: T
  message: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface AvailabilityResponse {
  available: boolean
}
