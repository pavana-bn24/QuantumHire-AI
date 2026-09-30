import { Compass, SearchX } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 px-6 text-center">
      <span className="grid h-12 w-12 place-items-center rounded-xl bg-brand-600/20 text-brand-300 ring-1 ring-brand-500/30">
        <SearchX size={22} />
      </span>
      <h1 className="text-2xl font-bold text-white">Page not found</h1>
      <p className="max-w-sm text-sm text-slate-400">
        That route does not exist in this prototype yet.
      </p>
      <Link to="/dashboard" className="btn-ghost mt-2">
        <Compass size={16} /> Back to dashboard
      </Link>
    </div>
  )
}
