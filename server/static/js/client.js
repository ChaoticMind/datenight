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
    socket.emit('set ua', {'user_agent': "web_client_test"});
    socket.emit('update state', {
      "title": "",
      "position": "",
      "status": "Stopped",
    });
  });

  socket.on('disconnect', function() {
    add_to_log("Disconnected...");
  });

  socket.on('error', function(x) {
    add_to_log("Socket error: " + x);
  });

  socket.on('log_message', function(msg) {
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
    socket.emit('update state', {
      "title": "",
      "position": "",
      "status": "Paused",
    });
  });

  socket.on('resume', function(msg) {
    add_to_log("Resume requested");
    socket.emit('update state', {
      "title": "",
      "position": "",
      "status": "Playing",
    });
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
    socket.emit('update state', {
        'title': "some_title",
        'status': 'Playing',
        position: full_position,
        "show": true,
      }, function() {
        add_to_log("Successfully sent state update...");
      }
    );
  };

  document.getElementById("disconnect").onclick = function() {
    socket.emit('disconnect request');
    // socket.close();
    return false;
  };
}

}());  // end 'use strict'
