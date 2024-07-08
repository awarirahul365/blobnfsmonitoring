import logging
import os
import azure.functions as func
from prometheus_client import CollectorRegistry,Gauge
from prometheus_client.exposition import basic_auth_handler
from prometheus_client import  generate_latest
import json

class Promethus:
    def collector(metriclist):
        registry=CollectorRegistry()
        UsedCapacity_metrics=Gauge('Used_capacity','Used Capacity for storage',['Customerid','Storageaccountname','subscriptionId'],registry=registry)
        for metric in metriclist:
            UsedCapacity_metrics.labels(
                metric['Customerid'],
                metric['Storageaccountname'],
                metric['subscriptionId']
            ).set(metric['metrics'])
        return generate_latest(registry).decode()