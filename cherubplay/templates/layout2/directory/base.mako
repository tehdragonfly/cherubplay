<%inherit file="/layout2/base.mako" />\
<%def name="tag_li(tag)">\
<li${" class=\"trigger\"" if tag.tag.type == "trigger" else ""|n}>\
% if tag.tag.type == request.matchdict.get("type") and tag.tag.url_name == request.matchdict.get("name"):
${"TW: " if tag.tag.type == "trigger" else ""}${tag.alias}\
% else:
<a href="${request.route_path("directory_tag", type=tag.tag.type, name=tag.tag.url_name)}">${"TW: " if tag.tag.type == "trigger" else ""}${tag.alias}</a>\
% endif
</li>\
</%def>
<%def name="render_request(rq, expanded=False)">\
        % if rq.status != "posted":
        <div class="status">${rq.status.capitalize()}</div>
        % endif
        % if request.user.status == "admin":
        <p>User: <a href="${request.route_path("admin_user", username=rq.user.username)}">${rq.user.username}</a></p>
        % endif
        <% tags_by_type = rq.tags_by_type() %>
        <ul class="request_tags">
          % for tag in tags_by_type["maturity"]:
          ${tag_li(tag)}
          % endfor
          % for tag in tags_by_type["trigger"]:
          ${tag_li(tag)}
          % endfor
          % for tag in tags_by_type["type"]:
          ${tag_li(tag)}
          % endfor
        </ul>
        % if tags_by_type["character"] or tags_by_type["fandom"] or tags_by_type["gender"]:
        <h3>Playing:</h3>
        <ul class="request_tags">
          % for tag in tags_by_type["character"]:
          ${tag_li(tag)}
          % endfor
          % for tag in tags_by_type["fandom"]:
          ${tag_li(tag)}
          % endfor
          % for tag in tags_by_type["gender"]:
          ${tag_li(tag)}
          % endfor
        </ul>
        % endif
        % if tags_by_type["character_wanted"] or tags_by_type["fandom_wanted"] or tags_by_type["gender_wanted"]:
        <h3>Looking for:</h3>
        <ul class="request_tags">
          % for tag in tags_by_type["character_wanted"]:
          ${tag_li(tag)}
          % endfor
          % for tag in tags_by_type["fandom_wanted"]:
          ${tag_li(tag)}
          % endfor
          % for tag in tags_by_type["gender_wanted"]:
          ${tag_li(tag)}
          % endfor
        </ul>
        % endif
        % if tags_by_type["misc"]:
        <h3>Other tags:</h3>
        <ul class="request_tags">
          % for tag in tags_by_type["misc"]:
          ${tag_li(tag)}
          % endfor
        </ul>
        % endif
        % if rq.scenario:
        <hr>
        % if expanded or len(rq.scenario) <= 250:
        <p>${rq.scenario}</p>
        % else:
        <div class="expandable">
          <a class="toggle" href="${request.route_path("directory_request", id=rq.id)}">(more)</a>
          <p class="expanded_content" data-href="${request.route_path("directory_request_ext", ext="json", id=rq.id)}" data-type="request_scenario"></p>
          <p class="collapsed_content">${rq.scenario[:250]}...</p>
        </div>
        % endif
        % endif
        % if rq.prompt:
        <hr>
        % if expanded or len(rq.prompt) <= 250:
        <p style="color: #${rq.colour};">${rq.prompt}</p>
        % else:
        <div class="expandable">
          <a class="toggle" href="${request.route_path("directory_request", id=rq.id)}">(more)</a>
          <p class="expanded_content" style="color: #${rq.colour};" data-href="${request.route_path("directory_request_ext", ext="json", id=rq.id)}" data-type="request_prompt"></p>
          <p class="collapsed_content" style="color: #${rq.colour};">${rq.prompt[:250]}...</p>
        </div>
        % endif
        % endif
        % if request.matched_route.name != "directory_request_delete":
        <hr>
        <div class="actions">
          % if not expanded:
          <div class="left"><a href="${request.route_path("directory_request", id=rq.id)}">Permalink</a></div>
          % endif
          <div class="right">
            % if request.user.status == "admin":
            % if rq.status == "removed":
            <form action="${request.route_path("directory_request_unremove", id=rq.id)}" method="post"><button type="submit">Unremove</button></form> ·
            % else:
            <form action="${request.route_path("directory_request_remove", id=rq.id)}" method="post"><button type="submit">Remove</button></form> ·
            % endif
            % endif
            % if rq.user_id == request.user.id:
            <a href="${request.route_path("directory_request_edit", id=rq.id)}">Edit</a> ·
            <a href="${request.route_path("directory_request_delete", id=rq.id)}">Delete</a>
            % else:
            <form action="${request.route_path("directory_request_answer", id=rq.id)}" method="post"><button type="submit">Answer</button></form>
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
% if request.matched_route.name == "directory":
        <li>Directory</li>
% else:
        <li><a href="${request.route_path("directory")}">Directory</a></li>
% endif
% if request.user.status == "admin":
% if request.matched_route.name == "directory_tag_list":
        <li>Tag list</li>
% else:
        <li><a href="${request.route_path("directory_tag_list")}">Tag list</a></li>
% endif
% endif
% if request.matched_route.name == "directory_blacklist":
        <li>Blacklisted tags</li>
% else:
        <li><a href="${request.route_path("directory_blacklist")}">Blacklisted tags</a></li>
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
    </nav>
  </div>
  <div class="side_column">
  </div>
  <div id="content">
${next.body()}
  </div>
</main>
