<%inherit file="base.mako" />\
<%block name="heading">Directory</%block>
    <ul id="chat_list">
      % for rq in requests:
      ${parent.render_request(rq)}
      % endfor
    </ul>
