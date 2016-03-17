<%inherit file="/layout2/base.mako" />\
<%block name="title">Tags - </%block>
<% from cherubplay.models import Tag %>
<h2>Tags</h2>
<main>
  <table class="tile2" width="100%">
    <thead>
      <tr>
        % for tag_type in Tag.type.type.enums:
        <th>${tag_type.replace("_", " ").capitalize()}</th>
        % endfor
      </tr>
    </thead>
    <tbody>
      % for row in rows:
      <tr>
        % for tag_type in Tag.type.type.enums:
        % if tag_type in row:
        <td class="\
% if row[tag_type].synonym_id is not None:
synonym\
% endif
">
          <a href="${request.route_path("directory_tag", type=row[tag_type].type, name=row[tag_type].url_name)}">${row[tag_type].name}</a>
        </td>
        % else:
        <td></td>
        % endif
        % endfor
      </tr>
      % endfor
    </tbody>
  </table>
</main>
