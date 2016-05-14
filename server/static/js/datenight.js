/*jshint esversion: 6 */
(function () {
"use strict";
window.onload = initialize;

var nick = null;

function initialize() {
  websock();

  document.body.onkeydown = function(event) {
    if (document.activeElement == document.body) {
      hotkeys(event);
    }
  };

  document.getElementById("help-toggle").onclick = function() {
    $('#help-screen').modal('toggle');
  };

  document.getElementById("clear").onclick = function() {
    document.getElementById("log").innerHTML = "";
    add_to_log("Log cleared...");
  };
}


function update_subscription_list(text) {
  let subscription_element = document.getElementById("subscribers_info");
  let content = "Connected subscribers: ";
  for (let e of text) {  // TODO: add to DOM in a sane way
    if (e == nick) {
      content += "<span class='red'>" + e + "</span>, ";
    } else {
      content += "<span>" + e + "</span>, ";
    }
  }
  subscription_element.innerHTML = content;
}


function update_nick(old_nick, new_nick) {
  nick = new_nick;
  if (old_nick)
    add_to_log('Your nick has been changed from "' + old_nick + '" to: "' + nick + '"');
  else
    add_to_log('Your nick has been set to: "' + nick + '"');
}


function websock() {
  const namespace = '/subscribe';
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

  socket.on('nick change', function(msg) {
    update_nick(msg.old, msg.new);
    update_subscription_list(msg.complete);
  });

  socket.on('update subscriptions', function(msg) {
    update_subscription_list(msg.complete);

    if (msg.old && msg.new) {
      add_to_log('"' + msg.old + '" has changed nick to "' + msg.new + '"');
    } else if (msg.new) {
      add_to_log('"' + msg.new + '" has joined.');
    } else if (msg.old) {
      add_to_log('"' + msg.old + '" has left.');
    } else {
      add_to_log('Error - Invalid data :(');
    }
  });

  socket.on('update publishers', function(msg) {
    let html_items = "<br/>";
    const data = msg.data;
    for (let x in data) {
      if (!data.hasOwnProperty(x)) {
        continue;
      }
      html_items += x + ": " + JSON.stringify(data[x]) + "<br/>";
    }

    if (msg.old && msg.new) {
      add_to_log('Publisher "' + msg.old + '" has changed nick to "' + msg.new + '"');
    } else if (msg.new) {
      add_to_log('Publisher "' + msg.new + '" has joined.');
    } else if (msg.old) {
      add_to_log('Publisher "' + msg.old + '" has left.');
    } else if (msg.update) {
      if (msg.show) {
        const relevant = msg.data[msg.update];
        add_to_log('Publisher "' + msg.update + '" updated state. (' + JSON.stringify(relevant) + ')');
      }
    } else {
      // got full data with no nick change, probably on initial connect
      add_to_log('Received complete publisher list.');
    }

    let publishers_element = document.getElementById("publishers_info");
    publishers_element.innerHTML = 'Connected publishers: ' + html_items;
  });

  document.getElementById("send-broadcast").onclick = function() {
    const content = document.getElementById("broadcast-data").value;
    if (!content)
      return false;

    if (content.startsWith('/help')) {
      socket.emit("help", null, function(msg) {
        document.getElementById("broadcast-data").value = "";
      });
    } else if (content.startsWith('/nick ')) {
      const new_nick = content.substring("/nick ".length);
      socket.emit("change nick", {new: new_nick}, function(msg) {
        document.getElementById("broadcast-data").value = "";
      });
    } else if (content.startsWith('/pause')) {
      socket.emit("pause", null, function(msg) {
        document.getElementById("broadcast-data").value = "";
      });
    } else {
      socket.emit('broadcast message', {data: content}, function(msg) {
        add_to_log('You: ' + msg);
        document.getElementById("broadcast-data").value = "";
      });
    }
    return false;
  };
}

function hotkeys(evt) {
  const key = evt.key.toLowerCase();
  // console.log(key);
  if (key == '?') {
    $('#help-screen').modal('toggle');
  } else if (key == 'escape') {
    $('#help-screen').modal('hide');
  }
}

}());  // end 'use strict'
