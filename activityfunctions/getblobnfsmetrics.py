import logging
import json
from services.auth_service import AuthService
import asyncio
import azure.functions as func
from services.auth_service import AuthService
from services.monitor_service import MonitorService

class Blobnfsmetrics:
    def __init__(self) -> None:
        pass

    async def nfsmetricfunction(name):
        credential,cloud=AuthService.get_credential(name['credential_key'])
        #print("Name Data")
        #print(name['data'])
        async with credential:
            metric=await MonitorService.get_metrics_for_data(
                credential=credential,
                data=name['data'],
                metricnames="UsedCapacity"
            )
        logging.info(metric)  
        return metric
