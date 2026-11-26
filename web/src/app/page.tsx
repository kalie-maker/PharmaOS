import { ButtonLink } from "@/components/Button";
import { Logo } from "@/components/AppShell";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center px-6">
      <Logo />
      <h1 className="mt-6 text-2xl font-semibold tracking-tight">
        Tu lista de acciones del lunes, con euros.
      </h1>
      <div className="mt-6">
        <ButtonLink href="/lunes" variant="primary">
          Abrir
        </ButtonLink>
      </div>
    </main>
  );
}
