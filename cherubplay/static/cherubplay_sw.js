var port;

self.onmessage = function(e) {
    console.log(e);
    port = e.ports[0];
}

self.addEventListener("push", function(event) {
    event.waitUntil(fetch("/chats/notification/", {credentials: "same-origin"}).then(function(response) {
        return response.json();
    }).then(function(body) {
        if (body) {
            self.registration.showNotification(body.title, {
                body: body.handle + ": " + body.text,
                data: {url: "/chats/" + body.url},
            });
        }
    }));
});
