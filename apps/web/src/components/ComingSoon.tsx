import Link from "next/link";

export default function ComingSoon({ title }: { title: string }) {
  return (
    <main className="mx-auto max-w-3xl px-6 py-20">
      <Link href="/" className="font-semibold text-teal-700">DubsiBhai / Home</Link>
      <h1 className="mt-8 text-4xl font-bold">{title}</h1>
      <p className="mt-4 text-slate-600">This feature is planned and is not available yet.</p>
    </main>
  );
}
