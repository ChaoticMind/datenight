/*jshint esversion: 6 */
(function () {
'use strict';
window.onload = initialize;

function initialize() {
  websock();

  document.getElementById("clear").onclick = function() {
    document.getElementById("log").innerHTML = "";
    add_to_log("Log cleared...");
  };
}

function websock() {
  const namespace = '/publish';
  const protocol = window.location.protocol;
  let socket = io.connect(protocol + '//' + document.domain + ':' + location.port + namespace);

  socket.on('connect', function() {
    add_to_log("Connected...");
  });

  socket.on('disconnect', function() {
    add_to_log("Disconnected...");
  });

  socket.on('error', function(x) {
    add_to_log("Socket error: " + x);
  });

  socket.on('log message', function(msg) {
    if (msg.nick)
      add_to_log(msg.nick + ': ' + msg.data);
    else
      add_to_log(msg.data);

    if (msg.fatal) {
      socket.close();
    }
  });

  socket.on('pause', function(msg) {
    add_to_log("Pause requested");
  });

  socket.on('resume', function(msg) {
    add_to_log("Resume requested");
  });

  socket.on('seek', function(msg) {
    add_to_log("Seek requested to " + msg.seek);
  });

  socket.on('latency_ping', function(msg) {
    socket.emit('latency_pong', {'token': msg.token});
  });

  document.getElementById("send-state").onclick = function() {
    const max = 5*60;
    const pos = Math.floor(Math.random() * (max + 1));
    const full_position = pos + '/' + max;
    socket.emit('update state', {'status': 'playing', position: full_position, 'title': "some_title", "show": true}, function() {
      add_to_log("Successfully sent state update...");
    });
  };

  document.getElementById("disconnect").onclick = function() {
    socket.emit('disconnect request');
    // socket.close();
    return false;
  };
}

}());  // end 'use strict'