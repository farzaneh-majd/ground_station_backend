# Seed definitions for demo only. Replace with authoritative F Prime TopologyDictionary mapping.
DEFAULT_FIELDS = [
 ('1','LED State','EPS',[{'key':'state','name':'LED State','format':'u8','unit':None}]),
 ('2','IMU Data','ADCS',[{'key':'ax','name':'Acceleration X','format':'f32','unit':'m/s²'},{'key':'ay','name':'Acceleration Y','format':'f32','unit':'m/s²'},{'key':'az','name':'Acceleration Z','format':'f32','unit':'m/s²'}]),
 ('3','Environment Data','Payload',[{'key':'temperature','name':'Temperature','format':'f32','unit':'°C'},{'key':'humidity','name':'Humidity','format':'f32','unit':'%'}]),
]
