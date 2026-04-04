
-- 1) Anlık durum tablosu
create table if not exists public.signal_state (
  symbol text primary key,
  action text not null,
  alert_level integer not null,
  signal_price double precision,
  tf_1h text,
  tf_4h text,
  tf_1d text,
  tf_1w text,
  raw_payload jsonb,
  updated_at timestamptz not null default now()
);

-- 2) Geçmiş log tablosu
create table if not exists public.signal_history (
  id bigint generated always as identity primary key,
  symbol text not null,
  action text not null,
  alert_level integer not null,
  signal_price double precision,
  tf_1h text,
  tf_4h text,
  tf_1d text,
  tf_1w text,
  telegram_sent boolean not null default false,
  telegram_message text,
  raw_payload jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_signal_history_symbol_created_at
on public.signal_history (symbol, created_at desc);
