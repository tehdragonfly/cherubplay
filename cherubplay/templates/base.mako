<!DOCTYPE html>
<html>
<head>
<title>CHERUBPLAY</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/static/cherubplay.css?4">
</head>
<body>
<header>
% if request.user:
  <nav>
    <p>${request.user.username}</p>
    <a href="${request.route_path("chat_list")}">Your chats\
% if request.unread_chats>0:
 (${request.unread_chats} unread)\
% endif
</a>
    <form action="${request.route_path("log_out")}" method="post"><button type="submit">Log out</button></form>
  </nav>
% elif request.matched_route.name!="home":
  <nav>
    <p><a href="${request.route_path("home")}">Sign up / Log in</a></p>
  </nav>
% endif
  <h1><a href="${request.route_path("home")}"><img src="/static/logo.png" alt="CHERUBPLAY"></a></h1>
  <br class="clear">
</header>

<main>
${next.body()}\
</main>

</body>
</html>
