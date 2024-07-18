from paapi5_python_sdk.api.default_api import DefaultApi
from paapi5_python_sdk.models.partner_type import PartnerType
from paapi5_python_sdk.models.search_items_request import SearchItemsRequest
from paapi5_python_sdk.models.search_items_resource import SearchItemsResource
from paapi5_python_sdk.models.get_items_request import GetItemsRequest
from paapi5_python_sdk.models.get_items_resource import GetItemsResource
from paapi5_python_sdk.models.condition import Condition
from paapi5_python_sdk.rest import ApiException
from response_parser import parse_response, parse_get_response
from consts import *
import logging



#get item 
def get_item(item_id: str):
    default_api = DefaultApi(
        access_key=AMAZON_ACCESS_KEY,
        secret_key=AMAZON_SECRET_KEY,
        host=AMAZON_HOST,
        region=AMAZON_REGION,
    )


    """ Choose resources you want from GetItemsResource enum """
    """ For more details, refer: https://webservices.amazon.com/paapi5/documentation/get-items.html#resources-parameter """
    get_items_resource = [
        GetItemsResource.ITEMINFO_TITLE,
        GetItemsResource.OFFERS_LISTINGS_PRICE,
        GetItemsResource.IMAGES_PRIMARY_LARGE,
        GetItemsResource.OFFERS_LISTINGS_SAVINGBASIS,
        GetItemsResource.ITEMINFO_FEATURES,
        GetItemsResource.OFFERS_LISTINGS_PROMOTIONS,
        GetItemsResource.OFFERS_LISTINGS_CONDITION,
        GetItemsResource.OFFERS_LISTINGS_ISBUYBOXWINNER,
    ]

    """ Forming request """

    try:
        get_items_request = GetItemsRequest(
            partner_tag=PARTNER_TAG,
            partner_type=PartnerType.ASSOCIATES,
            item_ids=[item_id],
            marketplace="www.amazon.it",
            resources=get_items_resource
        )
        print("Request:")
        print(get_items_request.to_dict())

    except ValueError as exception:
        print("Error in forming GetItemsRequest: ", exception)
        return

    try:
        """ Sending request """
        response = default_api.get_items(get_items_request)

        logging.info(f"RESPONSE: {response.items_result}")

        if response.items_result is not None:
            logging.info("Ok")
            res = parse_get_response(response)
            logging.info(f"res: {res}")

        # errors = response['errors']

        """ Parse response """
        # if errors is None:
            # print("Printing all item information in ItemsResult:")
            # res = parse_get_response(response)
            # if item_id in res:
            #     item = res[item_id]
            #     if item is not None:
            #         if item.asin is not None:
            #             print("ASIN: ", item.asin)
            #         if item.detail_page_url is not None:
            #             print("DetailPageURL: ", item.detail_page_url)
            #         if (
            #             item.item_info is not None
            #             and item.item_info.title is not None
            #             and item.item_info.title.display_value is not None
            #         ):
            #             print("Title: ", item.item_info.title.display_value)
            #         if (
            #             item.offers is not None
            #             and item.offers.listings is not None
            #             and item.offers.listings[0].price is not None
            #             and item.offers.listings[0].price.display_amount is not None
            #         ):
            #             print(
            #                 "Buying Price: ",
            #                 item.offers.listings[0].price.display_amount,
            #             )
        # else:
        #     print("Item not found, check errors")
        return res
        
        if response.errors is not None:
            print("\nPrinting Errors:\nPrinting First Error Object from list of Errors")
            print("Error code", response.errors[0].code)
            print("Error message", response.errors[0].message)
        return None
        
    except ApiException as exception:
        print("Error calling PA-API 5.0!")
        print("Status code:", exception.status)
        print("Errors :", exception.body)
        print("Request ID:", exception.headers["x-amzn-RequestId"])

    except TypeError as exception:
        print("TypeError :", exception)

    except ValueError as exception:
        print("ValueError :", exception)

    except Exception as exception:
        print("Exception :", exception)



# function that search amazon products
def search_items( search_index="All", item_page=1, item_count = 20, min_sale = 15, min_rate = 4):
    default_api = DefaultApi(
        access_key=AMAZON_ACCESS_KEY,
        secret_key=AMAZON_SECRET_KEY,
        host=AMAZON_HOST,
        region=AMAZON_REGION,
    )

    """ Specify the category in which search request is to be made """
    """ For more details, refer: https://webservices.amazon.com/paapi5/documentation/use-cases/organization-of-items-on-amazon/search-index.html """

    """ Specify item count to be returned in search result """
    # item_count = 20

    """ Choose resources you want from SearchItemsResource enum """
    """ For more details, refer: https://webservices.amazon.com/paapi5/documentation/search-items.html#resources-parameter """
    search_items_resource = [
        SearchItemsResource.ITEMINFO_TITLE,
        SearchItemsResource.OFFERS_LISTINGS_PRICE,
        SearchItemsResource.IMAGES_PRIMARY_LARGE,
        SearchItemsResource.OFFERS_LISTINGS_SAVINGBASIS,
        SearchItemsResource.ITEMINFO_FEATURES,
        SearchItemsResource.OFFERS_LISTINGS_PROMOTIONS,
        SearchItemsResource.OFFERS_LISTINGS_CONDITION,
        SearchItemsResource.OFFERS_LISTINGS_ISBUYBOXWINNER,
    ]

    """ Forming request """
    try:
        search_items_request = SearchItemsRequest(
            partner_tag=PARTNER_TAG,
            partner_type=PartnerType.ASSOCIATES,
            search_index=search_index,
            item_count=item_count,
            resources=search_items_resource,
            item_page=item_page,
            keywords=search_index,
            min_reviews_rating=min_rate,
            min_saving_percent=min_sale
        )
    except ValueError as exception:
        print("Error in forming SearchItemsRequest: ", exception)
        return

    try:
        """Sending request"""
        response = default_api.search_items(search_items_request)
        print("Request received")
        res = parse_response(response)

        if response.errors is not None:
            print("\nPrinting Errors:\nPrinting First Error Object from list of Errors")
            print("Error code", response.errors[0].code)
            print("Error message", response.errors[0].message)
        return res

    except ApiException as exception:
        print("Error calling PA-API 5.0!")
        print("Status code:", exception.status)
        print("Errors :", exception.body)
        print("Request ID:", exception.headers["x-amzn-RequestId"])

    except TypeError as exception:
        print("TypeError :", exception)

    except ValueError as exception:
        print("ValueError :", exception)

    except Exception as exception:
        print("Exception :", exception)
