def evaluate(value, limits: dict | None) -> str:
    if not isinstance(value,(int,float)) or isinstance(value,bool): return 'UNKNOWN'
    limits = limits or {}
    for bound,comparison in [('criticalLow',lambda a,b:a<b),('criticalHigh',lambda a,b:a>b)]:
        if limits.get(bound) is not None and comparison(value,limits[bound]): return 'CRITICAL'
    for bound,comparison in [('warningLow',lambda a,b:a<b),('warningHigh',lambda a,b:a>b)]:
        if limits.get(bound) is not None and comparison(value,limits[bound]): return 'WARNING'
    return 'GOOD' if limits else 'UNKNOWN'
