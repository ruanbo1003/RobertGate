export const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
export const PASSWORD_REGEX = /^(?=.*[a-zA-Z])(?=.*\d).{8,32}$/
export const USERNAME_REGEX = /^[\w\u4e00-\u9fff]{2,20}$/

export function validateEmail(email: string): string | null {
  if (!email) return '请输入邮箱'
  if (!EMAIL_REGEX.test(email)) return '请输入有效的邮箱地址'
  return null
}

export function validatePassword(password: string): string | null {
  if (!password) return '请输入密码'
  if (password.length < 8 || password.length > 32) return '密码需要 8-32 个字符'
  if (!PASSWORD_REGEX.test(password)) return '密码需包含字母和数字'
  return null
}

export function validateUsername(username: string): string | null {
  if (!username) return '请输入用户名'
  if (username.length < 2 || username.length > 20) return '用户名需要 2-20 个字符'
  if (!USERNAME_REGEX.test(username)) return '用户名只能包含中英文、数字、下划线'
  return null
}

export function validateConfirmPassword(password: string, confirm: string): string | null {
  if (!confirm) return '请确认密码'
  if (password !== confirm) return '两次密码不一致'
  return null
}

export type PasswordStrength = 'weak' | 'medium' | 'strong'

export function getPasswordStrength(password: string): { strength: PasswordStrength; label: string } {
  if (!password || password.length < 8) return { strength: 'weak', label: '弱' }

  let score = 0
  if (password.length >= 12) score++
  if (/[A-Z]/.test(password)) score++
  if (/[a-z]/.test(password)) score++
  if (/\d/.test(password)) score++
  if (/[^a-zA-Z\d]/.test(password)) score++

  if (score >= 4) return { strength: 'strong', label: '强' }
  if (score >= 2) return { strength: 'medium', label: '中' }
  return { strength: 'weak', label: '弱' }
}
