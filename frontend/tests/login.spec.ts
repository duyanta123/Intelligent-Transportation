import { describe, it, expect } from 'vitest'

/**
 * 登录核心逻辑单测（纯函数部分）：
 * 登录页使用的校验规则与登录流程的前置判断
 */

// 与 Login.vue / vehicles.vue 保持一致的车牌校验正则（用于识别结果校验）
const platePattern = /^[京津沪渝冀晋辽吉黑苏浙皖闽赣鲁豫鄂湘粤桂琼川贵云陕甘青蒙藏宁新][A-HJ-NP-Z][A-HJ-NP-Z0-9]{4,6}$/

const usernamePattern = /^[A-Za-z0-9_]{3,32}$/

function canSubmitLogin(form: { username: string; password: string; captcha_code: string }): boolean {
  return form.username.trim().length > 0 && form.password.length > 0 && form.captcha_code.trim().length === 4
}

describe('登录表单校验', () => {
  it('用户名规则：3-32 位字母数字下划线', () => {
    expect(usernamePattern.test('admin')).toBe(true)
    expect(usernamePattern.test('user_01')).toBe(true)
    expect(usernamePattern.test('ab')).toBe(false)
    expect(usernamePattern.test('有中文')).toBe(false)
    expect(usernamePattern.test('a'.repeat(33))).toBe(false)
  })

  it('表单可提交条件：账号+密码+4 位验证码', () => {
    expect(canSubmitLogin({ username: 'admin', password: '123456', captcha_code: 'A2C4' })).toBe(true)
    expect(canSubmitLogin({ username: '', password: '123456', captcha_code: 'A2C4' })).toBe(false)
    expect(canSubmitLogin({ username: 'admin', password: '', captcha_code: 'A2C4' })).toBe(false)
    expect(canSubmitLogin({ username: 'admin', password: '123456', captcha_code: 'A2' })).toBe(false)
  })

  it('车牌识别结果校验：支持普通 7 位与新能源 8 位', () => {
    expect(platePattern.test('京A12345')).toBe(true)
    expect(platePattern.test('京AD12345')).toBe(true)
    expect(platePattern.test('冀B6F888')).toBe(true)
    expect(platePattern.test('BAD123')).toBe(false)
    expect(platePattern.test('京A')).toBe(false)
    expect(platePattern.test('京I12345')).toBe(false) // 发牌机关字母不含 I/O
  })
})
