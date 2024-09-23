import azure.functions as func
import azure.durable_functions as df
from activityfunctions.getnfslist import Nfsbloblist
from activityfunctions.divide import Divide
from activityfunctions.getblobnfsmetrics import Blobnfsmetrics
from services.promethus_service import Promethus
import json
import logging

myApp = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)


# An HTTP-Triggered Function with a Durable Functions Client binding
@myApp.route(route="orchestrators/sddrlddr_orchestrator")
@myApp.durable_client_input(client_name="client")
async def http_start(req: func.HttpRequest, client):
    # logger = logging.getLogger('azure')
    # logger.setLevel(logging.WARNING)
    function_name = req.route_params.get("sddrlddr_orchestrator")
    instance_id = await client.start_new("sddrlddr_orchestrator", None, None)
    response = await client.wait_for_completion_or_create_check_status_response(
        req, instance_id, timeout_in_milliseconds=500000
    )
    return response


# Orchestrator
@myApp.orchestration_trigger(context_name="context")
def sddrlddr_orchestrator(context):
    nfsblobaccounts = yield context.call_activity("getnfsbloblist")
    blobnfs_metrics_parallel = []
    bloblist_final = []
    # logging.info(f"BlobNFS account list are {nfsblobaccounts}")
    for i in nfsblobaccounts:
        blobnfs_list_divided = yield context.call_activity("divideaccounts", i["data"])
        # logging.info(f"Divided batch of blobnfs monitor {blobnfs_list_divided}")
        blobnfs_metrics_parallel.extend(
            [
                context.call_activity(
                    "getnfsblobmetrics",
                    {"credential_key": i["credential_key"], "data": db},
                )
                for db in blobnfs_list_divided
            ]
        )

    bloblist_final = yield context.task_all(blobnfs_metrics_parallel)
    logging.info(f"bloblist_final {bloblist_final}")
    json_list = []
    for mainlist in bloblist_final:
        for sublist in mainlist:
            if sublist is not None:
                json_list.append(sublist)
    promethus_output = Promethus.collector(metriclist=json_list)
    logging.info(f"Prometheus Output {promethus_output}")
    return promethus_output


# Activity
@myApp.activity_trigger(input_name="name")
async def getnfsbloblist(name: str):
    try:
        blobnfsaccounts = await Nfsbloblist.getnfsbloblistfunction()
        return blobnfsaccounts
    except Exception as e:
        logging.error(f"Error with NFSbloblist function {e}")
        return []


@myApp.activity_trigger(input_name="blobnfslist")
def divideaccounts(blobnfslist):
    try:
        divided_list = Divide.dividefunction(blobnfslist)
        return divided_list
    except Exception as e:
        logging.error(f"Error with dividing list {e}")
        return []


@myApp.activity_trigger(input_name="component")
async def getnfsblobmetrics(component):
    try:
        responseoutput = await Blobnfsmetrics.nfsmetricfunction(component)
        return responseoutput
    except Exception as e:
        logging.error(f"Error in get nfs metrics {e}")
        return []
