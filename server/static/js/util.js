/*jshint esversion: 6 */
function add_to_log(text) {
  'use strict';
  let log_element = document.getElementById("log");

  const now = new Date();
  // const timestamp = now.toLocaleString('sv-SE');
  // const timestamp = now.getHours() + ':' + now.getMinutes() + ':' + now.getSeconds();
  const time_string = now.toTimeString();
  const timestamp = time_string.substr(0, time_string.indexOf(" "));


  // prepend
  log_element.innerText = ("\n" + timestamp + " - " + text) + log_element.innerText;
  // or append
  // log_element.innerText += ("\n" + timestamp + " - " + text);

  // o.O -- couldn't get it to work without innerText :/
  // log_element.innerHTML = log_element.innerHTML.replace(/\r\n/g, '<br/>');
}
