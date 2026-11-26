-- PharmaOS · esquema PROPUESTO para Supabase (no aplicado todavía).
-- Sustituye: localStorage (ActionStore) y out/api/report.json (ReportSource "motor").
-- Sin datos de pacientes: solo informes de producto y estados de acciones.

create table farmacias (
  id uuid primary key default gen_random_uuid(),
  nombre text not null,
  programa text,                       -- farmatic, nixfarma…
  coste_mensual numeric not null default 149,
  creada timestamptz not null default now()
);

create table miembros (                -- quién puede ver cada farmacia (auth.users)
  farmacia_id uuid references farmacias on delete cascade,
  usuario_id uuid references auth.users on delete cascade,
  rol text not null default 'titular',
  primary key (farmacia_id, usuario_id)
);

create table informes (                -- un report.json por semana (contrato v1)
  id uuid primary key default gen_random_uuid(),
  farmacia_id uuid not null references farmacias on delete cascade,
  semana text not null,                -- '2026-W47'
  fecha_datos date not null,
  nucleo jsonb not null,               -- report-core.json (acciones + sus productos)
  completo_path text,                  -- report.json completo en Storage (2–3 MB)
  creado timestamptz not null default now(),
  unique (farmacia_id, semana)
);

create table acciones_estado (         -- lo que hoy guarda ActionStore en localStorage
  farmacia_id uuid not null references farmacias on delete cascade,
  semana text not null,
  accion_id text not null,             -- 'devolver-654321'
  estado text not null check (estado in ('hecha', 'pospuesta', 'descartada')),
  importe_eur numeric not null,        -- copia para el histórico de /recuperado
  marcado timestamptz not null default now(),
  marcado_por uuid references auth.users,
  primary key (farmacia_id, semana, accion_id)
);

alter table farmacias enable row level security;
alter table miembros enable row level security;
alter table informes enable row level security;
alter table acciones_estado enable row level security;

create policy "miembros ven su farmacia" on farmacias for select
  using (exists (select 1 from miembros m where m.farmacia_id = id and m.usuario_id = auth.uid()));
create policy "miembros ven sus filas" on miembros for select using (usuario_id = auth.uid());
create policy "miembros leen informes" on informes for select
  using (exists (select 1 from miembros m where m.farmacia_id = informes.farmacia_id and m.usuario_id = auth.uid()));
create policy "miembros gestionan acciones" on acciones_estado for all
  using (exists (select 1 from miembros m where m.farmacia_id = acciones_estado.farmacia_id and m.usuario_id = auth.uid()))
  with check (exists (select 1 from miembros m where m.farmacia_id = acciones_estado.farmacia_id and m.usuario_id = auth.uid()));
-- Los informes los escribe el servidor del motor con la service role key (nunca el navegador).
