from services.auth_service import AuthService
from services.subscription_service import SubscriptionService
import asyncio
from services.graph_service import GraphService
import logging


class Nfsbloblist:
    def __init__(self) -> None:
        pass

    async def _get_query_result(credential_key: str):
        credential, cloud = AuthService.get_credential(credential_key)
        query = f"""resourcecontainers 
                | where type == 'microsoft.resources/subscriptions'
                | project subscriptionName=name,subscriptionId 
                | join ( resources| where type=='microsoft.storage/storageaccounts' 
                | where name contains 'blobnfs') on subscriptionId 
                | extend Customerid=substring(resourceGroup,6,3) 
                | project subscriptionId,resourceGroup,Customerid,id,Storageaccountname=name,subscriptionName"""

        async with credential:
            subscriptions = await SubscriptionService.subscription_list(
                credential, cloud
            )
            sub_ids = SubscriptionService.filter_ids(subscriptions)
            blobnfs_list = await GraphService.run_query(
                query_str=query, credential=credential, sub_ids=sub_ids, cloud=cloud
            )
        blobnfs_dict = {"credential_key": credential_key, "data": blobnfs_list}
        return blobnfs_dict

    async def getnfsbloblistfunction():
        credential_list = AuthService.get_credential_keys()
        result = []
        try:
            result = await asyncio.gather(
                *(
                    asyncio.create_task(Nfsbloblist._get_query_result(cred))
                    for cred in credential_list
                )
            )
            return result
        except Exception as e:
            logging.error(f"Failed to fetch getnfsbloblistfunction {e}")
