<%inherit file="/layout2/base.mako" />\
<%! from cherubplay.models.enums import TagType %>
<%def name="tag_li(tag)">\
<li${" class=\"warning\"" if tag.type == TagType.warning else ""|n}>\
% if request.matched_route.name == "directory_tag" and len(request.context.tags) == 1 and request.context.tags[0] == tag:
${tag.name}\
% else:
<a href="${request.route_path("directory_tag", tag_string=tag.tag_string)}" draggable="true" data-tag-type="${tag.type.value}" data-tag-name="${tag.url_name}">${tag.name}</a>\
% endif
</li>\
</%def>
<%def name="render_request(rq, answered=False, expanded=False)">\
        % if rq.status not in ("posted", "locked"):
        <div class="status">${rq.status.capitalize()}</div>
        % endif
        % if request.has_permission("admin"):
          <p>\
            User: ${rq.user.username} \
            (<a href="${request.route_path("directory_user", username=rq.user.username)}">requests</a>, \
            <a href="${request.route_path("admin_user", username=rq.user.username)}">admin page</a>)
          </p>
        % endif
        <% tags_by_type = rq.tags_by_type() %>
        <ul class="request_tags">
          % for tag in tags_by_type[TagType.maturity]:
          ${tag_li(tag)}
          % endfor
          % for tag in tags_by_type[TagType.warning]:
          ${tag_li(tag)}
          % endfor
          % for tag in tags_by_type[TagType.type]:
          ${tag_li(tag)}
          % endfor
        </ul>
        % if tags_by_type[TagType.fandom] or tags_by_type[TagType.character] or tags_by_type[TagType.gender]:
        <h3>Playing:</h3>
        <ul class="request_tags">
          % for tag in tags_by_type[TagType.fandom]:
          ${tag_li(tag)}
          % endfor
          % for tag in tags_by_type[TagType.character]:
          ${tag_li(tag)}
          % endfor
          % for tag in tags_by_type[TagType.gender]:
          ${tag_li(tag)}
          % endfor
        </ul>
        % endif
        % if tags_by_type[TagType.fandom_wanted] or tags_by_type[TagType.character_wanted] or tags_by_type[TagType.gender_wanted]:
        <h3>Looking for:</h3>
        <ul class="request_tags">
          % for tag in tags_by_type[TagType.fandom_wanted]:
          ${tag_li(tag)}
          % endfor
          % for tag in tags_by_type[TagType.character_wanted]:
          ${tag_li(tag)}
          % endfor
          % for tag in tags_by_type[TagType.gender_wanted]:
          ${tag_li(tag)}
          % endfor
        </ul>
        % endif
        % if tags_by_type[TagType.misc]:
        <h3>Other tags:</h3>
        <ul class="request_tags">
          % for tag in tags_by_type[TagType.misc]:
          ${tag_li(tag)}
          % endfor
        </ul>
        % endif
        % if rq.ooc_notes:
        <hr>
        % if expanded or len(rq.ooc_notes) <= 250:
        <p>${rq.ooc_notes}</p>
        % else:
        <div class="expandable">
          <a class="toggle" href="${request.route_path("directory_request", id=rq.id)}">(more)</a>
          <p class="expanded_content" data-href="${request.route_path("directory_request_ext", ext="json", id=rq.id)}" data-type="request_ooc_notes"></p>
          <p class="collapsed_content">${rq.ooc_notes[:250]}...</p>
        </div>
        % endif
        % endif
        % if rq.starter:
        <hr>
        % if expanded or len(rq.starter) <= 250:
        <p style="color: #${rq.colour};">${rq.starter}</p>
        % else:
        <div class="expandable">
          <a class="toggle" href="${request.route_path("directory_request", id=rq.id)}">(more)</a>
          <p class="expanded_content" style="color: #${rq.colour};" data-href="${request.route_path("directory_request_ext", ext="json", id=rq.id)}" data-type="request_starter"></p>
          <p class="collapsed_content" style="color: #${rq.colour};">${rq.starter[:250]}...</p>
        </div>
        % endif
        % endif
        % if request.matched_route.name != "directory_request_delete":
        <hr>
        % if rq.slots:
          <% has_any_slot = rq.slots.by_user(request.user) is not None %>
          % for slot in rq.slots:
            <label class="slot${slot.order}">
              Slot ${slot.order}
              % if slot.user_id == request.user.id:
                - taken by you
              % elif slot.taken:
                - taken by ${slot.user_name}
              % endif
            </label>

            % if request.user.id != rq.user_id and slot.user_id == request.user.id:
              <form class="slot_unanswer" action="${request.route_path("directory_request_unanswer", id=rq.id)}" method="post">
                <p class="slot_description ${"taken" if slot.taken else ""}">
                  ${slot.description}
                  <button type="submit">Unanswer</button>
                </p>
              </form>
            % elif request.user.id == rq.user_id and slot.taken and slot.user_id != request.user.id:
              <form class="slot_unanswer" action="${request.route_path("directory_request_kick", id=rq.id)}" method="post">
                <input type="hidden" name="slot" value="${slot.order}">
                <p class="slot_description taken">
                  ${slot.description}
                  <button type="submit">Kick</button>
                </p>
              </form>
            % else:
              <p class="slot_description ${"taken" if slot.taken else ""}">
                ${slot.description}
                % if rq.status == "locked":
                  <span class="status">Locked</span>
                % elif not has_any_slot and not slot.taken and not answered:
                  <a href="${request.route_path("directory_request_answer", id=rq.id, _query={"slot": slot.order})}">Answer</a>
                % endif
              </p>
            % endif

            <hr>
          % endfor
        % endif
        <div class="actions">
          % if not expanded:
          <div class="left"><a href="${request.route_path("directory_request", id=rq.id)}">${request.user.localise_time(rq.posted or rq.created).strftime("%Y-%m-%d %H:%M")}</a></div>
          % else:
          <div class="left">${request.user.localise_time(rq.posted or rq.created).strftime("%Y-%m-%d %H:%M")}</div>
          % endif
          <div class="right">
            % if request.has_permission("admin") or request.has_permission("request.remove"):
              % if rq.status == "removed":
                <form action="${request.route_path("directory_request_unremove", id=rq.id)}" method="post"><button type="submit">Unremove</button></form> ·
              % else:
                <form action="${request.route_path("directory_request_remove", id=rq.id)}" method="post"><button type="submit">Remove</button></form> ·
              % endif
            % endif
            % if rq.user_id == request.user.id:
              <a href="${request.route_path("directory_request_edit", id=rq.id)}">Edit</a>
              · <a href="${request.route_path("directory_request_delete", id=rq.id)}">Delete</a>
              % if rq.status == "locked":
                · <span class="status">Locked</span>
              % endif
            % else:
              <a href="https://www.tumblr.com/submit_form/cherubplay.tumblr.com/link?post[one]=Report&amp;post[two]=${request.route_url("directory_request", id=rq.id)}" target="_blank">Report</a>
              % if rq.status == "locked":
                · <span class="status">Locked</span>
              % elif answered:
                · Answered
              % elif not rq.slots:
                · <form action="${request.route_path("directory_request_answer", id=rq.id)}" method="post"><button type="submit">Answer</button></form>
              % endif
            % endif
          </div>
        </div>
        % endif
</%def>
<%block name="title">${next.heading()} - </%block>
<%block name="body_class">layout2</%block>
<h2><%block name="heading"></%block></h2>
<main class="flex">
  <div class="side_column">
    <nav>
      <ul>
        % if request.matched_route.name == "directory" and not "before" in request.GET:
          <li>Directory</li>
        % else:
          <li><a href="${request.route_path("directory")}">Directory</a></li>
        % endif
        % if request.matched_route.name == "directory_blacklist":
          <li id="blacklist_link">Blacklisted tags</li>
        % else:
          <li id="blacklist_link"><a href="${request.route_path("directory_blacklist")}">Blacklisted tags</a></li>
        % endif
        % if request.matched_route.name == "directory_yours":
          <li>Your requests</li>
        % else:
          <li><a href="${request.route_path("directory_yours")}">Your requests</a></li>
        % endif
        % if request.matched_route.name == "directory_new":
          <li>New request</li>
        % else:
          <li><a href="${request.route_path("directory_new")}">New request</a></li>
        % endif
      </ul>
      <h3>Lucky dip</h3>
      <ul>
        <li><a href="${request.route_path("directory_random")}">Find a random request</a></li>
      </ul>
      % if request.has_permission("directory.manage_tags"):
      <h3>Tags</h3>
      <ul>
        % if request.matched_route.name == "directory_tag_list":
          <li>All tags</li>
        % else:
          <li><a href="${request.route_path("directory_tag_list")}">All tags</a></li>
        % endif
        % if request.matched_route.name == "directory_tag_list_unapproved":
          <li>Unapproved tags</li>
        % else:
          <li><a href="${request.route_path("directory_tag_list_unapproved")}">Unapproved tags</a></li>
        % endif
        % if request.matched_route.name == "directory_tag_list_blacklist_default":
          <li>Blacklist default tags</li>
        % else:
          <li><a href="${request.route_path("directory_tag_list_blacklist_default")}">Blacklist default tags</a></li>
        % endif
        <li><a href="${request.route_path("directory_tag_table")}">Table</a></li>
      </ul>
      % endif
    </nav>
  </div>
  <div class="side_column">
    <nav>
      % if request.matched_route.name == "directory_tag":
        <h3>New search</h3>
      % else:
        <h3>Search</h3>
      % endif
      <form class="directory_search_form" action="${request.route_path("directory_search")}" method="get" data-autocomplete-path="${request.route_path("directory_search_autocomplete")}">
        <div class="tag_input single">
          <input type="text" class="directory_search full" name="name" maxlength="100" placeholder="Look up a tag..." required>
        </div>
        <button>Search</button>
      </form>
      <%block name="tag_links"></%block>
    </nav>
  </div>
  <div id="content">
${next.body()}
  </div>
</main>
<%block name="scripts">
<script>cherubplay.directory();</script>
</%block>
