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
            var options = {
                body: body.handle + ": " + body.text,
                data: {url: body.url},
                icon: "/static/icon-128.png",
            }

            if ("actions" in Notification.prototype) {
                if (Notification.maxActions == 2) {
                    options.actions = [
                        {action: "chat", title: "Chat"},
                        {action: "info", title: "Info"},
                    ]
                } else if (Notification.maxActions >= 3) {
                    options.actions = [
                        {action: "chat",    title: "Chat"},
                        {action: "archive", title: "Archive"},
                        {action: "info",    title: "Info"},
                    ]
                }
            }

            self.registration.showNotification(body.title, options);
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
        if (event.action && event.action == "archive") {
            path += "?page=1";
        } else if (event.action && event.action == "info") {
            path += "info/";
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

