import azure.functions as func
import azure.durable_functions as df
from activityfunctions.getnfslist import Nfsbloblist
from activityfunctions.divide import Divide
from activityfunctions.getblobnfsmetrics import Blobnfsmetrics
from services.promethus_service import Promethus
import json
import logging
import itertools
myApp = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# An HTTP-Triggered Function with a Durable Functions Client binding
@myApp.route(route="sddrlddr_orchestrator")
@myApp.durable_client_input(client_name="client")
async def http_start(req: func.HttpRequest, client:df.DurableOrchestrationClient):
    instance_id = await client.start_new('sddrlddr_orchestrator',None,None)
    response=await client.wait_for_completion_or_create_check_status_response(
        req,
        instance_id,
        timeout_in_milliseconds=400000
        )
    return response

# Orchestrator
@myApp.orchestration_trigger(context_name="context")
def sddrlddr_orchestrator(context):
    nfsblobaccounts=yield context.call_activity('getnfsbloblist')
    blobnfs_metrics_parallel=[]
    bloblist_final=[]
    for i in nfsblobaccounts:
        blobnfs_list_divided=yield context.call_activity('divideaccounts',i['data'])
        blobnfs_metrics_parallel.extend([context.call_activity("getnfsblobmetrics",{"credential_key":i['credential_key'],"data":db}) for db in blobnfs_list_divided])
    bloblist_final=yield context.task_all(blobnfs_metrics_parallel)
    json_list=list(itertools.chain(*bloblist_final))
    promethus_output=Promethus.collector(metriclist=json_list)
    return promethus_output
    

# Activity
@myApp.activity_trigger(input_name="name")
async def getnfsbloblist(name: str):
    try:
        blobnfsaccounts=await Nfsbloblist.getnfsbloblistfunction()
        return blobnfsaccounts
    except Exception as e:
        logging.error(f"Error with NFSbloblist function {e}")

@myApp.activity_trigger(input_name="blobnfslist")
def divideaccounts(blobnfslist):
    try:
        divided_list=Divide.dividefunction(blobnfslist)
        return divided_list
    except Exception as e:
        logging.error(f"Error with dividing list {e}")

@myApp.activity_trigger(input_name="component")
async def getnfsblobmetrics(component):
    try:
        responseoutput=await Blobnfsmetrics.nfsmetricfunction(component)
        return responseoutput
    except Exception as e:
        logging.error(f"Error in get nfs metrics {e}")

