import { Outlet } from 'react-router-dom'

import Sidebar from './Sidebar.jsx'
import Topbar from './Topbar.jsx'

/** Shell for every authenticated page: fixed sidebar + top bar + content. */
export default function AppLayout() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="mx-auto w-full max-w-7xl flex-1 px-5 py-7 md:px-8">
          <Outlet />
        </main>
        <footer className="border-t border-white/5 px-5 py-4 text-center text-xs text-slate-500 md:px-8">
          QuantumHire AI · one recruiter workflow: role → resume → profile → AI evaluation →
          skill test → recruiter approval
        </footer>
      </div>
    </div>
  )
}
