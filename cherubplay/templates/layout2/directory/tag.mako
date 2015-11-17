<%inherit file="base.mako" />\
<%block name="heading">Requests tagged "${tag.type.replace("_", " ")}:${tag.name.replace("_", " ")}"</%block>
    <ul id="chat_list">
      % for rq in requests:
      <li class="tile2 request">
        ${parent.render_request(rq)}
      </li>
      % endfor
    </ul>
