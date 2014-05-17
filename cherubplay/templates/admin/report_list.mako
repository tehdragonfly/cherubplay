<%inherit file="../base.mako" />\
  <h2>Prompt reports</h2>
% if len(reports)==0:
  <p>No reports. <a href="${request.route_path("home")}">Try shitposting until the users decide they're fed up with you</a>.</p>
% else:
% if paginator.page_count!=1:
  <p class="pager">
${paginator.pager(format='~5~')}
  </p>
% endif
  <ul id="chat_list">
% for report in reports:
    <li class="tile">
      <h3><a href="${request.route_path("admin_report", id=report.id)}">#${report.id}: ${report.reporting_user.username} reported ${report.reported_user.username}</a></h3>
      <p>Category: ${prompt_categories[report.category]}</p>
      <p style="color: #${report.colour};">Prompt: \
% if len(report.prompt)>250:
${report.prompt[:250]}...\
% else:
${report.prompt}\
% endif
</p>
      <p>Reason: ${report.reason}</p>
% if report.notes!="":
      <p>Notes: ${report.notes}</p>
% endif
    </li>
% endfor
  </ul>
% if paginator.page_count!=1:
  <p class="pager">
${paginator.pager(format='~5~')}
  </p>
% endif
% endif
