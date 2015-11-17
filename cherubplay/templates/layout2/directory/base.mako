<%inherit file="/layout2/base.mako" />\
<%def name="tag_li(tag)">\
<li${" class=\"trigger\"" if tag["type"] == "trigger" else ""|n}>\
% if tag["type"] == request.matchdict.get("type") and tag["name"] == request.matchdict.get("name"):
${tag["alias"]}\
% else:
<a href="${request.route_path("directory_tag", type=tag["type"], name=tag["name"])}">${tag["alias"]}</a>\
% endif
</li>\
</%def>
<%def name="render_request(rq, expanded=False)">\
        <% tags_by_type = rq.tags_by_type() %>
        <ul class="tag_list">
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
        <ul class="tag_list">
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
        <ul class="tag_list">
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
        <ul class="tag_list">
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
        <p>${rq.scenario[:247]}... <a href="${request.route_path("directory_request", id=rq.id)}">(more)</a></p>
        % endif
        % endif
        % if rq.prompt:
        <hr>
        % if expanded or len(rq.prompt) <= 250:
        <p style="color: #${rq.colour};">${rq.prompt}</p>
        % else:
        <p style="color: #${rq.colour};">${rq.prompt[:247]}... <a href="${request.route_path("directory_request", id=rq.id)}">(more)</a></p>
        % endif
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
