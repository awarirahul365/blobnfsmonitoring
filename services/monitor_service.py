from datetime import datetime, timedelta
from time import time
import logging
import asyncio
from statistics import mean
import json
from azure.mgmt.monitor.aio import MonitorManagementClient
from azure.mgmt.monitor.models import (
    Metric,
    MetricValue,
    MetricCollection,
    TimeSeriesElement,
    MetadataValue,
)
from azure.core.credentials_async import AsyncTokenCredential
from msrestazure.azure_cloud import Cloud, AZURE_PUBLIC_CLOUD

from shared_code.utilities import get_resource_value, gather_with_concurrency

from typing import Optional, Any


class MonitorService(object):
    """Class that handles the interaction with the Azure Monitor API to obtain resources' metrics"""

    @staticmethod
    async def _get_metrics(
        credential: AsyncTokenCredential,
        resource_id: str,
        metricnames: str,
        range: Optional[dict] = None,
        interval: Optional[dict] = None,
        timestamp: Optional[str] = None,
        filter: Optional[str] = None,
        timeout: float = 3600.0,
        aggregation: str = "average",
        cloud: Cloud = AZURE_PUBLIC_CLOUD,
    ):
        if timestamp is not None:
            timestamp = datetime.fromisoformat(timestamp)
        else:
            timestamp = datetime.utcnow()

        if range is None:
            range = {"hours": 1}

        now = timestamp
        past = now - timedelta(**range)
        timespan = f"{past}/{now}"

        if interval is not None:
            interval = timedelta(**interval)

        t0 = time()
        data = None
        subscription_id = get_resource_value(resource_id, "/subscriptions")
        client = MonitorManagementClient(
            credential=credential,
            subscription_id=subscription_id,
            base_url=cloud.endpoints.resource_manager,
            credential_scopes=[cloud.endpoints.resource_manager + "/.default"],
        )
        async with client:
            try:
                task = asyncio.create_task(
                    client.metrics.list(
                        resource_id,
                        metricnames=metricnames,
                        timespan=timespan,
                        interval=interval,
                        aggregation=aggregation,
                        filter=filter,
                    )
                )
                data: MetricCollection = await asyncio.wait_for(task, timeout=timeout)
            except asyncio.TimeoutError:
                logging.warning(
                    f"The metric fetching for '{resource_id}' has timed out."
                )
            except Exception as ex:
                logging.error(f"Error getting metrics: {ex}")

        logging.info(
            "The metric fetching for '{}' took {:.3f}s".format(resource_id, time() - t0)
        )

        if data is None or not hasattr(data, "value"):
            return None

        result = {}
        value: Metric
        for value in data.value:
            try:
                timeseries: list[TimeSeriesElement] = value.timeseries
                result[value.name.value] = {
                    "unit": value.unit,
                    "description": value.display_description,
                    "resource": [],
                }
                for element in timeseries:
                    timeseries_data: list[MetricValue] = element.data
                    metadata: list[MetadataValue] = element.metadatavalues
                    latest = MonitorService._latest_value(
                        timeseries_data, aggregation=aggregation
                    )
                    output = {
                        "timeseries": timeseries_data,
                        "latest": latest,
                        "metadata": metadata,
                    }
                    result[value.name.value]["resource"].append(output)
            except Exception as ex:
                logging.error(f"{ex}")

        return result

    @staticmethod
    async def get_metrics_single_resource(
        credential: AsyncTokenCredential,
        resource_id: str,
        metricnames: str,
        range: Optional[dict] = None,
        interval: Optional[dict] = None,
        timestamp: Optional[str] = None,
        filter: Optional[str] = None,
        timeout: float = 3600.0,
        aggregation: str = "average",
        cloud: Cloud = AZURE_PUBLIC_CLOUD,
    ):
        """Method that fetches metrics for a single Azure resource

        Args:
            credential: token credential that has access the resource.
            resource_id: The identifier of the resource.
            metricnames: single string with the desired metric names, separated by commas.
            range: total time range of the fetched metrics in dictionary format.
                Default is {"hours": 1}.
            interval: time interval between elements in the returned timeseries in dictionary format.
                Default is {"minutes": 5}
            timestamp: UTC timestamp of the latest value in the timeseries.
                Default is current timestamp (now).
            filter: Addional filter for resources or metrics (can allow splitting).
            aggregation: The list of aggregation types (comma separated) to retrieve.
            timeout: number of seconds allowed to wait for the API response.
            cloud: Azure cloud instance to indicate where are the resources.
        Returns:
            Metric dictionary that contains the full timeseries and latest value
        """
        data = None
        async with credential:
            data = await MonitorService._get_metrics(
                credential,
                resource_id,
                metricnames=metricnames,
                range=range,
                interval=interval,
                timestamp=timestamp,
                timeout=timeout,
                aggregation=aggregation,
                filter=filter,
                cloud=cloud,
            )
        return data

    @staticmethod
    async def get_metrics_for_data(
        credential: AsyncTokenCredential,
        data: list[dict],
        metricnames: str,
        range: Optional[dict] = None,
        interval: Optional[dict] = None,
        timestamp: Optional[str] = None,
        aggregation: str = "average",
        filter: Optional[str] = None,
        num_threads: Optional[int] = None,
        timeout: float = 3600.0,
        cloud: Cloud = AZURE_PUBLIC_CLOUD,
    ):
        """Method that fetches metrics for a list of Azure resources

        Args:
            credential: token credential that has access to all resources in the list.
            data: list with the resource information.
                For each element it is required its Resource ID with key "id".
            metricnames: single string with the desired metric names, separated by commas.
            range: total time range of the fetched metrics in dictionary format.
                Default is {"hours": 1}.
            interval: time interval between elements in the returned timeseries in dictionary format.
                Default is {"minutes": 5}
            timestamp: UTC timestamp of the latest value in the timeseries.
                Default is current timestamp (now).
            aggregation: The list of aggregation types (comma separated) to retrieve.
            filter: Addional filter for resources or metrics (can allow splitting)
            num_threads: if given, maximum number of resources that will be simultaneously processed.
            timeout: number of seconds allowed to wait for the API response.
            cloud: Azure cloud instance to indicate where are the resources.
        Returns:
            data_with_metrics: similar list as the input data, but now each element has an additional
                "metrics" dictionary with the full timeseries and latest value.
        """
        n = len(data)
        logging.info(f"Fetching metrics for {n} resources...")

        t0 = time()
        data_with_metrics = []
        async with credential:
            tasks = [
                asyncio.create_task(
                    MonitorService._get_metrics(
                        credential,
                        elem["id"],
                        metricnames=metricnames,
                        range=range,
                        interval=interval,
                        timestamp=timestamp,
                        timeout=timeout,
                        aggregation=aggregation,
                        filter=filter,
                        cloud=cloud,
                    )
                )
                for elem in data
            ]
            if num_threads is not None:
                metrics = await gather_with_concurrency(num_threads, *tasks)
            else:
                metrics = await asyncio.gather(*tasks)

        data_with_metrics = [
            {
                **elem,
                "metrics": round(
                    float(
                        metric["UsedCapacity"]["resource"][0]["latest"]["average"]
                        / (1024**3)
                    ),
                    2,
                ),
            }
            for elem, metric in zip(data, metrics)
        ]
        logging.info("Total metric fetching for took {:.3f}s".format(time() - t0))
        logging.info(f"Metric with value of UsedCapacity for {data_with_metrics}")
        return data_with_metrics

    @staticmethod
    def _latest_value(
        timeseries: list[MetricValue], aggregation: str = "average", default: Any = None
    ) -> dict:

        if aggregation is None:
            aggregation = "average,maximum,minimum,total"

        aggregation_list = aggregation.split(",")
        default_dict = {key: default for key in aggregation_list}
        output = {**default_dict, "time_stamp": None}
        # iterate the timeseries from the latest value onwards
        for aggregation in aggregation_list:
            for metric_value in timeseries[::-1]:
                try:
                    value = getattr(metric_value, aggregation)
                    time_stamp = metric_value.time_stamp.isoformat()
                except:
                    continue

                if value != None and time_stamp != None:
                    output[aggregation] = value
                    output["time_stamp"] = time_stamp
                    break

        return output

    @staticmethod
    def expand_stats(timeseries: list[MetricValue], aggregation: str = "average"):
        """Calculates the average, maximum and minimum values of a timeseries from Azure Monitor"""
        stats = {"total_average": None, "max": None, "min": None}
        try:
            value_lst = [getattr(value, aggregation) for value in timeseries]
            # filter out the non-numeric values to avoid issues
            value_lst = [value for value in value_lst if value is not None]
            stats["total_average"] = mean(value_lst)
            stats["max"] = max(value_lst)
            stats["min"] = min(value_lst)
        except Exception as ex:
            logging.error(f"Error expanding stats: {ex}")

        return stats
