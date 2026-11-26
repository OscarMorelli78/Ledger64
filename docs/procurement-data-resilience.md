# Ledger64 Data Resilience — synthetic pilot

This administrator-only local CLI backs up one procurement SQLite database for one
explicit company and the synthetic data class. It includes originals, normalized
documents, revision events, queues and supplier templates. ALE signals are recomputed
from the restored approved documents. It does NOT back up auth.sqlite3, core
data.sqlite3, external configuration, model weights, or the whole installation.

Create a private existing backup directory, preferably on another physical device.
On Windows use a restricted NTFS folder with appropriate ACLs; on POSIX use mode 700.
Never put data in GitHub or a public folder. The database and backup are not encrypted.

    python -m procurement_backup create --source /private/procurement.sqlite3 --destination /backup/snapshot.sqlite3 --tenant COMPANY_ID
    python -m procurement_backup verify --source /backup/snapshot.sqlite3 --tenant COMPANY_ID --sha256 EXPECTED_HASH
    python -m procurement_backup restore --source /backup/snapshot.sqlite3 --destination /recovery/recovered.sqlite3 --tenant COMPANY_ID --sha256 EXPECTED_HASH

Keep the SHA-256 printed at creation separately in a trusted location. The expected
hash is mandatory for verification and restoration. SQLite's online backup API
captures a transactionally consistent snapshot, including committed WAL content.
The candidate snapshot is checked for SQLite integrity, known schema, company and
data scope, original hashes, event replay, queue linkage and template hashes.
Pending and rejected requests are retained; their status is not independently
anchored cryptographically. No externally signed manifest or hostile database
sandbox is provided. Only use locally trusted snapshots and a trusted OS account.

Restore verifies the exact staged copy before atomically publishing a NEW file
using a same-filesystem hard link; existing destinations and sidecars are refused.
Hard-link-incompatible filesystems fail closed. Never point a restore at the live
database. After verifying the recovered reports, stop the application and follow
an administrator-approved cutover plan. No automatic live cutover or overwrite.

No automatic scheduling, retention deletion, encryption or remote storage in this
increment. Maximum snapshot size 512 MiB and bounded SQLite backup operation.
Production requires backup of authentication and core stores, OS ACL review,
encryption and key recovery, recovery drills on target hardware and documented RPO/RTO.

CI also runs a CLI disaster-recovery drill with the original synthetic database
moved out of its usual location, verified backup and new-path restoration, and
asserts the recovered EUR 150 documentary exposure and no confirmed paid loss.
The original is retained in the temporary runner for safety. Tests separately
exercise actual deletion of a temporary fixture, WAL consistency, revoked sources,
CSV and table templates and pending review requests. No real data is involved.
