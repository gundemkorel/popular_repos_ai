-- Username-only favorites store for the GitHub Pages dashboard.
-- This intentionally allows anonymous reads/writes because the UI has no password.
-- Do not use this pattern for sensitive data.

create table if not exists public.favorites (
  username text not null
    check (username ~ '^[a-z0-9._-]{1,32}$'),
  repo text not null
    check (length(repo) between 1 and 255),
  created_at timestamptz not null default now(),
  primary key (username, repo)
);

alter table public.favorites enable row level security;

drop policy if exists "favorites_public_select" on public.favorites;
drop policy if exists "favorites_public_insert" on public.favorites;
drop policy if exists "favorites_public_delete" on public.favorites;

create policy "favorites_public_select"
  on public.favorites
  for select
  to anon
  using (true);

create policy "favorites_public_insert"
  on public.favorites
  for insert
  to anon
  with check (true);

create policy "favorites_public_delete"
  on public.favorites
  for delete
  to anon
  using (true);

grant usage on schema public to anon;
grant select, insert, delete on table public.favorites to anon;
