var port;

self.onmessage = function(e) {
    console.log(e);
    port = e.ports[0];
}

self.addEventListener("push", function(event) {
    event.waitUntil(fetch("/chats/notification/").then(function(response) {
        event.waitUntil(response.json().then(function(body) {
            self.registration.showNotification("Cherubplay", {
                body: body,
            });
        }));
    }));
});
