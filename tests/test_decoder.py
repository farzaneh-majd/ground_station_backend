import struct
import pytest
from app.decoder import decode
from app.quality import evaluate
class Channel:
    name='Temperature';kind='scalar';endian='big'
    fields=[{'key':'temperature','name':'Temperature','format':'f32','unit':'C'}]

def test_decode_float():
    result=decode('3',struct.pack('>f',25.5).hex(),Channel())
    assert result['values']['temperature']==25.5

def test_short_packet():
    with pytest.raises(ValueError):decode('3','00',Channel())

def test_invalid_hex():
    with pytest.raises(ValueError):decode('3','Z1',Channel())

def test_quality():
    assert evaluate(90,{'warningHigh':80,'criticalHigh':100})=='WARNING'
    assert evaluate(110,{'warningHigh':80,'criticalHigh':100})=='CRITICAL'
    assert evaluate(50,{})=='UNKNOWN'
