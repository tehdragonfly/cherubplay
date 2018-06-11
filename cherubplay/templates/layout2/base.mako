<% from cherubplay.services.redis import INewsStore %>
<% news_store = request.find_service(INewsStore) %>
<!DOCTYPE html>
<html>
<head>
<title><%block name="title"></%block>Cherubplay</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#393">
<link rel="stylesheet" href="/static/cherubplay2.css?32">
<link rel="shortcut icon" href="/static/favicon.ico">
<link rel="manifest" href="/static/manifest.json">
</head>
<body class="<%block name="body_class"></%block>">

<header>
  <h1><a href="${request.route_path("home")}"><img src="/static/logo.png" alt="CHERUBPLAY"></a></h1>
</header>

% if request.user:
  <nav id="nav">
    <ul>
      <li><a href="${request.route_path("home")}" id="nav_home">Home</a></li>
      <li><a href="${request.route_path("prompt_list")}" id="nav_prompt_list">Your prompts</a></li>
      <li><a href="${request.route_path("directory")}" id="nav_directory">Directory</a></li>
      <li><a href="${request.route_path("chat_list")}" id="nav_chat_list"\
% if request.unread_chats>0:
 data-unread="${request.unread_chats}">Your chats (${request.unread_chats} unread)\
% else:
>Your chats\
% endif
</a></li>
      <li><a href="${request.route_path("account")}" id="nav_account">${request.user.username}</a></li>
      <li><form action="${request.route_path("log_out")}" method="post"><button type="submit" id="nav_log_out">Log out</button></form></li>
    </ul>
  </nav>
    % if news_store.should_show_news(request.user):
    <% news = news_store.get_news() %>
    % if news:
      <aside id="news">
        News: ${news|n}
        <a href="#" id="news_hide">Hide</a>
      </aside>
    % endif
  % elif request.user.away_message:
    <aside id="news">
      Your account is marked as away. If you're back, remember to remove your away message in your <a href="${request.route_path("account")}">account settings</a>.
    </aside>
  % endif
% elif request.matched_route.name != "home":
  <nav id="nav">
    <ul>
      <li><a href="${request.route_path("home")}" id="nav_home">Sign up / Log in</a></li>
    </ul>
  </nav>
% endif

${next.body()}\

<script src="https://lurantis.scorpiaproductions.co.uk/js/jquery-2.0.3.min.js"></script>
<script src="/static/cherubplay.js?33"></script>
<%block name="scripts"></%block>

% if request.user and request.user.timezone is None:
<script src="https://lurantis.scorpiaproductions.co.uk/js/jstz-1.0.4.min.js"></script>
<script>
var timezone = jstz.determine().name();
if (timezone) {
	$.post("/account/timezone/", {"timezone": timezone});
}
</script>
% endif

</body>
</html>

