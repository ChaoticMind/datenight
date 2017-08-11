/*jshint esversion: 6 */
function add_to_log(text, color) {
  'use strict';
  let log_element = document.getElementById("log");

  // handle timestamp
  const now = new Date();
  // const timestamp = now.toLocaleString('sv-SE');
  // const timestamp = now.getHours() + ':' + now.getMinutes() + ':' + now.getSeconds();
  const time_string = now.toTimeString();
  const timestamp = time_string.substr(0, time_string.indexOf(" "));


  let newElement = document.createElement("div");
  let ts_html = "<span class='timestamp'>" + timestamp + "</span> - ";
  newElement.innerHTML =  ts_html;


  // handle text
  let textSpan = document.createElement("span");
  textSpan.appendChild(document.createTextNode(text));
  if (color) {
    textSpan.style.color = color;
  }
  newElement.appendChild(textSpan);

  // prepend
  log_element.prepend(newElement);
}
