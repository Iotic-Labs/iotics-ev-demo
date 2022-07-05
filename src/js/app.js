// needs the conf in conf.js

var availablePropKeys = [
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
    'https://data.iotics.com/app#Model',
    'http://data.iotics.com/iotics/host_id',
    'http://demo.iotics.com/ont/demo/isDemoTwin',
    'http://demo.iotics.com/ont/ev/date_last_status_update',
    'http://demo.iotics.com/ont/ev/date_last_verified',
    'http://schema.org/address',
    'http://schema.org/description',
    'http://schema.org/identifier',
    'http://schema.org/name',
    'http://schema.org/price',
    'http://www.productontology.org/doc/UUID',
    'http://www.w3id.org/urban-iot/electric#hasPowerSupply',
    'http://www.w3id.org/urban-iot/electric#isFastCharger',
    'http://www.w3id.org/urban-iot/electric#isOperational',
    'http://www.w3id.org/urban-iot/electric#isPrivate',
    'http://www.w3id.org/urban-iot/electric#max_amperage_in_A',
    'http://www.w3id.org/urban-iot/electric#max_power_in_kW',
    'http://www.w3id.org/urban-iot/electric#max_voltage_in_V',
    'http://www.w3id.org/urban-iot/electric#numberOfConnectors',
    'http://www.w3id.org/urban-iot/electric#operated_by',
    'http://www.w3id.org/urban-iot/electric#uses_charging_station',
]

var availableDataTypes = [
    "boolean",
    "double",
    "decimal",
    "int",
    "string"
]

var possibleValues = [
    'http://www.w3id.org/urban-iot/electric#ChargingStation',
    'http://www.w3id.org/urban-iot/electric#Connector',
    'http://schema.org/Place',
    'http://schema.org/Service',
    'http://www.productontology.org/doc/Algorithm',
    'http://www.productontology.org/doc/Application',
    'http://www.productontology.org/doc/Forecast',
    'http://www.productontology.org/doc/Linear_regression',
    'http://www.productontology.org/doc/Predictive_analytics',
    "true",
    "false",
]


var found_twins = {};

var feeds_subscribed = [];

var chargersTable = null;
var chargersTableData = [];

var connectionsTable = null;
var connectionsTableData = [];

var predictionsTable = null;
var predictionsTableData = [];

var applicationTwinsTable = null;
var applicationTwinsTableData = [];


var connect_callback = function () {
    console.log("stompClient connected...")

    found_twins = {}
    feeds_subscribed = []

    // subscribe to search
    h = def_h()
    h["id"] = nextSequence()
    try {
        var subscription = stompClient.subscribe("/qapi/searches/results", search_callback, h);
        console.log("subscribed to async search..." + JSON.stringify(subscription))
    } catch (err) {
        console.log("unable to subscribe to search results " + err)
    }
};

var error_callback = function (error) {
    // display the error's message header:
    e = error
    if (typeof (e.headers) === undefined) {
        e = e.headers.message
    }
    console.error("some error when handling the websocket: " + e);
};

var close_event_callback = function (error) {
    if (typeof (error.headers) !== "undefined") {
        console.error("close event from websocket: " + error.headers.message);
    } else {
        console.warning("some event on websocket received - unable to interpret it: " + error);
    }
}

function app_init() {

    var confId = $('#hosts_select option:selected').attr("id");

    qapi = GetConf(confId)["qapi"]
    wss = GetConf(confId)["wss"]

    color = GetConf(confId)["bgcolor"]

    $('body').css('background-color', color);

    stompClient = Stomp.client(wss);
    stompClient.debug = function (str) {
        // append the debug log to a #debug div somewhere in the page using JQuery:
        if (str !== ">>> PING" && str !== "<<< PONG" && str.length <= 1) {
            console.log("STOMP CLIENT:\n" + str + "\n");
        }
        return null
    };

    userName = $("#userName").val();
    userNameKey = userName
    userSeed = $("#userSeed").val();

    agentSeed = $("#agentSeed").val()
    agentName = $("#agentName").val();
    agentNameKey = agentName

    qapi_spec = qapi + "/openapi.json"

    iotics_init(agentSeed, agentName, agentNameKey, userSeed, userName, userNameKey, qapi, qapi_spec).then(() => {
        stompClient.heartbeat.outgoing = 1000; // stompClient will send heartbeats every 20000ms
        stompClient.heartbeat.incoming = 1000; // stompClient does not want to receive heartbeats from the server
        stompClient.reconnect_delay = 5000;
        console.log("connecting...")
        console.log("token... " + jwtTokenJSON.token)
        stompClient.connect({
            passcode: jwtTokenJSON.token
        }, connect_callback, error_callback);
    }).then(() => {

        $("#connect_container").hide()
        $("#disconnect_container").show()
        $("#main_container").show()

        saveLoginData()
    })
}

function fill_host_select_options() {
    var confId = $('#hosts_select option:selected').attr("id");
    var conf = GetConf(confId)

    $("#userName").val(conf["userName"])
    $("#userSeed").val(conf["userSeed"])
    $("#agentName").val(conf["agentName"])
    $("#agentSeed").val(conf["agentSeed"])

    $('body').css('background-color', conf["bgcolor"]);
    $('#spaceName').html(conf["agentName"] + " @ " + conf["endpoint"]);

}


function app_teardown() {
    stompClient.disconnect(function () {
        $("#connect_container").show()
        $("#disconnect_container").hide()
        $("#main_container").hide()
    })
    clean_data()

}

// what to do with the next message
var message_callback = function (message) {
    // headers received as map
    dest = message.headers["destination"];
    // body received as a string
    var jsonBody = JSON.parse(message.body);
    // payload encoded in b64
    var value = atob(jsonBody.feedData.data);

    var feed = jsonBody.interest.followedFeed.feed
    var twin_id = feed.twinId.value;
    var field_key = feed.id.value
    var table_upd = {}
    table_upd["id"] = twin_id
    table_upd[field_key] = value

    var table = null
    if (chargersTable.getData().find(e => e.id === twin_id)) {
        table = chargersTable
    } else if (connectionsTable.getData().find(e => e.id === twin_id)) {
        table = connectionsTable
    } else if (predictionsTable.getData().find(e => e.id === twin_id)) {
        table = predictionsTable
    } else if (applicationTwinsTable.getData().find(e => e.id === twin_id)) {
        table = applicationTwinsTable
    }

    if (table) {
        table.updateData([table_upd]).then(e => {
            table.deselectRow()
            table.getRows()
                .filter(row => row.getData().id == twin_id)
                .forEach(row => row.toggleSelect());
        })

    }

};

var propVal2Val = function (v) {
    val = v.split("/")
    return val[val.length - 1]
}

var prop2obj = function (p) {
    k = propVal2Val(p.key)
    v = null
    if (typeof (p.langLiteralValue) !== "undefined") {
        v = p.langLiteralValue.value
    } else if (typeof (p.literalValue) !== "undefined") {
        v = p.literalValue.value
    } else if (typeof (p.stringLiteralValue) !== "undefined") {
        v = p.stringLiteralValue.value
    } else if (typeof (p.uriValue) !== "undefined") {
        v = p.uriValue.value
    }
    return { key: k, value: v }
}

function clean_data() {
    chargersTable.clearData()
    connectionsTable.clearData()
    applicationTwinsTable.clearData()
    predictionsTable.clearData()
}

var search_callback = function (message) {

    // process the result of a search request to repackage the data in tabular format
    // specifically some of the properties and some of the feeds

    // we also detect the feeds we want to subscribe to...
    var processEnt = function (type, hostId, arr) {
        filtered = arr.filter(p => p.types.includes(type))
        result = []
        feeds = []
        // for each entity of the type we care
        filtered.forEach(f => {
            cdata = {
                // we set the ID to its twin_did
                id: f.id
            }
            f.feeds.forEach(p => {
                // each feed k/v is a column
                feed_id = make_full_feed_id(agent_did, hostId, p.feed.twinId.value, p.feed.id.value)
                // ...and a feed_id to subscribe to.
                feeds.push(feed_id)
                // when a feed arrives, the id col will match the entity, then we find the feed by it's name (ie the column)
                cdata[p.feed.id.value] = ""
            })
            f.props.forEach(p => {
                // each prop k/v is a column
                var po = prop2obj(p);
                cdata[po.key] = po.value
            })
            result.push(cdata)
        })
        return [result, feeds]
    }

    new Promise((resolve, reject) => {
        searchResponse = JSON.parse(message.body)
        twins = searchResponse.twins
        remoteHost = null
        hostStr = "localhost"
        if (searchResponse.remoteHostId != null) {
            remoteHost = searchResponse.remoteHostId.value
            hostStr = remoteHost
        }
        if (twins.length > 0) {
            console.log("received search response from " + hostStr + " for " + message.headers["Iotics-ClientRef"] + " - found #" + twins.length + " twins")
        }
        found_twins = twins.map(function (ent) {
            prop = ent.properties.filter(p => p.key === ("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"))
            if (prop.length == 0) {
                return null
            }
            console.log(hostStr)
            prop2 = prop.map(p => propVal2Val(p.uriValue.value))
            return {
                id: ent.id.value,
                types: prop2,
                feeds: ent.feeds,
                props: ent.properties,
            };
        }).filter(ent => ent != null);

        chargersTablePoints = processEnt("electric#ChargingStation", remoteHost, found_twins)
        connectionsTablePoints = processEnt("electric#Connector", remoteHost, found_twins)
        predictionsTablePoints = processEnt("Algorithm", remoteHost, found_twins)
        applicationTwinsTablePoints = processEnt("Application", remoteHost, found_twins)

        // we subscribe to all the feeds from the twins found on this search
        sub1 = new Promise((resolve, reject) => {
            resolve(connectionsTablePoints[1].concat(chargersTablePoints[1]).concat(predictionsTablePoints[1]).concat(applicationTwinsTablePoints[1]))
        }).then(feeds => feeds.forEach(p => {
            console.log("subscribing to '" + p + "'")
            subNow = feeds_subscribed[p]
            if (subNow == null) {
                headers = def_h()
                headers["id"] = nextSequence()
                sub = stompClient.subscribe(p, message_callback, headers)
                feeds_subscribed[p] = sub
                console.log("subscribed to " + p)
            } else {
                console.log("already subscribed to " + p)
            }
        }))
        resolve([chargersTablePoints[0], connectionsTablePoints[0], predictionsTablePoints[0], applicationTwinsTablePoints[0]]);
    }).then(data => {
        if (data[0].length > 0) {
            var p
            if (chargersTable.getData().length == 0) {
                p = chargersTable.setData(data[0])
            } else {
                p = chargersTable.updateOrAddData(data[0])
            }
            p.then(function () {
                console.log("table loaded for charging stations")
            }).catch(function (error) {
                //handle error loading data
            });
        }
        if (data[1].length > 0) {
            var p
            if (connectionsTable.getData().length == 0) {
                p = connectionsTable.setData(data[1])
            } else {
                p = connectionsTable.updateOrAddData(data[1])
            }
            p.then(function () {
                console.log("table loaded for connections")
            }).catch(function (error) {
                //handle error loading data
            });

        }
        if (data[2].length > 0) {
            var p
            if (predictionsTable.getData().length == 0) {
                p = predictionsTable.setData(data[2])
            } else {
                p = predictionsTable.updateOrAddData(data[2])
            }
            p.then(function () {
                console.log("table loaded for predictions")
            }).catch(function (error) {
                //handle error loading data
            });
        }
        if (data[3].length > 0) {
            var p
            if (applicationTwinsTable.getData().length == 0) {
                p = applicationTwinsTable.setData(data[3])
            } else {
                p = applicationTwinsTable.updateOrAddData(data[3])
            }
            p.then(function () {
                console.log("table loaded for application twins")
            }).catch(function (error) {
                //handle error loading data
            });
        }
    })
};

function openModal(content) {
    html = "<pre><code class='language-json'>" + content + "</code></pre>"
    $("#content").html(html)
    $("#overlay").removeClass("is-hidden")
}

function closeModal() {
    $("#content").html("")
    $("#overlay").addClass("is-hidden")
}

function saveLoginData() {
    storage = window.localStorage;
    storage.setItem("userName", userName);
    storage.setItem("agentName", agentName);
    storage.setItem("userSeed", userSeed);
    storage.setItem("agentSeed", agentSeed);
}


function app_ui_init(confJson) {

    storage = window.localStorage;
    var fields = ["userName", "agentName", "userSeed", "agentSeed"];
    fields.forEach(function (value, _) {
        $("#" + value).change(function () {
            val = $(this).val();
            storage.setItem(value, val);
        });
    });
    fields.forEach(function (value, index) {
        val = storage.getItem(value);
        $("#" + value).val(val);
    });

    $("#connect_container").show()
    $("#disconnect_container").hide()
    $("#main_container").hide()

    sel = true
    $.each(confJson, function (key, value) {
        selected = ""
        if (sel) {
            sel = false
            selected = "selected"
        }
        e = key + ": " + value.endpoint
        console.log("selection: " + e)
        $('#hosts_select').append('<option id="' + key + '" ' + selected + ' value="' + key + '">' + e + '</option>');
    });
    fill_host_select_options();

    for (i = 1; i <= 3; i++) {
        $("#searchPropKey_" + i).autocomplete({
            source: availablePropKeys,
        })
        $("#searchDataType_" + i).autocomplete({
            source: availableDataTypes,
        })
        $("#searchDataType_" + i).focusout(function () {
            if ($("#searchDataType_" + i).val().startsWith("http://")) {
                $("searchIsValueUri_" + i).prop('checked', true);
            }
        })
        $("#searchPropValue_" + i).autocomplete({
            source: possibleValues,
        })
    }

    $("#debug").html("")
    $("#debug").click(function () {
        $("#debug").html("")
    })

    function doDescribe(row) {
        describe(qapi, row.getData().id).then(
            (resp) => {
                console.log(resp)
                openModal(JSON.stringify(resp.body, undefined, 2))
            },
            (reason) => console.log("unable to describe: " + reason))

    }

    chargersTable = new Tabulator("#chargers", {
        autoColumns: true,
        selectable: true,
        data: chargersTableData,   //load row data from array
        rowDblClick: function (e, row) {
            doDescribe(row)
        },
    });

    connectionsTable = new Tabulator("#connections", {
        autoColumns: true,
        selectable: true,
        data: connectionsTableData,   //load row data from array
        rowDblClick: function (e, row) {
            doDescribe(row)
        },
    });

    predictionsTable = new Tabulator("#predictions", {
        autoColumns: true,
        selectable: true,
        data: predictionsTableData,   //load row data from array
        rowDblClick: function (e, row) {
            doDescribe(row)
        },
    });

    applicationTwinsTable = new Tabulator("#applicationTwins", {
        autoColumns: true,
        selectable: true,
        data: applicationTwinsTableData,   //load row data from array
        rowDblClick: function (e, row) {
            doDescribe(row)
        },
    });

    //trigger download of data.xlsx file
    document.getElementById("chargers-download-xlsx").addEventListener("click", function () {
        chargersTable.download("xlsx", "chargers-data.xlsx", { sheetName: "My Data" });
    });

    //trigger download of data.xlsx file
    document.getElementById("connections-download-xlsx").addEventListener("click", function () {
        chargersTable.download("xlsx", "connections-data.xlsx", { sheetName: "My Data" });
    });

    //trigger download of data.xlsx file
    document.getElementById("predictions-download-xlsx").addEventListener("click", function () {
        connectionsTable.download("xlsx", "predictions-data.xlsx", { sheetName: "My Data" });
    });

    //trigger download of data.xlsx file
    document.getElementById("applicationTwins-download-xlsx").addEventListener("click", function () {
        connectionsTable.download("xlsx", "applicationTwins-data.xlsx", { sheetName: "My Data" });
    });

}

function isBlank(str) {
    return (!str || /^\s*$/.test(str));
}

function statusMessage(message) {
    $("#debug").html(message)
}

function uiSearch() {
    text = $("#searchText").val()
    place = $("#searchPlace").val()
    radius = $("#searchRadius").val()
    local = !$("#searchGlobalScope").is(":checked")

    var getGeo = function (where) {
        uri = "https://api.opencagedata.com/geocode/v1/json?q=" + where + "&key=dba090bcf34643fb8064082a54ff4e22"
        return fetch(uri).then(function (response) {
            if (!response.ok) {
                throw Error(response.statusText);
            }
            return response.json();
        })
    }

    var doSearch = (async function () {
        geoResult = null
        if (!isBlank(place)) {
            geoResult = await getGeo(place.trim())
        }
        searchRequest = new SearchRequest()
        searchRequest.setScope(local)
        if (geoResult != null) {
            // we pick the first result if it e
            results = geoResult.results
            if (results.length > 0) {
                var loc = results[0].geometry
                if (typeof (loc) !== "undefined") {
                    radius = parseInt(radius)
                    if (isNaN(radius)) {
                        statusMessage("invalid radius")
                        return
                    }
                    searchRequest.location({ 'lat': loc.lat, 'lon': loc.lng }, radius)
                } else {
                    statusMessage("this place doesn't have geo: " + place)
                }
            } else {
                statusMessage("can't find the place: " + place)
            }
        }
        if (!isBlank(text)) {
            searchRequest.text(text.trim())
        }

        for (i = 1; i <= 3; i++) {
            key = $("#searchPropKey_" + i).val()
            value = $("#searchPropValue_" + i).val()
            isUri = $("#searchIsValueUri_" + i).prop('checked')
            dataType = $("#searchDataType_" + i).val()

            if (!isBlank(key)) {
                if (isUri) {
                    searchRequest.addUriValueProperty(key, value)
                } else if (!isBlank(dataType)) {
                    searchRequest.addLiteralValueProperty(key, value, dataType)
                } else {
                    searchRequest.addStringLiteralValueProperty(key, value)
                }
            }
        }

        if (!searchRequest.valid()) {
            statusMessage("Nothing to search! - search invalid")
        } else {
            search(searchRequest)
        }

        return false

    })

    return doSearch()
}
