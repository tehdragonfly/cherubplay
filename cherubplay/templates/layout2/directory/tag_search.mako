<%inherit file="base.mako" />\
<% from cherubplay.models import Tag %>
<%block name="heading">Search</%block>
    % if tags:
      <p>There are multiple tags called <strong>${tags[0].name}</strong>.</p>
      <section class="tile2">
        <ul class="tag_list">
          % for tag in tags:
            % if tag.synonym_of:
              <li>
                ${tag.type.replace("_", " ")}:${tag.name}
                (synonym of <a href="${request.route_path("directory_tag", tag_string=tag.synonym_of.tag_string)}">${tag.synonym_of.type.replace("_", " ")}:${tag.synonym_of.name}</a>)
              </li>
            % else:
              <li><a href="${request.route_path("directory_tag", tag_string=tag.tag_string)}">${tag.type.replace("_", " ")}:${tag.name}</a></li>
            % endif
          % endfor
        </ul>
      </section>
    % else:
      <p>No tags were found for this search.</p>
    % endif
