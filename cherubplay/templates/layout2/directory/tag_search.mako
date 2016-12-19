<%inherit file="base.mako" />\
<% from cherubplay.models import Tag %>
<%block name="heading">Search</%block>
    % if tags:
      <p>There are multiple tags called <strong>${tags[0].name}</strong>.</p>
      <section class="tile2">
        <ul class="tag_list">
          % for tag in tags:
            <li><a href="${request.route_path("directory_tag", type=tag.type, name=tag.url_name)}">${tag.type.replace("_", " ")}:${tag.name}</a></li>
          % endfor
        </ul>
      </section>
    % else:
      <p>No tags were found for this search.</p>
    % endif
