<!DOCTYPE html>
<html>
<head>
<title>CHERUBPLAY</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/static/cherubplay.css">
</head>
<body>

<header>
% if request.user:
  <nav>
    <p>${request.user.username}</p>
    <form action="${request.route_path("chat_list")}" method="get"><button type="submit">Your chats</button></form>
    <form action="${request.route_path("log_out")}" method="post"><button type="submit">Log out</button></form>
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
