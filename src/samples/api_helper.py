import logging
import random
import time

from threading import Thread
from typing import Callable, Iterable, List, Tuple
import grpc

from google.protobuf.wrappers_pb2 import StringValue, BoolValue
from google.protobuf.timestamp_pb2 import Timestamp
from iotics.api import search_pb2_grpc
from iotics.api import twin_pb2_grpc
from iotics.api import feed_pb2_grpc
from iotics.api import interest_pb2_grpc
from iotics.api.common_pb2 import FeedData, GeoLocation, Headers, HostID, Property, PropertyUpdate, StringLiteral, \
    SubscriptionHeaders, Scope, TwinID, FeedID, Values, Value, Uri, Literal, Visibility
from iotics.api.search_pb2 import SearchRequest, ResponseType
from iotics.api.twin_pb2 import DeleteTwinRequest, DeleteTwinResponse, DescribeTwinRequest, DescribeTwinResponse, GeoLocationUpdate, \
    ListAllTwinsRequest, ListAllTwinsResponse, \
    CreateTwinRequest, CreateTwinResponse, \
    UpdateTwinRequest, UpdateTwinResponse, \
    VisibilityUpdate
from iotics.api.interest_pb2 import CreateInterestResponse, \
    FetchInterestRequest,  \
    Interest
from iotics.api.feed_pb2 import DescribeFeedRequest, \
    Feed, CreateFeedRequest, CreateFeedResponse, \
    ShareFeedDataRequest, ShareFeedDataResponse, \
    UpdateFeedRequest, UpdateFeedResponse

from samples.identity_helper import IdHelper

logger = logging.getLogger("evdemo")
logger.setLevel(level=logging.DEBUG)


class ApiHelper():

    def __init__(self, id_helper: IdHelper) -> None:
        super().__init__()
        self.__id_helper = id_helper

        self.__grpc_channel = None
        self.__last_jwt_token = None

        self.__twin_api = TwinApi(self)
        self.__search_api = SearchApi(self)
        self.__interest_api = InterestApi(self)
        self.__feed_api = FeedApi(self)
        self.__init_grpc_channel()

    def make_headers(self, client_app_id: str = None, client_ref: str = None, timeout: int = None) -> Headers:
        return Headers(clientAppId=client_app_id,
                       clientRef=client_ref,
                       requestTimeout=self.make_timestamp(seconds=timeout),
                       transactionRef=[ApiHelper.randTxRef()])

    def __init_grpc_channel(self):
        # create a new grpc channel everytime the jwt token changes
        if self.__last_jwt_token != self.__id_helper.jwt_token:
            self.__last_jwt_token = self.__id_helper.jwt_token
            call_credentials = grpc.access_token_call_credentials(self.__id_helper.jwt_token)
            channel_credentials = grpc.ssl_channel_credentials()
            composite_credentials = \
                grpc.composite_channel_credentials(channel_credentials, call_credentials)
            self.__grpc_channel = grpc.secure_channel(f"{self.__id_helper.space_dns}:10001",
                                                      credentials=composite_credentials)

    @staticmethod
    def randTxRef():
        return f't-{random.randint(1_000_000_000, 9_999_999_999)}'

    @staticmethod
    def randClientRef():
        return f'c-{random.randint(1_000_000_000, 9_999_999_999)}'

    @staticmethod
    def make_timestamp(seconds: int = None) -> Timestamp:
        if seconds is None:
            return None

        now_seconds = int(time.time())
        return Timestamp(seconds=now_seconds + seconds)

    @staticmethod
    def make_sub_headers(client_app_id: str = None) -> SubscriptionHeaders:
        return SubscriptionHeaders(clientAppId=client_app_id,
                                   transactionRef=[ApiHelper.randTxRef()])

    @staticmethod
    def make_property_string(predicate: str, obj: str) -> Property:
        return Property(key=predicate, stringLiteralValue=StringLiteral(value=obj))

    @staticmethod
    def make_property_bool(predicate: str, obj: bool) -> Property:
        value = "true" if obj else "false"
        return Property(key=predicate, literalValue=Literal(dataType="boolean", value=value))

    @staticmethod
    def make_property_uri(predicate: str, obj: str) -> Property:
        return Property(key=predicate, uriValue=Uri(value=obj))

    @staticmethod
    def make_property_literal(predicate: str, obj: str, datatype) -> Property:
        return Property(key=predicate, literalValue=Literal(value=obj, dataType=datatype))

    @property
    def id_helper(self):
        return self.__id_helper

    @property
    def twin_api(self):
        return self.__twin_api

    @property
    def search_api(self):
        return self.__search_api

    @property
    def interest_api(self):
        return self.__interest_api

    @property
    def feed_api(self):
        return self.__feed_api

    @property
    def grpc_channel(self) -> grpc.Channel:
        self.__init_grpc_channel()
        return self.__grpc_channel


class TwinApi:

    def __init__(self, api_helper: ApiHelper) -> None:
        self.__api_helper = api_helper

    def list(self) -> ListAllTwinsResponse:
        twin_stub = twin_pb2_grpc.TwinAPIStub(self.__api_helper.grpc_channel)
        headers = self.__api_helper.make_headers(client_app_id=self.__api_helper.id_helper.agent_registered_id.did)
        list_req = ListAllTwinsRequest(headers=headers)
        return twin_stub.ListAllTwins(list_req)

    def describe_twin(self, did: str) -> DescribeTwinResponse:
        twin_stub = twin_pb2_grpc.TwinAPIStub(self.__api_helper.grpc_channel)
        headers = self.__api_helper.make_headers(client_app_id=self.__api_helper.id_helper.agent_registered_id.did)
        describe_req = DescribeTwinRequest(headers=headers,
                                           args=DescribeTwinRequest.Arguments(twinId=TwinID(value=did)))
        return twin_stub.DescribeTwin(describe_req)

    def delete_twin(self, did: str) -> DeleteTwinResponse:
        twin_stub = twin_pb2_grpc.TwinAPIStub(self.__api_helper.grpc_channel)
        headers = self.__api_helper.make_headers(client_app_id=self.__api_helper.id_helper.agent_registered_id.did)
        delete_req = DeleteTwinRequest(headers=headers,
                                       args=DeleteTwinRequest.Arguments(twinId=TwinID(value=did)))
        return twin_stub.DeleteTwin(delete_req)

    def create_twin(self, did: str) -> CreateTwinResponse:
        twin_stub = twin_pb2_grpc.TwinAPIStub(self.__api_helper.grpc_channel)
        headers = self.__api_helper.make_headers(client_app_id=self.__api_helper.id_helper.agent_registered_id.did)
        create_req = CreateTwinRequest(headers=headers,
                                       payload=CreateTwinRequest.Payload(twinId=TwinID(value=did)))
        return twin_stub.CreateTwin(create_req)

    def replace_twin_properties(self, did: str, properties: List[Property]) -> UpdateTwinResponse:
        # the list of properties here will be the only (non-system) properties on the twin as clearedAll is set to true
        twin_stub = twin_pb2_grpc.TwinAPIStub(self.__api_helper.grpc_channel)
        headers = self.__api_helper.make_headers(client_app_id=self.__api_helper.id_helper.agent_registered_id.did)

        payload = UpdateTwinRequest.Payload(properties=PropertyUpdate(added=properties,
                                                                      clearedAll=True))
        update_req = UpdateTwinRequest(headers=headers,
                                       args=UpdateTwinRequest.Arguments(twinId=TwinID(value=did)),
                                       payload=payload)
        return twin_stub.UpdateTwin(update_req)

    def update_twin_visibility(self, did: str, visibility: Visibility) -> UpdateTwinResponse:
        twin_stub = twin_pb2_grpc.TwinAPIStub(self.__api_helper.grpc_channel)
        headers = self.__api_helper.make_headers(client_app_id=self.__api_helper.id_helper.agent_registered_id.did)

        payload = UpdateTwinRequest.Payload(newVisibility=VisibilityUpdate(visibility=visibility))

        args = UpdateTwinRequest.Arguments(twinId=TwinID(value=did))
        update_req = UpdateTwinRequest(headers=headers,
                                       args=args,
                                       payload=payload)
        return twin_stub.UpdateTwin(update_req)

    def update_twin_location(self, did: str, location: Tuple) -> UpdateTwinResponse:
        twin_stub = twin_pb2_grpc.TwinAPIStub(self.__api_helper.grpc_channel)
        headers = self.__api_helper.make_headers(client_app_id=self.__api_helper.id_helper.agent_registered_id.did)

        location_update = GeoLocationUpdate(location=GeoLocation(lat=location[0], lon=location[1]))

        payload = UpdateTwinRequest.Payload(location=location_update)
        update_req = UpdateTwinRequest(headers=headers,
                                       args=UpdateTwinRequest.Arguments(twinId=TwinID(value=did)),
                                       payload=payload)
        return twin_stub.UpdateTwin(update_req)


class FeedApi:

    def __init__(self, api_helper) -> None:
        self.__api_helper = api_helper

    def create_feed(self, did: str, feed_name: str) -> CreateFeedResponse:
        feed_stub = feed_pb2_grpc.FeedAPIStub(self.__api_helper.grpc_channel)
        headers = self.__api_helper.make_headers(client_app_id=self.__api_helper.id_helper.agent_registered_id.did)
        create_req = CreateFeedRequest(headers=headers,
                                       payload=CreateFeedRequest.Payload(feedId=FeedID(value=feed_name)),
                                       args=CreateFeedRequest.Arguments(twinId=TwinID(value=did)))
        return feed_stub.CreateFeed(create_req)

    def update_feed(self, twin_id: str, feed_name: str,
                    values: List[Value], properties: List[Property], store_last: bool = False) -> UpdateFeedResponse:
        feed_stub = feed_pb2_grpc.FeedAPIStub(self.__api_helper.grpc_channel)
        headers = self.__api_helper.make_headers(client_app_id=self.__api_helper.id_helper.agent_registered_id.did)
        values = Values(added=values)
        properties = PropertyUpdate(clearedAll=True,
                                    added=properties)
        update_req = UpdateFeedRequest(headers=headers,
                                       payload=UpdateFeedRequest.Payload(storeLast=BoolValue(value=store_last),
                                                                         values=values,
                                                                         properties=properties),
                                       args=UpdateFeedRequest.Arguments(feed=Feed(
                                           id=FeedID(value=feed_name),
                                           twinId=TwinID(value=twin_id))))
        return feed_stub.UpdateFeed(update_req)

    def describe_feed(self, twin_id: str, feed_name: str) -> DescribeTwinResponse:
        feed_stub = feed_pb2_grpc.FeedAPIStub(self.__api_helper.grpc_channel)
        headers = self.__api_helper.make_headers(client_app_id=self.__api_helper.id_helper.agent_registered_id.did)
        describe_req = DescribeFeedRequest(headers=headers,
                                           args=DescribeFeedRequest.Arguments(feed=Feed(
                                               id=FeedID(value=feed_name),
                                               twinId=TwinID(value=twin_id))))
        return feed_stub.DescribeFeed(describe_req)

    def share_feed_data(self, twin_id: str, feed_name: str, payload: str) -> ShareFeedDataResponse:
        feed_stub = feed_pb2_grpc.FeedAPIStub(self.__api_helper.grpc_channel)
        headers = self.__api_helper.make_headers(client_app_id=self.__api_helper.id_helper.agent_registered_id.did)
        share_req = ShareFeedDataRequest(headers=headers,
                                         payload=ShareFeedDataRequest.Payload(
                                             sample=FeedData(occurredAt=Timestamp(seconds=int(time.time())),
                                                             mime="text/json",
                                                             data=bytes(payload, 'utf-8'))),
                                         args=ShareFeedDataRequest.Arguments(
                                             feed=Feed(id=FeedID(value=feed_name),
                                                       twinId=TwinID(value=twin_id))))
        return feed_stub.ShareFeedData(share_req)

    @staticmethod
    def make_value(label: str, comment: str, unit: str, datatype: str) -> Value:
        return Value(label=label, comment=comment, unit=unit, dataType=datatype)


class InterestApi:

    def __init__(self, api_helper) -> None:
        self.__api_helper = api_helper

    def create_interest_local(self, twin_id: str, feed_id: str) -> CreateInterestResponse:
        raise NotImplementedError
        # interest_stub = interest_pb2_grpc.InterestAPIStub(self.__api_helper.grpc_channel)
        # headers = self.__api_helper.make_headers(client_app_id=self.__api_helper.id_helper.agent_registered_id.did)
        # payload = CreateInterestRequest.Payload(
        #                                         interest=Interest(
        #                                             followedFeed=Interest.FollowedFeed(
        #                                                     feed=Feed(id=FeedID(value=feed_id))
        #                                                 ),
        #                                             followerTwinId=TwinID(value=twin_id)
        #                                         ))
        # create_req = CreateInterestRequest(headers=headers,
        #                                    payload=payload)
        # return interest_stub.CreateInterest(create_req)

    def fetch_interest_iter(self, follower_twin_id: str, twin_id: str, feed_id: str, remote_host_id: str = None) -> Iterable:
        while True:
            interest_stub = interest_pb2_grpc.InterestAPIStub(self.__api_helper.grpc_channel)
            headers = self.__api_helper.make_headers(client_app_id=self.__api_helper.id_helper.agent_registered_id.did)
            args = FetchInterestRequest.Arguments(
                interest=Interest(
                    followedFeed=Interest.FollowedFeed(
                        feed=Feed(id=FeedID(value=feed_id),
                                  twinId=TwinID(value=twin_id)),
                        hostId=HostID(value=remote_host_id)
                    ),
                    followerTwinId=TwinID(value=follower_twin_id)
                ))

            fetch_req = FetchInterestRequest(headers=headers,
                                             args=args,
                                             fetchLastStored=BoolValue(value=False))

            try:
                stream = interest_stub.FetchInterests(fetch_req)
                for resp in stream:
                    yield resp
            except grpc.RpcError as err:
                if err.code() == grpc.StatusCode.UNAUTHENTICATED:  # pylint: disable=no-member
                    logger.info("fetch_interest_iter - JWT timed out, retrying")
                    continue
                elif err.code() == grpc.StatusCode.NOT_FOUND:  # pylint: disable=no-member
                    logger.info(f'NOT FOUND: {twin_id}/{feed_id}')
                    break
            # except grpc.RpcError as err: #TODO terminated error condition
            #     if err.code() == grpc.StatusCode.????:  # pylint: disable=no-member
            #         logger.info("JWT timed out, retrying")
            #         continue
                else:
                    logger.error(f'rpc error fetch_interest_iter of {twin_id}/{feed_id}: {err}')
                    break

    def fetch_interest_callback(self,
                                follower_twin_id: str,
                                twin_id: str,
                                feed_id: str,
                                callback: Callable,
                                remote_host_id=None) -> Callable:
        def cb_caller():
            for resp in self.fetch_interest_iter(follower_twin_id,
                                                 twin_id,
                                                 feed_id,
                                                 remote_host_id=remote_host_id):
                callback(resp)

        bg_thread = Thread(target=cb_caller)  # TODO Thread pool executor
        bg_thread.start()

        # return "stop" function to the caller for them to call
        return bg_thread.join


class SearchPayloadBuilder:
    def __init__(self):
        self.__reset()

    def __reset(self):
        self.__response_type = ResponseType.FULL
        self.__text = None
        self.__location = None
        self.__properties = None
        self.__language = None

    def build(self) -> SearchRequest.Payload:
        payload = SearchRequest.Payload(
            responseType=self.response_type,
            filter=SearchRequest.Payload.Filter(text=self.text,
                                                location=self.location,
                                                properties=self.properties))
        self.__reset()
        return payload

    @property
    def response_type(self) -> ResponseType:
        return self.__response_type

    @response_type.setter
    def response_type(self, value: ResponseType):
        self.__response_type = value

    @property
    def text(self) -> str:
        return self.__text

    @text.setter
    def text(self, value: str):
        self.__text = StringValue(value=value)

    @property
    def location(self):
        return self.__location

    @location.setter
    def location(self, value):
        self.__location = value

    @property
    def properties(self) -> List[Property]:
        return self.__properties

    @properties.setter
    def properties(self, value: List[Property]):
        self.__properties = value

    @property
    def language(self):
        return self.__language

    @language.setter
    def language(self, value):
        self.__language = value


class SearchApi:

    def __init__(self, api_helper) -> None:
        self.__api_helper: ApiHelper = api_helper
        self.__timeout = None
        self.__search_callbacks: dict = dict()

    def register_callback(self, clientRef, callback):
        if callback is None:
            self.__search_callbacks.pop(clientRef)
            return
        self.__search_callbacks[clientRef] = callback

    def receive_search_responses(self, timeout=8600):
        time_start = int(time.time())
        while True:
            try:
                search_stub = search_pb2_grpc.SearchAPIStub(self.__api_helper.grpc_channel)
                sub_headers = self.__api_helper.make_sub_headers(
                    client_app_id=self.__api_helper.id_helper.agent_registered_id.did)
                stream = search_stub.ReceiveAllSearchResponses(sub_headers, timeout=timeout)
                for resp in stream:
                    cRef = resp.headers.clientRef
                    callback = self.__search_callbacks[cRef]
                    if callback is not None:
                        callback(resp)
            except grpc.RpcError as err:
                if err.code() == grpc.StatusCode.DEADLINE_EXCEEDED:  # pylint: disable=no-member
                    logger.info("Application timeout reached. Stopped the search subscription (receive_search_responses)")
                    break
                elif err.code() == grpc.StatusCode.UNAUTHENTICATED:  # pylint: disable=no-member
                    logger.info("receive_search_responses - JWT timed out, retrying")
                    self.__timeout -= (int(time.time()) - time_start)  # remove the elapsed time from the timeout
                    if self.__timeout <= 0:
                        break
                    continue
                else:
                    # the callback may raise too
                    logger.error(f'rpc error receive_search_responses: {err}')
        return "Done"

    def dispatch_search_request_async(self,
                                      payload: SearchRequest.Payload,
                                      scope: Scope = Scope.LOCAL,
                                      client_ref: str = None,
                                      timeout: int = None):
        self.__timeout = timeout
        search_stub = search_pb2_grpc.SearchAPIStub(self.__api_helper.grpc_channel)

        headers = self.__api_helper.make_headers(
            client_app_id=self.__api_helper.id_helper.agent_registered_id.did,
            client_ref=client_ref,
            timeout=timeout)
        search_req = SearchRequest(
            headers=headers,
            scope=scope,
            payload=payload)
        # NB have to get the stream before dispatching the search request or we'll miss some

        search_stub.DispatchSearchRequest(search_req)
        # TODO: timer to unregister the callback with this clientRef

    def dispatch_search_request(self,
                                payload: SearchRequest.Payload,
                                scope: Scope = Scope.LOCAL,
                                client_ref: str = None,
                                timeout: int = None) -> grpc.Channel.unary_stream:
        self.__timeout = timeout

        sub_headers = self.__api_helper.make_sub_headers(
            client_app_id=self.__api_helper.id_helper.agent_registered_id.did)

        search_stub = search_pb2_grpc.SearchAPIStub(self.__api_helper.grpc_channel)

        search_req = SearchRequest(
            headers=self.__api_helper.make_headers(
                client_app_id=self.__api_helper.id_helper.agent_registered_id.did,
                client_ref=client_ref,
                timeout=timeout),
            scope=scope,
            payload=payload)
        # NB have to get the stream before dispatching the search request or we'll miss some
        result_stream = search_stub.ReceiveAllSearchResponses(sub_headers, timeout=timeout)
        search_stub.DispatchSearchRequest(search_req)
        return result_stream

    def process_results_stream(self, stream) -> Iterable:
        time_start = int(time.time())
        while True:
            try:
                for resp in stream:
                    yield resp
            except grpc.RpcError as err:
                if err.code() == grpc.StatusCode.DEADLINE_EXCEEDED:  # pylint: disable=no-member
                    logger.info(
                        f'Application timeout reached. Stopped the search subscription (process_results_stream) {err}')
                    break
                if err.code() == grpc.StatusCode.UNAUTHENTICATED:  # pylint: disable=no-member
                    logger.info("process_results_stream - JWT timed out, retrying")
                    self.__timeout -= (int(time.time()) - time_start)  # remove the elapsed time from the timeout
                    if self.__timeout <= 0:
                        break
                    search_stub = search_pb2_grpc.SearchAPIStub(self.__api_helper.grpc_channel)
                    sub_headers = self.__api_helper.make_sub_headers(
                        client_app_id=self.__api_helper.id_helper.agent_registered_id.did)
                    stream = search_stub.ReceiveAllSearchResponses(sub_headers, timeout=self.__timeout)
                    continue
                logger.error(f'rpc error process_results_stream: {err}')
