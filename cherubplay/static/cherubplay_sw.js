var port;

self.onmessage = function(e) {
  console.log(e);
  port = e.ports[0];
}

self.addEventListener("push", function(event) {
  event.waitUntil(self.registration.showNotification("Cherubplay", {
    body: "insert message text here...",
  }));
});
