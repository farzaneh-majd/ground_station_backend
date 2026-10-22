from datetime import datetime,timezone
from uuid import uuid4
from sqlalchemy import select
from app.db import Session
from app.models import Channel,RawPacket,Command
from app.decoder import decode,normalize_hex
from app.influx import write_points
from app.quality import evaluate
from app.events import bus
from app.config import settings
import httpx

async def store_packet(satellite_id,telemetry_id,payload,when=None,record_id=None):
    if satellite_id not in ('SAT-A','SAT-B'): raise ValueError('Unknown satellite')
    when=when or datetime.now(timezone.utc)
    if when.tzinfo is None: raise ValueError('Timestamp must include timezone')
    async with Session() as session:
        channel=(await session.execute(select(Channel).where(Channel.satellite_id==satellite_id,Channel.telemetry_id==telemetry_id))).scalars().first()
        decoded=decode(telemetry_id,payload,channel)
        record=RawPacket(record_id=record_id or str(uuid4()),satellite_id=satellite_id,telemetry_id=telemetry_id,payload=normalize_hex(payload),time=when,decoded=decoded)
        session.add(record)
        # Write to time-series store before committing packet record.
        if channel: await write_points(satellite_id,channel.id,telemetry_id,decoded['values'],when)
        await session.commit()
    packet={'recordId':record.record_id,'satelliteId':satellite_id,'telemetryId':telemetry_id,'payload':record.payload,'time':when,'decoded':decoded}
    await bus.publish('raw',packet)
    if channel:
        for field in channel.fields:
            key=field['key']
            if key in decoded['values']:
                point={'satelliteId':satellite_id,'channelId':channel.id,'telemetryId':telemetry_id,'field':key,'timestamp':when,'value':decoded['values'][key],'unit':field.get('unit'),'quality':evaluate(decoded['values'][key],field.get('limits'))}
                await bus.publish('point',point)
    return packet

async def send_command(satellite_id,command_hex):
    if satellite_id not in ('SAT-A','SAT-B'): raise ValueError('Unknown satellite')
    command_hex=normalize_hex(command_hex)
    if not command_hex or len(command_hex)>4096: raise ValueError('Command must be 1–2048 bytes')
    record=Command(command_id=str(uuid4()),satellite_id=satellite_id,command_hex=command_hex,status='CREATED')
    async with Session() as session:
        session.add(record);await session.commit()
        if settings.command_simulation:
            record.status='QUEUED'  # Simulation never implies real RF transmission.
        elif not settings.gds_bridge_url:
            record.status='REJECTED'
        else:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response=await client.post(settings.gds_bridge_url,json={'satellite_id':satellite_id,'command_hex':command_hex,'command_id':record.command_id},headers={'Authorization':f'Bearer {settings.gds_bridge_token}'})
                    response.raise_for_status()
                    record.status='SENT' # Means bridge accepted, not spacecraft acknowledged.
                    record.response={'bridge_http_status':response.status_code}
            except Exception as exc:
                record.status='FAILED';record.response={'error':type(exc).__name__}
        await session.commit();await session.refresh(record)
    return record
