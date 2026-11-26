import { Dialog } from "./Dialog";

const SHORTCUTS: [string, string][] = [
  ["J / K", "Siguiente / anterior acción"],
  ["H", "Marcar como hecha"],
  ["P", "Posponer"],
  ["D", "Descartar"],
  ["Enter", "Ver ficha y cálculo"],
  ["/", "Buscar"],
  ["Esc", "Cerrar o salir de la búsqueda"],
  ["?", "Mostrar esta ayuda"],
];

export function ShortcutsHelp({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Dialog open={open} onClose={onClose} title="Atajos de teclado">
      <dl className="divide-y divide-line-soft text-sm">
        {SHORTCUTS.map(([keys, label]) => (
          <div key={keys} className="flex items-center justify-between py-2">
            <dt className="text-ink-soft">{label}</dt>
            <dd className="flex gap-1">
              {keys.split(" / ").map((k) => (
                <kbd key={k}>{k}</kbd>
              ))}
            </dd>
          </div>
        ))}
      </dl>
    </Dialog>
  );
}
