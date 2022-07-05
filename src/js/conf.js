var conf = {
    "publisher": {
        "endpoint": "demo.iotics.space",
        "agentName": "streaming-analytics",
        "bgcolor": "#EEF7FF"
    },
    "services": {
        "endpoint": "demo2.iotics.space",
        "agentName": "consumer-app",
        "bgcolor": "#FFFFEE"
    }
}


function initConfig() {
    var req = new XMLHttpRequest();
    req.overrideMimeType("application/json");
    req.open('GET', 'conf.json', false);
    req.onload = function () {
        if (req.status !== 200) {
            return;
        }
        conf = { ...conf, ...JSON.parse(req.responseText) };
    }
    req.send(null);
    console.info("config loaded:\n" + JSON.stringify(conf))
}


var GetConf = function (id) {
    v = conf[id]
    v["wss"] = "wss://" + v["endpoint"] + "/ws"
    v["qapi"] = "https://" + v["endpoint"] + "/qapi"
    return v
}
