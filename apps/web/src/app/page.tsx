import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col justify-center px-6 py-16">
      <p className="text-sm font-semibold uppercase tracking-widest text-teal-700">Dhaka, Bangladesh</p>
      <h1 className="mt-4 text-5xl font-bold tracking-tight sm:text-7xl">DubsiBhai</h1>
      <p className="mt-6 max-w-2xl text-xl leading-relaxed text-slate-600">
        Urban waterlogging and drainage management. A place to report problems,
        follow their resolution, and help build a better Dhaka.
      </p>
      <p className="mt-6 text-sm text-slate-500">Development is underway. Reporting and map features are coming soon.</p>
      <nav aria-label="Main navigation" className="mt-8 flex flex-wrap gap-4">
        <Link href="/map" className="rounded-lg bg-teal-700 px-5 py-3 font-semibold text-white">Explore the map</Link>
        <Link href="/login" className="rounded-lg border border-teal-700 px-5 py-3 font-semibold text-teal-800">Sign in</Link>
      </nav>
    </main>
  );
}
