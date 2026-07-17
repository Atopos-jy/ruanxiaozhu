import { useState } from 'react'
import type { FormProps } from 'antd'
import { Alert, Button, Checkbox, Form, Input, Typography } from 'antd'
import { ProCard } from '@ant-design/pro-components'
import { EyeInvisibleOutlined, EyeTwoTone, LockOutlined, MailOutlined, RobotOutlined } from '@ant-design/icons'
import { getApiError, saveTokens } from '../lib/auth'
import type { TokenResponse, User } from '../types/auth'

type AuthMode = 'login' | 'register'
type AuthFormValues = { email: string; password: string; confirmPassword?: string; acceptedTerms?: boolean }
type Props = { onAuthenticated: (user: User) => void }

export function AuthPage({ onAuthenticated }: Props) {
  const [mode, setMode] = useState<AuthMode>('register')
  const [form] = Form.useForm<AuthFormValues>()
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const isRegister = mode === 'register'
  const switchMode = (nextMode: AuthMode) => { form.resetFields(); setError(''); setNotice(''); setMode(nextMode) }
  const submitAuth: FormProps<AuthFormValues>['onFinish'] = async values => {
    setError(''); setNotice(''); setSubmitting(true)
    try {
      const endpoint = isRegister ? '/api/auth/register' : '/api/auth/login'
      const body = isRegister ? { email: values.email.trim().toLowerCase(), password: values.password, accepted_terms: values.acceptedTerms } : { email: values.email.trim().toLowerCase(), password: values.password }
      const response = await fetch(`http://127.0.0.1:8000${endpoint}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      const data = await response.json().catch(() => null)
      if (!response.ok) throw new Error(getApiError(data, '请求未完成，请稍后重试'))
      if (isRegister) { form.resetFields(['password', 'confirmPassword', 'acceptedTerms']); setMode('login'); setNotice('注册成功，请使用新账号登录'); return }
      saveTokens(data as TokenResponse); onAuthenticated((data as TokenResponse).user)
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : '网络异常，请确认后端服务已启动') } finally { setSubmitting(false) }
  }
  return <main className="grid h-screen grid-cols-1 overflow-hidden bg-white lg:grid-cols-2"><aside className="hidden h-screen w-full overflow-hidden lg:block"><img className="h-full w-full object-cover object-top" src="/auth-hero.png" alt="软小筑 AI 管家" /></aside><section className="flex h-screen min-h-0 w-full items-center justify-center overflow-y-auto bg-slate-50 px-4 py-4 sm:px-8"><ProCard className="w-full max-w-[500px] border border-slate-200 shadow-xl shadow-slate-200/45" bordered><div className="px-1 py-1 sm:px-3"><div className="mb-5 text-center"><RobotOutlined className="text-3xl text-indigo-500" /><Typography.Title level={2} className="!mb-1 !mt-2 !text-3xl">{isRegister ? '创建账号' : '欢迎回来'}</Typography.Title><Typography.Text type="secondary">{isRegister ? '注册后即可使用 AI 管家与知识库' : '登录后继续你的智能工作与知识体验'}</Typography.Text></div>{error && <Alert className="!mb-3" type="error" showIcon message={error} />}{notice && <Alert className="!mb-3" type="success" showIcon message={notice} />}<Form form={form} layout="vertical" requiredMark={false} size="middle" onFinish={submitAuth}><Form.Item className="!mb-3" label="邮箱" name="email" rules={[{ required: true, message: '请输入邮箱地址' }, { type: 'email', message: '请输入有效的邮箱地址' }]}><Input prefix={<MailOutlined className="text-slate-400" />} placeholder="请输入邮箱地址" autoComplete="email" /></Form.Item><Form.Item className="!mb-3" label="密码" name="password" extra={isRegister ? '至少 8 位密码' : undefined} rules={[{ required: true, message: '请输入密码' }, { min: 8, message: '密码至少需要 8 位' }]}><Input.Password prefix={<LockOutlined className="text-slate-400" />} placeholder="请输入密码" autoComplete={isRegister ? 'new-password' : 'current-password'} iconRender={visible => visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />} /></Form.Item>{isRegister && <Form.Item className="!mb-3" label="确认密码" name="confirmPassword" dependencies={['password']} rules={[{ required: true, message: '请再次输入密码' }, ({ getFieldValue }) => ({ validator(_, value) { return !value || getFieldValue('password') === value ? Promise.resolve() : Promise.reject(new Error('两次输入的密码不一致')) } })]}><Input.Password prefix={<LockOutlined className="text-slate-400" />} placeholder="请再次输入密码" autoComplete="new-password" /></Form.Item>}{isRegister && <Form.Item className="!mb-4" name="acceptedTerms" valuePropName="checked" rules={[{ validator: (_, value) => value ? Promise.resolve() : Promise.reject(new Error('请先同意服务条款和隐私政策')) }]}><Checkbox className="text-xs text-slate-500">我已阅读并同意 <a href="#terms" className="text-indigo-500">《服务条款》</a> 与 <a href="#privacy" className="text-indigo-500">《隐私政策》</a></Checkbox></Form.Item>}<Button className="!h-11 !text-base !font-semibold" type="primary" htmlType="submit" block loading={submitting}>{isRegister ? '注册' : '登录'}</Button></Form><div className="mt-5 border-t border-slate-100 pt-4 text-center text-sm text-slate-500">{isRegister ? '已有账号？' : '还没有账号？'} <Button className="!h-auto !p-0 !align-baseline" type="link" onClick={() => switchMode(isRegister ? 'login' : 'register')}>{isRegister ? '立即登录' : '立即注册'}</Button></div></div></ProCard></section></main>
}
