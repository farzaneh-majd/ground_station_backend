import struct
import re

FORMATS = {'u8':'B','u16':'H','u32':'I','i8':'b','i16':'h','i32':'i','f32':'f'}
HEX = re.compile(r'^(?:[0-9a-fA-F]{2})*$')

def normalize_hex(payload: str) -> str:
    clean = payload.strip().replace(' ', '').removeprefix('0x').removeprefix('0X')
    if not HEX.fullmatch(clean): raise ValueError('Payload must contain complete hexadecimal bytes')
    return clean.upper()

def decode(telemetry_id: str, payload: str, channel=None) -> dict:
    payload = normalize_hex(payload)
    data = bytes.fromhex(payload)
    if channel is None:
        return {'telemetryId':telemetry_id,'name':'Unknown telemetry','kind':'unknown','rawPayload':payload,'byteLength':len(data),'values':{},'fields':[]}
    fields = channel.fields or []
    offset=0;values={};decoded=[]
    for field in fields:
        fmt=FORMATS.get(field.get('format'))
        if not fmt: raise ValueError(f'Unsupported field format: {field.get("format")}')
        size=struct.calcsize(fmt)
        if offset+size>len(data): raise ValueError('Packet is shorter than telemetry definition')
        endian = '<' if field.get('endian',channel.endian)=='little' else '>'
        value=struct.unpack_from(endian+fmt,data,offset)[0]
        offset+=size
        key=field['key'];values[key]=value
        decoded.append({'name':field.get('name',key),'value':value,'unit':field.get('unit'),'format':field['format']})
    if offset!=len(data): raise ValueError('Packet length does not match telemetry definition')
    return {'telemetryId':telemetry_id,'name':channel.name,'kind':channel.kind,'rawPayload':payload,'byteLength':len(data),'values':values,'fields':decoded}
