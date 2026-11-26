import Link from "next/link";
import { Logo } from "@/components/AppShell";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <Logo />
      <h1 className="mt-6 text-xl font-semibold text-ink">Esta página no existe</h1>
      <p className="mt-2 text-sm text-ink-muted">
        Puede que el enlace esté mal escrito o que la página se haya movido.
      </p>
      <Link
        href="/lunes"
        className="mt-6 inline-flex h-9 w-fit items-center rounded-ctl bg-ink px-3.5 text-sm font-medium text-white hover:bg-ink-soft"
      >
        Ir a la lista del lunes
      </Link>
    </main>
  );
}
