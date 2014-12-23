txopenbci = (function () {
    "use strict";
    var xport = {};
    var $eeg, $accel;
    var ACCEL_MAX = 0x7FFF;

    var handleSample = function handleSample(jsonmsg) {
        var counter, eeg, accel;
        var msg = $.parseJSON(jsonmsg.data);
        var hue, sat, lum;
        counter = msg[0];
        eeg = msg[1];
        accel = msg[2];

        $eeg.text(eeg);

        hue = Math.floor(accel[0] / 8192 * 180) % 360;
        sat = Math.floor(100 * (-accel[2] / ACCEL_MAX / 3) + 64);
        lum = Math.floor(100 * (accel[1] / ACCEL_MAX / 3) + 65);
        $accel.css('background',
                   'hsl(' + hue + ',' + sat + '%,' + lum + '%)');
    }

    var main = function main() {
        $eeg = $("#eeg");
        $accel = $("#accel");
        xport.source = new EventSource("stream");
        xport.source.addEventListener("sensorData", handleSample);
    }

    xport.main = main;
    return xport;
})();

jQuery(document).ready(txopenbci.main)
