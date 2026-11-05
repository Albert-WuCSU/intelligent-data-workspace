"""User-approved soft estimate budget. No keys, prompts, rows, refunds or reset API."""
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

from pydantic import BaseModel
from .auth import PublicError
from .retention_native import PinnedObject, pin_directories
from .upload_preflight import checked_runtime_path

UNIT = Decimal('0.25')
TARGET = Decimal('15')
CEILING = Decimal('20')
MAX_REQUESTS = 60
# One SDK task reserves the approved 2 USD estimate as eight 0.25 USD units.
# The ledger is an estimate campaign, not a provider bill; units are never refunded.
SDK_TASK_RESERVE_UNITS = 8
SDK_TASK_RESERVE_USD = '2.00'

class EstimatedBudgetSummary(BaseModel):
    mode: str = 'estimated_soft_budget'
    estimated_reserved_usd: str
    estimated_remaining_usd: str
    target_usd: str = '15'
    planning_ceiling_usd: str = '20'
    per_request_estimate_usd: str = '0.25'
    reserved_requests: int
    max_requests: int = 60
    hard_cost_guarantee: bool = False

class EstimatedBudget:
    """Fixed project campaign, protected SQLite transaction; reservations never refunded."""
    def __init__(self, root):
        self.root = Path(root).absolute()

    @contextmanager
    def _database(self):
        try:
            if os.name != 'nt':raise ValueError('requires verified Windows pinning')
            checked_runtime_path(self.root,self.root)
            self.root.mkdir(parents=True,exist_ok=True)
            with ExitStack() as stack:
                pin_directories(stack,self.root,self.root,delete_folder=False)
                path=self.root/'estimated-budget.sqlite3'
                checked_runtime_path(self.root,path)
                # Create empty file exclusively; unknown existing DB/schema is not reinitialized.
                created=False
                try:
                    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd);created=True
                except FileExistsError:pass
                obj=stack.enter_context(PinnedObject(self.root,path,mutable=True))
                if obj.size>2*1024*1024:raise ValueError('ledger oversized')
                db=sqlite3.connect(path,timeout=1,isolation_level=None)
                stack.callback(db.close)
                db.execute('PRAGMA journal_mode=DELETE')
                db.execute('BEGIN IMMEDIATE')
                try:
                    tables={x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    if created:
                        if tables:raise ValueError('unexpected new file')
                        db.execute('CREATE TABLE campaign (id INTEGER PRIMARY KEY, version INTEGER NOT NULL, unit_cents INTEGER NOT NULL, max_requests INTEGER NOT NULL)')
                        db.execute('INSERT INTO campaign VALUES (1,1,25,60)')
                        db.execute('CREATE TABLE reservations (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, outcome TEXT NOT NULL, input_tokens INTEGER, output_tokens INTEGER)')
                    elif tables != {'campaign','reservations'}:
                        raise ValueError('unknown or interrupted ledger')
                    if db.execute('SELECT * FROM campaign').fetchall()!=[(1,1,25,60)]:raise ValueError('campaign changed')
                    rows=db.execute('SELECT id,created_at,outcome,input_tokens,output_tokens FROM reservations LIMIT 61').fetchall()
                    if len(rows)>60 or any(r[2] not in ('reserved_unknown','completed','failed_or_unknown') for r in rows):raise ValueError('ledger inconsistent')
                    yield db
                    db.execute('COMMIT')
                except BaseException:
                    db.execute('ROLLBACK');raise
        except PublicError:raise
        except (OSError,ValueError,sqlite3.Error):
            raise PublicError(503,'MODEL_BUDGET_UNAVAILABLE','估算账本不可用或正忙，未发起新请求；不要删除账本，请稍后重试。') from None

    def summary(self):
        with self._database() as db:
            count=db.execute('SELECT count(*) FROM reservations').fetchone()[0]
        amount=UNIT*count
        return EstimatedBudgetSummary(estimated_reserved_usd=str(amount.quantize(Decimal('0.00'))),
            estimated_remaining_usd=str(max(Decimal(0),TARGET-amount).quantize(Decimal('0.00'))),reserved_requests=count)

    async def reserve(self, *, request_bytes, max_output_tokens):
        # Only the currently approved small request regime, never caller-priced.
        if type(request_bytes) is not int or not 0<request_bytes<=16384 or type(max_output_tokens) is not int or not 0<max_output_tokens<=128:
            raise PublicError(422,'MODEL_BUDGET_REQUEST_LIMIT','请求超出本轮估算预算适用范围，未调用模型。')
        id=str(uuid4())
        with self._database() as db:
            count=db.execute('SELECT count(*) FROM reservations').fetchone()[0]
            if count>=MAX_REQUESTS:
                raise PublicError(409,'MODEL_ESTIMATED_BUDGET_EXHAUSTED','估算预算已到15美元或60次请求，请复核实际费用后再决定；不会自动继续。')
            db.execute('INSERT INTO reservations VALUES (?,?,?,NULL,NULL)',(id,datetime.now(timezone.utc).isoformat(),'reserved_unknown'))
        return id

    async def reserve_sdk_task(self):
        """Reserve the approved 2 USD estimate before any SDK model call.

        The fixed ledger unit is 0.25 USD; one SDK task therefore occupies eight
        units. This keeps the existing ledger schema and the 15 USD / 60 unit
        campaign unchanged. No refund on failure or cancellation.
        """
        ids = [str(uuid4()) for _ in range(SDK_TASK_RESERVE_UNITS)]
        with self._database() as db:
            count = db.execute('SELECT count(*) FROM reservations').fetchone()[0]
            if count + len(ids) > MAX_REQUESTS:
                raise PublicError(
                    409,
                    'MODEL_ESTIMATED_BUDGET_EXHAUSTED',
                    '估算预算不足以为本任务预留2美元（15美元/60次单元）；不会自动继续，请复核实际费用。',
                )
            for reservation_id in ids:
                db.execute(
                    'INSERT INTO reservations VALUES (?,?,?,NULL,NULL)',
                    (reservation_id, datetime.now(timezone.utc).isoformat(), 'reserved_unknown'),
                )
        return ids

    def finish_sdk_task(self, ids, input_tokens=None, output_tokens=None):
        """Close all units of one SDK task; only one unit records usage."""
        if not isinstance(ids, (list, tuple)) or not 1 <= len(ids) <= SDK_TASK_RESERVE_UNITS:
            raise ValueError('invalid sdk reservation set')
        if len(set(ids)) != len(ids) or any(not isinstance(item, str) for item in ids):
            raise ValueError('invalid sdk reservation set')
        if input_tokens is not None and (type(input_tokens) is not int or input_tokens < 0):
            input_tokens = None
        if output_tokens is not None and (type(output_tokens) is not int or output_tokens < 0):
            output_tokens = None
        with self._database() as db:
            for index, reservation_id in enumerate(ids):
                if input_tokens is None or output_tokens is None:
                    db.execute(
                        "UPDATE reservations SET outcome='failed_or_unknown' WHERE id=? AND outcome='reserved_unknown'",
                        (reservation_id,),
                    )
                elif index == 0:
                    db.execute(
                        "UPDATE reservations SET outcome='completed',input_tokens=?,output_tokens=? WHERE id=? AND outcome='reserved_unknown'",
                        (input_tokens, output_tokens, reservation_id),
                    )
                else:
                    db.execute(
                        "UPDATE reservations SET outcome='completed' WHERE id=? AND outcome='reserved_unknown'",
                        (reservation_id,),
                    )

    def finish(self, id, generation=None):
        # Only safe usage/outcome is persisted; no output/prompt/model Key in DB.
        with self._database() as db:
            if generation is None:
                db.execute("UPDATE reservations SET outcome='failed_or_unknown' WHERE id=? AND outcome='reserved_unknown'",(id,))
            else:
                db.execute("UPDATE reservations SET outcome='completed',input_tokens=?,output_tokens=? WHERE id=? AND outcome='reserved_unknown'",(generation.input_tokens,generation.output_tokens,id))

    def receipt_outcome(self,id):
        with self._database() as db:
            row=db.execute('SELECT outcome FROM reservations WHERE id=?',(id,)).fetchone()
        return row[0] if row else None
