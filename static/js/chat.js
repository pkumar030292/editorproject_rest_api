const chatWS = new WebSocket(`ws://${window.location.host}/chat/ws`);
const messagesDiv = document.getElementById("messages");
const chatInput = document.getElementById("chatInput");

chatWS.onmessage = (event) => {
  const msg = document.createElement("div");
  msg.textContent = event.data;
  messagesDiv.appendChild(msg);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
};

function sendChat() {
  if (chatInput.value.trim() !== "") {
    chatWS.send(chatInput.value);
    chatInput.value = "";
  }
}
