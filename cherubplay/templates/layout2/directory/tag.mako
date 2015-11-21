<%inherit file="base.mako" />\
<%block name="heading">Requests tagged "${tag.type.replace("_", " ")}:${tag.name.replace("_", " ")}"</%block>
    % if paginator.page_count!=1:
    <p class="pager tile">
    ${paginator.pager(format='~5~')}
    </p>
    % endif
    <ul id="chat_list">
      % for rq in requests:
      <li class="tile2 request">
        ${parent.render_request(rq)}
      </li>
      % endfor
    </ul>
    % if paginator.page_count!=1:
    <p class="pager tile">
    ${paginator.pager(format='~5~')}
    </p>
    % endif
