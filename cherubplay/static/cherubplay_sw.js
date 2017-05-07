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
                data: {url: body.url},
            });
        }
    }));
});

self.addEventListener("notificationclick", function(event) {
    event.waitUntil(clients.matchAll({
        type: "window",
    }).then(function(client_list) {
        if (event.notification.data) {
            var path = "/chats/" + event.notification.data.url + "/";
        } else {
            var path = "/chats/";
        }
        for (var client of client_list) {
            if (client.url == location.origin + path && "focus" in client) {
                return client.focus();
            }
        }
        if (clients.openWindow) {
            return clients.openWindow(path);
        }
    }));
});

