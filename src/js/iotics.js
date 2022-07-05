const go = new Go();

var subId_sequence = 0

var stompClient = null;

// utility method to build the twin loc - this should not be needed in reality since the id should be found from the search response
function make_full_feed_id(f, h, e, p) {
    hs = ""
    if (h != null) {
        hs = "/hosts/" + h
    }

    return (
        "/qapi/twins/" + f + "/interests" + hs + "/twins/" + e + "/feeds/" + p
    );
}

function SearchRequest() {
    this.scope = "LOCAL"
    this.json = {
        filter: {
            properties: [
            ],
        },
        responseType: "FULL",
    };
}

SearchRequest.prototype.valid = function (local) {
    f = this.json.filter
    return f.properties.length > 0 ||
        typeof (f.text) !== "undefined" && f.text.length > 0 ||
        typeof (f.location) !== "undefined"
}

SearchRequest.prototype.setScope = function (local) {
    if (local) {
        this.scope = "LOCAL"
    } else {
        this.scope = "GLOBAL"
    }
    return this
}

SearchRequest.prototype.addStringLiteralValueProperty = function (key, value) {
    let p = {
        key: key.trim(),
        stringLiteralValue: {
            value: value.trim(),
        }
    }
    this.json.filter.properties.push(p);
    return this
}

SearchRequest.prototype.addUriValueProperty = function (key, uri) {
    let p = {
        key: key.trim(),
        uriValue: {
            value: uri.trim(),
        }
    }
    this.json.filter.properties.push(p);
    return this
}
SearchRequest.prototype.addLangLiteralValueProperty = function (key, value, lang) {
    let p = {
        key: key.trim(),
        langLiteralValue: {
            lang: lang.trim(),
            value: value.trim(),
        }
    }
    this.json.filter.properties.push(p);
    return this
}
SearchRequest.prototype.addLiteralValueProperty = function (key, value, dataType) {
    let p = {
        key: key.trim(),
        literalValue: {
            dataType: dataType.trim(),
            value: value.trim(),
        }
    }
    this.json.filter.properties.push(p);
    return this
}
SearchRequest.prototype.text = function (text) {
    this.json.filter.text = text
    return this
}
SearchRequest.prototype.expiryTimeout = function (sec) {
    expiry = new Date();
    expiry.setSeconds(expiry.getSeconds() + expirySec);

    json.expiryTimeout = expiry.toISOString();
    return this
}

SearchRequest.prototype.location = function (loc, radiusKm) {
    this.json.filter.location = {
        location: {
            lat: loc.lat,
            lon: loc.lon,
        },
        radiusKm: radiusKm,
    }
    return this
};

function nextSequence() {
    subId_sequence = subId_sequence + 1;
    return subId_sequence
}

function search(searchReq) {
    headers = def_h()
    headers.scope = searchReq.scope
    payload = JSON.stringify(searchReq.json)
    console.log("searching for: " + payload)
    searchTemplate = stompClient.send("/qapi/searches/dispatches", headers, payload);
}

// simple short uuid func
function my_uuid(prefix = "", length = 16) {
    var result = "";
    var characters =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    var charactersLength = characters.length;
    for (var i = 0; i < length; i++) {
        result += characters.charAt(
            Math.floor(Math.random() * charactersLength)
        );
    }
    return prefix + result;
}

let mod, inst, agentKeyID, agent_did, user_did, qapi, agent_key_name, openapi_endpoint;

// default iotics headers
function def_h(to_delta_sec = 0) {
    ret = {
        "Iotics-ClientAppId": agent_did,
        "Iotics-ClientRef": my_uuid((prefix = "c-")),
        "Iotics-TransactionRef": my_uuid((prefix = "t-")),
    };
    if (to_delta_sec > 0) {
        var dt = Date.now() + to_delta_sec * 1000;
        ret["Iotics-RequestTimeout"] = new Date(dt).toISOString();
    }
    return ret;
}

function iotics_init(agent_seed, agent_name, agent_key, user_seed, user_name, user_key, qapi_ep, openapi_spec_endpoint) {

    qapi_endpoint = qapi_ep

    agent_key_name = agent_key
    user_key_name = user_key
    agent_name = agent_name
    user_name = user_name

    return WebAssembly.instantiateStreaming(
        fetch("id/id-sdk.wasm?ts=" + Date.now()),
        go.importObject
    ).then((result) => {
        mod = result.module;
        inst = result.instance;
        console.log("running instance");
        go.run(result.instance);
    }).then(() => {
        // primes the map in the sdk with the agent private key.
        console.log("making agent priv key. agent_key=" + agent_key);
        agentKeyID = NewPrivateKeyECDSAFromPathString(agent_seed, "agent", agent_key);
        console.log("made agent priv key with id: " + agentKeyID);

        console.log("making user priv key. user_key=" + user_key);
        userKeyID = NewPrivateKeyECDSAFromPathString(user_seed, "user", user_key);
        console.log("made user priv key with id: " + userKeyID);

        var agentDocString = NewDIDDocument("agent", agentKeyID);
        agentDoc = JSON.parse(agentDocString);
        agent_did = agentDoc.id;

        console.log("agent DiD: " + agent_did);

        var userDocString = NewDIDDocument("user", userKeyID);
        userDoc = JSON.parse(userDocString);
        user_did = userDoc.id;

        console.log("user DiD: " + user_did);

        $("#userDiD").text(user_did);
        $("#agentDiD").text(agent_did);

        result = NewAuthenticationDelegationToken("http://resolver", userKeyID, userDocString, agentKeyID, agentDocString)
        console.log(result)

        init_jwtGenerator(1000)

        qapi = new SwaggerClient({
            url: openapi_spec_endpoint,
            requestInterceptor: reqInterceptor,
        });
        SwaggerClient.http.withCredentials = true;
        console.log("created qapi client for " + openapi_spec_endpoint)

        logger = function (r) {
            if (typeof (r) === "undefined") {
                return "not created"
            } else {
                return "created: " + JSON.stringify(r.body)
            }
        }

        // this is being setup in del.py
        console.log("making agent priv key. twin_key=" + agent_key);
        followerKeyID = NewPrivateKeyECDSAFromPathString(agent_seed, "twin", agent_key);
        var followerDocString = NewDIDDocument("agent", followerKeyID);
        followerDoc = JSON.parse(followerDocString);
        follower_did = followerDoc.id;

        create_twin(qapi, agent_key, follower_did).then(
            response => console.log("follower twin " + logger(response)),
            reason => console.log("error creating follower twin: " + reason)
        )
    });
}

function newJwtToken(timeout) {
    jwtTokenString = NewAuthenticationToken(
        agentKeyID,
        agent_key_name, // what key name to use
        agent_did,
        user_did,
        qapi_endpoint,
        timeout //sec
    );
    return JSON.parse(jwtTokenString);
}

let jwtTokenJSON = {};
let jwtTokenRefresher = null;
function init_jwtGenerator(timeout) {
    jwtTokenJSON = newJwtToken(timeout)
    if (jwtTokenRefresher != null) {
        clearInterval(jwtTokenRefresher);
    }
    jwtTokenRefresher = setInterval(function () {
        jwtTokenJSON = newJwtToken(timeout)
    }, 1000 * (timeout - 1));
}

var reqInterceptor = (req) => {
    if (typeof jwtTokenJSON.error !== "undefined") {
        console.log("unable to get token: " + jwtTokenJSON.error);
        return;
    }
    bearer = "Bearer " + jwtTokenJSON.token;
    req.headers["Authorization"] = bearer;
    console.log("authorize called");
    return req;
};

function describe(qapi, twin_did) {
    params = def_h(10)
    params["twinId"] = twin_did
    return qapi.then(
        swaggerClient => swaggerClient.apis.Twin.describe_twin(params),
        reason => console.error("failed to load the spec: " + reason)
    );
}

function create_twin(qapi, name, twin_did) {
    return qapi.then(
        swaggerClient => {
            es = swaggerClient.apis.Twin
            params = def_h(10)

            // params["twinId"] = twin_did
            // deleted = es.delete_twin(params)
            // deleted.then(() => {
            //     console.log("aaaaaaaaaaaaaaaaaaaaa" + deleted)
            // })
            // if (true) return

            created = es.create_twin(params, {
                requestBody: {
                    "twinId": {
                        "value": twin_did
                    }
                }
            })
            params = def_h(10)
            params["twinId"] = twin_did
            updated = es.update_twin(params, {
                "requestBody": {
                    "newVisibility": {
                        "visibility": "PUBLIC"
                    },
                    "properties": {
                        "deletedByKey": [
                            "http://data.iotics.com/public#hostAllowList",
                        ],
                        "added": [
                            {
                                "uriValue": {
                                    "value": "http://www.productontology.org/doc/Application"
                                },
                                "key": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
                            },
                            {
                                "uriValue": {
                                    "value": "http://data.iotics.com/public#allHosts"
                                },
                                "key": "http://data.iotics.com/public#hostAllowList"
                            },
                            {
                                "langLiteralValue": {
                                    "lang": "en",
                                    "value": "Agent " + name,
                                },
                                "key": "{ON_RDFS}#label"
                            },
                            {
                                "langLiteralValue": {
                                    "lang": "en",
                                    "value": "twin browser application '" + name + "' that demonstrates the EV ecosystem use cases"
                                },
                                "key": "{ON_RDFS}#comment"
                            },
                            {
                                "literalValue": {
                                    "value": "true"
                                },
                                "key": "http://demo.iotics.com/ont/demo/isDemoTwin"
                            },
                            {
                                "literalValue": {
                                    "value": name
                                },
                                "key": "http://schema.org/name"
                            }
                        ]
                    }
                }
            })
            console.log("browser follower updated: " + updated)
            return created
        },
        reason => console.error("failed to load the spec: " + reason)
    ).catch(function (error) {
        console.log("error when making twin " + error)
    });
}
