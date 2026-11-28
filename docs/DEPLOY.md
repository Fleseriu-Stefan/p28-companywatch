# Deploy CompanyWatch on Azure

Target `companywatch-live` (Ubuntu 24.04 amd64). Caddy serves
`companywatch-sf.austriaeast.cloudapp.azure.com` over HTTPS using ports 80/443.
MySQL and the API stay inside Compose. The static directory is ready for a
future React build. Restore the published database from the local machine.

## 1. Install Docker and clone on the VM

Run as `azureuser` in Bash. The packages come from the
[official Docker Ubuntu repository](https://docs.docker.com/engine/install/ubuntu/).

```bash
set -euo pipefail
sudo apt-get update
sudo apt-get install -y ca-certificates curl git gzip openssl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<'EOF'
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
git clone --branch main https://github.com/Fleseriu-Stefan/p28-companywatch.git "$HOME/companywatch"
cd "$HOME/companywatch"
mkdir -p frontend/dist
install -d -m 700 "$HOME/.local/share/companywatch-backups"
```

Generate credentials once, before creating the MySQL volume. Keep the private
file and its credentials when updating or recreating containers.

```bash
cd "$HOME/companywatch"
(
  set -eu
  umask 077
  set -C
  mysql_password=$(openssl rand -hex 32)
  mysql_root_password=$(openssl rand -hex 32)
  {
    sed '/^MYSQL_PASSWORD=/d; /^MYSQL_ROOT_PASSWORD=/d' .env.production.example
    printf 'MYSQL_PASSWORD=%s\nMYSQL_ROOT_PASSWORD=%s\n' "$mysql_password" "$mysql_root_password"
  } > .env.production
)
test "$(stat -c '%a' .env.production)" = 600
```

## 2. Dump and transfer from the local machine

Run from the local checkout with its existing private `.env`. Pause ETL and
schema changes while taking the dump. The staging check must return zero.
The dump includes the application schema and Alembic revision.

```bash
set -euo pipefail
umask 077
backup_dir=$(mktemp -d "$HOME/companywatch-transfer.XXXXXXXX")
source_db() {
  MYSQL_DATABASE=companywatch_d018 docker compose --env-file .env -f compose.yaml \
    -p companywatch-d018-local exec -T db "$@"
}
test "$(source_db sh -ec 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -N -B companywatch_d018 -e "SELECT COUNT(*) FROM etl_staging_rows"')" = 0
source_db sh -ec 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --single-transaction --quick --no-tablespaces --set-gtid-purged=OFF --skip-add-drop-table companywatch_d018' \
  | gzip > "$backup_dir/companywatch_d018.sql.gz.part"
gzip -t "$backup_dir/companywatch_d018.sql.gz.part"
mv "$backup_dir/companywatch_d018.sql.gz.part" "$backup_dir/companywatch_d018.sql.gz"
scp -p -i ~/.ssh/companywatch-key.pem "$backup_dir/companywatch_d018.sql.gz" \
  azureuser@companywatch-sf.austriaeast.cloudapp.azure.com:.local/share/companywatch-backups/companywatch_d018.sql.gz
```

## 3. Restore and start on the VM

Run in Bash. Use the same project name for every server operation. This initial
restore requires an empty database. If the import fails partway, stop here and
use a fresh empty target before retrying. Preserve existing production volumes
when updating or recreating containers.

```bash
set -euo pipefail
cd "$HOME/companywatch"
prod() {
  sudo docker compose --env-file .env.production -f compose.prod.yaml -p companywatch-live "$@"
}
dump="$HOME/.local/share/companywatch-backups/companywatch_d018.sql.gz"
gzip -t "$dump"
prod config --quiet
prod up -d --wait --wait-timeout 180 db
test "$(prod exec -T db sh -ec 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -N -B "$MYSQL_DATABASE" -e "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()"')" = 0
gzip -dc "$dump" | prod exec -T db sh -ec 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot "$MYSQL_DATABASE"'
prod pull caddy
prod run --rm --no-deps caddy caddy validate --config /etc/caddy/Caddyfile
prod up -d --build --wait --wait-timeout 180
prod ps -a
```

## 4. Verify and recreate

From outside the VM, verify HTTPS with normal certificate validation. Readiness
must return HTTP 200 and `{"status":"ready"}`.

```bash
base=https://companywatch-sf.austriaeast.cloudapp.azure.com
curl -fsS "$base/health/ready"
curl -fsS -o /dev/null "$base/docs"
curl -fsS -o /dev/null "$base/openapi.json"
```

On the VM, use the `prod` function above to verify both editions and the
current pointer. Run the query before and after the force-recreate. Repeat the
external HTTPS checks afterward.

```bash
verify_snapshots() {
  prod exec -T db sh -ec 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -N -B "$MYSQL_DATABASE"' <<'SQL'
SELECT v.edition, v.id, COUNT(r.version_id)
FROM etl_versions v LEFT JOIN company_version_rows r ON r.version_id = v.id
WHERE v.state = 'published'
GROUP BY v.edition, v.id ORDER BY v.edition;
SELECT v.edition, v.id
FROM dataset_publications p JOIN etl_versions v ON v.id = p.current_version_id;
SQL
}
verify_snapshots
prod up -d --force-recreate --wait --wait-timeout 180
verify_snapshots
```

Expect 120,000 rows for 2026-10-19 and 120,163 for 2026-11-04, with
2026-11-04 current. [Published versions](../DATA.md#calitatea-edițiilor-publicate).

## 5. Backup and update

From `~/companywatch` with `prod` defined, take a backup before each update.
Store backups outside Git and retain the named database and Caddy volumes.

```bash
set -euo pipefail
umask 077
backup=$(mktemp --suffix=.sql.gz.part "$HOME/.local/share/companywatch-backups/companywatch-$(date -u +%Y%m%dT%H%M%SZ).XXXXXXXX")
prod exec -T db sh -ec 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --single-transaction --quick --no-tablespaces --set-gtid-purged=OFF --skip-add-drop-table "$MYSQL_DATABASE"' \
  | gzip > "$backup"
gzip -t "$backup"
mv "$backup" "${backup%.part}"
git pull --ff-only origin main
prod pull db caddy
prod up -d --build --force-recreate --wait --wait-timeout 180
```

### 5.1 Apply the authentication release

Run the block on the VM in Bash as `azureuser`, with the verified merge SHA as
the script's only argument. Pause ingestion and publication during the update.
The Azure API and Caddy use a dedicated ingress network. Check the VM has no
overlapping network before creating it. Keep the dump in the mode-700 backup
directory and preserve the existing volumes.

```bash
set -euo pipefail
umask 077

expected_sha=${1:?Pass the verified merge SHA}
cd "$HOME/companywatch"
test "$(git branch --show-current)" = main
test -z "$(git status --porcelain)"
git fetch origin main
test "$(git rev-parse FETCH_HEAD)" = "$expected_sha"

prod() {
  sudo docker compose --env-file .env.production \
    -f compose.prod.yaml -p companywatch-live "$@"
}

snapshot_state() {
  prod exec -T db sh -ec \
    'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -N -B "$MYSQL_DATABASE"' <<'SQL'
SELECT v.edition, v.id, COUNT(r.version_id)
FROM etl_versions v LEFT JOIN company_version_rows r ON r.version_id = v.id
WHERE v.state = 'published'
GROUP BY v.edition, v.id ORDER BY v.edition, v.id;
SELECT v.edition, v.id
FROM dataset_publications p JOIN etl_versions v ON v.id = p.current_version_id;
SQL
}

before=$(snapshot_state)
expected=$(printf '%s\t%s\t%s\n%s\t%s\t%s\n%s\t%s\n' \
  2026-10-19 0b8328dd-b952-4f8d-bcf5-6473234be54a 120000 \
  2026-11-04 ed5fdad9-ef2f-4aea-8f19-80fd4bcad744 120163 \
  2026-11-04 ed5fdad9-ef2f-4aea-8f19-80fd4bcad744)
test "$before" = "$expected"

backup_dir="$HOME/.local/share/companywatch-backups"
install -d -m 700 "$backup_dir"
backup=$(mktemp --suffix=.sql.gz.part \
  "$backup_dir/companywatch-$(date -u +%Y%m%dT%H%M%SZ).XXXXXXXX")
prod exec -T db sh -ec \
  'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --single-transaction --quick --no-tablespaces --set-gtid-purged=OFF --skip-add-drop-table "$MYSQL_DATABASE"' \
  | gzip > "$backup"
gzip -t "$backup"
mv "$backup" "${backup%.part}"
printf 'Verified backup %s\n' "${backup%.part}"

git merge --ff-only "$expected_sha"
test "$(git rev-parse HEAD)" = "$expected_sha"
prod config --quiet
prod pull db caddy
caddy_image=$(prod config --images | awk '/^caddy:/{print}')
test -n "$caddy_image"
sudo docker run --rm --network none \
  --mount "type=bind,src=$PWD/deploy/Caddyfile,dst=/etc/caddy/Caddyfile,readonly" \
  "$caddy_image" caddy validate --config /etc/caddy/Caddyfile

prod up -d --build --force-recreate --wait --wait-timeout 180
after=$(snapshot_state)
test "$before" = "$after"
printf '%s\n' "$after"

base=https://companywatch-sf.austriaeast.cloudapp.azure.com
test "$(curl -fsS --max-time 20 "$base/health/ready")" = '{"status":"ready"}'
curl -fsS --max-time 20 -o /dev/null "$base/openapi.json"
curl -fsS --max-time 20 -o /dev/null "$base/api/web/v1/versions"
test "$(curl -sS --max-time 20 -o /dev/null -w '%{http_code}' "$base/api/v1/versions")" = 401
prod ps -a
```

If verification fails after the schema update, keep the backup and volumes.
Check readiness and the migration revision before choosing a recovery action.
An earlier API image expects its own Alembic head.

## 6. Bootstrap the first administrator

From your interactive SSH terminal on the VM, run after the update succeeds.

```bash
cd "$HOME/companywatch"
sudo docker compose --env-file .env.production -f compose.prod.yaml \
  -p companywatch-live exec api python -m app.auth.cli bootstrap-admin
```

Enter your email and the password twice at the prompts. The password is hidden
and the command persists its Argon2id hash. See the
[operator access contract](agents/CONTRACTS.md#c-004--operator-sessions-and-api-access).
