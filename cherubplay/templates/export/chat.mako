<!DOCTYPE html>
<%
    import paginate
    paginator = paginate.Page(
        [],
        page=current_page,
        items_per_page=messages_per_page,
        item_count=message_count,
        url_maker=lambda page: "%s.html" % page,
    )
%>
<% from cherubplay.models.enums import ChatMode, MessageType %>\
<html>
<head>
<title>${chat_user.display_title}</title>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8">
</head>
<body>

<h1>${chat_user.display_title}</h1>

% if paginator.page_count > 1:
    <p class="pager tile2">
${paginator.pager(format='~5~')|n}
    </p>
% endif

<ul>
% for message in messages:
  <li id="message_${message.id}" class="message_${message.type.value}${" edited" if message.show_edited else ""}" style="color: #${message.colour};">
% if message.symbol is not None:
    <span class="symbol">${message.symbol_character}</span>
% endif
% if message.symbol is not None and message.type == MessageType.system:
    <p>${message.text % message.symbol_character}</p>
% else:
    <p>${message.text}</p>
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

</body>
</html>