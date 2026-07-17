import { useState } from 'react'
import { Avatar, Button, Input } from 'antd'
import { AppstoreOutlined, BellOutlined, DatabaseOutlined, FileTextOutlined, LineChartOutlined, LogoutOutlined, RobotOutlined, SearchOutlined } from '@ant-design/icons'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { logout } from '../lib/auth'
import type { User } from '../types/auth'

type Props = { user: User; onLogout: () => void }

const navItems = [
  { label: 'AI管家', to: '/robot/chat', icon: <RobotOutlined /> },
  { label: '智能体', to: '/app', icon: <AppstoreOutlined /> },
  { label: '知识库', to: '/document', icon: <DatabaseOutlined /> },
]

const agents = [
  { name: 'AI管家', to: '/robot/chat', icon: <RobotOutlined />, iconClass: 'bg-gradient-to-br from-cyan-200 to-indigo-500' },
  { name: '企业级知识库必要性诊断', to: '/robot/knowledge-diagnosis', icon: <FileTextOutlined />, iconClass: 'bg-gradient-to-br from-sky-100 to-blue-300' },
  { name: '销售专家', to: '/robot/sales-expert', icon: <LineChartOutlined />, iconClass: 'bg-gradient-to-br from-slate-700 to-blue-950' },
]

export function AppLayout({ user, onLogout }: Props) {
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const handleLogout = async () => { await logout(); onLogout(); navigate('/') }
  return <main className="flex h-screen overflow-hidden bg-slate-100 text-slate-700">
    <aside className={`flex shrink-0 flex-col border-r border-slate-200 bg-white transition-[width] duration-200 ${collapsed ? 'w-[52px]' : 'w-[300px]'}`}>
      <div className={`flex h-14 items-center ${collapsed ? 'justify-center' : 'justify-between px-4'}`}>{!collapsed && <div className="flex items-center gap-2 text-lg font-bold text-slate-800"><span className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-gradient-to-br from-cyan-300 to-indigo-500 text-xs text-white">R</span>软小筑</div>}<Button type="text" size="small" aria-label={collapsed ? '展开导航栏' : '收起导航栏'} icon={<span className="relative block h-6 w-8 rounded-[7px] border-2 border-slate-600 before:absolute before:bottom-0 before:left-[55%] before:top-0 before:border-l-2 before:border-slate-600" />} onClick={() => setCollapsed(value => !value)} /></div>
      {!collapsed && <><div className="px-4"><Input className="!h-10 !rounded-lg !bg-slate-100 !text-sm" prefix={<SearchOutlined />} placeholder="搜索" suffix={<span className="text-xs text-slate-500">Ctrl K</span>} /></div>
      <nav className="mt-3 px-2">{navItems.map(item => <NavLink key={item.to} to={item.to} className={({ isActive }) => { const belongsToRobot = item.to === '/robot/chat' && location.pathname.startsWith('/robot/'); return `mb-1 flex h-11 items-center gap-3 rounded-lg px-3 text-sm transition ${isActive || belongsToRobot ? 'bg-indigo-50 text-indigo-600' : 'text-slate-600 hover:bg-slate-50'}` }}><span className="text-base">{item.icon}</span>{item.label}</NavLink>)}</nav>
      <div className="mt-3 border-t border-slate-200 px-4 pt-4"><p className="mb-3 text-xs font-medium text-slate-600">我的智能体</p>{agents.map(agent => <NavLink key={agent.name} to={agent.to} className={({ isActive }) => `mb-2 flex w-full items-center gap-3 rounded-lg p-1.5 text-left ${isActive ? 'bg-indigo-50 text-indigo-600' : 'hover:bg-slate-50'}`}><span className={`grid h-7 w-7 shrink-0 place-items-center rounded-md text-sm text-white ${agent.iconClass}`}>{agent.icon}</span><span className="truncate text-xs">{agent.name}</span></NavLink>)}</div>
      <div className="mt-auto flex items-center gap-2 border-t border-slate-200 p-4"><Avatar size="small" className="bg-indigo-100 text-indigo-600">{user.email.slice(0, 1).toUpperCase()}</Avatar><div className="min-w-0"><p className="truncate text-xs font-medium text-slate-700">{user.email}</p><p className="text-[11px] text-slate-400">当前登录账号</p></div><Button className="ml-auto" type="text" size="small" icon={<BellOutlined />} /><Button type="text" size="small" aria-label="退出登录" icon={<LogoutOutlined />} onClick={() => void handleLogout()} /></div></>}
    </aside>
    <section className="min-w-0 flex-1 overflow-y-auto p-6"><Outlet /></section>
  </main>
}
