<!DOCTYPE html>
<%
    import paginate
    from cherubplay.models.enums import ChatMode, MessageType
    paginator = paginate.Page(
        [],
        page=current_page,
        items_per_page=messages_per_page,
        item_count=message_count,
        url_maker=lambda page: "%s.html" % page,
    )
%>\
<html>
<head>
<title>${chat_user.display_title} - Cherubplay</title>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#393">
<link rel="stylesheet" href="cherubplay2.css">
</head>
<body class="layout2">

<header>
  <h1><img src="logo.png" alt="CHERUBPLAY"></h1>
</header>

<h2>${chat_user.display_title}</h2>

<main class="flex">
  <div class="side_column"></div>
  <div class="side_column"></div>
  <div id="content">
    % if paginator.page_count > 1:
      <p class="pager tile2">
        ${paginator.pager(format='~5~')|n}
      </p>
    % endif
    <ul id="messages" class="tile2">
      % for message in messages:
        <li id="message_${message.id}" class="message_${message.type.value}${" edited" if message.show_edited else ""}" style="color: #${message.colour};">
          % if message.symbol is not None:
            <span class="symbol">${message.symbol_character}</span>
          % endif
          % if message.symbol is not None and message.type == MessageType.system:
            <p>${message.text % message.symbol_character}</p>
          % else:
            <p>${message.formatter.as_html()}</p>
          % endif
          <div class="timestamp">
            % if chat.mode == ChatMode.group and message.handle:
              ${message.handle} ·
            % endif
            ${message.posted.strftime("%Y-%m-%d %H:%M:%S")}
          </div>
        </li>
      % endfor
    </ul>
    % if paginator.page_count > 1:
      <p class="pager tile2">
        ${paginator.pager(format='~5~')|n}
      </p>
    % endif
  </div>
</main>

</body>
</html>