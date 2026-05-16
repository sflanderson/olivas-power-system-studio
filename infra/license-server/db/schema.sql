-- Olivas License Server — Supabase schema
-- Sprint commercial-1 (v4.1.0)

-- ---------------------------------------------------------------------------
-- licenses
-- ---------------------------------------------------------------------------
create table if not exists licenses (
    id               uuid primary key default gen_random_uuid(),
    key              text not null unique,
    key_hash         text not null unique,
    tier             text not null check (tier in (
                         'educational', 'demo', 'commercial',
                         'pro_engineering', 'enterprise'
                     )),
    customer_id      text not null,
    customer_email   text,
    customer_name    text,
    expiry_date      timestamptz not null,
    max_activations  integer not null default 3,
    hotmart_event_id text,
    hotmart_product_id text,
    hotmart_subscription_id text,
    issued_at        timestamptz not null default now(),
    revoked_at       timestamptz,
    revoked_reason   text,
    created_at       timestamptz not null default now(),
    updated_at       timestamptz not null default now()
);

create index if not exists idx_licenses_customer_id on licenses (customer_id);
create index if not exists idx_licenses_customer_email on licenses (customer_email);
create index if not exists idx_licenses_hotmart_subscription on licenses (hotmart_subscription_id);
create index if not exists idx_licenses_active on licenses (key_hash)
    where revoked_at is null;

-- ---------------------------------------------------------------------------
-- activations
-- ---------------------------------------------------------------------------
create table if not exists activations (
    id            uuid primary key default gen_random_uuid(),
    license_id    uuid not null references licenses(id) on delete cascade,
    machine_id    text not null,
    activated_at  timestamptz not null default now(),
    last_seen_at  timestamptz not null default now(),
    ip_country    text,
    user_agent    text,
    unique (license_id, machine_id)
);

create index if not exists idx_activations_license on activations (license_id);
create index if not exists idx_activations_machine on activations (machine_id);

-- ---------------------------------------------------------------------------
-- webhooks_log (auditoria Hotmart)
-- ---------------------------------------------------------------------------
create table if not exists webhooks_log (
    id            uuid primary key default gen_random_uuid(),
    source        text not null,      -- 'hotmart' / 'manual' / 'ml'
    event_type    text not null,
    event_id      text,
    payload       jsonb not null,
    status        text not null check (status in (
                      'received', 'processed', 'failed', 'ignored'
                  )),
    error_message text,
    received_at   timestamptz not null default now(),
    processed_at  timestamptz
);

create index if not exists idx_webhooks_source_event
    on webhooks_log (source, event_type);
create index if not exists idx_webhooks_received_at
    on webhooks_log (received_at desc);

-- ---------------------------------------------------------------------------
-- Trigger: updated_at
-- ---------------------------------------------------------------------------
create or replace function set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_licenses_updated_at on licenses;
create trigger trg_licenses_updated_at
    before update on licenses
    for each row execute function set_updated_at();

-- ---------------------------------------------------------------------------
-- RLS — service role bypassa; cliente não deve acessar diretamente
-- ---------------------------------------------------------------------------
alter table licenses enable row level security;
alter table activations enable row level security;
alter table webhooks_log enable row level security;

-- (sem policies — apenas service_role acessa via Worker)
