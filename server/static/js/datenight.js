/*jshint esversion: 6 */
(function () {
"use strict";
window.onload = initialize;


var nick = null;
var color = null;
var current_state = null;


function initialize() {
  update_state("Paused");
  websock();

  document.body.onkeydown = function(event) {
    if (document.activeElement == document.body) {
      hotkeys(event);
    }
  };

  document.getElementById("clear").onclick = function() {
    document.getElementById("log").innerHTML = "";
    add_to_log("Log cleared...");
  };
}


function update_subscription_list(text) {
  let subscription_element = document.getElementById("subscribers_info");
  subscription_element.innerHTML = "";
  for (let e in text) {
    if (subscription_element.innerHTML !== "") {
      subscription_element.appendChild(document.createTextNode(', '));
    } else {
      subscription_element.appendChild(document.createTextNode("Connected subscribers: "));
    }

    var newElement = document.createElement("span");
    if (e == nick) {
      newElement.className = 'own-nick fw-bold';
    }

    newElement.style.color = text[e].color;
    newElement.appendChild(document.createTextNode(e));
    subscription_element.appendChild(newElement);
  }
}


function update_nick(old_nick, new_nick, new_color) {
  nick = new_nick;
  color = new_color;
  if (old_nick)
    add_to_log('Your nick has been changed from "' + old_nick + '" to: "' + nick + '"');
  else
    add_to_log('Your nick has been set to: "' + nick + '"');
}


function update_state(new_state) {
  let btn_text = "Unknown state!";
  if (new_state == "Paused") {
    console.log("now Paused");
    btn_text = "Resume";
  } else if (new_state == "Playing") {
    console.log("now playing");
    btn_text = "Pause";
  } else {
    console.log("Invalid state received");
  }
  current_state = new_state;

  document.getElementById("current-state-btn").innerHTML = btn_text;

  // Can I make this into some sort of event listener tied to current_state?
  document.getElementById("current-state-text").innerHTML = current_state;
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

  socket.on('log_message', function(msg) {
    if (msg.nick)
      add_to_log(msg.nick + ': ' + msg.data, msg.color);
    else
      add_to_log(msg.data, msg.color);

    if (msg.fatal) {
      socket.close();
    }

    if (msg.state) {  // happens after a state is toggled
      update_state(msg.state);
    }
  });

  socket.on('nick change', function(msg) {
    update_nick(msg.old, msg.new, msg.color);
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

    if (msg.state) {  // happens on initial connnection
      update_state(msg.state);
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
    } else if (content.startsWith('/pause') || content.startsWith('/stop')) {
      socket.emit("pause", null, function(msg) {
        document.getElementById("broadcast-data").value = "";
      });
    } else if (content.startsWith('/resume') || content.startsWith('/play')) {
      socket.emit("resume", null, function(msg) {
        document.getElementById("broadcast-data").value = "";
      });
    } else if (content.startsWith('/seek ')) {
      const seek_dst = content.substring("/seek ".length);
      socket.emit("seek", {"seek": seek_dst}, function(msg) {
        document.getElementById("broadcast-data").value = "";
      });
    } else {
      socket.emit('broadcast message', {data: content}, function(msg) {
        add_to_log('You: ' + msg, color);
        document.getElementById("broadcast-data").value = "";
      });
    }
    return false;
  };

  document.getElementById("current-state-btn").onclick = function() {
    if (current_state == "Paused") {
      socket.emit("resume", null);
    } else if (current_state == "Playing") {
      socket.emit("pause", null);
    } else {
      console.log("Unknown state, no action taken...");
      return;
    }
  };
}

function hotkeys(evt) {
  const key = evt.key.toLowerCase();
  // console.log(key);
  if (key == '?') {
    new bootstrap.Modal(document.getElementById("help-screen")).show();
  }
}

}());  // end 'use strict'
