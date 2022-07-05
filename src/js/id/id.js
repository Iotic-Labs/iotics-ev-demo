var resolver

const go = new Go();

var fields = ["userName", "agentName", "userSeed", "agentSeed"];

var userSeed = "", agentSeed = "";
var userName = "", agentName = "";
var userDiD = "", agentDiD = "";


let mod, inst;
let userKeyID, agentKeyID;

let jwtToken = ""
let jwtTokenRefresher = null
let delegationResultText = "unverified"

WebAssembly.instantiateStreaming(
    fetch("id/id-sdk.wasm?ts=" + Date.now()),
    go.importObject
).then(async (result) => {
    mod = result.module;
    inst = result.instance;
    await go.run(inst);
});


function getDocument(did) {
    return new Promise((resolve, reject) => {
        fetch(resolver + "/1.0/discover/" + encodeURI(did), {
            method: 'GET',
            mode: 'cors',
        }).then(response => {
            if (response.status === 200) {
                return resolve(response.json());
            } else {
                return reject(response.status, response.statusText);
            }
        });
    });
}

function registerToken(token) {
    return new Promise((resolve, reject) => {
        fetch(resolver + "/1.0/register", {
            method: 'POST',
            mode: 'cors',
            headers: {
                'Content-Type': 'text/plain'
            },
            body: token
        }).then(response => {
            if (response.status === 200) {
                return resolve(response.json());
            } else {
                return reject(response.status, response.json());
            }
        });
    });
}


function jwtFactory(timeout) {
    if (jwtTokenRefresher != null) {
        clearInterval(jwtTokenRefresher);
    }
    jwtTokenRefresher = setInterval(function () {
        jwtTokenString = NewAuthenticationToken(
            agentKeyID, agentName, agentDiD,
            userDiD, "http://audience", timeout)
        jwtTokenJSON = JSON.parse(jwtTokenString)
        if (typeof jwtTokenJSON.error !== "undefined") {
            jwtToken = jwtTokenJSON.error
        } else {
            jwtToken = jwtTokenJSON.token
        }
        console.log("made new token: '" + jwtToken + "'")
    }, timeout - 1)
}

function delegate() {
    // === user doc and registration

    const initUserDocPromise = new Promise((resolve, reject) => {
        userKeyID = NewPrivateKeyECDSAFromPathString(userSeed, "user", userName);
        console.log("user key ID: " + userKeyID);
        var userDocString = NewDIDDocument("user", userKeyID);
        userDoc = JSON.parse(userDocString)
        userDiD = userDoc.id
        console.log("userDocString: =====================")
        console.log(userDocString)
        getDocument(userDoc.id).then(userDocToken => {
            doc = VerifyDocument(userDocToken.token, false)
            resolve(doc)
        }).catch((err, message) => {
            var userDocToken = NewDocumentToken(resolver, userDocString, userKeyID);
            registerToken(userDocToken).then(regResult => {
                resolve(userDoc)
            }).catch((code, message) => {
                reject(message)
            })
        })
    })


    const initAgentDocPromise = new Promise((resolve, reject) => {
        agentKeyID = NewPrivateKeyECDSAFromPathString(agentSeed, "agent", agentName);
        console.log("agent key ID: " + agentKeyID);
        var agDocString = NewDIDDocument("agent", agentKeyID);
        agentDoc = JSON.parse(agDocString)
        agentDiD = agentDoc.id
        console.log("agDocString: =====================")
        console.log(agDocString)
        getDocument(agentDoc.id).then(agentDocToken => {
            console.log(agentDocToken)
            doc = VerifyDocument(agentDocToken.token, true)
            resolve(doc)
        }).catch((err, message) => {
            var agDocToken = NewDocumentToken(resolver, agDocString, agentKeyID);
            registerToken(agDocToken).then(regResult => {
                resolve(agentDoc)
            }).catch((code, message) => {
                reject(message)
            })
        })
    })

    return Promise.all([initUserDocPromise, initAgentDocPromise]).then((values) => {
        console.log(values);
        userDocString = values[0]
        agentDocString = values[1]

        result = NewAuthenticationDelegationToken(resolver, userKeyID, userDocString, agentKeyID, agentDocString)
        updatedTokenWithFlag = JSON.parse(result)
        if (typeof updatedTokenWithFlag.error !== "undefined") {
            delegationResultText = updatedTokenWithFlag.error
        } else {
            if (updatedTokenWithFlag.updated) {
                console.log("result: " + result)
                registerToken(updatedTokenWithFlag.token).then(regResult => {
                    text = `[OK]: <pre>${JSON.stringify(regResult)}</pre>`
                    delegationResultText = text
                }).catch((code, message) => {
                    text = `[${code}]: ${message}`
                    doc = VerifyDocument(updatedTokenWithFlag.token, false)
                    delegationResultText = `${text} <pre>${JSON.stringify(JSON.parse(doc), null, "    ")}</pre>`
                })
            } else {
                delegationResultText = "already delegated"
            }
        }
    }).catch((error) =>
        delegationResultText = "delegation error: " + error
    );
}

function initSeeds() {
    var seedInit = function (type) {
        var seed = "";
        seedString = MakeNewSeed();
        seedJson = JSON.parse(seedString);
        seed = seedJson.seed;
        $("#" + type + "Mnemonics").html(
            "<b>" + seedJson["mnemonics"] + "</b>"
        );
        $("#" + type + "Seed").val(seed);
        return seed;
    };
    seedInit("user");
    seedInit("agent");
    init();
}


