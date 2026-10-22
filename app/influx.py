from datetime import datetime, timezone
from influxdb_client import Point, WritePrecision
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from app.config import settings

CONFIG = {
 'SAT-A': (settings.influx_a_url,settings.influx_a_token,settings.influx_a_org,settings.influx_a_bucket),
 'SAT-B': (settings.influx_b_url,settings.influx_b_token,settings.influx_b_org,settings.influx_b_bucket),
}
def config(satellite_id):
    if satellite_id not in CONFIG: raise ValueError('Satellite must be SAT-A or SAT-B')
    return CONFIG[satellite_id]

def client(satellite_id):
    url,token,org,bucket=config(satellite_id)
    return InfluxDBClientAsync(url=url,token=token,org=org,timeout=15000)

async def write_points(satellite_id,channel_id,telemetry_id,values,timestamp):
    _,_,org,bucket=config(satellite_id)
    points=[]
    for field,value in values.items():
        if isinstance(value,(int,float)) and not isinstance(value,bool):
            points.append(Point('telemetry').tag('satellite_id',satellite_id).tag('channel_id',channel_id).tag('telemetry_id',telemetry_id).tag('field',field).field('value',float(value)).time(timestamp,WritePrecision.NS))
    if not points: return
    async with client(satellite_id) as db:
        await db.write_api().write(bucket=bucket,org=org,record=points)

def _flux_string(value: str) -> str:
    # Escape user input as a Flux string literal; no arbitrary Flux query exposure.
    import json
    return json.dumps(value)

async def history(satellite_id,channel_id,field,start,end,limit=1000):
    _,_,org,bucket=config(satellite_id)
    limit=max(1,min(limit,10000))
    query=(f'from(bucket: {_flux_string(bucket)}) '
           f'|> range(start: time(v: {_flux_string(start)}), stop: time(v: {_flux_string(end)})) '
           f'|> filter(fn: (r) => r._measurement == "telemetry" and r.channel_id == {_flux_string(channel_id)} and r.field == {_flux_string(field)}) '
           f'|> sort(columns: ["_time"], desc: true) |> limit(n: {limit})')
    async with client(satellite_id) as db:
        tables=await db.query_api().query(query,org=org)
    rows=[{'timestamp':r.get_time(),'value':r.get_value()} for t in tables for r in t.records]
    return list(reversed(rows))

async def minute_summaries(satellite_id,start,end):
    _,_,org,bucket=config(satellite_id)
    base=(f'from(bucket: {_flux_string(bucket)}) '
          f'|> range(start: time(v: {_flux_string(start)}), stop: time(v: {_flux_string(end)})) '
          '|> filter(fn: (r) => r._measurement == "telemetry" and r._field == "value") '
          '|> group(columns: ["channel_id","field"]) ')
    result={}
    async with client(satellite_id) as db:
        for name,fn in [('mean','mean'),('minimum','min'),('maximum','max'),('count','count'),('stddev','stddev')]:
            query=base+f'|> aggregateWindow(every: 1m, fn: {fn}, createEmpty: false)'
            tables=await db.query_api().query(query,org=org)
            for t in tables:
                for rec in t.records:
                    key=(rec.values['channel_id'],rec.values['field'],rec.get_time())
                    result.setdefault(key,{})[name]=rec.get_value()
    return result
