from contextlib import asynccontextmanager
from datetime import datetime,timezone
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field
from strawberry.fastapi import GraphQLRouter
from sqlalchemy import select
from app.config import settings
from app.db import Session
from app.models import Satellite,Channel
from app.catalog import DEFAULT_FIELDS
from app.service import store_packet
from app.graphql import schema

@asynccontextmanager
async def lifespan(app):
    async with Session() as s:
        for sat in ['SAT-A','SAT-B']:
            if not await s.get(Satellite,sat):s.add(Satellite(id=sat,name=sat))
            for tlm,name,subsystem,fields in DEFAULT_FIELDS:
                cid=f'{sat}:{tlm}'
                if not await s.get(Channel,cid):
                    s.add(Channel(id=cid,satellite_id=sat,telemetry_id=tlm,subsystem=subsystem,name=name,kind='struct',endian='big',source='SIMULATOR',fields=fields))
        await s.commit()
    yield

app=FastAPI(title='Twin CubeSat Ground Station Backend',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(',')],allow_credentials=False,allow_methods=['GET','POST','OPTIONS'],allow_headers=['Content-Type','Authorization','X-API-Key'])
app.include_router(GraphQLRouter(schema,graphql_ide='graphiql'),prefix='/graphql')

class IngestPacket(BaseModel):
    satellite_id: str
    telemetry_id: str
    payload: str
    timestamp: datetime|None=None

async def require_ingest(x_api_key:str|None=Header(None)):
    import secrets
    if not settings.ingest_api_key or not x_api_key or not secrets.compare_digest(x_api_key,settings.ingest_api_key):
        raise HTTPException(status_code=401,detail='Invalid ingest API key')

@app.get('/health')
async def health():return {'status':'ok','service':'gs-backend'}

@app.post('/ingest/packet',dependencies=[Depends(require_ingest)])
async def ingest_packet(packet:IngestPacket):
    try:
        item=await store_packet(packet.satellite_id,packet.telemetry_id,packet.payload,packet.timestamp)
        return {'record_id':item['recordId'],'satellite_id':item['satelliteId'],'telemetry_id':item['telemetryId'],'time':item['time']}
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc

@app.post('/ingest/batch',dependencies=[Depends(require_ingest)])
async def ingest_batch(packets:list[IngestPacket]):
    if len(packets)>500:raise HTTPException(status_code=413,detail='Maximum 500 packets per batch')
    results=[]
    for p in packets:
        try:
            item=await store_packet(p.satellite_id,p.telemetry_id,p.payload,p.timestamp)
            results.append({'record_id':item['recordId'],'ok':True})
        except Exception as exc:
            results.append({'ok':False,'error':str(exc)})
    return {'results':results}
