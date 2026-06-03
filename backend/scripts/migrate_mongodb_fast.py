"""
Fast MongoDB Migration Script with Batch Processing + Parallel Workers
Optimized for large datasets - processes documents in chunks with concurrency
"""

import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pymongo import MongoClient
from pymongo.errors import BulkWriteError
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
#  ENV CONFIG
# ─────────────────────────────────────────────
LOCAL_MONGODB_URL   = os.getenv('LOCAL_MONGODB_URL',    'mongodb://localhost:27017/')
LIVE_MONGODB_URL    = os.getenv('LIVE_MONGODB_URL')
LOCAL_DB_NAME       = os.getenv('MONGODB_LOCAL_DB',     'local')
LIVE_LOCAL_DB_NAME  = os.getenv('MONGODB_LOCAL_DB_LIVE','local_data')   # Atlas target for 'local'
LIVE_DB_NAME        = os.getenv('MONGODB_DBFULL_DB',    'dbfull')       # Atlas target for 'dbfull'

# ─────────────────────────────────────────────
#  PERFORMANCE TUNING  (tweak to your machine)
# ─────────────────────────────────────────────
BATCH_SIZE          = 10_000   # documents per insert_many call
MAX_WORKERS         = 4        # parallel collection threads
SKIP_OPLOG          = True     # skip internal oplog.rs collection
CONNECT_TIMEOUT_MS  = 10_000

# ─────────────────────────────────────────────
#  GUARD
# ─────────────────────────────────────────────
if not LIVE_MONGODB_URL:
    print("❌  ERROR: LIVE_MONGODB_URL not set in .env file")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
class FastMongoDBMigrator:
# ══════════════════════════════════════════════════════════════════════════════

    def __init__(
        self,
        local_url:      str,
        live_url:       str,
        local_db:       str,
        live_local_db:  str,
        live_dbfull_db: str,
    ):
        self.local_url          = local_url
        self.live_url           = live_url
        self.local_db_name      = local_db
        self.live_local_db_name = live_local_db
        self.live_dbfull_db_name= live_dbfull_db

        self.local_client = None
        self.live_client  = None

    # ──────────────────────────────────────────
    def _make_live_client(self) -> MongoClient:
        """
        Each thread needs its own MongoClient – MongoClient is NOT thread-safe
        when shared across threads for heavy writes.
        """
        return MongoClient(
            self.live_url,
            serverSelectionTimeoutMS = CONNECT_TIMEOUT_MS,
            connectTimeoutMS         = CONNECT_TIMEOUT_MS,
            socketTimeoutMS          = 60_000,
            # Speed-up options ---------------------------------------------------
            w           = 0,         # fire-and-forget writes (fastest for bulk load)
            compressors = ["zstd"],  # compress wire traffic (pymongo 3.12+)
        )

    # ──────────────────────────────────────────
    def connect(self) -> bool:
        """Verify both endpoints are reachable."""
        try:
            print("🔗  Connecting to local MongoDB …")
            self.local_client = MongoClient(
                self.local_url,
                serverSelectionTimeoutMS=CONNECT_TIMEOUT_MS,
            )
            self.local_client.admin.command('ping')
            print("✅  Local MongoDB – connected")
        except Exception as exc:
            print(f"❌  Local MongoDB connection failed: {exc}")
            return False

        try:
            print("🔗  Connecting to live MongoDB Atlas …")
            probe = self._make_live_client()
            probe.admin.command('ping')
            probe.close()
            print("✅  Live MongoDB Atlas – connected")
        except Exception as exc:
            print(f"❌  Atlas connection failed: {exc}")
            return False

        return True

    # ──────────────────────────────────────────
    def _filtered_collections(self, client: MongoClient, db_name: str) -> list[str]:
        names = client[db_name].list_collection_names()
        if SKIP_OPLOG:
            names = [n for n in names if n != 'oplog.rs']
        return names

    # ──────────────────────────────────────────
    def _migrate_collection(
        self,
        collection_name: str,
        source_client:   MongoClient,
        source_db_name:  str,
        target_db_name:  str,
        label:           str,
    ) -> int:
        """
        Migrate one collection.  Creates its own live MongoClient so it is
        safe to call from multiple threads simultaneously.
        """
        live_client = self._make_live_client()
        try:
            src  = source_client[source_db_name][collection_name]
            dst  = live_client[target_db_name][collection_name]

            total = src.count_documents({})
            print(f"\n  [{label}] 📦  '{collection_name}'  –  {total:,} docs")

            if total == 0:
                print(f"  [{label}] ⏭️   Empty – skipped")
                return 0

            migrated   = 0
            batch_num  = 0
            batch      = []
            start      = time.time()

            for doc in src.find({}).batch_size(BATCH_SIZE):
                batch.append(doc)

                if len(batch) >= BATCH_SIZE:
                    inserted   = self._flush_batch(dst, batch, label, batch_num)
                    migrated  += inserted
                    batch_num += 1
                    batch      = []

                    # progress
                    elapsed = time.time() - start
                    rate    = migrated / elapsed if elapsed else 0
                    eta     = (total - migrated) / rate if rate else 0
                    print(
                        f"  [{label}]  ├─ batch {batch_num}: "
                        f"{migrated:,}/{total:,}  "
                        f"{rate:,.0f} docs/s  ETA {int(eta)}s"
                    )

            # flush remainder
            if batch:
                migrated  += self._flush_batch(dst, batch, label, batch_num + 1)
                batch_num += 1

            elapsed = time.time() - start
            rate    = migrated / elapsed if elapsed else 0
            print(
                f"  [{label}] ✅  '{collection_name}' done – "
                f"{migrated:,} docs in {elapsed:.1f}s  ({rate:,.0f} docs/s)"
            )
            return migrated

        except Exception as exc:
            print(f"  [{label}] ❌  Error on '{collection_name}': {exc}")
            traceback.print_exc()
            return 0
        finally:
            live_client.close()

    # ──────────────────────────────────────────
    @staticmethod
    def _flush_batch(collection, batch: list, label: str, batch_num: int) -> int:
        """insert_many with ordered=False so duplicates are skipped, not fatal."""
        try:
            result = collection.insert_many(batch, ordered=False)
            return len(result.inserted_ids)
        except BulkWriteError as bwe:
            inserted = bwe.details.get('nInserted', 0)
            skipped  = len(batch) - inserted
            if skipped:
                print(
                    f"  [{label}]  ⚠️   batch {batch_num}: "
                    f"{inserted:,} inserted, {skipped:,} duplicates skipped"
                )
            return inserted

    # ──────────────────────────────────────────
    def _migrate_database(
        self,
        source_client:   MongoClient,
        source_db_name:  str,
        target_db_name:  str,
        section_title:   str,
    ) -> int:
        """Migrate all collections of one database using a thread pool."""
        collections = self._filtered_collections(source_client, source_db_name)
        total_cols  = len(collections)

        print(f"\n{'─'*70}")
        print(f"📍  {section_title}")
        print(f"    Source : {source_db_name}  →  Target : {target_db_name}")
        print(f"    Collections : {total_cols}  |  Workers : {MAX_WORKERS}")
        print(f"{'─'*70}")

        if not collections:
            print("    (no collections found)")
            return 0

        grand_total = 0
        futures     = {}

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            for idx, col in enumerate(collections, 1):
                label  = f"{source_db_name} {idx}/{total_cols}"
                future = pool.submit(
                    self._migrate_collection,
                    col,
                    source_client,
                    source_db_name,
                    target_db_name,
                    label,
                )
                futures[future] = col

            for future in as_completed(futures):
                col = futures[future]
                try:
                    grand_total += future.result()
                except Exception as exc:
                    print(f"  ❌  Unhandled error for '{col}': {exc}")

        return grand_total

    # ──────────────────────────────────────────
    def migrate_all(self) -> bool:
        if not self.connect():
            return False

        print("\n" + "═"*70)
        print("🚀  FAST MONGODB MIGRATION  –  Batch + Parallel")
        print("═"*70)
        print(f"  Batch size  : {BATCH_SIZE:,} docs")
        print(f"  Workers     : {MAX_WORKERS} threads")
        print(f"  Skip oplog  : {SKIP_OPLOG}")
        print("═"*70)

        wall_start  = time.time()
        grand_total = 0

        # 1️⃣  local  →  live local_data
        grand_total += self._migrate_database(
            source_client  = self.local_client,
            source_db_name = self.local_db_name,
            target_db_name = self.live_local_db_name,
            section_title  = f"DATABASE  '{self.local_db_name}'  →  '{self.live_local_db_name}'",
        )

        # 2️⃣  dbfull  →  live dbfull
        grand_total += self._migrate_database(
            source_client  = self.local_client,
            source_db_name = self.live_dbfull_db_name,
            target_db_name = self.live_dbfull_db_name,
            section_title  = f"DATABASE  '{self.live_dbfull_db_name}'  →  '{self.live_dbfull_db_name}'",
        )

        wall_elapsed = time.time() - wall_start
        rate_overall = grand_total / wall_elapsed if wall_elapsed else 0

        print("\n" + "═"*70)
        print("🏁  MIGRATION COMPLETE")
        print(f"    Total docs migrated : {grand_total:,}")
        print(f"    Wall-clock time     : {wall_elapsed:.1f}s")
        print(f"    Overall throughput  : {rate_overall:,.0f} docs/s")
        print("═"*70)
        return True

    # ──────────────────────────────────────────
    def disconnect(self):
        for client, label in [
            (self.local_client, "local"),
            (self.live_client,  "live"),
        ]:
            if client:
                try:
                    client.close()
                    print(f"✅  Closed {label} MongoDB connection")
                except Exception:
                    pass


# ══════════════════════════════════════════════════════════════════════════════
def main():
    migrator = FastMongoDBMigrator(
        local_url      = LOCAL_MONGODB_URL,
        live_url       = LIVE_MONGODB_URL,
        local_db       = LOCAL_DB_NAME,
        live_local_db  = LIVE_LOCAL_DB_NAME,   # ← was missing before
        live_dbfull_db = LIVE_DB_NAME,
    )

    try:
        ok = migrator.migrate_all()
        if not ok:
            print("❌  Migration failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️   Migration interrupted by user")
        sys.exit(1)
    except Exception as exc:
        print(f"\n❌  Unexpected error: {exc}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        migrator.disconnect()


if __name__ == "__main__":
    main()