"""Periodic, idempotent one-minute summary sync from each InfluxDB into PostgreSQL.
Only fully closed windows are synchronized. A checkpoint advances only after a successful DB commit.
"""
import asyncio,logging
from datetime import datetime,timezone,timedelta
from sqlalchemy.dialects.postgresql import insert
from app.db import Session
from app.models import Summary,SyncCheckpoint
from app.influx import minute_summaries
from app.config import settings
logging.basicConfig(level=settings.log_level)
log=logging.getLogger('gs.sync')

def floor_minute(t):return t.replace(second=0,microsecond=0)

async def sync_satellite(satellite_id):
    async with Session() as s:
        checkpoint=await s.get(SyncCheckpoint,satellite_id)
        end=floor_minute(datetime.now(timezone.utc))-timedelta(minutes=1)
        start=checkpoint.through if checkpoint else end-timedelta(minutes=60)
        if start>=end:return 0
        # Bound each pass; backfill older history through repeated iterations.
        end=min(end,start+timedelta(hours=6))
        rows=await minute_summaries(satellite_id,start.isoformat(),end.isoformat())
        count=0
        for (channel_id,field,window_start),data in rows.items():
            if data.get('count') is None or data.get('mean') is None:continue
            values=dict(satellite_id=satellite_id,channel_id=channel_id,field=field,window_start=window_start,count=int(data['count']),mean=float(data['mean']),minimum=float(data.get('minimum',data['mean'])),maximum=float(data.get('maximum',data['mean'])),stddev=float(data.get('stddev') or 0))
            stmt=insert(Summary).values(**values)
            stmt=stmt.on_conflict_do_update(index_elements=['satellite_id','channel_id','field','window_start'],set_={k:values[k] for k in ('count','mean','minimum','maximum','stddev')})
            await s.execute(stmt);count+=1
        if checkpoint:checkpoint.through=end
        else:s.add(SyncCheckpoint(satellite_id=satellite_id,through=end))
        await s.commit()
        return count

async def main():
    while True:
        for sat in ('SAT-A','SAT-B'):
            try: log.info('%s: synchronized %d windows',sat,await sync_satellite(sat))
            except Exception:log.exception('%s sync failed; checkpoint unchanged',sat)
        await asyncio.sleep(max(10,settings.sync_interval_seconds))
if __name__=='__main__':asyncio.run(main())
