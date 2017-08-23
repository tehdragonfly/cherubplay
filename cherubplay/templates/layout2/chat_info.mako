<%inherit file="chat_base.mako" />\
<% from cherubplay.models.enums import ChatUserStatus %>
<%block name="title">Info - ${own_chat_user.title or chat.url} - </%block>
% if request.GET.get("saved") == "end":
  <p>This chat has now been ended.</p>
% elif request.GET.get("saved") == "info":
  <p>Your changes have been saved.</p>
% else:
  <p>Here, you can write a title and notes for this chat to help you organise it. The information you post here is for your reference only and is not visible to anyone else.</p>
% endif
  <form class="tile2" action="${request.route_path("chat_info", url=request.matchdict["url"])}" method="post">
    <h3><input type="text" id="chat_notes_title" class="full" name="title" placeholder="Title..." value="${own_chat_user.title}" maxlength="100"></h3>
    <p><textarea id="chat_notes_notes" name="notes" placeholder="Notes..." rows="5">${own_chat_user.notes}</textarea></p>
    <p><input type="text" id="chat_notes_labels" class="full" name="labels" placeholder="Labels..." value="${", ".join(_.replace("_", " ") for _ in own_chat_user.labels)}" maxlength="500"></textarea></p>
    <div class="actions">
      <div class="right">
        <button type="submit">Save</button>
      </div>
    </div>
  </form>
% if request.context.chat.status == "ongoing" and request.context.mode == "group":
  <section class="tile2">
    <h3>Dramatis personae</h3>
    <ul class="tag_list">
      % for user_id, chat_user in request.context.chat_users.items():
        <li style="color: #${chat_user.last_colour}">
          % if chat_user.user_id == request.user.id:
            % if request.GET.get("error") == "name_taken":
              <p class="error">Someone else has already chosen that name. Please choose another.</p>
            % endif
            <form action="${request.route_path("chat_change_name", url=request.context.chat.url)}" method="post">
              <div style="float: right;">
                <button type="submit">Save</button>
              </div>
              <div style="overflow: hidden;">
                <input type="text" name="name" value="${chat_user.name}" class="full" maxlength="50" required placeholder="Your handle...">
              </div>
            </form>
          % elif chat_user.status == ChatUserStatus.deleted:
            <del>${chat_user.name}</del>
          % elif request.context.first_message and request.context.first_message.user_id == request.user.id:
            <form action="${request.route_path("chat_remove_user", url=request.context.chat.url)}" method="post">
              <input type="hidden" name="name" value="${chat_user.name}">
              <div class="actions">
                <div class="left">
                  ${chat_user.name}
                  % if chat_user in request.context.banned_chat_users:
                    (${"temporarily" if chat_user.user.unban_date else "permanently"} banned)
                  % elif chat_user.user.away_message:
                    <p>${chat_user.handle} has marked their account as away. They left this message:

${chat_user.user.away_message}</p>
                  % endif
                </div>
                <div class="right"><button type="submit">Remove</button></div>
              </div>
            </form>
          % else:
            ${chat_user.name}
          % endif
        </li>
      % endfor
    </ul>
  </section>
% endif
% if chat.status == "ongoing" and len(request.context.active_chat_users) > 2:
  <section class="tile2 danger">
    <h3>Leave chat</h3>
    <p>If you leave this chat it will no longer appear on your chats page and you won't be able to take part in it, but the other participants will be able to continue.</p>
    <p>Leaving a chat is irreversible and cannot be undone, so please do not do this unless you're absolutely sure you're done with this chat.</p>
    <p class="middle_actions"><a href="${request.route_path("chat_leave", url=request.matchdict["url"])}">Leave chat</a></p>
  </section>
% elif chat.status == "ongoing":
  <section class="tile2 danger">
    <h3>End or delete chat</h3>
    <p>Ending a chat prevents any further messages from being sent, and deleting it also deletes it from the your chats page. These actions are both irreversible and cannot be undone, so please do not do them unless you're absolutely sure you're done with this chat.</p>
    <p class="middle_actions"><a href="${request.route_path("chat_end", url=request.matchdict["url"])}">End chat</a> · <a href="${request.route_path("chat_delete", url=request.matchdict["url"])}">Delete chat</a></p>
  </section>
% else:
  <section class="tile2 danger">
    <h3>Delete chat</h3>
    <p>Deleting a chat is irreversible and cannot be undone, so please do not do this unless you're absolutely sure you're done with this chat.</p>
    <p class="middle_actions"><a href="${request.route_path("chat_delete", url=request.matchdict["url"])}">Delete chat</a></p>
  </section>
% endif
  <p><a href="${request.route_path("chat_list")}">Back to your chats</a></p>
