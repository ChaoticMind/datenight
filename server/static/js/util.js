/*jshint esversion: 6 */
function add_to_log(text) {
  'use strict';
  let log_element = document.getElementById("log");

  const now = new Date();
  // const timestamp = now.toLocaleString('sv-SE');
  // const timestamp = now.getHours() + ':' + now.getMinutes() + ':' + now.getSeconds();
  const time_string = now.toTimeString();
  const timestamp = time_string.substr(0, time_string.indexOf(" "));

  log_element.innerHTML += ("<br/>" + timestamp + " - " + text);
}
